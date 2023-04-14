from datetime import datetime
import requests
import re
from lxml import etree
import base64


class Handler:
    API_BASE_URL = ""
    base_url = "https://legilux.public.lu/"
    NICK_NAME = "legilux.public.lu"
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

        if fetch_type is None or fetch_type == "":
            ids = self.get_pages(searchquery)

            if ids is not None:
                data = self.parse_pages(ids)
            else:
                data = []
            dataset = data

        else:
            data = self.fetch_by_field(searchquery)
            dataset = [data]
        return dataset

    def get_pages(self, searchquery):
        search_url = self.base_url + "/mesoc/entr/search/frame/index.php"
        day, month, year = datetime.today().strftime("%d-%m-%Y").split("-")
        data = {
            "ss_soc": f"{searchquery}",
            "sr_soc": "name",
            "sr_fj": "all",
            "sl_fj[]": "50",
            "sr_tp": "all",
            "sr_date": "all",
            "sl_d": "1",
            "sl_m": "1",
            "sl_y": f"{year}",
            "sl_d1": "1",
            "sl_m1": "1",
            "sl_y1": f"{year}",
            "sl_d2": f"{day}",
            "sl_m2": f"{month}",
            "sl_y2": f"{year}",
            "page_len": "100",
            "page": "result",
            "submit": "Chercher",
        }
        r = self.session.get(search_url, headers=self.browser_header, params=data)
        tree = etree.HTML(r.content)
        try:
            ids = tree.xpath('//td/input[@name="idm"]/@value')[:10]
            if len(ids) > 10:
                return ids[:10]
            else:
                return ids
        except:
            ids = []
        return ids

    def fetch_by_field(self, link):
        link = base64.b64decode(link).decode("utf-8")
        res = self.parse(link)
        return res

    def parse_pages(self, ids):
        rlist = []
        for id in ids:
            res = self.parse(id)
            if res is not None:
                rlist.append(res)
                if len(rlist) == 10:
                    break
        return rlist

    def parse_firm_name(self, tree):
        try:
            names = tree.xpath(
                '/html/body/table/table[2]//tr/td/a[@class="res1"]/text()'
            )
        except:
            return None, None
        if names:
            company_name = names[0]
            if len(names) > 1:
                previous_names = [{"name": name} for name in names[1:]]
                return company_name, previous_names
            else:
                return company_name, None

    def get_address(self, tree):
        address = {"country": "LUXEMBOURG"}
        adr = tree.xpath("/html/body/table/table[2]/tr[5]/td[2]/a/text()")
        adr = " ".join([i.strip() for i in adr])
        address["fullAddress"] = adr.strip()
        return address

    def get_incorporated(self, tree):
        date = tree.xpath(
            '/html/body/table/table[2]/tr[4]/td[2]/a[@class="res3"][1]/text()'
        )[0].strip()
        date = datetime.strptime(date, "%d.%m.%Y").strftime("%Y-%m-%d")
        return date

    def get_identifiers(self, tree):
        try:
            reg_no = tree.xpath(
                '/html/body/table/table[2]/tr[2]/td[2]/a[@class="res3"][1]/text()'
            )[0].strip()
        except:
            return False
        temp_dict = {"trade_register_number": reg_no}
        return temp_dict

    def get_lei(self, tree):
        temp_dict = {"code": ""}
        temp_dict["label"] = tree.xpath(
            '/html/body/table/table[2]/tr[3]/td[2]/a[@class="res3"][1]/text()'
        )[0].strip()
        return temp_dict

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
        data["documents"] = {
            "method": "GET",
            "url": self.API_BASE_URL
            + "?source="
            + base_url
            + "&url="
            + link2
            + "&fields=documents",
        }
        return data

    def parse(self, id):
        search_url = self.base_url + "/mesoc/entr/search/frame/index.php"
        params = {
            "ss_soc": "bank",
            "sc_soc": "",
            "sr_soc": "name",
            "sr_fj": "all",
            "sl_fj[0]": "50",
            "sr_tp": "all",
            "sr_date": "all",
            "sl_d": "1",
            "sl_m": "1",
            "sl_y": "2021",
            "sl_d1": "1",
            "sl_m1": "1",
            "sl_y1": "2021",
            "sl_d2": "02",
            "sl_m2": "11",
            "sl_y2": "2021",
            "page_len": "100",
            "page_no": "1",
            "idm": f"{id}",
            "page": "result",
            "select_soc": "true",
            "submit": "Choisir",
        }
        r = self.session.get(search_url, params=params)
        tree = etree.HTML(r.content)
        edd = {}

        if self.FETCH_TYPE == "overview" or self.FETCH_TYPE == "":
            try:
                orga_name, previous_names = self.parse_firm_name(tree)
            except:
                return None
            company = {"vcard:organization-name": orga_name, "isDomiciledIn": "LU"}
            if previous_names:
                company["previous_names"] = previous_names

            try:
                company["mdaas:RegisteredAddress"] = self.get_address(tree)
            except:
                pass

            try:
                company["isIncorporatedIn"] = self.get_incorporated(tree)
            except:
                pass
            try:
                company["identifiers"] = self.get_identifiers(tree)
            except:
                pass
            try:
                company["lei:legalForm"] = self.get_lei(tree)
            except:
                pass
            company["@source-id"] = "legilux.public.lu"

            edd["overview"] = company

        elif self.FETCH_TYPE == "documents":
            documents = []
            try:
                doc_count = len(tree.xpath("/html/body/table/table[3]//tr")) - 1
                for item in range(doc_count):
                    doc = {}
                    try:
                        doc["url"] = tree.xpath(
                            f"/html/body/table/table[3]/td[{1 + (item * 6)}]/a/@href"
                        )[0].strip()
                    except:
                        continue
                    try:
                        date = tree.xpath(
                            f"/html/body/table/table[3]/td[{2 + (item * 6)}]/a/text()"
                        )[0].strip()
                        doc["date"] = datetime.strptime(date, "%d.%m.%Y").strftime(
                            "%Y-%m-%d"
                        )
                    except:
                        pass
                    try:
                        doc["description"] = tree.xpath(
                            f"/html/body/table/table[3]/td[{5 + (item * 6)}]/a/text()"
                        )[0].strip()
                    except:
                        pass

                    if doc:
                        documents.append(doc)
            except:
                pass
            if documents:
                edd["documents"] = documents
        edd["_links"] = self.links(id)
        return edd
