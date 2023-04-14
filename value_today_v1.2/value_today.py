import datetime
import re
import math
import pycountry
import json

from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://www.value.today"
    NICK_NAME = base_url.split("//")[-1]
    fields = ["overview", "officership", "Financial_Information"]
    overview = {}
    tree = None
    api = None

    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9;application/json;application/json;odata=verbose",
        "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }

    def getpages(self, searchquery):
        result = []
        link_1 = "https://www.value.today/"
        self.get_working_tree_api(link_1, "tree")
        link_2 = "https://www.value.today/views/ajax?_wrapper_format=drupal_ajax"
        link_new = f"https://www.value.today/?title={searchquery}&field_company_category_primary_target_id=&field_headquarters_of_company_target_id=All&field_company_website_uri=&field_market_value_jan072022_value="

        self.get_working_tree_api(link_new, "tree")

        result = self.get_by_xpath("//h2/a/@href")
        result = [self.base_url + i for i in result]

        return result

    def get_by_xpath(self, xpath):
        try:
            el = self.tree.xpath(xpath)
        except Exception as e:
            print(e)
            return None
        if el:
            if type(el) == str or type(el) == list:
                el = [i.strip() for i in el]
                el = [i for i in el if i != ""]
            if len(el) > 1 and type(el) == list:
                el = list(dict.fromkeys(el))
            return el
        else:
            return None

    def reformat_date(self, date, format):
        date = datetime.datetime.strptime(date.strip(), format).strftime("%Y-%m-%d")
        return date

    def fill_business_classifier(
        self, xpathCodes=None, xpathDesc=None, xpathLabels=None, api=False
    ):
        res = []
        length = None
        codes, desc, labels = None, None, None

        if xpathCodes:
            codes = (
                self.get_by_xpath(xpathCodes)
                if not api
                else [self.get_by_api(xpathCodes)]
            )
            if codes:
                length = len(codes)
        if xpathDesc:
            desc = (
                self.get_by_xpath(xpathDesc)
                if not api
                else [self.get_by_api(xpathDesc)]
            )
            if desc:
                length = len(desc)
        if xpathLabels:
            labels = (
                self.get_by_xpath(xpathLabels)
                if not api
                else [self.get_by_api(xpathLabels)]
            )
            if labels:
                length = len(labels)

        if length:
            for i in range(length):
                temp = {
                    "code": codes[i] if codes else "",
                    "description": desc[i] if desc else "",
                    "label": labels[i] if labels else "",
                }
                res.append(temp)
        if res:
            self.overview["bst:businessClassifier"] = res

    def get_post_addr(self, tree):
        addr = self.get_by_xpath(
            tree, '//span[@id="lblMailingAddress"]/..//text()', return_list=True
        )
        if addr:
            addr = [
                i
                for i in addr
                if i != ""
                and i != "Mailing Address:"
                and i != "Inactive"
                and i != "Registered Office outside NL:"
            ]
            if addr[0] == "No address on file":
                return None
            if (
                addr[0] == "Same as Registered Office"
                or addr[0] == "Same as Registered Office in NL"
            ):
                return "Same"
            fullAddr = ", ".join(addr)
            temp = {
                "fullAddress": fullAddr
                if "Canada" in fullAddr
                else (fullAddr + " Canada"),
                "country": "Canada",
            }
            replace = re.findall("[A-Z]{2},\sCanada,", temp["fullAddress"])
            if not replace:
                replace = re.findall("[A-Z]{2},\sCanada", temp["fullAddress"])
            if replace:
                torepl = replace[0].replace(",", "")
                temp["fullAddress"] = temp["fullAddress"].replace(replace[0], torepl)
            try:
                zip = re.findall("[A-Z]\d[A-Z]\s\d[A-Z]\d", fullAddr)
                if zip:
                    temp["zip"] = zip[0]
            except:
                pass

        if len(addr) == 4:
            temp["city"] = addr[-3]
            temp["streetAddress"] = addr[0]
        if len(addr) == 5:
            temp["city"] = addr[-4]
            temp["streetAddress"] = addr[0]
        if len(addr) == 6:
            temp["city"] = addr[-4]
            temp["streetAddress"] = ", ".join(addr[:2])

        return temp

    def get_address(
        self, xpath=None, zipPattern=None, key=None, returnAddress=False, addr=None
    ):
        if xpath:
            addr = self.get_by_xpath(xpath)
        if key:
            addr = self.get_by_api(key)
        if addr:
            if type(addr) == list:
                splittedAddr = addr
                addr = ", ".join(addr)

            addr = addr.replace("\n", " ")
            addr = addr[0] if type(addr) == list else addr
            temp = {"country": splittedAddr[-2]}
            if zipPattern:
                zip = re.findall(zipPattern, addr)
                if zip:
                    temp["zip"] = zip[0]

            try:
                temp["zip"] = splittedAddr[-1]
            except:
                pass
            try:
                temp["city"] = splittedAddr[-3]
            except:
                pass
            try:
                temp["streetAddress"] = " ".join(splittedAddr[:-3])
            except:
                pass
            try:
                temp["fullAddress"] = " ".join(splittedAddr)
            except:
                pass
            try:
                patterns = ["Suite\s\d+"]
                for pattern in patterns:
                    pat = re.findall(pattern, addr)
                    if pat:
                        first_part = addr.split(pat[0])
                        temp["streetAddress"] = first_part[0] + pat[0]
            except:
                pass

            if returnAddress:
                return temp
            self.overview["mdaas:RegisteredAddress"] = temp

    def get_operational_address(
        self, xpath=None, zipPattern=None, key=None, returnAddress=False, addr=None
    ):
        if xpath:
            addr = self.get_by_xpath(xpath)
        if key:
            addr = self.get_by_api(key)
        if addr:
            if type(addr) == list:
                splittedAddr = addr
                addr = ", ".join(addr)

            addr = addr.replace("\n", " ")
            addr = addr[0] if type(addr) == list else addr
            temp = {"country": splittedAddr[-2]}
            if zipPattern:
                zip = re.findall(zipPattern, addr)
                if zip:
                    temp["zip"] = zip[0]

            try:
                temp["zip"] = splittedAddr[-1]
            except:
                pass
            try:
                temp["city"] = splittedAddr[-3]
            except:
                pass
            try:
                temp["streetAddress"] = " ".join(splittedAddr[:-3])
            except:
                pass
            try:
                temp["fullAddress"] = " ".join(splittedAddr)
            except:
                pass
            try:
                patterns = ["Suite\s\d+"]
                for pattern in patterns:
                    pat = re.findall(pattern, addr)
                    if pat:
                        first_part = addr.split(pat[0])
                        temp["streetAddress"] = first_part[0] + pat[0]
            except:
                pass

            if returnAddress:
                return temp
            self.overview["mdaas:OperationalAddress"] = temp

    def get_prev_names(self, tree):
        prev = []
        names = self.get_by_xpath(
            tree,
            '//table[@id="tblPreviousCompanyNames"]//tr[@class="row"]//tr[@class="row"]//td[1]/text() | //table[@id="tblPreviousCompanyNames"]//tr[@class="row"]//tr[@class="rowalt"]//td[1]/text()',
            return_list=True,
        )
        dates = self.get_by_xpath(
            tree,
            '//table[@id="tblPreviousCompanyNames"]//tr[@class="row"]//tr[@class="row"]//td[2]/span/text() | //table[@id="tblPreviousCompanyNames"]//tr[@class="row"]//tr[@class="rowalt"]//td[2]/span/text()',
            return_list=True,
        )
        print(names)
        if names:
            names = [i for i in names if i != ""]
        if names and dates:
            for name, date in zip(names, dates):
                temp = {"name": name, "valid_to": date}
                prev.append(temp)
        return prev

    def get_by_api(self, key):
        try:
            el = self.api[key]
            return el
        except:
            return None

    def getPathType(self, dataPath):
        if dataPath[:2] == "//":
            return "xpath"
        elif dataPath == "defaultFill":
            return "defaultFill"
        else:
            return "key"

    def fillField(self, fieldName, dataPath=None, reformatDate=None, el=None):
        dataType = self.getPathType(dataPath)
        if dataType == "xpath":
            el = self.get_by_xpath(dataPath)
        if dataType == "key":
            el = self.get_by_api(dataPath)
        if dataType == "defaultFill":
            el = dataPath
        if el:
            if len(el) == 1:
                el = el[0]
            el = self.reformat_date(el, reformatDate) if reformatDate else el

            if fieldName == "isDomiciledIn":
                country = pycountry.countries.search_fuzzy(el)
                if country:
                    self.overview[fieldName] = country[0].alpha_2
                else:
                    self.overview[fieldName] = el

            elif fieldName == "Service":
                if type(el) == list:
                    el = ", ".join(el)
                self.overview[fieldName] = {"serviceType": el}

            elif fieldName == "vcard:organization-tradename":
                self.overview[fieldName] = el.split("\n")[0].strip()

            elif fieldName == "bst:aka":
                names = el.split(" D/B/A ")
                if len(names) > 1:
                    names = [i.strip() for i in names]
                    self.overview[fieldName] = names
                else:
                    self.overview[fieldName] = names

            elif fieldName == "lei:legalForm":
                self.overview[fieldName] = {"code": "", "label": el}

            elif fieldName == "map":
                self.overview[fieldName] = el[0] if type(el) == list else el

            elif fieldName == "previous_names":
                el = el.strip()
                el = el.split("\n")
                if len(el) < 1:
                    self.overview[fieldName] = {"name": [el[0].strip()]}
                else:
                    el = [i.strip() for i in el]
                    res = []
                    for i in el:
                        temp = {"name": i}
                        res.append(temp)
                    self.overview[fieldName] = res

            elif fieldName == "bst:description":
                if type(el) == list:
                    el = ", ".join(el)
                self.overview[fieldName] = el

            elif fieldName == "hasURL" and el != "http://":
                if "www" in el:
                    el = el.split(", ")[-1]
                if "http:" not in el:
                    el = "http://" + el.strip()
                if "www" in el:
                    self.overview[fieldName] = el

            elif fieldName == "tr-org:hasRegisteredPhoneNumber":
                if type(el) == list and len(el) > 1:
                    el = el[0]
                self.overview[fieldName] = el

            elif fieldName == "bst:stock_info":
                if type(el) == list:
                    el = el[0]
                self.overview[fieldName] = {"main_exchange": el}
            elif fieldName == "agent":
                self.overview[fieldName] = {
                    "name": el.split("\n")[0],
                    "mdaas:RegisteredAddress": self.get_address(
                        returnAddress=True,
                        addr=" ".join(el.split("\n")[1:]),
                        zipPattern="[A-Z]\d[A-Z]\s\d[A-Z]\d",
                    ),
                }

            elif fieldName == "logo":
                self.overview["logo"] = self.base_url + el

            elif fieldName == "hasRegisteredFaxNumber":
                if type(el) == list and len(el) > 1:
                    el = el[0]
                self.overview[fieldName] = el

            else:
                self.overview[fieldName] = el

    def fill_identifiers(
        self,
        xpathTradeRegistry=None,
        xpathOtherCompanyId=None,
        xpathInternationalSecurIdentifier=None,
        xpathLegalEntityIdentifier=None,
    ):
        try:
            temp = self.overview["identifiers"]
        except:
            temp = {}

        if xpathTradeRegistry:
            trade = self.get_by_xpath(xpathTradeRegistry)
            if trade:
                temp["trade_register_number"] = re.findall("HR.*", trade[0])[0]
        if xpathOtherCompanyId:
            other = self.get_by_xpath(xpathOtherCompanyId)
            if other:
                temp["other_company_id_number"] = other[0]
        if xpathInternationalSecurIdentifier:
            el = self.get_by_xpath(xpathInternationalSecurIdentifier)
            temp["international_securities_identifier"] = el[0]
        if xpathLegalEntityIdentifier:
            el = self.get_by_xpath(xpathLegalEntityIdentifier)
            temp["legal_entity_identifier"] = el[0]

        if temp:
            self.overview["identifiers"] = temp

    def check_tree(self):
        print(self.tree.xpath("//text()"))

    def get_working_tree_api(self, link_name, type, method="GET", data=None):
        if type == "tree":
            if data:
                self.tree = self.get_tree(
                    link_name, headers=self.header, method=method, data=data
                )
            else:
                self.tree = self.get_tree(link_name, headers=self.header, method=method)
        if type == "api":
            if data:
                self.api = self.get_content(
                    link_name, headers=self.header, method=method, data=data
                )

            else:
                self.api = self.get_content(
                    link_name, headers=self.header, method=method
                )

            self.api = self.api.content

    def fillRatingSummary(self, xpathRatingGroup=None, xpathRatings=None):
        temp = {}
        if xpathRatingGroup:
            group = self.get_by_xpath(xpathRatingGroup)
            if group:
                temp["rating_group"] = group[0]
        if xpathRatings:
            rating = self.get_by_xpath(xpathRatings)
            if rating:
                temp["ratings"] = rating[0].split(" ")[0]
        if temp:
            self.overview["rating_summary"] = temp

    def fillAgregateRating(self, xpathReview=None, xpathRatingValue=None):
        temp = {}
        if xpathReview:
            review = self.get_by_xpath(xpathReview)
            if review:
                temp["reviewCount"] = review[0].split(" ")[0]
        if xpathRatingValue:
            value = self.get_by_xpath(xpathRatingValue)
            if value:
                temp["ratingValue"] = "".join(value)

        if temp:
            temp["@type"] = "aggregateRating"
            self.overview["aggregateRating"] = temp

    def fillReviews(
        self, xpathReviews=None, xpathRatingValue=None, xpathDate=None, xpathDesc=None
    ):
        res = []
        try:
            reviews = self.tree.xpath(xpathReviews)
            for i in range(len(reviews)):
                temp = {}
                if xpathRatingValue:
                    ratingsValues = len(
                        self.tree.xpath(
                            f"//async-list//review[{i + 1}]" + xpathRatingValue
                        )
                    )
                    if ratingsValues:
                        temp["ratingValue"] = ratingsValues
                if xpathDate:
                    date = self.tree.xpath(f"//async-list//review[{i + 1}]" + xpathDate)
                    if date:
                        temp["datePublished"] = date[0].split("T")[0]

                if xpathDesc:
                    desc = self.tree.xpath(f"//async-list//review[{i + 1}]" + xpathDesc)
                    if desc:
                        temp["description"] = desc[0]
                if temp:
                    res.append(temp)
        except:
            pass
        if res:
            self.overview["review"] = res

    def fillRegulatorAddress(
        self, xpath=None, zipPattern=None, key=None, returnAddress=False, addr=None
    ):
        if xpath:
            addr = self.get_by_xpath(xpath)[1:-2]
        if key:
            addr = self.get_by_api(key)
        if addr:
            if type(addr) == list:
                addr = ", ".join(addr)
            if "\n" in addr:
                splitted_addr = addr.split("\n")
            if ", " in addr:
                splitted_addr = addr.split(", ")

            addr = addr.replace("\n", " ")
            addr = addr[0] if type(addr) == list else addr
            temp = {"fullAddress": addr, "country": "USA"}
            if zipPattern:
                zip = re.findall(zipPattern, addr)
                if zip:
                    temp["zip"] = zip[0]
            try:
                patterns = ["Suite\s\d+"]
                for pattern in patterns:
                    pat = re.findall(pattern, addr)
                    if pat:
                        first_part = addr.split(pat[0])
                        temp["streetAddress"] = first_part[0] + pat[0]
            except:
                pass
            try:
                street = addr.split("Street")
                if len(street) == 2:
                    temp["streetAddress"] = street[0] + "Street"
                temp["streetAddress"] = addr.split(",")[0]

            except:
                pass
            try:
                temp["city"] = addr.split(", ")[-2].replace(".", "")

            except:
                pass
            temp["fullAddress"] += f', {temp["country"]}'
            temp["fullAddress"] = temp["fullAddress"].replace(".,", ",")
            if returnAddress:
                return temp
            self.overview["regulatorAddress"] = temp

    def getOfficerFromPage(self, link, officerType):
        self.get_working_tree_api(link, "tree")
        temp = {}
        temp["name"] = self.get_by_xpath(
            '//div[@class="form-group"]//strong[2]/text()'
        )[0]

        temp["type"] = officerType
        addr = ",".join(
            self.get_by_xpath('//div[@class="MasterBorder"]//div[2]//div/text()')[:-1]
        )
        if addr:
            temp["address"] = {
                "address_line_1": addr,
            }
            zip = re.findall("\d\d\d\d\d-\d\d\d\d", addr)[0]
            if zip:
                temp["address"]["postal_code"] = zip
                temp["address"]["address_line_1"] = addr.split(zip)[0]

        temp["officer_role"] = "PRODUCER" if officerType == "individual" else "COMPANY"

        temp["status"] = self.get_by_xpath(
            '//td//text()[contains(., "License Status")]/../../following-sibling::td//text()'
        )[0]

        temp["information_source"] = self.base_url
        temp["information_provider"] = "Idaho department of Insurance"
        return temp if temp["status"] == "Active" else None

    def getHiddenValuesASP(self):
        names = self.get_by_xpath('//input[@type="hidden"]/@name')
        temp = {}
        for name in names:
            value = self.get_by_xpath(
                f'//input[@type="hidden"]/@name[contains(., "{name}")]/../@value'
            )
            temp[name] = value[0] if value else ""
        return temp

    def makeDictFromString(self, link_dict):
        link_dict = (
            link_dict.replace("'", '"').replace("None", '"None"').replace('""', '"')
        )
        return json.loads(link_dict)

    def extractData(self, requiredFields, hardCodedFields):
        for k, v in requiredFields.items():
            self.fillField(k, v)

        for k, v in hardCodedFields.items():
            self.overview[k] = v

    def get_overview(self, link):
        self.overview = {}
        self.get_working_tree_api(link, "tree")

        requiredFieldsMap = {
            "isDomiciledIn": '//text()[contains(., "Headquarters Country")]/../following-sibling::div[1]//text()',
            "vcard:organization-name": "//h1/a/text()",
            "hasLatestOrganizationFoundedDate": '//text()[contains(., "Founded Year")]/../following-sibling::div[1]//text()',
            "logo": '//div[@class="clearfix col-sm-12 field field--name-field-company-logo-lc field--type-image field--label-hidden field--item"]/a/img/@src',
            "hasURL": '//text()[contains(., "Company Website:")]/../following-sibling::div[1]/a/@href',
            "bst:description": '//text()[contains(., "About Company Business:")]/../following-sibling::div[1]//text()',
            "registeredIn": '//text()[contains(., "Headquarters Region")]/../following-sibling::div[1]//text()',
            "bst:stock_info": '//text()[contains(., "Stock Exchange")]/../following-sibling::div[1]//text()',
            "size": '//text()[contains(., "Number of Employees")]/../following-sibling::div[1]//text()',
            "Service": '//div[@class="clearfix group-left"]/div//text()[contains(., "Company Business")]/../following-sibling::div[1]//text()',
        }

        hardCodedFields = {"bst:registryURI": link}
        self.extractData(requiredFieldsMap, hardCodedFields)
        return self.overview

    def get_officership(self, link):
        off = []
        self.get_working_tree_api(link, "tree")

        ceo = self.get_by_xpath(
            '//text()[contains(., "CEO:")]/../following-sibling::div[1]//text()'
        )
        founders = self.get_by_xpath(
            '//text()[contains(., "Founders")]/../following-sibling::div[1]//text()'
        )

        try:
            for name in founders:
                off.append(
                    {
                        "name": name,
                        "type": "individual",
                        "officer_role": "Founder",
                        "status": "Active",
                        "occupation": "Founder",
                        "information_source": self.base_url,
                        "information_provider": "Value Today",
                    }
                )
        except:
            pass
        try:
            off.append(
                {
                    "name": ceo[0],
                    "type": "individual",
                    "officer_role": "CEO",
                    "status": "Active",
                    "occupation": "CEO",
                    "information_source": self.base_url,
                    "information_provider": "Value Today",
                }
            )
        except:
            pass
        return off

    def get_financial_information(self, link):
        self.get_working_tree_api(link, "tree")
        total_assets = self.get_by_xpath(
            '//text()[contains(., "Balance Sheet Summary - in ")]/../../following-sibling::table[1]//tr[3]//td[2]/text()'
        )
        revenue = self.get_by_xpath(
            '//text()[contains(., "Annual\xa0Results - Revenue and Net Profit")]/../../following-sibling::table[1]//tr[3]//td[2]/text()'
        )
        date = self.get_by_xpath(
            '//text()[contains(., "Balance Sheet Summary - in ")]/../../following-sibling::table[1]//tr[3]//td[1]/text()'
        )
        market_capitalization = self.get_by_xpath(
            '//text()[contains(., "Market Cap ")]/../following-sibling::div[1]//text()'
        )
        total_liabilities = self.get_by_xpath(
            '//text()[contains(., "Balance Sheet Summary - in ")]/../../following-sibling::table[1]//tr[3]//td[3]/text()'
        )
        profit = self.get_by_xpath(
            '//text()[contains(., "Annual\xa0Results - Revenue and Net Profit")]/../../following-sibling::table[1]//tr[3]//td[4]/text()'
        )

        income = {}
        balance = {}
        if date:
            balance["date"] = date[0].split("-")[-1]
        res = {}

        try:
            if "Billion" in market_capitalization[0]:
                balance["market_capitalization"] = str(
                    float(market_capitalization[0].split(" ")[0]) * 1000000000
                )[:-2]
            if "Million" in market_capitalization[0]:
                balance["market_capitalization"] = str(
                    float(market_capitalization[0].split(" ")[0]) * 1000000
                )[:-2]
        except:
            pass

        try:
            balance["total_assets"] = total_assets[0]

        except:
            pass

        try:
            balance["total_liabilities"] = total_liabilities[0]
        except:
            pass

        temp = {}
        try:
            name = self.get_by_xpath(
                '//text()[contains(., "Annual\xa0Results - Revenue and Net Profit")]'
            )
            if "Billion" in name[0]:
                mult = 1000000000
            else:
                mult = 1000000

            temp["revenue"] = str(float(revenue[0]) * mult)
        except:
            pass
        try:
            date = date.split("-")[-1]
            temp["period"] = f"{date}-01-01-{date}-12-31"

        except:
            pass

        try:
            name = self.get_by_xpath(
                '//text()[contains(., "Annual\xa0Results - Revenue and Net Profit")]'
            )
            if "Billion" in name[0]:
                mult = 1000000000
            else:
                mult = 1000000

            temp["profit"] = str(math.ceil(float(profit[0]) * mult))
        except:
            pass

        print(temp)
        income = temp

        res["Summary_Financial_data"] = [
            {"source": link, "summary": {"currency": "USD", "balance_sheet": balance}}
        ]
        if income:
            res["Summary_Financial_data"][0]["summary"]["income_statement"] = income

        return res
