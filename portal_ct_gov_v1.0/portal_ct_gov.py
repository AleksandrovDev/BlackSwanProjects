import datetime
import hashlib
import json
import re
from lxml import etree

import pandas as pd
import numpy as np


from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://portal.ct.gov"
    NICK_NAME = base_url.split("//")[-1]
    fields = ["overview"]
    overview = {}
    tree = None
    api = None

    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
    }

    def getpages(self, searchquery):
        result = []
        url = f"https://portal.ct.gov/-/media/CID/1_Lists/Licencom.pdf"
        df = self.getpages_pdf(
            searchquery=searchquery, pages="all", file_base_url=url, search_column="1"
        )
        desired_width = 620

        pd.set_option("display.width", desired_width)

        np.set_printoptions(linewidth=desired_width)

        pd.set_option("display.max_columns", 10)

        for page in df:
            col1 = page.iloc[:, 0].astype(str).str.replace("\r", " ")
            col2 = page.iloc[:, 1].astype(str).str.replace("\r", " ")
            col3 = page.iloc[:, 2].astype(str).str.replace("\r", " ")
            col4 = page.iloc[:, 3].astype(str).str.replace("\r", " ")
            col5 = page.iloc[:, 4].astype(str).str.replace("\r", " ")
            for c1, c2, c3, c4, c5 in zip(col1, col2, col3, col4, col5):
                if str(c1) != "nan":
                    if searchquery.lower() in c1.lower():
                        result.append(f"{c1}=?{c2}=?{c3}=?{c4}=?{c5}")

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
                el = [i for i in el if i != "" and i != "n/a"]
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
            addr = addr[1]

            if "\n" in addr:
                splitted_addr = addr.split("\n")
            if ", " in addr:
                splitted_addr = addr.split(", ")

            addr = addr.replace("\n", " ")
            addr = addr[0] if type(addr) == list else addr
            temp = {
                "fullAddress": addr,
            }
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

    def getSpecialAddress(self):
        streetAddr = self.get_by_xpath(
            '//h6/text()[contains(., "Registered address")]/../following-sibling::div[1]//div[@class="row"]/div/text()[contains(., "Street address")]/../following-sibling::div[1]/text()'
        )
        temp = {}
        if streetAddr:
            temp["streetAddress"] = streetAddr[0]
        city = self.get_by_xpath(
            '//h6/text()[contains(., "Registered address")]/../following-sibling::div[1]//div[@class="row"]/div/text()[contains(., "Locality")]/../following-sibling::div[1]/text()'
        )
        if city:
            temp["city"] = city[0]

        zip = self.get_by_xpath(
            '//h6/text()[contains(., "Registered address")]/../following-sibling::div[1]//div[@class="row"]/div/text()[contains(., "Postal code")]/../following-sibling::div[1]/text()'
        )
        if zip:
            temp["zip"] = zip[0]

        country = self.get_by_xpath(
            '//h6/text()[contains(., "Registered address")]/../following-sibling::div[1]//div[@class="row"]/div/text()[contains(., "Country")]/../following-sibling::div[1]/text()'
        )
        if country:
            temp["country"] = country[0]

        if temp:
            temp["fullAddress"] = ", ".join(temp.values())
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

    def fill_identifiers(
        self,
        xpathTradeRegistry=None,
        xpathOtherCompanyId=None,
        xpathInternationalSecurIdentifier=None,
        xpathLegalEntityIdentifier=None,
        xpathSWIFT=None,
    ):
        try:
            temp = self.overview["identifiers"]
        except:
            temp = {}

        if xpathTradeRegistry:
            trade = self.get_by_xpath(xpathTradeRegistry)
            if trade:
                temp["trade_register_number"] = trade[0]
        if xpathOtherCompanyId:
            other = self.get_by_xpath(xpathOtherCompanyId)
            if other:
                temp["other_company_id_number"] = other[0]
        if xpathInternationalSecurIdentifier:
            el = self.get_by_xpath(xpathInternationalSecurIdentifier)
            if el:
                temp["international_securities_identifier"] = el[0]
        if xpathLegalEntityIdentifier:
            el = self.get_by_xpath(xpathLegalEntityIdentifier)
            if el:
                temp["legal_entity_identifier"] = el[0]
        if xpathSWIFT:
            el = self.get_by_xpath(xpathSWIFT)
            if el:
                temp["swift_code"] = el[0]

        if temp:
            self.overview["identifiers"] = temp

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
                if type(el) == list:
                    el = " ".join(el)
                el = "".join(el.split("Registered Charity Number: ")[1]).split(" ")[0]
                if el:
                    self.overview[fieldName] = el.replace("\n", "")

            if fieldName == "Service":
                self.overview[fieldName] = {"serviceType": el}

            if fieldName == "regExpiryDate":
                el = el.split(" ")[0]
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
                self.overview[fieldName] = {"code": el, "label": ""}

            if fieldName == "identifiers":
                self.overview[fieldName] = {"other_company_id_number": el}
            if fieldName == "map":
                self.overview[fieldName] = el[0] if type(el) == list else el

            if fieldName == "dissolutionDate":
                self.overview[fieldName] = el

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

            if fieldName == "bst:description":
                if type(el) == list:
                    self.overview[fieldName] = " ".join(el)
                else:
                    self.overview[fieldName] = el

            if fieldName == "hasURL" and el != "http://":
                self.overview[fieldName] = el

            if fieldName == "tr-org:hasRegisteredPhoneNumber":
                if type(el) == list and len(el) > 1:
                    el = el[0]
                self.overview[fieldName] = el

            if fieldName == "logo":
                self.overview["logo"] = el
            if fieldName == "bst:email":
                self.overview["bst:email"] = el
            if fieldName == "registeredIn":
                self.overview["registeredIn"] = el
            if fieldName == "hasRegisteredFaxNumber":
                self.overview["hasRegisteredFaxNumber"] = el

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
                link_name, headers=self.header, method=method, data=data
            )
            self.api = json.loads(self.api.content)

    def removeQuotes(self, text):
        text = text.replace('"', "")
        return text

    def get_overview(self, link_name):
        self.overview = {}

        self.overview["isDomiciledIn"] = "US"

        self.overview["@source-id"] = self.NICK_NAME
        self.overview["bst:sourceLinks"] = [
            "https://portal.ct.gov/-/media/CID/1_Lists/Licencom.pdf"
        ]
        self.overview[
            "bst:registryURI"
        ] = "https://portal.ct.gov/-/media/CID/1_Lists/Licencom.pdf"

        self.overview["vcard:organization-name"] = link_name.split("=?")[0]
        self.overview["registeredIn"] = link_name.split("=?")[2]
        self.overview["bst:businessClassifier"] = [
            {
                "code": link_name.split("=?")[1],
                "description": link_name.split("=?")[4],
                "label": "NAIC",
            }
        ]
        self.overview["regulator_name"] = "Connecticut Insurance Department"
        self.overview["identifiers"] = {
            "other_company_id_number": link_name.split("=?")[1]
        }
        self.overview["regulator_url"] = self.base_url
        self.overview["RegulationStatus"] = "Authorised"

        return self.overview
