import datetime
import hashlib
import json
import re


from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "http://www.jucerja.rj.gov.br"
    NICK_NAME = "jucerja.rj.gov.br"
    fields = ["overview"]

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
        pages_parse = 4
        res_list = []
        for i in range(pages_parse):
            url = f"http://www.jucerja.rj.gov.br/Informacoes/PaginarEmpresasPublicas?pagina={i + 1}&ordenacao=nome&_=1640690440331"
            tree = self.get_tree(url, headers=self.header)
            names = self.get_by_xpath(
                tree, '//h4[@class="u-md-texto u-bold"]/text()', return_list=True
            )
            numb = self.get_by_xpath(
                tree,
                '//h5/text()[contains(., "NIRE:")]/../following-sibling::h6/text()',
                return_list=True,
            )
            for name, num in zip(names, numb):
                if searchquery.lower() in name.lower():
                    res_list.append(name + "?=" + num + "?=" + str(i + 1))
        return res_list

    def get_overview(self, link_name):
        company_name = link_name.split("?=")[0]
        company_num = link_name.split("?=")[1]
        page = link_name.split("?=")[-1]
        url = f"http://www.jucerja.rj.gov.br/Informacoes/PaginarEmpresasPublicas?pagina={page}&ordenacao=nome&_=1640690440331"
        tree = self.get_tree(url, headers=self.header)
        base_xpath = f'//h5/text()[contains(., "NIRE:")]/../following-sibling::h6/text()[contains(., "{company_num}")]/../../../..'
        company = {}

        try:
            orga_name = self.get_by_xpath(tree, base_xpath + "//h4/text()")
        except:
            return None

        if orga_name:
            company["vcard:organization-name"] = orga_name.strip()

        company["isDomiciledIn"] = "BR"
        company["bst:sourceLinks"] = [
            "http://www.jucerja.rj.gov.br/Informacoes/EmpresasPublicas"
        ]
        self.check_create(
            tree,
            base_xpath
            + '//h5/text()[contains(., "Status")]/../following-sibling::h6/text()',
            "hasActivityStatus",
            company,
        )

        buss_class = self.get_by_xpath(
            tree,
            base_xpath
            + '//h5/text()[contains(., "Qualifica")]/../following-sibling::h6/text()',
        )
        if buss_class:
            company["bst:businessClassifier"] = [
                {"code": "", "description": buss_class, "label": ""}
            ]
        addr = self.get_by_xpath(
            tree,
            base_xpath
            + '//h5/text()[contains(., "Endere")]/../following-sibling::h6/text()',
        )
        if addr:
            company["mdaas:RegisteredAddress"] = {
                "country": "Brasil",
                "fullAddress": addr + ", Brasil",
            }
        company["identifiers"] = {"other_company_id_number": company_num}
        vat = self.get_by_xpath(
            tree,
            base_xpath
            + '//h5/text()[contains(., "CNPJ")]/../following-sibling::h6/text()',
        )
        if vat:
            company["identifiers"]["vat_tax_number"] = vat

        company["bst:registrationId"] = company_num

        company["@source-id"] = self.NICK_NAME
        return company
