import datetime
import hashlib
import json
import re


from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://jucees.es.gov.br"
    NICK_NAME = "jucees.es.gov.br"
    fields = ["overview", "officership"]

    header = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
    }

    def get_by_xpath(self, tree, xpath, return_list=False):
        try:
            el = tree.xpath(xpath)
        except Exception as e:
            print(e)
            return None
        if el:
            if return_list:
                return [i.strip() for i in el]
            else:
                return el[0].strip()
        else:
            return None

    def check_tree(self, tree):
        print(tree.xpath("//text()"))

    def check_create(self, tree, xpath, title, dictionary, date_format=None):
        item = self.get_by_xpath(tree, xpath)
        if item:
            if date_format:
                item = self.reformat_date(item, date_format)
            dictionary[title] = item.strip()

    def getpages(self, searchquery):
        url = "https://jucees.es.gov.br/consulta-empresas"

        searchquery = searchquery.replace(" ", "+")
        url_auto = f"https://apps.jucees.es.gov.br/consulta_empresas/php/autocomplete.php?term=&term={searchquery}"
        res = self.get_content(url_auto, headers=self.header)
        companies = json.loads(res.text)

        if not companies:
            return None
        rse = []
        for company in companies:
            temp = company["nire"] + "?=" + str(company["cnpj"])
            rse.append(temp)
        return rse

    def reformat_date(self, date, format):
        date = datetime.datetime.strptime(date.strip(), format).strftime("%Y-%m-%d")
        return date

    def get_business_class(self, tree):
        res = []
        codes = self.get_by_xpath(
            tree,
            '//div/text()[contains(.,"Atividade Econômica Principal")]/../following-sibling::div//tr/td[1]/small/text()',
            return_list=True,
        )
        desc = self.get_by_xpath(
            tree,
            '//div/text()[contains(.,"Atividade Econômica Principal")]/../following-sibling::div//tr/td[2]/small/text()',
            return_list=True,
        )
        for c, d in zip(codes, desc):
            temp = {"code": c, "description": d}
            res.append(temp)
        return res

    def get_address(self, tree):
        addr = self.get_by_xpath(
            tree,
            '//div/text()[contains(.,"Endereço")]/../following-sibling::div/small/text()',
        )
        if not addr:
            return None
        splitted = addr.split(",")
        temp = {
            "fullAddress": addr.replace(", ,", ",") + " Portuguese",
            "country": "Portuguese",
        }
        zip = self.get_by_xpath(
            tree,
            '//div/text()[contains(.,"CEP")]/../following-sibling::div/small/text()',
        )
        if zip:
            temp["zip"] = zip
        if splitted[0] != "":
            temp["streetAddress"] = splitted[0]
        if splitted[2] != "":
            temp["city"] = splitted[2]
        return temp

    def get_overview(self, link_name):
        data = {
            "nire": link_name.split("?=")[0],
            "nr_cgc": link_name.split("?=")[1],
            "enviar": "",
        }
        tree = self.get_tree(
            "https://apps.jucees.es.gov.br/consulta_empresas/php/consulta.php",
            headers=self.header,
            data=data,
            method="POST",
        )

        company = {}
        try:
            orga_name = self.get_by_xpath(
                tree,
                '//div/text()[contains(.,"Nome Empresarial")]/../following-sibling::div/small/text()',
            )
        except:
            return None
        if orga_name:
            company["vcard:organization-name"] = orga_name.strip()
        company["isDomiciledIn"] = "PT"
        self.check_create(
            tree,
            '//div/text()[contains(.,"Nome Empresarial")]',
            "vcard:organizationtradename",
            company,
        )

        self.check_create(
            tree,
            '//div/text()[contains(.,"Nome Empresarial")]/../following-sibling::div/small/text()',
            "localName",
            company,
        )
        self.check_create(
            tree,
            '//div/text()[contains(.,"Situação")]/../following-sibling::div/small/text()',
            "hasActivityStatus",
            company,
        )
        self.check_create(
            tree,
            '//div/text()[contains(.,"Término da Atividade")]/../following-sibling::div/small/text()',
            "dissolutionDate",
            company,
            date_format="%d/%m/%Y",
        )
        bus_class = self.get_business_class(tree)
        if bus_class:
            company["bst:businessClassifier"] = bus_class

        company["identifiers"] = {"trade_register_number": link_name.split("?=")[1]}
        self.check_create(
            tree,
            '//div/text()[contains(.,"Endereço")]/../following-sibling::div/a/@href',
            "map",
            company,
        )
        self.check_create(
            tree,
            '//div/text()[contains(.,"Término da Atividade")]/../following-sibling::div/a/@href',
            "regExpiryDate",
            company,
            date_format="%d/%B/%Y",
        )
        addr = self.get_address(tree)
        if addr:
            company["mdaas:RegisteredAddress"] = addr

        company["@source-id"] = self.NICK_NAME

        return company

    def get_officership(self, link_name):
        data = {
            "nire": link_name.split("?=")[0],
            "nr_cgc": link_name.split("?=")[1],
            "enviar": "",
        }
        tree = self.get_tree(
            "https://apps.jucees.es.gov.br/consulta_empresas/php/consulta.php",
            headers=self.header,
            data=data,
            method="POST",
        )
        names = self.get_by_xpath(
            tree,
            '//div/text()[contains(.,"Dados dos Sócios")]/../following-sibling::div//tr/td[1]/small/text()',
            return_list=True,
        )
        roles = self.get_by_xpath(
            tree,
            '//div/text()[contains(.,"Dados dos Sócios")]/../following-sibling::div//tr/td[2]/small/text()',
            return_list=True,
        )
        off = []
        for n, r in zip(names, roles):
            home = {
                "name": n,
                "type": "individual",
                "officer_role": r,
                "occupation": r,
                "status": "Active",
            }
            off.append(home)
        return off
