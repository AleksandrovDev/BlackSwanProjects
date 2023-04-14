import datetime
import hashlib
import json
import re


from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://ariregister.rik.ee"
    NICK_NAME = base_url.split("//")[-1]
    fields = ["overview", "officership", "documents", "Financial_Information"]
    overview = {}
    tree = None

    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    def getResultListFromResponse(self, response, type):
        if type == "API":
            data = json.loads(response.content)
            result = []
            for company in data["data"]:
                code = company["reg_code"]
                name = company["name"].replace(" ", "-")
                link = f"https://ariregister.rik.ee/eng/company/{code}/{name}"
                result.append(link)
            return result

    def getpages(self, searchquery):
        url = f"https://ariregister.rik.ee/eng/api/autocomplete?q={searchquery}&results=10&_=1641493419662"
        response = self.get_content(url, headers=self.header, method="GET")
        result = self.getResultListFromResponse(response, "API")
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
            if len(el) > 1:
                return el
            else:
                return el[0]
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
        codes = codes if type(codes) == list else [codes]
        desc = desc if type(desc) == list else [desc]
        labels = labels if type(labels) == list else [labels]
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

    def get_address(self, xpath, zipPattern=None):
        addr = self.get_by_xpath(xpath)
        if addr:
            addr = addr[0] if type(addr) == list else addr
            temp = {"fullAddress": addr + ", Estonia", "country": "Estonia"}
            zip = re.findall(zipPattern, addr)
            if zip:
                temp["zip"] = zip[0]
            try:
                temp["city"] = addr.split(", ")[1]
            except:
                pass
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
        if names:
            names = [i for i in names if i != ""]
        if names and dates:
            for name, date in zip(names, dates):
                temp = {"name": name, "valid_to": date}
                prev.append(temp)
        return prev

    def getFrombaseXpath(self, tree, baseXpath):
        pass

    def fillField(self, fieldName, xpath, test=False):
        el = self.get_by_xpath(xpath)
        if test:
            print(el)
        if el:
            if fieldName == "vcard:organization-name":
                self.overview[fieldName] = el.split("(")[0].strip()

            if fieldName == "hasActivityStatus":
                self.overview[fieldName] = el

            if fieldName == "lei:legalForm":
                self.overview[fieldName] = {"code": "", "label": el}

            if fieldName == "identifiers":
                if type(el) == list:
                    el = el[0]
                self.overview[fieldName] = {"trade_register_number": el}
            if fieldName == "map":
                self.overview[fieldName] = el[0] if type(el) == list else el

            if fieldName == "isIncorporatedIn":
                self.overview[fieldName] = self.reformat_date(el, "%d.%m.%Y")

            if fieldName == "sourceDate":
                self.overview[fieldName] = self.reformat_date(el, "%d.%m.%Y")

    def check_tree(self):
        print(self.tree.xpath("//text()"))

    def get_working_tree(self, link_name):
        self.tree = self.get_tree(
            link_name + "?active_tab=register", headers=self.header
        )

    def get_overview(self, link_name):
        self.overview = {}
        self.tree = self.get_tree(
            link_name + "?active_tab=register", headers=self.header
        )
        try:
            self.fillField(
                "vcard:organization-name", '//div[@class="h2 text-primary mb-2"]/text()'
            )
        except:
            return None
        self.overview["isDomiciledIn"] = "EE"
        self.overview["bst:sourceLinks"] = [link_name]

        self.fillField(
            "hasActivityStatus",
            '//div/text()[contains(., "Status")]/../following-sibling::div//text()',
        )
        self.fillField(
            "lei:legalForm",
            '//div/text()[contains(., "Legal form")]/../following-sibling::div//text()',
        )
        self.fillField(
            "identifiers",
            '//div/text()[contains(., "Registry code")]/../following-sibling::div//text()',
        )
        self.fillField(
            "map",
            '//div/text()[contains(., "Address")]/../following-sibling::div/a/@href',
        )
        self.fillField(
            "isIncorporatedIn",
            '//div/text()[contains(., "Registered")]/../following-sibling::div/text()',
        )

        self.get_business_class(
            '//div/text()[contains(., "EMTAK code")]/../following-sibling::div/text()',
            '//div/text()[contains(., "Area of activity")]/../following-sibling::div/text()',
            '//div/text()[contains(., "EMTAK code")]/../following-sibling::div/text()',
        )

        self.get_address(
            '//div/text()[contains(., "Address")]/../following-sibling::div/text()',
            zipPattern="\d{5}",
        )

        self.overview["sourceDate"] = datetime.datetime.today().strftime("%Y-%m-%d")

        self.overview["@source-id"] = self.NICK_NAME

        return self.overview

    def get_officership(self, link_name):
        self.get_working_tree(link_name)
        names = self.get_by_xpath(
            '//div/text()[contains(., "Right of representation")]/../following-sibling::div//tr/td[1]/text()'
        )
        roles = self.get_by_xpath(
            '//div/text()[contains(., "Right of representation")]/../following-sibling::div//tr/td[3]/text()'
        )
        off = []
        names = [names] if type(names) == str else names
        roles = [roles] if type(roles) == str else roles
        for n, r in zip(names, roles):
            home = {
                "name": n,
                "type": "individual",
                "officer_role": r,
                "status": "Active",
                "information_source": "E-Business Portal",
                "information_provider": "https://ariregister.rik.ee/index?lang=eng",
            }
            off.append(home)
        return off

    def get_documents(self, link_name):
        docs = []
        self.get_working_tree(link_name)
        docs_links = self.get_by_xpath('//div/a/text()[contains(., "PDF")]/../@href')
        docs_links = docs_links if type(docs_links) == list else [docs_links]
        docs_links = [f"{self.base_url}{i}" for i in docs_links]
        for doc in docs_links:
            temp = {"url": doc, "description": "Summary of company details"}
            docs.append(temp)
        return docs

    def get_financial_information(self, link_name):
        self.get_working_tree(link_name)
        fin = {}
        summ = self.get_by_xpath(
            '//div/text()[contains(., "Capital")]/../following-sibling::div//text()'
        )
        if summ:
            summ = re.findall("\d+", summ[0])
            if summ:
                fin["Summary_Financial_data"] = [
                    {
                        "summary": {
                            "currency": "Euro",
                            "balance_sheet": {
                                "authorized_share_capital": "".join(summ)
                            },
                        }
                    }
                ]
        return fin
