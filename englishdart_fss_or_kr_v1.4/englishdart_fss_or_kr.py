import datetime
import hashlib
import json
import re


from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://englishdart.fss.or.kr"
    NICK_NAME = base_url.split("//")[-1]
    fields = ["overview", "officership", "graph:shareholders", "Financial_Information"]
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

        self.get_working_tree_api(
            "https://englishdart.fss.or.kr/dsbc001/main.do", "tree"
        )
        data = {
            "currentPage": "1",
            "maxResults": "45",
            "maxLinks": "5",
            "sort": "",
            "series": "",
            "selectKey": "",
            "searchIndex": "",
            "textCrpCik": "",
            "startDate": "",
            "endDate": "",
            "businessCode": "",
            "textCrpNm": searchquery,
            "corporationType": "all",
        }
        self.get_working_tree_api(
            "https://englishdart.fss.or.kr/dsbc001/search.ax",
            "tree",
            data=data,
            method="POST",
        )
        links = self.get_by_xpath('//td[@class="tL ellipsis"]/a/@href')

        for link in links:
            data = {"selectKey": link.split("=")[-1], "corpDetail": "Y"}
            self.get_working_tree_api(
                "https://englishdart.fss.or.kr/dsbc001/select.ax",
                "tree",
                data=data,
                method="POST",
            )
            btn = self.get_by_xpath(
                '//button/text()[contains(., "More detailed Information")]/../@onclick'
            )
            if btn:
                company_code = btn[0].split(",")[0].split("(")[-1].replace("'", "")
                company_name = btn[0].split(", ")[-1].split(")")[0].replace("'", "")
                result.append(company_code + "?=" + company_name)
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
                addr = ", ".join(addr)
            if "\n" in addr:
                splitted_addr = addr.split("\n")
            if ", " in addr:
                splitted_addr = addr.split(", ")

            addr = addr.replace("\n", " ")
            addr = addr[0] if type(addr) == list else addr
            temp = {"fullAddress": addr, "country": "South Korea"}
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
                else:
                    temp["streetAddress"] = "".join(addr.split(",")[0:2])

            except:
                pass
            try:
                temp["city"] = addr.split(", ")[-1].replace(".", "")

            except:
                pass
            temp["fullAddress"] += f', {temp["country"]}'

            temp["fullAddress"] = temp["fullAddress"].replace(".,", ",")
            if returnAddress:
                return temp
            self.overview["mdaas:RegisteredAddress"] = temp

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

    def fillField(self, fieldName, key=None, xpath=None, test=False, reformatDate=None):
        if xpath:
            el = self.get_by_xpath(xpath)
        if key:
            el = self.get_by_api(key)
        if test:
            print(el)
        if el:
            if len(el) == 1:
                el = el[0]
            el = self.reformat_date(el, reformatDate) if reformatDate else el
            if fieldName == "vcard:organization-name":
                self.overview[fieldName] = el.split("(")[0].strip()

            if fieldName == "hasActivityStatus":
                self.overview[fieldName] = el

            if fieldName == "size":
                self.overview["size"] = el

            if fieldName == "bst:registrationId":
                self.overview[fieldName] = el

            if fieldName == "Service":
                self.overview[fieldName] = {"serviceType": el}

            if fieldName == "vcard:organization-tradename":
                self.overview[fieldName] = el.split("\n")[0].strip()

            if fieldName == "bst:aka":
                names = el.split("\n")
                names = el.split(" D/B/A ")
                if len(names) > 1:
                    names = [i.strip() for i in names]
                    self.overview[fieldName] = names
                else:
                    self.overview[fieldName] = names

            if fieldName == "lei:legalForm":
                self.overview[fieldName] = {"code": "", "label": el}

            if fieldName == "map":
                self.overview[fieldName] = el[0] if type(el) == list else el

            if fieldName == "previous_names":
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

            if fieldName == "hasLatestOrganizationFoundedDate":
                self.overview[fieldName] = el

            if fieldName == "isIncorporatedIn":
                self.overview[fieldName] = el

            if fieldName == "sourceDate":
                self.overview[fieldName] = self.reformat_date(el, "%d.%m.%Y")
            if fieldName == "regExpiryDate":
                self.overview[fieldName] = el

            if fieldName == "bst:description":
                self.overview[fieldName] = el

            if fieldName == "hasURL" and el != "http://":
                if "www" in el:
                    el = el.split(", ")[-1]
                if "http:" not in el:
                    el = "http://" + el.strip()
                if "www" in el:
                    self.overview[fieldName] = el
            if fieldName == "bst:email":
                self.overview["bst:email"] = el

            if fieldName == "tr-org:hasRegisteredPhoneNumber":
                if type(el) == list and len(el) > 1:
                    el = el[0]
                self.overview[fieldName] = el

            if fieldName == "agent":
                self.overview[fieldName] = {
                    "name": el.split("\n")[0],
                    "mdaas:RegisteredAddress": self.get_address(
                        returnAddress=True,
                        addr=" ".join(el.split("\n")[1:]),
                        zipPattern="[A-Z]\d[A-Z]\s\d[A-Z]\d",
                    ),
                }
            if fieldName == "RegulationStatusEffectiveDate":
                self.overview["RegulationStatusEffectiveDate"] = el

            if fieldName == "logo":
                self.overview["logo"] = (
                    "https://m.bvb.ro/FinancialInstruments/Details/" + el
                )

            if fieldName == "hasRegisteredFaxNumber":
                if type(el) == list and len(el) > 1:
                    el = el[0]
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
                    link_name, headers=self.header, method=method, data=json.dumps(data)
                )
            else:
                self.api = self.get_content(
                    link_name, headers=self.header, method=method
                )
            self.api = json.loads(self.api.content)

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

    def get_overview(self, link_name):
        self.overview = {}
        url = "https://englishdart.fss.or.kr/dsbc002/main.do"
        data = {
            "selectKey": link_name.split("?=")[0],
            "textCrpNm": link_name.split("?=")[-1],
        }
        self.get_working_tree_api(url, "tree", "POST", data=data)

        try:
            self.fillField(
                "vcard:organization-name",
                xpath='//label/text()[contains(., "Company Name")]/../../following-sibling::td[1]/text()',
            )
        except:
            return None

        self.overview["isDomiciledIn"] = "KR"
        self.fillField(
            "hasURL",
            xpath='//label/text()[contains(., "Newspaper(s) used For major notices")]/../../following-sibling::td[1]/text()',
        )

        self.get_address(
            '//label/text()[contains(., "Main Office Address")]/../../following-sibling::td[1]/text()'
        )
        self.fillField(
            "hasLatestOrganizationFoundedDate",
            xpath='//label/text()[contains(., "Establishment Date")]/../../following-sibling::td[1]/text()',
            reformatDate="%Y.%m.%d",
        )

        self.fillField(
            "isIncorporatedIn",
            xpath='//label/text()[contains(., "Listing Date")]/../../following-sibling::td[1]/text()',
            reformatDate="%Y.%m.%d",
        )
        self.fillField(
            "tr-org:hasRegisteredPhoneNumber",
            xpath='//label/text()[contains(., "Telephone")]/../../following-sibling::td[1]/text()',
        )
        self.fill_identifiers(
            xpathOtherCompanyId='//label/text()[contains(., "Company Code")]/../../following-sibling::td[1]/text()'
        )
        self.fillField(
            "size",
            xpath='//label/text()[contains(., "Employees")]/../../following-sibling::td[1]/text()',
        )

        self.fillField(
            "bst:registrationId",
            xpath='//label/text()[contains(., "Company Code")]/../../following-sibling::td[1]/text()',
        )
        self.overview["@source-id"] = self.NICK_NAME
        businesses = self.get_by_xpath(
            '//div/text()[contains(., "Main Businesses")]/../following-sibling::div[1]//td/text()'
        )
        if businesses:
            self.overview["Service"] = {
                "areaServed": "",
                "serviceType": ", ".join(businesses),
            }

        return self.overview

    def get_officership(self, link_name):
        off = []

        url = "https://englishdart.fss.or.kr/dsbc002/main.do"
        data = {
            "selectKey": link_name.split("?=")[0],
            "textCrpNm": link_name.split("?=")[-1],
        }
        self.get_working_tree_api(url, "tree", "POST", data=data)

        names = self.get_by_xpath(
            '//label/text()[contains(., "Representative Director")]/../../following-sibling::td[1]/text()'
        )

        try:
            if "," in names[0]:
                names = names[0].split(", ")
            for name in names:
                off.append(
                    {
                        "name": name,
                        "type": "individual",
                        "officer_role": "Representative Director",
                        "status": "Active",
                        "occupation": "Representative Director",
                        "information_source": self.base_url,
                        "information_provider": "Korea ListedCompanies Association (KLCA)",
                    }
                )
        except:
            pass

        auditor = self.get_by_xpath(
            '//label/text()[contains(., "External Auditor")]/../../following-sibling::td[1]/text()'
        )

        try:
            off.append(
                {
                    "name": auditor[0],
                    "type": "company",
                    "officer_role": "External Auditor",
                    "status": "Active",
                    "occupation": "External Auditor",
                    "information_source": self.base_url,
                    "information_provider": "Korea ListedCompanies Association (KLCA)",
                }
            )
        except:
            pass

        return off

    def get_shareholders(self, link_name):
        url = "https://englishdart.fss.or.kr/dsbc002/main.do"
        data = {
            "selectKey": link_name.split("?=")[0],
            "textCrpNm": link_name.split("?=")[-1],
        }
        self.get_working_tree_api(url, "tree", "POST", data=data)

        edd = {}
        shareholders = {}
        sholdersl1 = {}

        company = self.get_overview(link_name)
        company_name_hash = hashlib.md5(
            company["vcard:organization-name"].encode("utf-8")
        ).hexdigest()

        try:
            names = self.get_by_xpath(
                '//div/text()[contains(., "Major Stockholders")]/../following-sibling::div[1]//td/text()'
            )

            holders = [names] if type(names) == str else names

            for i in range(len(holders)):
                holder_name_hash = hashlib.md5(holders[i].encode("utf-8")).hexdigest()
                shareholders[holder_name_hash] = {
                    "source": "Korea Listed Companies Association (KLCA)",
                    "totalPercentage": holders[i].split("(")[-1].split(")")[0],
                }

                if "bank" in holders[i].lower():
                    holder_type = "B"
                elif (
                    ".co" in holders[i].lower()
                    or "corporation" in holders[i].lower()
                    or "service" in holders[i].lower()
                    or "limited" in holders[i].lower()
                ):
                    holder_type = "C"
                else:
                    holder_type = "I"

                basic_in = {
                    "vcard:organization-name": holders[i].split("(")[0],
                    "isDomiciledIn": "KR",
                    "entity_type": holder_type,
                }
                sholdersl1[holder_name_hash] = {"basic": basic_in, "shareholders": {}}
        except:
            pass

        edd[company_name_hash] = {
            "basic": company,
            "entity_type": "C",
            "shareholders": shareholders,
        }

        return edd, sholdersl1

    def get_financial_information(self, link_name):
        url = "https://englishdart.fss.or.kr/dsbc002/main.do"
        data = {
            "selectKey": link_name.split("?=")[0],
            "textCrpNm": link_name.split("?=")[-1],
        }
        self.get_working_tree_api(url, "tree", "POST", data=data)

        periods = len(
            self.get_by_xpath(
                '//th/text()[contains(., "Net Sales")]/../following-sibling::td/text()'
            )
        )

        assetsy = None
        tempList = []
        for i in range(periods):
            period = self.get_by_xpath(
                f'//div/text()[contains(., "Summarized Income Statements (In KRW, thousands)")]/../..//th/text()[contains(., "Account")]/../following-sibling::th[{i+1}]/text()'
            )

            net_sales = self.get_by_xpath(
                f'//th/text()[contains(., "Net Sales")]/../following-sibling::td[{i+1}]/text()'
            )

            operating_inc = self.get_by_xpath(
                f'//th/text()[contains(., "Operating Income (Loss)")]/../following-sibling::td[{i+1}]/text()'
            )

            try:
                assets = self.get_by_xpath(
                    f'//th/text()[contains(., "Capital Stock")]/../following-sibling::td[{i + 1}]/text()'
                )
                assets = [assets[0]]
            except:
                assets = ["no"]

            temp = {}
            if period and net_sales and operating_inc and assets:
                period = period[0].split(".")[0]
                period = [f"{period}-01-01-{period}-12-31"]
                revenue = net_sales

                for p, r, prof, sh in zip(period, revenue, operating_inc, assets):
                    ggg = {
                        "period": p,
                        "revenue": r + ",000",
                        "profit": prof + ",000",
                    }
                    if sh != "no":
                        assetsy = sh + ",000"
                        ggg["authorized_share_capital"] = sh + ",000"
                    tempList.append(ggg)

                temp["Summary_Financial_data"] = [
                    {
                        "source": "Korea ListedCompanies Association (KLCA)",
                        "summary": {"currency": "KRW", "income_statement": tempList[0]},
                    }
                ]
                try:
                    temp["Summary_Financial_data"][0]["summary"]["balance_sheet"] = {
                        "authorized_share_capital": assetsy
                    }
                except:
                    pass
            break

        return temp
