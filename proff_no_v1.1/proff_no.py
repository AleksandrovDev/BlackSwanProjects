import requests
import re
from lxml import etree
import base64
from datetime import datetime


class Handler:
    API_BASE_URL = ""
    base_url = "https://www.proff.no"
    NICK_NAME = "proff.no"
    FETCH_TYPE = ""
    TAG_RE = re.compile(r"<[^>]+>")

    session = requests.session()

    def Execute(self, searchquery, fetch_type, action, API_BASE_URL):
        self.FETCH_TYPE = fetch_type
        self.API_BASE_URL = API_BASE_URL

        pages = self.get_pages(searchquery)
        if fetch_type is None or fetch_type == "":
            if pages is not None:
                data = self.parse_pages(pages)
            else:
                data = []
            dataset = data
        else:
            data = self.fetch_by_field(searchquery)
            dataset = [data]
        return dataset

    def parse_pages(self, pages):
        rlist = []
        for link in pages:
            res = self.parse(link)
            if res is not None:
                rlist.append(res)
                if len(rlist) == 10:
                    break
        return rlist

    def get_pages(self, searchquery):
        search_url = self.base_url + "/bransjesøk"
        data = {"q": searchquery}
        r = self.session.get(search_url, params=data)
        tree = etree.HTML(r.content)
        try:
            links = tree.xpath(
                '//div[@class="search-container-wrap"]//a[@class="addax addax-cs_hl_hit_company_name_click"]/@href'
            )
            links = [self.base_url + link for link in links]
        except:
            return None
        if links:
            if len(links) > 10:
                return links[:10]
            else:
                return links
        else:
            return None

    def get_previous_names(self, tree):
        names = []
        try:
            name = tree.xpath(
                '//section[@class="panel official-info"]//*[text()[contains(., "Tidl. navn")]]/following-sibling::span/text()'
            )
        except:
            name = False
        if name:
            temp_dict = {"name": name}
            names.append(temp_dict)
        if names:
            return names
        else:
            return None

    def get_business_classifier(self, tree):
        temp_list = []
        temp_dict = {}
        try:
            info = tree.xpath(
                '//section[@class="panel official-info"]//*[text()[contains(., "NACE-bransje:")]]/following-sibling::span/text()'
            )[0]
            code = info.split(" ")[0]
            desc = info.split(" ")[1:]
            temp_dict["code"] = code
            temp_dict["description"] = " ".join(desc)
            temp_dict["label"] = "NACE"
            temp_list.append(temp_dict)
        except:
            return None
        return temp_list

    def get_address(self, tree):
        try:
            address = tree.xpath(
                '//section[@class="panel contacts-panel panel-no-pad"]//*[text()[contains(., "ksadresse:")]]/following-sibling::span/a/span/text()'
            )[0]

            temp_dict = {}
            temp_dict["country"] = "Norway"
            splitted = address.split(",")
            temp_dict["streetAdress"] = splitted[0]
            temp_dict["zip"] = splitted[1].split(" ")[1]
            temp_dict["city"] = splitted[1].split(" ")[2]
            temp_dict["fullAddress"] = address + " Norway"
            return temp_dict
        except:
            return None

    def get_postal_address(self, tree):
        try:
            address = tree.xpath(
                '//section[@class="panel contacts-panel panel-no-pad"]//*[text()[contains(., "Postadresse:")]]/following-sibling::span/text()'
            )[0]
            temp_dict = {}
            temp_dict["country"] = "Norway"
            splitted = address.split(",")
            temp_dict["streetAdress"] = splitted[0]
            temp_dict["zip"] = splitted[1].split(" ")[1]
            temp_dict["city"] = splitted[1].split(" ")[2]
            temp_dict["fullAddress"] = address + ", Norway"
            return temp_dict
        except:
            return None

    def get_found_date(self, tree):
        try:
            date = tree.xpath(
                '//section[@class="panel official-info"]//*[text()[contains(., "Stiftelsesdato:")]]/following-sibling::span/text()'
            )[0]
            date = datetime.strptime(date, "%d.%m.%Y").strftime("%Y-%m-%d")
            return date
        except:
            return None

    def get_reg_date(self, tree):
        try:
            date = tree.xpath(
                '//section[@class="panel official-info"]//*[text()[contains(., "Registreringsdato:")]]/following-sibling::span/text()'
            )[0]
            date = datetime.strptime(date, "%d.%m.%Y").strftime("%Y-%m-%d")
            return date
        except:
            return None

    def get_identifiers(self, tree):
        temp_dict = {}
        org_num = tree.xpath(
            '//section[@class="panel official-info"]//*[text()[contains(., "Org nr:")]]/following-sibling::span/text()'
        )
        bdr_num = tree.xpath(
            '//section[@class="panel official-info"]//*[text()[contains(., "Bdr nr:")]]/following-sibling::span/text()'
        )
        if org_num:
            temp_dict["trade_register_number"] = org_num[0]
        if bdr_num:
            temp_dict["other_company_id_number"] = bdr_num[0]
        return temp_dict

    def get_lei(self, tree):
        try:
            label = tree.xpath(
                '//section[@class="panel official-info"]//*[text()[contains(., "Selskapsform:")]]/following-sibling::span/text()'
            )[0]
            if label:
                temp_dict = {"code": "", "label": label}
            return temp_dict
        except:
            return None

    def get_open_hours(self, tree):
        try:
            days = tree.xpath(
                '//section[@class="panel main-panel"]//div[@class="secondary-panel"]//dt/text()'
            )
            time = tree.xpath(
                '//section[@class="panel main-panel"]//div[@class="secondary-panel"]//dd/span/text()'
            )[0]

            temp_dict = {}

            temp_dict["dayOfWeek"] = days
            temp_dict["Opens"] = time.split(" - ")[0]
            temp_dict["Closes"] = time.split(" - ")[1]
            return temp_dict
        except:
            return None

    def get_summary_fin_data(self, tree):
        temp_dict = {}
        summary = {}
        balance_sheet = {}
        income_statement = {}
        temp_dict = {
            "source": self.NICK_NAME,
        }

        try:
            currency = tree.xpath(
                '//th[text()[contains(., "Valutakode")]]/following-sibling::td[1]/text()'
            )[0]
            if currency:
                summary["currency"] = currency
        except:
            pass

        try:
            date = tree.xpath(
                '//span[text()[contains(., "REGNSKAPSPERIODE")]]/../following-sibling::th[1]/span/text()'
            )[0]
            if date:
                balance_sheet["date"] = date
        except:
            pass

        try:
            total_assets = tree.xpath(
                '//span[text()[contains(., "Sum eiendeler")]]/../following-sibling::td[1]/text()'
            )[0]
            if total_assets:
                balance_sheet["total_assets"] = total_assets
        except:
            pass

        try:
            summary["balance_sheet"] = balance_sheet
        except:
            pass

        try:
            revenue = tree.xpath(
                '//span[text()[contains(., "Sum driftsinntekter")]]/../following-sibling::td[1]/text()'
            )[0]
            if revenue:
                income_statement["revenue"] = revenue
        except:
            pass

        try:
            period = f"{str(int(date) - 1)} - {date}"
            income_statement["period"] = period
        except:
            pass

        try:
            profit = tree.xpath(
                '//span[text()[contains(., "Driftsresultat")]]/../following-sibling::td[1]/text()'
            )[0]
            if profit:
                income_statement["profit"] = profit
        except:
            pass

        try:
            cash_flow_from_operations = tree.xpath(
                '//span[text()[contains(., "Driftsresultat")]]/../following-sibling::td[1]/text()'
            )[0]
            if cash_flow_from_operations:
                income_statement[
                    "cash_flow _from_operations"
                ] = cash_flow_from_operations
        except:
            pass

        try:
            summary["income_statement"] = income_statement
        except:
            pass

        try:
            temp_dict["summary"] = summary
        except:
            pass

        return temp_dict

    def get_financial_statements(self, tree):
        temp_dict = {}
        balance_sheet = []
        balance_dict = {}
        try:
            total_intengible_assets = tree.xpath(
                '//span[text()[contains(., "Sum immaterielle midler")]]/../following-sibling::td[1]/text()'
            )[0]
            if total_intengible_assets:
                balance_dict["line_item_desc"] = "Total intangible assets"
                balance_dict["line_item_amount"] = total_intengible_assets
        except:
            pass

        balance_sheet.append(balance_dict)
        temp_dict["balance_sheet"] = balance_sheet

        return temp_dict

    def parse(self, link):
        r = self.session.get(link)
        tree = etree.HTML(r.content)
        edd = {}

        if self.FETCH_TYPE == "overview" or self.FETCH_TYPE == "":
            try:
                orga_name = tree.xpath("//header/h1/text()")[0].strip()
            except:
                return None
            company = {"vcard:organization-name": orga_name}
            try:
                company["logo"] = (
                    self.base_url
                    + tree.xpath('//*[@id="sidebar"]/div/section/div[1]/a/img/@src')[0]
                )
            except:
                pass

            prev_names = self.get_previous_names(tree)
            if prev_names:
                company["previous_names"] = prev_names
            try:
                website = tree.xpath(
                    '//section[@class="panel contacts-panel panel-no-pad"]//*[text()[contains(., "Hjemmeside")]]/following-sibling::span/a/text()'
                )
                if website:
                    company["hasURL"] = website
            except:
                pass

            try:
                mail = tree.xpath(
                    '//section[@class="panel contacts-panel panel-no-pad"]//*[text()[contains(., "E-post:")]]/following-sibling::span/a/span/text()'
                )
                if mail:
                    lenght = int(len(mail) / 2)
                    company["bst:email"] = "".join(mail[:lenght])
            except:
                pass

            classifier = self.get_business_classifier(tree)
            if classifier:
                company["bst:businessClassifier"] = classifier

            address = self.get_address(tree)
            if address:
                company["mdaas:RegisteredAddress"] = address

            post_address = self.get_postal_address(tree)
            if post_address:
                company["mdaas:PostalAddress"] = post_address

            found_date = self.get_found_date(tree)
            if found_date:
                company["hasLatestOrganizationFoundedDate"] = found_date

            reg_date = self.get_reg_date(tree)
            if reg_date:
                company["IncorporatedIn"] = reg_date

            company["isDomiciledIn"] = "NO"

            try:
                phone = tree.xpath(
                    '//section[@class="panel contacts-panel panel-no-pad"]//*[text()[contains(., "Telefon:")]]/following-sibling::span/a/text()'
                )[0]
                if phone:
                    company["tr-org:hasRegisteredPhoneNumber"] = phone
            except:
                pass

            identifiers = self.get_identifiers(tree)
            if identifiers:
                company["identifiers"] = identifiers

            try:
                size = tree.xpath(
                    '//section[@class="statusbar-wrap ui-wide"]//*[text()[contains(., "Ansatte:")]]/following-sibling::em/text()'
                )[0]
                if size:
                    company["size"] = size
            except:
                pass

            try:
                desc = tree.xpath('//div[@class="secondary-panel ui-wide"]//p/text()')[
                    0
                ]
                if desc:
                    company["bst:description"] = desc
            except:
                pass

            try:
                points = "\n".join(
                    tree.xpath('//div[@class="secondary-panel ui-wide"]//li/text()')
                )
                if points:
                    company["bst:description"] += points
            except:
                pass

            lei = self.get_lei(tree)
            if lei:
                company["lei:legalForm"] = lei

            company["bst:registryURI"] = link

            try:
                map = tree.xpath('//a[@class="panel-col map-wrapper ui-wide"]/@href')[0]
                if map:
                    company["map"] = self.base_url + map
            except:
                pass

            open_hours = self.get_open_hours(tree)
            if open_hours:
                company["@type:OpeningHoursSpecifications"] = open_hours

            edd["overview"] = company

        if self.FETCH_TYPE == "officership":
            officers = []
            off_link = link.replace("selskap", "roller")
            r = self.session.get(off_link)
            tree = etree.HTML(r.content)

            try:
                roles = tree.xpath('//header/h2[text()="Roller"]/../..//tr/th/text()')
                names = tree.xpath(
                    '//header/h2[text()="Roller"]/../..//tr/td/a/span/text()'
                )
                names = [name[:-9] if "(f" in name else name for name in names]

                for role, name in zip(roles, names):
                    officer = {
                        "name": name,
                        "type": "individual",
                        "officer_role": role,
                        "status": "active",
                        "occupation": role,
                        "information_source": self.base_url,
                        "information_provider": self.NICK_NAME,
                    }
                    officers.append(officer)
            except:
                pass

            if len(officers) > 0:
                edd["officership"] = officers

        if self.FETCH_TYPE == "shareholders":
            shareholders = []
            off_link = link.replace("selskap", "roller")
            r = self.session.get(off_link)
            tree = etree.HTML(r.content)

            try:
                shareholders_list = tree.xpath(
                    '//header/h2[text()[contains(., "Aksjon")]]/../..//tr/td/a/span/text()'
                )
                shareholders_share_list = tree.xpath(
                    '//header/h2[text()[contains(., "Aksjon")]]/../..//tr/td[3]/text()'
                )
                for holder, share in zip(shareholders_list, shareholders_share_list):
                    temp_dict = {
                        "isDomiciledIn": "NO",
                        "vcard: organization-name": holder,
                        "relation": {
                            "natureOfControl": "SHH",
                            "source": self.NICK_NAME,
                            "totalPercentage": share,
                        },
                    }
                    shareholders.append(temp_dict)
            except:
                pass

            if len(shareholders) > 0:
                edd["shareholders"] = shareholders

        if self.FETCH_TYPE == "subsidiaries":
            subsidiaries = []
            off_link = link.replace("selskap", "roller")
            r = self.session.get(off_link)
            tree = etree.HTML(r.content)
            try:
                names = tree.xpath(
                    '//header/h2[text()[contains(., "Konsern")]]/../..//div[@class="company-name"]/a/span/text()'
                )[1:]
                ids = tree.xpath(
                    '//header/h2[text()[contains(., "Konsern")]]/../..//div[@class="mute"]/text()'
                )[1:]
                for name, id in zip(names, ids):
                    temp_dict = {
                        "@sourceReferenceID": id,
                        "entity_type": "C",
                        "isDomiciledIn": "NO",
                        "vcard:organization-name": name,
                        "relation": {
                            "natureOfControl": "SHH",
                            "source": self.NICK_NAME,
                        },
                    }
                    subsidiaries.append(temp_dict)
                if len(subsidiaries) > 0:
                    edd["subsidiaries"] = subsidiaries

            except:
                pass

        if self.FETCH_TYPE == "Financial_Information":
            off_link = link.replace("selskap", "regnskap")
            r = self.session.get(off_link)
            tree = etree.HTML(r.content)

            financials = {}
            summary_financial_data = self.get_summary_fin_data(tree)

            if summary_financial_data:
                financials["Summary_Financial_data"] = summary_financial_data

            financial_statements = self.get_financial_statements(tree)
            if financial_statements:
                financials["financial_statements"] = financial_statements

            if len(financials) > 0:
                edd["Financial_Information"] = financials

        edd["_links"] = self.links(link)
        return edd

    def links(self, link):
        data = {}
        base_url = self.NICK_NAME
        link2 = base64.b64encode(link.encode("utf-8"))
        link2 = link2.decode("utf-8")
        data["overview"] = {
            "method": "GET",
            "url": self.API_BASE_URL
            + "?source="
            + base_url
            + "&url="
            + link2
            + "&fields=overview",
        }
        data["documents"] = {
            "method": "GET",
            "url": self.API_BASE_URL
            + "?source="
            + base_url
            + "&url="
            + link2
            + "&fields=documents",
        }
        data["officership"] = {
            "method": "GET",
            "url": self.API_BASE_URL
            + "?source="
            + base_url
            + "&url="
            + link2
            + "&fields=officership",
        }
        data["shareholders"] = {
            "method": "GET",
            "url": self.API_BASE_URL
            + "?source="
            + base_url
            + "&url="
            + link2
            + "&fields=shareholders",
        }
        data["subsidiaries"] = {
            "method": "GET",
            "url": self.API_BASE_URL
            + "?source="
            + base_url
            + "&url="
            + link2
            + "&fields=subsidiaries",
        }
        data["Financial_Information"] = {
            "method": "GET",
            "url": self.API_BASE_URL
            + "?source="
            + base_url
            + "&url="
            + link2
            + "&fields=Financial_Information",
        }

        return data

    def fetch_by_field(self, link):
        link = base64.b64decode(link).decode("utf-8")
        res = self.parse(link)
        return res
