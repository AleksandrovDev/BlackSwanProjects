import datetime
import hashlib
import json
import re


from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://www.e-register.am"
    NICK_NAME = "e-register.am"
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

    def getpages(self, searchquery):
        url = "https://www.e-register.am/en/search"
        data = {"q_comp": {searchquery}, "comp_types": "", "search_type": "exact"}
        tree = self.get_tree(
            url, headers=self.header, data=data, method="POST", verify=False
        )

        links = self.get_by_xpath(
            tree, '//div[@class="search-center"]//td/a/@href', return_list=True
        )
        links = [self.base_url + i for i in links]
        return links

    def check_create(self, tree, xpath, title, dictionary, date_format=None):
        item = self.get_by_xpath(tree, xpath)
        if item:
            if date_format:
                item = self.reformat_date(item, date_format)
            dictionary[title] = item.strip()

    def get_overview(self, link_name):
        tree = self.get_tree(link_name, headers=self.header, verify=False)
        company = {}
        try:
            orga_name = self.get_by_xpath(tree, '//div[@class="compname"]//text()')
        except:
            return None
        if orga_name:
            company["vcard:organization-name"] = orga_name.strip()
        company["isDomiciledIn"] = "AM"
        self.check_create(
            tree,
            '//td[@class="fnam"]/text()[contains(., "Status")]/../following-sibling::td/text()',
            "hasActivityStatus",
            company,
        )
        incorp = self.get_by_xpath(
            tree,
            '//td[@class="fnam"]/text()[contains(., "Registration number:")]/../following-sibling::td/text()',
        )
        if incorp:
            company["isIncorporatedIn"] = incorp.split("/")[-1].strip()

        iden = self.get_by_xpath(
            tree,
            '//td[@class="fnam"]/text()[contains(., "Tax ID:")]/../following-sibling::td/text()',
        )
        other_id = self.get_by_xpath(
            tree,
            '//td[@class="fnam"]/text()[contains(., "Z-Code:")]/../following-sibling::td/text()',
        )
        if iden:
            company["identifiers"] = {"vat_tax_number": iden}
            if other_id:
                company["identifiers"]["other_company_id_number"] = other_id

        reg_id = self.get_by_xpath(
            tree,
            '//td[@class="fnam"]/text()[contains(., "Registration number:")]/../following-sibling::td/text()',
        )
        if reg_id:
            company["bst:registrationId"] = reg_id.split("/")[0].strip()

        company["@source-id"] = self.NICK_NAME

        return company
