import datetime
import re


from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://www.ekcci.org.kw/"
    NICK_NAME = "ekcci.org.kw"
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
                return el
            else:
                return el[0].strip()
        else:
            return None

    def getpages(self, searchquery):
        url = "https://www.ekcci.org.kw/newweb/members/search"
        self.get_tree(url, headers=self.header)
        ses = self.session.cookies.get_dict()["ci_session"]
        url = f"https://www.ekcci.org.kw/newweb/langswitch/switchLanguage/english?jsessionID={ses}"
        self.get_tree(url, headers=self.header)
        url = f"https://www.ekcci.org.kw/newweb/members/search?jsessionID={ses}"
        tree = self.get_tree(
            url,
            method="POST",
            headers=self.header,
            data={"S001_F000": f"{searchquery}"},
        )
        company_name_list = self.get_by_xpath(
            tree, '//span[@class="nLink"]/a/text()', return_list=True
        )
        link_list = self.get_by_xpath(
            tree, '//span[@class="nLink"]/a/@id', return_list=True
        )
        membership_list = self.get_by_xpath(
            tree,
            '//span[@class="nLink"]/../../..//span/text()[contains(., "Membership")]/../following-sibling::a/text()',
            return_list=True,
        )
        mem_type = self.get_by_xpath(
            tree,
            '//span[@class="nLink"]/../../..//span/text()[contains(., "Member Type")]/../../text()',
            return_list=True,
        )
        url = f"https://www.ekcci.org.kw/newweb/members/details"

        company_names = []

        if link_list:
            company_names = [
                c + f'?={i.split("_")[1]}?={ml}?={mt}'
                for i, c, ml, mt in zip(
                    link_list, company_name_list, membership_list, mem_type
                )
            ]
        return company_names

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

    def get_address(self, tree, postal=False):
        address = self.get_by_xpath(
            tree,
            '//div[@class="caption search"]//td/text()[contains(., "Address")]/../following-sibling::td/text()',
        )
        street = re.findall(".*Box \d+", address)[0]
        zip = re.findall("\d\d\d\d\d", address)
        temp_dict = {
            "streetAddress": street,
            "country": address.split(" ")[-1]
            if len(address.split(" ")) == 9
            else "KUWAIT",
            "fullAddress": address,
        }
        if zip:
            temp_dict["zip"] = zip[-1]

        if len(address.split(" ")) == 9:
            temp_dict["city"] = address.split(" ")[-3]

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

    def get_overview(self, link_name):
        url = "https://www.ekcci.org.kw/newweb/members/search"
        self.get_tree(url, headers=self.header)
        ses = self.session.cookies.get_dict()["ci_session"]
        url = f"https://www.ekcci.org.kw/newweb/langswitch/switchLanguage/english?jsessionID={ses}"
        self.get_tree(url, headers=self.header)

        link = f"https://www.ekcci.org.kw/newweb/members/details"
        company_id = link_name.split("?=")[1]
        ses = self.session.cookies.get_dict()["ci_session"]

        tree = self.get_tree(
            link,
            method="POST",
            headers=self.header,
            data={"mID": f"{company_id}", "jsessionID": {ses}},
        )

        company = {}

        try:
            orga_name = self.get_by_xpath(
                tree,
                '//div[@class="caption search"]//td/text()[contains(., "Member Name")]/../following-sibling::td/text()',
            )
        except:
            return None
        if orga_name:
            company["vcard:organization-name"] = orga_name.strip()

        company["isDomiciledIn"] = "KW"
        company["hasActivityStatus"] = link_name.split("?=")[2]
        company["lei:legalForm"] = {"code": "", "label": link_name.split("?=")[3]}

        self.check_create(
            tree,
            '//div[@class="caption search"]//td/text()[contains(., "Website")]/../following-sibling::td/text()',
            "hasURL",
            company,
        )

        self.check_create(
            tree,
            '//div[@class="caption search"]//td/text()[contains(., "Email")]/../following-sibling::td/text()',
            "bst:email",
            company,
        )
        self.check_create(
            tree,
            '//div[@class="caption search"]//td/text()[contains(., "Reg. Date")]/../following-sibling::td/text()',
            "isIncorporatedIn",
            company,
            "%d/%m/%Y",
        )

        self.check_create(
            tree,
            '//div[@class="caption search"]//td/text()[contains(., "Phone")]/../following-sibling::td/text()',
            "tr-org:hasRegisteredPhoneNumber",
            company,
        )
        if company["tr-org:hasRegisteredPhoneNumber"]:
            company["tr-org:hasRegisteredPhoneNumber"] = company[
                "tr-org:hasRegisteredPhoneNumber"
            ].split(" ")[0]

        self.check_create(
            tree,
            '//div[@class="caption search"]//td/text()[contains(., "Fax")]/../following-sibling::td/text()',
            "hasRegisteredFaxNumber",
            company,
        )
        if company["hasRegisteredFaxNumber"]:
            company["hasRegisteredFaxNumber"] = (
                company["hasRegisteredFaxNumber"].strip().split(" ")[0]
            )

        company["identifiers"] = {
            "trade_register_number": self.get_by_xpath(
                tree,
                '//div[@class="caption search"]//td/text()[contains(., "Trade CR No")]/../following-sibling::td/text()',
            ),
            "other_company_id_number": self.get_by_xpath(
                tree,
                '//div[@class="caption search"]//td/text()[contains(., "Member No")]/../following-sibling::td/text()',
            ),
        }

        self.check_create(
            tree,
            '//div[@class="caption search"]//td/text()[contains(., "Permit Expiry")]/../following-sibling::td/text()',
            "regExpiryDate",
            company,
            "%d/%m/%Y",
        )

        address = self.get_address(tree)
        if address:
            company["mdaas:RegisteredAddress"] = address

        classifier = self.get_business_classifier(tree)
        if classifier:
            company["bst:businessClassifier"] = classifier

        company["@source-id"] = self.NICK_NAME

        return company

    def get_officership(self, link):
        url = "https://www.ekcci.org.kw/newweb/members/search"
        self.get_tree(url, headers=self.header)
        ses = self.session.cookies.get_dict()["ci_session"]
        url = f"https://www.ekcci.org.kw/newweb/langswitch/switchLanguage/english?jsessionID={ses}"
        self.get_tree(url, headers=self.header)

        company_name = link.split("?=")[0]
        company_id = link.split("?=")[1]

        link = f"https://www.ekcci.org.kw/newweb/members/details"
        tree = self.get_tree(
            link,
            method="POST",
            headers=self.header,
            data={"mID": f"{company_id}", "jsessionID": {ses}},
        )

        names = self.get_by_xpath(
            tree,
            '//table//th/text()[contains(., "Nationality")]/../../../..//tr/td[1]/text()',
            return_list=True,
        )
        positions = self.get_by_xpath(
            tree,
            '//table//th/text()[contains(., "Nationality")]/../../../..//tr/td[2]/text()',
            return_list=True,
        )
        nationalities = self.get_by_xpath(
            tree,
            '//table//th/text()[contains(., "Nationality")]/../../../..//tr/td[3]/text()',
            return_list=True,
        )

        officers = []

        for i in range(len(names)):
            temp_dict = {
                "name": names[i],
                "officer_role": positions[i],
                "status": "Active",
                "country_of_residence": nationalities[i],
                "occupation": positions[i],
                "information_source": "https://www.ekcci.org.kw",
                "information_provider": "“Kuwait Chamber of Commerce and Industry",
            }
            officers.append(temp_dict)

        return officers
