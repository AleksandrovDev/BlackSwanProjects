import datetime
import hashlib
import json
import re


from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "http://qkb.gov.al"
    NICK_NAME = "qkb.gov.al"
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
        res_list = []
        url = "https://qkb.gov.al/search/search-in-trade-register/search-for-subject/"
        tree = self.get_tree(url, headers=self.header, verify=False)
        hidden = tree.xpath('//input[@type="hidden"]/@value')[1:]
        name = tree.xpath('//input[@type="hidden"]/@name')[1:]
        data = dict(zip(name, hidden))
        data["SubjectName"] = searchquery
        data["IdentificationNumber"] = ""
        data["FullAddress"] = ""
        tree = self.get_tree(
            url, headers=self.header, verify=False, method="POST", data=data
        )

        names = self.get_by_xpath(
            tree, '//div[@class="result-element"]//span[2]/text()', return_list=True
        )
        for name in names:
            if searchquery.lower() in name.lower():
                res_list.append(name)
        return res_list

    def get_overview(self, link_name):
        company_name = link_name
        company_name = company_name.split("/")[0].strip()
        url = "https://qkb.gov.al/search/search-in-trade-register/search-for-subject/"
        tree = self.get_tree(url, headers=self.header, verify=False)
        hidden = tree.xpath('//input[@type="hidden"]/@value')[1:]
        name = tree.xpath('//input[@type="hidden"]/@name')[1:]
        data = dict(zip(name, hidden))
        data["SubjectName"] = company_name
        data["IdentificationNumber"] = ""
        data["FullAddress"] = ""
        tree = self.get_tree(
            url, headers=self.header, verify=False, method="POST", data=data
        )
        company = {}

        try:
            orga_name = self.get_by_xpath(
                tree,
                f'//div[@class="result-element"]//span[2]/text()[contains(., "{company_name}")]',
            )
        except:
            return None
        print(orga_name)
        if orga_name:
            company["vcard:organization-name"] = orga_name.strip()
        baseXpath = f'//div[@class="result-element"]//span[2]/text()[contains(., "{company_name}")]/../../..'
        company["isDomiciledIn"] = "AL"
        company["regulator_name"] = "National Business Center"
        company["regulator_url"] = self.base_url
        company["regulationStatus"] = "Authorised"
        iden = self.get_by_xpath(tree, baseXpath + "/div//span[1]/text()")
        if iden:
            company["identifiers"] = {"vat_tax_number": iden}
        service = self.get_by_xpath(tree, baseXpath + "/div//span[3]/text()")
        if service and "Ju lutem paraqituni prane" not in service:
            company["Service"] = {"areaServed": "", "serviceType": service}
        company["hasActivityStatus"] = "Active"
        tree_addr = self.get_tree(
            "https://qkb.gov.al/contact/contact-us/", headers=self.header, verify=False
        )
        addres = self.get_by_xpath(
            tree_addr, '//div[@class="journal-content-article"]//p[3]/text()'
        )
        if addres:
            company["regulatorAddress"] = {
                "fullAddress": addres,
                "city": addres.split(",")[-1].strip(),
                "country": "Albania",
            }
        company["@source-id"] = self.NICK_NAME
        return company
