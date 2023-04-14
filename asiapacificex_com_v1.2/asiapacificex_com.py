import datetime
import hashlib
import json
import re

from geopy import Nominatim

from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://www.asiapacificex.com"
    NICK_NAME = "asiapacificex_com"
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
        url1 = "https://www.asiapacificex.com/?p=partner_vendor"
        url2 = "https://www.asiapacificex.com/?p=settlement"
        tree1 = self.get_tree(url1, headers=self.header)
        tree2 = self.get_tree(url2, headers=self.header)
        names1 = self.get_by_xpath(
            tree1,
            '//span[@class="member-title"]/text()[contains(., "Name:")]/../following-sibling::span/text()',
            return_list=True,
        )
        names2 = self.get_by_xpath(
            tree2,
            '//span[@class="member-title"]/text()[contains(., "Name:")]/../following-sibling::span/text()',
            return_list=True,
        )
        for name in names1:
            if searchquery.lower() in name.lower():
                res_list.append(url1 + "?=" + name)
        for name in names2:
            if searchquery.lower() in name.lower():
                res_list.append(url2 + "?=" + name)
        return res_list

    def get_address(self, tree, basex):
        address = self.get_by_xpath(
            tree,
            basex
            + '//div/span[@class="member-title"]/text()[contains(., "Address:")]/../following-sibling::span/text()',
        )
        try:
            country = address.split(" ")[-3:]
            country = " ".join(country)
            country = re.findall("[a-zA-Z\s][a-zA-Z\s][a-zA-Z\s]+", country)[-1].strip()
            geolocator = Nominatim(user_agent="anonymous@gmail.com")
        except:
            country = None
        temp_dict = {}
        if country and address:
            temp_dict["country"] = (
                geolocator.geocode(query=country, language="en")
                .raw.get("display_name")
                .split(", ")[-1]
            )
            if temp_dict["country"] == "United States":
                temp_dict["country"] = "USA"
            if temp_dict["country"] in address:
                temp_dict["fullAddress"] = address
            else:
                temp_dict["fullAddress"] = address + ", " + temp_dict["country"]
        elif address:
            temp_dict["fullAddress"] = address
        if temp_dict:
            return temp_dict
        else:
            return None

    def check_create(self, tree, xpath, title, dictionary, date_format=None):
        item = self.get_by_xpath(tree, xpath)
        if item:
            if date_format:
                item = self.reformat_date(item, date_format)
            dictionary[title] = item.strip()

    def get_overview(self, link_name):
        url = link_name.split("?=")[0]
        company_name = link_name.split("?=")[1]
        tree = self.get_tree(url, headers=self.header)
        company = {}

        try:
            orga_name = self.get_by_xpath(
                tree,
                f'//span[@class="member-title"]/text()[contains(., "Name:")]/../following-sibling::span/text()[contains(., "{company_name}")]',
            )
        except:
            return None
        if orga_name:
            company["vcard:organization-name"] = orga_name.strip()

        baseXpath = f'//span[@class="member-title"]/text()[contains(., "Name:")]/../following-sibling::span/text()[contains(., "{company_name}")]/../../../../../..'
        company["isDomiciledIn"] = "CN"
        logo = self.get_by_xpath(tree, baseXpath + "/div/img/@src")
        if logo:
            company["logo"] = self.base_url + "/" + logo

        company["hasActivityStatus"] = "Active"

        self.check_create(
            tree,
            baseXpath
            + '//div/span[@class="member-title"]/text()[contains(., "Url:")]/../following-sibling::span/a/@href',
            "hasURL",
            company,
        )

        self.check_create(
            tree,
            baseXpath
            + '//div/span[@class="member-title"]/text()[contains(., "Email:")]/../following-sibling::span/a/@data-email',
            "bst:email",
            company,
        )

        if "partner" in url:
            bus_class = self.get_by_xpath(tree, baseXpath + "/../../../..//h4/a/text()")
        else:
            bus_class = "SETTLEMENT BANKS"
        if bus_class:
            company["bst:businessClassifier"] = [
                {"code": "", "description": bus_class, "label": ""}
            ]

        tel = self.get_by_xpath(
            tree,
            baseXpath
            + '//div/span[@class="member-title"]/text()[contains(., "Tel:")]/../following-sibling::span/text()',
        )
        if tel:
            company["tr-org:hasRegisteredPhoneNumber"] = tel.split("/")[0].strip()

        address = self.get_address(tree, baseXpath)
        if address:
            company["mdaas:RegisteredAddress"] = address

        company["@source-id"] = self.NICK_NAME
        return company
