import datetime
import hashlib
import json
import re


from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://business.gov.ph"
    NICK_NAME = base_url.split("//")[-1]
    fields = ["overview"]
    overview = {}
    tree = None
    api = None

    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9;application/json",
        "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
        "Content-Type": "application/json",
    }

    def appendToResult(self, result, listOfValues):
        for value in listOfValues:
            result.append(value)
        return result

    def getResultListFromResponse(self, type, response=None, searchquery=None):
        result = []
        if type == "API" and response:
            data = json.loads(response.content)
            try:
                companies = data["data"][1]["data"]["rowData"]
                for company in companies:
                    code = company["cellData"][1]["value"]

                    result.append(code)
            except:
                return None
        if type == "tree" and searchquery:
            names = self.get_by_xpath(
                f'//h6/text()[contains(., "Government-Owned and Controlled Corporation")]/../../../h4/text()[contains(., "{searchquery}")]'
            )
            result = self.appendToResult(result, names)
        return result

    def getpages(self, searchquery):
        url = "https://www.gov.ph/es/directory-of-department-and-agencies.html"

        self.get_working_tree_api(url, "tree")

        result = self.getResultListFromResponse("tree", searchquery=searchquery)
        if result:
            return result

    def get_by_xpath(self, xpath):
        try:
            el = self.tree.xpath(xpath)
        except Exception as e:
            print(e)
            return None
        if el:
            el = [i.strip() for i in el]
            el = [i for i in el if i != ""]
            return el
        else:
            return None

    def reformat_date(self, date, format):
        date = datetime.datetime.strptime(date.strip(), format).strftime("%Y-%m-%d")
        return date

    def get_business_class(self, xpathCodes=None, xpathDesc=None, xpathLabels=None):
        res = []
        if xpathCodes:
            codes = self.get_by_xpath(xpathCodes)
        if xpathDesc:
            desc = self.get_by_xpath(xpathDesc)
        if xpathLabels:
            labels = self.get_by_xpath(xpathLabels)

        for c, d, l in zip(codes, desc, labels):
            temp = {
                "code": c.split(" (")[0],
                "description": d,
                "label": l.split("(")[-1].split(")")[0],
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
                addr = "".join(addr)
            if "\n" in addr:
                splitted_addr = addr.split("\n")
            if ", " in addr:
                splitted_addr = addr.split(", ")

            addr = addr.replace("\n", " ")

            addr = addr[0] if type(addr) == list else addr
            temp = {"fullAddress": addr, "country": "Philippines"}

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
                if temp["zip"]:
                    city = addr.replace(temp["zip"], "")
            except:
                pass
            try:
                if temp["streetAddress"]:
                    city = city.replace(temp["streetAddress"], "")
            except:
                city = addr.replace(",", "").strip()
                city = re.findall("[A-Z][a-z]+\sCity", city)
                if city:
                    temp["city"] = city[0]
            try:
                if temp["city"]:
                    temp["streetAddress"] = addr.split(temp["city"])[0][:-2]
            except:
                pass
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

    def getFrombaseXpath(self, tree, baseXpath):
        pass

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
            if type(el) == list and len(el) == 1:
                el = el[0].strip()
            if fieldName == "vcard:organization-name":
                self.overview[fieldName] = el.split("(")[0].strip()

            if fieldName == "hasActivityStatus":
                self.overview[fieldName] = el

            if fieldName == "Service":
                self.overview[fieldName] = {"serviceType": el}

            if fieldName == "regExpiryDate":
                self.overview[fieldName] = (
                    self.reformat_date(el, reformatDate) if reformatDate else el
                )

            if fieldName == "vcard:organization-tradename":
                self.overview[fieldName] = el.split("\n")[0].strip()

            if fieldName == "bst:email":
                if "mailto:" in el:
                    el = el.split("mailto:")[1]
                self.overview[fieldName] = el

            if fieldName == "bst:aka":
                names = el.split("\n")
                if len(names) > 1:
                    names = [i.strip() for i in names[1:]]
                    self.overview[fieldName] = names

            if fieldName == "lei:legalForm":
                self.overview[fieldName] = {"code": "", "label": el}

            if fieldName == "identifiers":
                self.overview[fieldName] = {"trade_register_number": el}
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

            if fieldName == "agent":
                self.overview[fieldName] = {
                    "name": el.split("\n")[0],
                    "mdaas:RegisteredAddress": self.get_address(
                        returnAddress=True,
                        addr=" ".join(el.split("\n")[1:]),
                        zipPattern="[A-Z]\d[A-Z]\s\d[A-Z]\d",
                    ),
                }

            if fieldName == "tr-org:hasRegisteredPhoneNumber":
                if type(el) == list and len(el) > 1:
                    el = el[0]
                self.overview[fieldName] = el

    def check_tree(self):
        print(self.tree.xpath("//text()"))

    def get_working_tree_api(self, link_name, type):
        if type == "tree":
            self.tree = self.get_tree(
                link_name + "?active_tab=register", headers=self.header
            )
        if type == "api":
            data = {
                "appName": "LegacyBusiness",
                "featureName": "LegacyBusiness",
                "metaVars": {"save_location": None, "service_id": None},
                "queryName": "LegacyBusinessView",
                "queryVars": {
                    "activity": "LegacyBusinessView",
                    "business_number": link_name,
                    "service": "LegacyBusiness",
                },
            }

            self.api = self.get_content(
                "https://wdf.princeedwardisland.ca/workflow",
                headers=self.header,
                method="POST",
                data=json.dumps(data),
            )
            self.api = json.loads(self.api.content)
            self.api = self.api["data"]["data"]["keyValuePairs"]

    def removeQuotes(self, text):
        text = text.replace('"', "")
        return text

    def get_overview(self, link_name):
        url = "https://www.gov.ph/es/directory-of-department-and-agencies.html"

        self.get_working_tree_api(url, "tree")

        self.overview = {}

        baseXpath = f'//h4/text()[contains(., "{link_name}")]/../..'
        try:
            self.fillField("vcard:organization-name", xpath=f"{baseXpath}/h4/text()")
        except:
            return None

        self.overview["isDomiciledIn"] = "PH"
        self.overview["@source-id"] = self.NICK_NAME

        self.fillField(
            "tr-org:hasRegisteredPhoneNumber",
            xpath=f'{baseXpath}/p[@class="telfax"]/text()',
        )
        self.fillField("bst:email", xpath=f'{baseXpath}/p[@class="email"]/a/@href')

        self.get_address(
            xpath=f'{baseXpath}/p[@id="address"]//*/text()', zipPattern="\d{4}"
        )

        return self.overview
