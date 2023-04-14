from datetime import datetime
import requests
import re
from lxml import etree
import base64


class Handler:
    API_BASE_URL = ""
    base_url = "https://eservice.egov.sc"
    NICK_NAME = "eservice.egov.sc"
    FETCH_TYPE = ""
    TAG_RE = re.compile(r"<[^>]+>")

    session = requests.session()
    browser_header = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.109 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def Execute(self, searchquery, fetch_type, action, API_BASE_URL):
        self.FETCH_TYPE = fetch_type
        self.API_BASE_URL = API_BASE_URL
        tree = self.get_pages(searchquery)
        if fetch_type is None or fetch_type == "":
            if tree is not None:
                data = self.parse_pages(tree)
            else:
                data = []
            dataset = data
        else:
            data = self.fetch_by_field(searchquery, tree)
            dataset = [data]
        return dataset

    def get_pages(self, searchquery):
        search_url = self.base_url + "/BizRegistration/WebSearchBusiness.aspx"
        r = self.session.get(search_url, headers=self.browser_header)

        data, tree = self.prepare_data(r, searchquery)
        r = self.session.post(search_url, data=data, headers=self.browser_header)
        data, tree = self.prepare_data(r, searchquery)

        if tree.xpath('//*[contains(text(), "0 Results Found")]'):
            return False
        else:
            return tree

    def prepare_data(self, r, searchquery):
        tree = etree.HTML(r.content)
        data = {i.get("name"): i.get("value", "") for i in tree.xpath("//input")}
        data["ctl00$ContentPlaceHolder1$txtSearch"] = searchquery
        data["ctl00$ContentPlaceHolder1$btnSearch"] = "Search"
        return data, tree

    def fetch_by_field(self, link, tree):
        link_list = base64.b64decode(link).decode("utf-8")
        link = link_list.split("?reg_no=")[0]
        id = link_list.split("?reg_no=")[1]
        res = self.parse(link, id, True)
        return res

    def parse_pages(self, tree):
        rlist = []
        for company in range(10):
            res = self.parse(company, tree)
            if res is not None:
                rlist.append(res)
                if len(rlist) == 10:
                    break
        return rlist

    def get_business_classifier(self, tree, company_number):
        temp_dict = {}
        temp_dict["code"] = ""
        try:
            temp_dict["description"] = tree.xpath(
                f'//*[@id="tableResults"]/tbody/tr[{company_number}]/td[3]/text()'
            )[0].strip()
        except:
            temp_dict["description"] = ""
        temp_dict["label"] = ""
        return [temp_dict]

    def get_lei_legal_form(self, tree, company_number):
        try:
            entity_type = tree.xpath(
                f'//*[@id="tableResults"]/tbody/tr[{company_number}]/td[4]/text()'
            )[0].strip()
        except:
            return False
        if entity_type == "Undefined":
            return False
        else:
            temp_dict = {"code": "", "label": entity_type}
            return temp_dict

    def get_identifiers(self, tree, company_number):
        try:
            reg_no = tree.xpath(
                f'//*[@id="tableResults"]/tbody/tr[{company_number}]/td[1]/text()'
            )[0].strip()
        except:
            return False
        temp_dict = {"trade_register_number": reg_no}
        return temp_dict

    def get_source_date(self, tree):
        try:
            source_date = tree.xpath('//td[@class="footer"]/text()')[2].strip()
        except:
            return False
        source_date = source_date.split(":")[1].strip()
        source_date = source_date.split(" ")
        date = "".join([i for i in source_date[0] if i.isdigit()])
        source_date = datetime.strptime(
            f"{date} {source_date[1]} {source_date[2]}", "%d %B %Y"
        ).strftime("%Y-%m-%d")
        return source_date

    def parse(self, company_number, tree, fetch_by_field=False):
        if fetch_by_field:
            id = tree
            tree = self.get_pages(company_number)
            row = 1
            while True:
                try:
                    company_code = tree.xpath(
                        f'//*[@id="tableResults"]/tbody/tr[{row}]/td[1]/text()'
                    )[0].strip()
                except:
                    break
                if company_code == id:
                    company_number = row - 1
                    break
                else:
                    row += 1
        edd = {}
        if self.FETCH_TYPE == "overview" or self.FETCH_TYPE == "":
            try:
                orga_name = tree.xpath(
                    f'//table[@id="tableResults"]/tbody/tr[{company_number + 1}]/td[2]/text()'
                )[0].strip()
            except:
                return None
            company = {"vcard:organization-name": orga_name, "isDomiciledIn": "SC"}
            business_classifier = self.get_business_classifier(tree, company_number + 1)
            if business_classifier:
                company["bst:businessClassifier"] = business_classifier
            lei_legal_form = self.get_lei_legal_form(tree, company_number + 1)
            if lei_legal_form:
                company["lei:legalForm"] = lei_legal_form
            identifiers = self.get_identifiers(tree, company_number + 1)
            if identifiers:
                company["identifiers"] = identifiers
            source_date = self.get_source_date(tree)
            if source_date:
                company["sourceDate"] = source_date
            edd["overview"] = company

        try:
            name = company["vcard:organization-name"]
            id = company["identifiers"]["trade_register_number"]
            link = name + "?reg_no=" + id
            edd["_links"] = self.links(link)
        except:
            pass
        return edd

    def links(self, link):
        data = {}
        base_url = self.NICK_NAME
        link2 = base64.b64encode(link.encode("utf-8"))
        link2 = link2.decode("utf-8")
        data["overview"] = {
            "method": "GET",
            "url": self.API_BASE_URL
            + "?source="
            + base_url
            + "&url="
            + link2
            + "&fields=overview",
        }
        return data
