import datetime
import hashlib
import json
import re


from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://naicom.gov.ng"
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

    def getResultListFromResponse(self, response, type):
        if type == "API":
            data = json.loads(response.content)
            result = []
            try:
                companies = data["data"][1]["data"]["rowData"]
                for company in companies:
                    code = company["cellData"][1]["value"]

                    result.append(code)
                return result
            except:
                return None

    def getpages(self, searchquery):
        result = []
        urls = [
            "https://naicom.gov.ng/insurance-industry/composite-companies/",
            "https://naicom.gov.ng/insurance-industry/general-companies/",
            "https://naicom.gov.ng/insurance-industry/life-companies/",
            "https://naicom.gov.ng/insurance-industry/takaful-companies/",
            "https://naicom.gov.ng/insurance-industry/re-insurance-companies/",
            "https://naicom.gov.ng/insurance-industry/licensed-brokers-companies/",
            "https://naicom.gov.ng/insurance-industry/loss-adjusters-companies/",
            "https://naicom.gov.ng/insurance-industry/micro-insurance/",
        ]
        for url in urls:
            self.get_working_tree_api(url, "tree")
            company_names = self.get_by_xpath(
                f'//div[@class="grid-container"]/ul/li[2]/text()[contains(translate(., "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{searchquery.lower()}")]'
            )
            if company_names:
                for name in company_names:
                    addr = self.get_by_xpath(
                        f'//div[@class="grid-container"]/ul/li[2]/text()[contains(., "{name}")]/../../li[3]/text()'
                    )
                    buss = self.get_by_xpath('//p[@class="composite-title"]/text()')
                    result.append(f"{name}?={addr[0]}?={buss[0]}")
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
            if "\n" in addr:
                splitted_addr = addr.split("\n")
            if ", " in addr:
                splitted_addr = addr.split(", ")

            addr = addr.replace("\n", " ")
            addr = addr[0] if type(addr) == list else addr
            temp = {"fullAddress": addr, "country": "Nigeria"}
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

            except:
                pass
            try:
                temp["city"] = addr.split(" ")[-1].replace(".", "")

            except:
                pass
            temp["fullAddress"] += ", Nigeria"
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
            if len(el) == 1:
                el = el[0]
            if fieldName == "vcard:organization-name":
                self.overview[fieldName] = el.split("(")[0].strip()

            if fieldName == "hasActivityStatus":
                self.overview[fieldName] = el

            if fieldName == "bst:registrationId":
                self.overview[fieldName] = el

            if fieldName == "Service":
                self.overview[fieldName] = {"serviceType": el}

            if fieldName == "regExpiryDate":
                self.overview[fieldName] = (
                    self.reformat_date(el, reformatDate) if reformatDate else el
                )

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

            if fieldName == "identifiers":
                self.overview[fieldName] = {"other_company_id_number": el}
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
                self.overview[fieldName] = self.reformat_date(el, "%m/%d/%Y")

            if fieldName == "bst:description":
                self.overview[fieldName] = el

            if fieldName == "hasURL" and el != "http://":
                self.overview[fieldName] = el

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
            self.api = self.get_content(
                link_name, headers=self.header, method=method, data=json.dumps(data)
            )
            self.api = json.loads(self.api.content)

    def removeQuotes(self, text):
        text = text.replace('"', "")
        return text

    def get_overview(self, link_name):
        self.overview = {}

        try:
            self.overview["vcard:organization-name"] = link_name.split("?=")[0]
        except:
            return None

        self.overview["isDomiciledIn"] = "NG"
        self.overview["bst:businessClassifier"] = [
            {"code": "", "description": link_name.split("?=")[-1], "label": ""}
        ]
        self.overview["bst:sourceLinks"] = [
            "https://naicom.gov.ng/insurance-industry/composite-companies/",
            "https://naicom.gov.ng/insurance-industry/general-companies/",
            "https://naicom.gov.ng/insurance-industry/life-companies/",
            "https://naicom.gov.ng/insurance-industry/takaful-companies/",
            "https://naicom.gov.ng/insurance-industry/re-insurance-companies/",
            "https://naicom.gov.ng/insurance-industry/licensed-brokers-companies/",
            "https://naicom.gov.ng/insurance-industry/loss-adjusters-companies/",
            "https://naicom.gov.ng/insurance-industry/micro-insurance/",
        ]

        self.overview["regulator_name"] = "National Insurance Commission"
        self.overview["regulatorAddress"] = {
            "fullAddress": "Plot 1239, Ladoke Akintola Boulevard, Garki II Abuja",
            "city": "Abuja",
            "country": "Naigeria",
        }
        self.overview["regulator_url"] = "https://naicom.gov.ng/about-us/"
        self.overview["RegulationStatus"] = "Authorised"
        self.overview["@source-id"] = self.NICK_NAME
        self.get_address(addr=link_name.split("?=")[1])

        return self.overview
