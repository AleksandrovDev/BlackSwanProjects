import datetime
import random
import string
import time

import numpy as np
from geopy import Nominatim

from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://www.sedar.com"
    NICK_NAME = "sedar.com"
    fields = ["overview"]

    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Safari/537.36",
    }

    def get_by_xpath(self, tree, xpath, return_list=False):
        try:
            el = tree.xpath(xpath)
        except Exception as e:
            print(e)
            return None
        if el:
            if return_list:
                return el
            else:
                return el[0].strip()
        else:
            return None

    def getpages(self, searchquery):
        searchquery = searchquery.lower()
        return_links = []
        if searchquery[0].isalpha():
            url = f"https://www.sedar.com/issuers/company_issuers_{searchquery.lower()[0]}_en.htm"
        elif searchquery[0].isdigit():
            url = f"https://www.sedar.com/issuers/company_issuers_nc_en.htm"
        else:
            return []
        tree = self.get_tree(url, headers=self.header, timeout=5)
        names = self.get_by_xpath(tree, '//li[@class="rt"]/a/text()', return_list=True)
        links = self.get_by_xpath(tree, '//li[@class="rt"]/a/@href', return_list=True)
        if links and names:
            for company in range(len(names)):
                if searchquery in names[company].lower():
                    return_links.append(self.base_url + links[company])
        return return_links

    def get_business_classifier(self, tree):
        business_classifier = self.get_by_xpath(
            tree,
            '//td[@class="bt"]/text()[contains(., "Industry Classification:")]/../following-sibling::td/text()',
        )
        if business_classifier:
            temp_dict = {"code": "", "description": business_classifier, "label": ""}
            return temp_dict
        else:
            return None

    def get_address(self, tree, postal=False):
        street = self.get_by_xpath(
            tree,
            '//td[@class="bt"]/text()[contains(., "Head Office Address:")]/../following-sibling::td/text()[1]',
        )
        street2 = self.get_by_xpath(
            tree,
            '//td[@class="bt"]/text()[contains(., "Head Office Address:")]/../following-sibling::td/text()[2]',
        )
        street3 = self.get_by_xpath(
            tree,
            '//td[@class="bt"]/text()[contains(., "Head Office Address:")]/../following-sibling::td/text()[3]',
        )
        street4 = self.get_by_xpath(
            tree,
            '//td[@class="bt"]/text()[contains(., "Head Office Address:")]/../following-sibling::td/text()[4]',
        )
        if postal:
            street = self.get_by_xpath(
                tree,
                '//td[@class="bt"]/text()[contains(., "Mailing Address:")]/../following-sibling::td/text()[1]',
            )
            street2 = self.get_by_xpath(
                tree,
                '//td[@class="bt"]/text()[contains(., "Mailing Address:")]/../following-sibling::td/text()[2]',
            )
            street3 = self.get_by_xpath(
                tree,
                '//td[@class="bt"]/text()[contains(., "Mailing Address:")]/../following-sibling::td/text()[3]',
            )
            street4 = self.get_by_xpath(
                tree,
                '//td[@class="bt"]/text()[contains(., "Mailing Address:")]/../following-sibling::td/text()[4]',
            )

        geolocator = Nominatim(user_agent="http")
        if street:
            if street4:
                temp_dict = {
                    "zip": street4,
                    "streetAddress": street + " " + street2,
                    "city": street3.split(",")[0],
                    "fullAddress": street
                    + " "
                    + street2
                    + " "
                    + street3
                    + " "
                    + street4,
                }
                temp_dict["country"] = (
                    geolocator.geocode(temp_dict["city"], language="en")
                    .raw["display_name"]
                    .split(",")[-1]
                    .strip()
                )
                return temp_dict
            else:
                temp_dict = {
                    "zip": street3,
                    "streetAddress": street,
                    "city": street2.split(",")[0],
                    "fullAddress": street + " " + street2 + " " + street3,
                }
                temp_dict["country"] = (
                    geolocator.geocode(temp_dict["city"], language="en")
                    .raw["display_name"]
                    .split(",")[-1]
                    .strip()
                )
                return temp_dict
        else:
            return None

    def reformat_date(self, date, format):
        date = datetime.datetime.strptime(date, format).strftime("%Y-%m-%d")
        return date

    def check_create(self, tree, xpath, title, dictionary):
        item = self.get_by_xpath(tree, xpath)
        if item:
            dictionary[title] = item

    def get_stock(self, tree):
        stock = self.get_by_xpath(
            tree,
            '//td[@class="bt"]/text()[contains(., "Stock Exchange:")]/../following-sibling::td/text()',
        )
        symbol = self.get_by_xpath(
            tree,
            '//td[@class="bt"]/text()[contains(., "Stock Symbol:")]/../following-sibling::td/text()',
        )
        if stock and stock != "N/A":
            temp_dict = {"main_exchange": stock}
            if symbol:
                temp_dict["ticket_symbol"] = symbol
            return temp_dict
        else:
            return None

    def get_overview(self, link):
        tree = self.get_tree(link, self.header, timeout=5)
        company = {}
        try:
            orga_name = self.get_by_xpath(tree, '//font[@class="btt"]/strong/text()')
        except:
            return None
        if orga_name:
            company["vcard:organization-name"] = orga_name

        self.check_create(
            tree,
            '//td[@class="bt"]/text()[contains(., "Business e-mail address:")]/../following-sibling::td/text()',
            "bst:email",
            company,
        )

        business_classifier = self.get_business_classifier(tree)
        if business_classifier:
            company["bst:businessClassifier"] = [business_classifier]

        address = self.get_address(tree)
        if address:
            company["mdaas:RegisteredAddress"] = address

        foundation = self.get_by_xpath(
            tree,
            '//td[@class="bt"]/text()[contains(., "Date of Formation:")]/../following-sibling::td/text()',
        )

        if foundation:
            company["hasLatestOrganizationFoundedDate"] = self.reformat_date(
                foundation, "%b %d %Y"
            )

        self.check_create(
            tree,
            '//td[@class="bt"]/text()[contains(., "Telephone Number:")]/../following-sibling::td/text()',
            "r-org:hasRegisteredPhoneNumber",
            company,
        )

        self.check_create(
            tree,
            '//td[@class="bt"]/text()[contains(., "Jurisdiction Where Formed:")]/../following-sibling::td/text()',
            "registeredIn",
            company,
        )

        self.check_create(
            tree,
            '//td[@class="bt"]/text()[contains(., "Fax Number:")]/../following-sibling::td/text()',
            "hasRegisteredFaxNumber",
            company,
        )

        stock = self.get_stock(tree)
        if stock:
            company["bst:stock_info"] = stock

        identifiers = self.get_by_xpath(
            tree,
            '//td[@class="bt"]/text()[contains(., "CUSIP Number:")]/../following-sibling::td/text()',
        )
        if identifiers and identifiers != "Transfer Agent:":
            company["identifiers"] = {"other_company_id_number": identifiers}

        if company["mdaas:RegisteredAddress"]["country"]:
            company["isDomiciledIn"] = company["mdaas:RegisteredAddress"]["country"]

        postal = self.get_address(tree, postal=True)
        if postal:
            company["mdaas:PostalAddress"] = postal
        company["@source-id"] = self.NICK_NAME

        return company
