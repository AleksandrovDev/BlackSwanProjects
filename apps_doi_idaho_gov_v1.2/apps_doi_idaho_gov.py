import datetime
import hashlib
import json
import re


from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://apps.doi.idaho.gov"
    NICK_NAME = base_url.split("//")[-1]
    fields = ["overview", "officership"]
    overview = {}
    tree = None
    api = None

    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9;application/json",
        "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
        "Content-Type": "application/json",
    }

    def getpages(self, searchquery):
        result = []
        url = f"https://apps.doi.idaho.gov/main/PublicForms/LicenseSearch?pn=1&ps=100&sc=0&sd=0&apn=1&aps=100&asc=1&asd=1&fc=2&fv={searchquery}&zip=&at=0&ct=0&loa=0&st=0"
        self.get_working_tree_api(url, "tree")
        result = self.get_by_xpath('//div[@id="seachTable"]//td/a/@href')
        if result:
            result = [f"{self.base_url}{i}" for i in result]
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
        self, xpathCodes=None, xpathDesc=None, xpathLabels=None
    ):
        res = []
        length = None
        codes, desc, labels = None, None, None
        if xpathCodes:
            codes = self.get_by_xpath(xpathCodes)
            if codes:
                length = len(codes)
        if xpathDesc:
            desc = self.get_by_xpath(xpathDesc)
            if desc:
                length = len(desc)
        if xpathLabels:
            labels = self.get_by_xpath(xpathLabels)
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
            addr = self.get_by_xpath(xpath)[:-1]
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

            if fieldName == "isIncorporatedIn":
                if reformatDate:
                    self.overview[fieldName] = self.reformat_date(el, reformatDate)
                else:
                    self.overview[fieldName] = el

            if fieldName == "sourceDate":
                self.overview[fieldName] = self.reformat_date(el, "%d.%m.%Y")
            if fieldName == "regExpiryDate":
                self.overview[fieldName] = el

            if fieldName == "bst:description":
                self.overview[fieldName] = el

            if fieldName == "hasURL" and el != "http://":
                if "http:" not in el:
                    el = "http:" + el
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

    def fill_identifiers(self, xpathTradeRegistry=None, xpathOtherCompanyId=None):
        temp = {}
        if xpathTradeRegistry:
            trade = self.get_by_xpath(xpathTradeRegistry)
            if trade:
                temp["trade_register_number"] = re.findall("HR.*", trade[0])[0]
        if xpathOtherCompanyId:
            other = self.get_by_xpath(xpathOtherCompanyId)
            if other and other[0] != "0":
                temp["other_company_id_number"] = other[0]

        if temp:
            self.overview["identifiers"] = temp

    def check_tree(self):
        print(self.tree.xpath("//text()"))

    def get_working_tree_api(self, link_name, type, method="GET", data=None):
        if type == "tree":
            if data:
                self.tree = self.get_tree(
                    link_name, headers=self.header, method=method, data=json.dumps(data)
                )
            else:
                self.tree = self.get_tree(link_name, headers=self.header, method=method)
        if type == "api":
            if data:
                self.api = self.get_content(
                    link_name, headers=self.header, method=method, data=json.dumps(data)
                )
            self.api = self.get_content(link_name, headers=self.header, method=method)
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
        if self.get_by_xpath('//div[@class="form-group"]//strong[2]/text()'):
            temp["name"] = self.get_by_xpath(
                '//div[@class="form-group"]//strong[2]/text()'
            )[0]

        type = self.get_by_xpath('//div[@id="content"]//h3/text()')
        if type:
            if "PRODUCER" in type[0]:
                temp["type"] = "individual"
            else:
                temp["type"] = "company"

            temp["officer_role"] = type[0].split(" ")[0]

        if self.get_by_xpath('//div[@class="MasterBorder"]//div[2]//div/text()'):
            addr = ",".join(
                self.get_by_xpath('//div[@class="MasterBorder"]//div[2]//div/text()')[
                    :-1
                ]
            )
            if addr:
                temp["address"] = {
                    "address_line_1": addr,
                }
                zip = re.findall("\d\d\d\d\d-\d\d\d\d", addr)
                if not zip:
                    zip = re.findall("\d\d\d\d\d", addr)
                if zip:
                    zip = zip[0]
                    temp["address"]["postal_code"] = zip
                    temp["address"]["address_line_1"] = addr.split(zip)[0]

        if self.get_by_xpath(
            '//td//text()[contains(., "License Status")]/../../following-sibling::td//text()'
        ):
            temp["status"] = self.get_by_xpath(
                '//td//text()[contains(., "License Status")]/../../following-sibling::td//text()'
            )[0]

        temp["information_source"] = self.base_url
        temp["information_provider"] = "Idaho department of Insurance"
        return temp if temp["status"] == "Active" else None

    def get_overview(self, link_name):
        self.overview = {}
        self.get_working_tree_api(link_name, "tree")
        try:
            self.fillField(
                "vcard:organization-name",
                xpath='//div[@class="form-group"]//strong[2]/text()',
            )
        except:
            return None

        self.overview["isDomiciledIn"] = "US"
        self.fillField("bst:aka", xpath='//div[@class="AliasList"]//div/text()')
        self.get_address(
            xpath='//div[@class="MasterBorder"]//div[2]//div/text()',
            zipPattern="\d\d\d\d\d+",
        )
        if self.overview["mdaas:RegisteredAddress"]["fullAddress"]:
            try:
                self.overview["registeredIn"] = (
                    self.overview["mdaas:RegisteredAddress"]["fullAddress"]
                    .split(",")[-2]
                    .split(" ")[1]
                )
            except:
                pass

        self.fill_business_classifier(
            xpathCodes='//table/@class[contains(., "matrix")]/..//tr/td[2]/text()',
            xpathDesc='//table/@class[contains(., "matrix")]/..//tr/td[1]/text()',
        )
        self.fillField(
            "tr-org:hasRegisteredPhoneNumber",
            xpath='//div[@class="MasterBorder"]//div[2]//div[3]/text()',
        )

        self.overview["regulator_name"] = "Idaho department of Insurance"
        self.overview["regulator_url"] = self.base_url
        self.overview["RegulationStatus"] = "Authorised"
        self.fillField(
            "hasActivityStatus",
            xpath='//td//text()[contains(., "License Status")]/../../following-sibling::td//text()',
        )
        self.fillField(
            "RegulationStatusEffectiveDate",
            xpath='//td//text()[contains(., "Date Effective")]/../../following-sibling::td//text()',
            reformatDate="%m/%d/%Y",
        )

        self.fillField(
            "regExpiryDate",
            xpath='//td//text()[contains(., "Date Expire")]/../../following-sibling::td//text()',
            reformatDate="%m/%d/%Y",
        )
        self.fill_identifiers(
            xpathOtherCompanyId='//td//text()[contains(., "NAIC Code")]/../../following-sibling::td//text()'
        )
        self.overview["bst:registryURI"] = link_name
        self.overview["bst:sourceLinks"] = [link_name]
        self.overview["@source-id"] = self.NICK_NAME

        try:
            if self.overview["bst:businessClassifier"]:
                self.overview["Service"] = {
                    "areaServed": "",
                    "serviceType": ", ".join(
                        i["description"]
                        for i in self.overview["bst:businessClassifier"]
                    ),
                }
        except:
            pass

        self.get_working_tree_api(
            "https://doi.idaho.gov/agency-contact/director/", "tree"
        )
        self.fillRegulatorAddress(
            xpath='//div/@class[contains(., "footer-widget")]/..//p[1]/strong/text()[contains(., "Main Office")]/../..//text()'
        )

        return self.overview

    def get_officership(self, link_name):
        off = []
        self.get_working_tree_api(link_name, "tree")

        officership_prod_links = self.get_by_xpath(
            '//div[@id="agentTable"]//td/a/@href'
        )
        if officership_prod_links:
            officership_prod_links = [
                self.base_url + i for i in officership_prod_links
            ][:-1]
            for i in officership_prod_links:
                officer = self.getOfficerFromPage(i, "individual")
                if officer:
                    off.append(officer)

        officership_insur_links = self.get_by_xpath(
            '//div[@id="companyTable"]//td/a/@href'
        )
        if officership_insur_links:
            officership_insur_links = [
                self.base_url + i for i in officership_insur_links
            ]
            for i in officership_insur_links[:-1]:
                officer = self.getOfficerFromPage(i, "company")
                if officer:
                    off.append(officer)

        return off
