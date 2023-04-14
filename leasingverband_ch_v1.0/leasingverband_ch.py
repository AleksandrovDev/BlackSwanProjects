import datetime
import hashlib
import json
import re

from geopy import Nominatim
import pycountry
from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "http://www.leasingverband.ch"
    NICK_NAME = "leasingverband_ch"
    fields = ["overview"]
    locator = Nominatim(user_agent="http")

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
                return el
            else:
                return el[0].strip()
        else:
            return None

    def getpages(self, searchquery):
        result_links = []

        url = "https://www.leasingverband.ch/de/schweizerischer-leasingverband-slv/ueber-uns/mitglieder/index.html"

        tree = self.get_tree(url, headers=self.header)
        names = self.get_by_xpath(tree, "//h3/text()", return_list=True)
        for i in names:
            if searchquery in i:
                result_links.append(i)
        return result_links

    def get_business_classifier(self, tree):
        final_list = []
        classifier_ids = self.get_by_xpath(
            tree,
            '//table//th/text()[contains(., "Activity Details")]/../../../..//tr/td[1]/text()',
            return_list=True,
        )
        classifier_names = self.get_by_xpath(
            tree,
            '//table//th/text()[contains(., "Activity Details")]/../../../..//tr/td[2]/text()',
            return_list=True,
        )

        ministry_ids = self.get_by_xpath(
            tree,
            '//table//th/text()[contains(., "Activities Registered Under")]/../../../..//td[1]/text()',
            return_list=True,
        )
        ministry_names = self.get_by_xpath(
            tree,
            '//table//th/text()[contains(., "Activities Registered Under")]/../../../..//td[2]/text()',
            return_list=True,
        )

        if classifier_ids and classifier_names:
            for i in range(len(classifier_ids)):
                temp_dict = {
                    "code": classifier_ids[i],
                    "description": classifier_names[i],
                    "label": "",
                }
                final_list.append(temp_dict)
        if ministry_ids and ministry_names:
            for i in range(len(ministry_ids)):
                temp_dict = {
                    "code": ministry_ids[i],
                    "description": ministry_names[i],
                    "label": "",
                }
                final_list.append(temp_dict)

        if final_list:
            return final_list
        else:
            return None

    def get_address(self, tree, link_name, postal=False):
        address = self.get_by_xpath(
            tree,
            f'//h3/text()[contains(., "{link_name}")]/..//following-sibling::text()',
            return_list=True,
        )
        address = " ".join([i.strip() for i in address[1:]])
        address = address.replace("\n", "").replace("   ", "").strip()
        splitted_addrs = address.split(" ")

        zip = re.findall("\d\d\d\d+", splitted_addrs[-2])
        city = re.findall("[a-zA-Z]+", splitted_addrs[-1])
        location = self.locator.geocode(city, language="en", timeout=10)
        code = pycountry.countries.search_fuzzy(str(location).split(",")[-1])[0].name
        temp_dict = {
            "streetAddress": " ".join(address.split(" ")[:-2]),
            "country": code,
            "fullAddress": address.strip() + ", " + code,
        }
        if zip:
            temp_dict["zip"] = zip[-1]

        if city:
            temp_dict["city"] = city[-1]
        return temp_dict

    def reformat_date(self, date, format):
        date = datetime.datetime.strptime(date.strip(), format).strftime("%Y-%m-%d")
        return date

    def check_create(self, tree, xpath, title, dictionary, date_format=None):
        item = self.get_by_xpath(tree, xpath)
        if item:
            if date_format:
                item = self.reformat_date(item, date_format)
            dictionary[title] = item.strip()

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

    def get_prev_names(self, tree):
        previous_names = []

        company_id = self.get_by_xpath(
            tree, '//div/text()[contains(., "Company Title Changes")]/../../@ng-click'
        ).split(",")[-1]
        id_clean = re.findall("\w+", company_id)[0]
        url = f"https://www.kap.org.tr/en/BildirimSgbfApproval/UNV/{id_clean}"
        tree = self.get_tree(url)

        js = tree.xpath("//text()")[0]
        if js:
            for i in json.loads(js):
                temp_dict = {
                    "name": i["basic"]["companyName"],
                    "valid_to": self.reformat_date(
                        i["basic"]["publishDate"], "%d.%m.%y %H:%M"
                    ),
                }
                previous_names.append(temp_dict)

        if previous_names:
            return previous_names
        return None

    def get_overview(self, link_name):
        url = "https://www.leasingverband.ch/de/schweizerischer-leasingverband-slv/ueber-uns/mitglieder/index.html"
        tree = self.get_tree(url, headers=self.header)

        company = {}

        try:
            orga_name = self.get_by_xpath(
                tree, f'//h3/text()[contains(., "{link_name}")]'
            )
        except:
            return None
        if orga_name:
            company["vcard:organization-name"] = orga_name.strip()
        domicled = self.get_by_xpath(
            tree, f'//h3/text()[contains(., "{link_name}")]/../../text()[3]'
        ).split(" ")[0]
        if domicled:
            location = self.locator.geocode(domicled, language="en", timeout=10)
            code = pycountry.countries.search_fuzzy(str(location).split(",")[-1])[
                0
            ].alpha_2
            company["isDomiciledIn"] = code

        company["hasActivityStatus"] = "Active"

        self.check_create(
            tree,
            f'//h3/text()[contains(., "{link_name}")]/../../a/text()',
            "hasURL",
            company,
        )

        service = self.get_by_xpath(
            tree, f'//h3/text()[contains(., "{link_name}")]/../..//text()[2]'
        )
        if service:
            company["Service"] = {
                "serviceType": service.replace("(", "").replace(")", "")
            }

        phone = self.get_by_xpath(
            tree,
            f'//h3/text()[contains(., "{link_name}")]/../../../div[2]//text()[contains(.,"Tel")]',
        )
        if phone:
            company["tr-org:hasRegisteredPhoneNumber"] = phone.replace("Tel: ", "")

        fax = self.get_by_xpath(
            tree,
            f'//h3/text()[contains(., "{link_name}")]/../../../div[2]//text()[contains(.,"Fax")]',
        )
        if fax:
            company["hasRegisteredFaxNumber"] = fax.replace("Fax: ", "")

        address = self.get_address(tree, link_name)
        if address:
            company["mdaas:RegisteredAddress"] = address

        company["@source-id"] = self.NICK_NAME

        return company
