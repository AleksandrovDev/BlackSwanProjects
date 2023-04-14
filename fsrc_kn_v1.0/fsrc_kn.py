import datetime
import re

from geopy import Nominatim

from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://www.fsrc.kn/"
    NICK_NAME = "fsrc.kn"
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
        url = "https://www.fsrc.kn/regulated-entities"
        tree = self.get_tree(url, headers=self.header)
        link_list = self.get_by_xpath(tree, "//h2/a/@href", return_list=True)
        company_names = []
        if link_list:
            link_list = [url + i for i in link_list]
            for link in link_list:
                tree = self.get_tree(link, headers=self.header)
                rows = self.get_by_xpath(
                    tree, "//h3/a/span[2]/text()", return_list=True
                )

                for row in range(len(rows)):
                    if searchquery in rows[row]:
                        company_names.append(link + "?=" + rows[row])
        return company_names

    def get_business_classifier(self, link):
        business_classifier = link.split("/")[-1].replace("-", " ").title()
        if business_classifier:
            temp_dict = {"code": "", "description": business_classifier, "label": ""}
            return [temp_dict]
        else:
            return None

    def get_address(self, tree, base_xpath, postal=False):
        address = self.get_by_xpath(
            tree,
            base_xpath
            + '/../../../../..//div[@class="qListItem_introtext"]//text()[contains(., "Address")]',
        )

        if address == "Address:":
            address = self.get_by_xpath(
                tree,
                base_xpath
                + '/../../../../..//div[@class="qListItem_introtext"]//text()[contains(., "Address")]/../../text()[1]',
            )

        if address is None:
            address = self.get_by_xpath(
                tree,
                base_xpath
                + '/../../../../..//div[@class="qListItem_introtext"]//text()',
                return_list=True,
            )
            address = "".join(address[:3])
        if address:
            address = address.split(",")
            address[0] = " ".join(address[0].split(" ")[1:])
            index = None
            for i in range(len(address)):
                if "street" in address[i].lower():
                    index = i
                if "box " in address[i].lower():
                    index = i
                if index is None:
                    index = 0
            street = " ".join(address[: index + 1]).strip()
            city = address[index + 1].strip()
            address = " ".join(address)
            temp_dict = {
                "streetAddress": street,
                "city": city,
                "country": "Saint Kitts and Nevis",
                "fullAddress": address.strip() + ", Saint Kitts and Nevis",
            }

            return temp_dict

        else:
            return None

    def check_create(self, tree, xpath, title, dictionary, date_format=None):
        item = self.get_by_xpath(tree, xpath)
        if item:
            if date_format:
                item = self.reformat_date(item, date_format)
            dictionary[title] = item

    def get_regulator_address(self, tree):
        address = self.get_by_xpath(
            tree, '//div[@class="custom_contactinfo"]/p/text()', return_list=True
        )
        address[1] = address[1].split(" - ")[-1]
        temp_dict = {
            "fullAddress": " ".join([i.strip() for i in address[1:-3]]),
            "city": address[3].split(",")[-1].strip(),
            "country": "Saint Kitts and Nevis",
        }
        return temp_dict

    def get_overview(self, link_name):
        link = link_name.split("?=")[0]
        company_name = link_name.split("?=")[1]
        tree = self.get_tree(link, self.header)
        company = {}
        base_xpath = f'//h3/a/span[2]/text()[contains(., "{company_name}")]'

        try:
            orga_name = self.get_by_xpath(tree, base_xpath)
        except:
            return None
        if orga_name:
            company["vcard:organization-name"] = orga_name

        company["isDomiciledIn"] = "KN"

        hasUrl = self.get_by_xpath(
            tree,
            base_xpath
            + '/../../../../..//div[@class="qListItem_introtext"]//text()[contains(., "www")]',
        )
        if hasUrl:
            company["hasURL"] = re.findall("www\.\w+\.\w+", hasUrl)[0]

        company["bst:businessClassifier"] = self.get_business_classifier(link)
        company["regulator_url"] = "https://www.fsrc.kn/"
        company["regulator_name"] = "Financial Services Regulatory Commission"
        company["RegulationStatus"] = "Authorised"

        regulator_address = self.get_regulator_address(tree)
        if regulator_address:
            company["regulatorAddress"] = regulator_address

        phone = self.get_by_xpath(
            tree,
            base_xpath
            + '/../../../../..//div[@class="qListItem_introtext"]//p/text()[contains(., "Contact Number")]',
        )

        if phone:
            company["tr-org:hasRegisteredPhoneNumber"] = phone.split(":")[-1].strip()
        else:
            phone = self.get_by_xpath(
                tree,
                base_xpath
                + '/../../../../..//div[@class="qListItem_introtext"]//text()[contains(., "Contact Number")]/../../text()[2]',
            )
            if phone:
                company["tr-org:hasRegisteredPhoneNumber"] = phone.split(":")[
                    -1
                ].strip()

        fax = self.get_by_xpath(
            tree,
            base_xpath
            + '/../../../../..//div[@class="qListItem_introtext"]//p/text()[contains(., "Fax")]',
        )
        if fax:
            company["hasRegisteredFaxNumber"] = fax.split("Fax:")[-1].strip()

        address = self.get_address(tree, base_xpath)
        if address:
            company["mdaas:RegisteredAddress"] = address

        company["@source-id"] = self.NICK_NAME

        return company
