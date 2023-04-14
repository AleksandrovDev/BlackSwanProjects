import datetime
import re

from geopy import Nominatim

from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://www.cbc.gov.tw"
    NICK_NAME = "cbc.gov.tw"
    fields = ["overview"]

    header = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
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
                return el[0]
        else:
            return None

    def getpages(self, searchquery):
        url = f"https://www.cbc.gov.tw/en/lp-495-2.html"
        tree = self.get_tree(url, headers=self.header)
        link_list = self.get_by_xpath(
            tree, '//table[@class="rwd-table"]//a/@href', return_list=True
        )
        company_names = []
        if link_list:
            link_list = [self.base_url + i for i in link_list]
            for link in link_list:
                tree = self.get_tree(link, headers=self.header)
                rows = self.get_by_xpath(
                    tree, '//section[@class="cp"]//tr/td[2]', return_list=True
                )

                for row in range(len(rows)):
                    name = self.get_by_xpath(
                        tree, f'//section[@class="cp"]//tr[{row + 2}]/td[2]/a/text()'
                    )

                    if not name:
                        name = self.get_by_xpath(
                            tree,
                            f'//section[@class="cp"]//tr[{row + 2}]/td[2]/text()[1]',
                        )

                    if searchquery in name:
                        company_names.append(link + "?=" + name)
        return company_names

    def get_business_classifier(self, tree):
        business_classifier = self.get_by_xpath(tree, "//h2/text()")
        if business_classifier:
            temp_dict = {"code": "", "description": business_classifier, "label": ""}
            return [temp_dict]
        else:
            return None

    def get_address(self, tree, base_xpath, postal=False):
        address = self.get_by_xpath(tree, base_xpath + "td[2]/text()")
        address = address.strip()
        if address:
            temp_dict = {
                "zip": re.findall("\d+", address.split(",")[-2])[0],
                "streetAddress": " ".join(address.split(",")[:-2]).strip(),
                "city": re.findall("[a-zA-Z ]+", address.split(",")[-2])[0].strip(),
                "country": re.findall("^[a-zA-Z ]+", address.split(",")[-1])[0].strip(),
                "fullAddress": address.strip(),
            }

            return temp_dict
        else:
            return None

    def reformat_date(self, date, format):
        date = datetime.datetime.strptime(date, format).strftime("%Y-%m-%d")
        return date

    def check_create(self, tree, xpath, title, dictionary, date_format=None):
        item = self.get_by_xpath(tree, xpath)
        if item:
            if date_format:
                item = self.reformat_date(item, date_format)
            dictionary[title] = item

    def get_regulator_address(self, tree):
        address = self.get_by_xpath(
            tree,
            '//ul[@class="footer_link"]/following-sibling::p//text()',
            return_list=True,
        )
        address.pop(1)
        temp_dict = {
            "fullAddress": address[0].strip(),
            "city": address[0].split(",")[3].strip(),
            "country": address[0].split(",")[5].strip(),
        }
        return temp_dict

    def get_overview(self, link_name):
        link = link_name.split("?=")[0]
        company_name = link_name.split("?=")[1]
        tree = self.get_tree(link, self.header)
        company = {}
        base_xpath = f'//section[@class="cp"]//tr/td[2]/a/text()[contains(., "{company_name}")]/../../../'

        try:
            orga_name = self.get_by_xpath(
                tree,
                f'//section[@class="cp"]//tr/td[2]/a/text()[contains(., "{company_name}")]',
            )
        except:
            return None
        if orga_name:
            company["vcard:organization-name"] = orga_name

        company["isDomiciledIn"] = "TW"

        self.check_create(tree, base_xpath + "td[2]/a/@href", "hasURL", company)

        business_classifier = self.get_business_classifier(tree)
        if business_classifier:
            company["bst:businessClassifier"] = business_classifier

        self.check_create(
            tree,
            base_xpath + "td[4]/text()",
            "hasLatestOrganizationFoundedDate",
            company,
            "%Y/%m/%d",
        )

        company["regulator_name"] = "Central Bank of The Republic of China (Taiwan)"
        company["regulator_url"] = "https://www.cbc.gov.tw/"
        company["RegulationStatus"] = "Authorised"

        identifiers = self.get_by_xpath(tree, base_xpath + "td[1]/text()")

        if identifiers:
            company["identifiers"] = {"other_company_id_number": identifiers}
            company["legislationidentifier"] = identifiers

        regulator_address = self.get_regulator_address(tree)
        if regulator_address:
            company["regulatorAddress"] = regulator_address

        address = self.get_address(tree, base_xpath)
        if address:
            company["mdaas:RegisteredAddress"] = address

        company["@source-id"] = self.NICK_NAME

        return company
