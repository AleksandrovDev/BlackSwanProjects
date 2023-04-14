import datetime
import hashlib
import json
import re


from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://ives.minv.sk"
    NICK_NAME = "ives.minv.sk"
    fields = ["overview", "officers"]

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
        url = "https://ives.minv.sk/rmno/?lang=en"
        tree = self.get_tree(url, headers=self.header)
        hidden = tree.xpath('//input[@type="hidden"]/@value')
        name = tree.xpath('//input[@type="hidden"]/@name')
        data = dict(zip(name, hidden))

        data["nazov"] = searchquery
        data["ctl00$container$checkLenAktualne"] = "on"
        data["ctl00$container$cmdpotvrd"] = "Search"
        tree = self.get_tree(url, headers=self.header, method="POST", data=data)
        comp_names = self.get_by_xpath(
            tree,
            '//div/div[@class="govuk-summary-list__row"][1]/dd/text()',
            return_list=True,
        )

        return [i.replace('"', "") for i in comp_names]

    def get_address(self, tree):
        address = self.get_by_xpath(
            tree,
            '//div[@class="govuk-summary-list__row"]/dt[@class="govuk-summary-list__key"]/text()[contains(., "Seat")]/../../dd/text()',
        )
        try:
            zip = re.findall("\d\d\d\s\d\d*", address)[-1]
        except:
            zip = None
        try:
            city = address.split(zip)[-1].strip()
        except:
            city = None

        try:
            street = address.split(zip)[0].split(",")[0]
        except:
            street = None
        temp_dict = {"country": "Slovakia", "fullAddress": address + ", Slovakia"}
        if zip:
            temp_dict["zip"] = zip

        if city:
            temp_dict["city"] = city
        if street:
            temp_dict["streetAddress"] = street
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

    def get_founders(self, tree):
        officers = []
        names = self.get_by_xpath(
            tree,
            '//div[@class="govuk-summary-list__row"]/dt[@class="govuk-summary-list__key"]/text()[contains(., "Founders")]/../../../following-sibling::div[1]//div[@class="govuk-grid-column-one-half"]/text()',
            return_list=True,
        )
        incorp = self.get_by_xpath(
            tree,
            '//div[@class="govuk-summary-list__row"]/dt[@class="govuk-summary-list__key"]/text()[contains(., "Founders")]/../../../following-sibling::div[1]//div[@class="govuk-grid-column-one-quarter"]/span/text()[contains(., "From")]/../../text()',
            return_list=True,
        )
        for name, icor in zip(names, incorp):
            off = {
                "name": name,
                "type": "Individual",
                "status": "Active",
                "occupation": "Director",
                "officer_role": "Director",
                "information_source": "https://ives.minv.sk/",
                "information_provider": "IVES",
            }
            if incorp:
                off["date_of_incorporation"] = {
                    "year": icor.split(".")[-1],
                    "month": icor.split(".")[-2],
                    "day": icor.split(".")[-3],
                }
            officers.append(off)
        return officers

    def get_comitte(self, tree):
        officers = []
        names = self.get_by_xpath(
            tree,
            '//div[@class="govuk-summary-list__row"]/dt[@class="govuk-summary-list__key"]/text()[contains(., "Members of the preparatory committee")]/../../following-sibling::div//div[@class="govuk-grid-column-one-half"]//text()[1]',
            return_list=True,
        )
        borns = self.get_by_xpath(
            tree,
            '//div[@class="govuk-summary-list__row"]/dt[@class="govuk-summary-list__key"]/text()[contains(., "Members of the preparatory committee")]/../../following-sibling::div//div[@class="govuk-grid-column-one-half"]//text()[2]',
            return_list=True,
        )
        names2 = self.get_by_xpath(
            tree,
            '//div[@class="govuk-summary-list__row"]/dt[@class="govuk-summary-list__key"]/text()[contains(., "Members of the preparatory committee")]/../../../following-sibling::div//div[@class="govuk-grid-column-one-half"]//text()[1]',
            return_list=True,
        )
        borns2 = self.get_by_xpath(
            tree,
            '//div[@class="govuk-summary-list__row"]/dt[@class="govuk-summary-list__key"]/text()[contains(., "Members of the preparatory committee")]/../../../following-sibling::div//div[@class="govuk-grid-column-one-half"]//text()[2]',
            return_list=True,
        )
        from2 = self.get_by_xpath(
            tree,
            '//div[@class="govuk-summary-list__row"]/dt[@class="govuk-summary-list__key"]/text()[contains(., "Members of the preparatory committee")]/../../../following-sibling::div//div[@class="govuk-grid-column-one-quarter"][1]/span/../text()',
            return_list=True,
        )
        positions2 = self.get_by_xpath(
            tree,
            '//span[@class="govuk-grid-column-one-quarter popis"]/text()[contains(., "Position")]/../../text()',
            return_list=True,
        )
        print(names2)
        print(borns2)
        print(from2)
        print(names)
        print(borns)

        if names2 and borns2 and positions2 and from2:
            for name, born, pos, fr in zip(names2, borns2, positions2, from2):
                off = {
                    "name": name,
                    "type": "Individual",
                    "status": "Active",
                    "occupation": pos,
                    "officer_role": pos,
                    "information_source": "https://ives.minv.sk/",
                    "information_provider": "IVES",
                }
            if fr:
                off["date_of_incorporation"] = {
                    "year": fr.split(".")[-1],
                    "month": fr.split(".")[-2],
                    "day": fr.split(".")[-3],
                }
            if born:
                off["date_of_birth"] = {
                    "year": born.split(".")[-1],
                    "month": born.split(".")[-2],
                    "day": born.split(".")[-3],
                }
            officers.append(off)
        if names and borns:
            for name, born in zip(names, borns):
                if name in names2:
                    continue
                off = {
                    "name": name,
                    "type": "Individual",
                    "status": "Active",
                    "occupation": "Member of the preparatory committee",
                    "officer_role": "Member of the preparatory committee",
                    "information_source": "https://ives.minv.sk/",
                    "information_provider": "IVES",
                }
                if born:
                    off["date_of_birth"] = {
                        "year": born.split(".")[-1],
                        "month": born.split(".")[-2],
                        "day": born.split(".")[-3][-2:],
                    }
                officers.append(off)

        return officers

    def get_overview(self, link_name):
        url = "https://ives.minv.sk/rmno/?lang=en"
        tree = self.get_tree(url, headers=self.header)
        hidden = tree.xpath('//input[@type="hidden"]/@value')
        name = tree.xpath('//input[@type="hidden"]/@name')
        data = dict(zip(name, hidden))

        data["nazov"] = link_name
        data["ctl00$container$checkLenAktualne"] = "on"
        data["ctl00$container$cmdpotvrd"] = "Search"
        tree = self.get_tree(url, headers=self.header, method="POST", data=data)

        company = {}

        try:
            orga_name = self.get_by_xpath(
                tree,
                f'//div/div[@class="govuk-summary-list__row"][1]/dd/text()[contains(., "{link_name}")]',
            )
        except:
            return None
        if orga_name:
            company["vcard:organization-name"] = orga_name.strip()

        details_link = "https://ives.minv.sk/rmno/" + self.get_by_xpath(
            tree, '//div/a[@class="govuk-button"]/@href'
        )

        tree = self.get_tree(details_link, headers=self.header)
        fullExtr = "https://ives.minv.sk/rmno/" + self.get_by_xpath(
            tree, '//div[@class="govuk-heading-m"]/div/a[@class="govuk-button"]/@href'
        )
        tree = self.get_tree(fullExtr, headers=self.header)
        company["isDomiciledIn"] = "SK"
        diss = self.get_by_xpath(
            tree,
            '//div[@class="govuk-summary-list__row"]/dt[@class="govuk-summary-list__key"]/text()[contains(., "Legal title of Dissolution")]',
        )
        if diss:
            company["hasActivityStatus"] = "Inactive"
            disDate = self.get_by_xpath(
                tree,
                '//div[@class="govuk-summary-list__row"]/dt[@class="govuk-summary-list__key"]/text()[contains(., "Legal title of Dissolution")]/../../preceding-sibling::div[1]/dd/text()',
            )
            if disDate:
                company["dissolutionDate"] = self.reformat_date(disDate, "%d.%m.%Y")
        else:
            company["hasActivityStatus"] = "Active"

        reg_date = self.get_by_xpath(
            tree,
            '//div[@class="govuk-summary-list__row"]/dt[@class="govuk-summary-list__key"]/text()[contains(., "Date of registration")]/../../dd/text()',
        )
        if reg_date:
            company["isIncorporatedIn"] = self.reformat_date(reg_date, "%d.%m.%Y")

        iden_num = self.get_by_xpath(
            tree,
            '//div[@class="govuk-summary-list__row"]/dt[@class="govuk-summary-list__key"]/text()[contains(., "Identification number (IČO)")]/../../dd/text()',
        )
        if iden_num:
            company["identifiers"] = {"other_company_id_number": iden_num}

        leg_form = self.get_by_xpath(
            tree,
            '//div[@class="govuk-summary-list__row"]/dt[@class="govuk-summary-list__key"]/text()[contains(., "Legal form")]/../../dd/text()',
        )
        if leg_form:
            company["lei:legalForm"] = {"code": "", "label": leg_form}

        regId = self.get_by_xpath(
            tree,
            '//div[@class="govuk-summary-list__row"]/dt[@class="govuk-summary-list__key"]/text()[contains(., "Registration number")]/../../dd/text()',
        )
        if regId:
            company["bst:registrationId"] = regId

        address = self.get_address(tree)
        if address:
            company["mdaas:RegisteredAddress"] = address

        company["@source-id"] = self.NICK_NAME
        return company

    def get_officership(self, link):
        officers = []
        url = "https://ives.minv.sk/rmno/?lang=en"
        tree = self.get_tree(url, headers=self.header)
        hidden = tree.xpath('//input[@type="hidden"]/@value')
        name = tree.xpath('//input[@type="hidden"]/@name')
        data = dict(zip(name, hidden))

        data["nazov"] = link
        data["ctl00$container$checkLenAktualne"] = "on"
        data["ctl00$container$cmdpotvrd"] = "Search"
        tree = self.get_tree(url, headers=self.header, method="POST", data=data)
        details_link = "https://ives.minv.sk/rmno/" + self.get_by_xpath(
            tree, '//div/a[@class="govuk-button"]/@href'
        )

        tree = self.get_tree(details_link, headers=self.header)
        fullExtr = "https://ives.minv.sk/rmno/" + self.get_by_xpath(
            tree, '//div[@class="govuk-heading-m"]/div/a[@class="govuk-button"]/@href'
        )
        tree = self.get_tree(fullExtr, headers=self.header)
        founders = self.get_by_xpath(
            tree,
            '//div[@class="govuk-summary-list__row"]/dt[@class="govuk-summary-list__key"]/text()[contains(., "Founders")]',
        )
        commitee = self.get_by_xpath(
            tree,
            '//div[@class="govuk-summary-list__row"]/dt[@class="govuk-summary-list__key"]/text()[contains(., "Members of the preparatory committee")]',
        )
        print(commitee)
        if founders:
            print("found")
            return self.get_founders(tree)
        elif commitee:
            print("com")
            return self.get_comitte(tree)
        return officers

        print(founders)
