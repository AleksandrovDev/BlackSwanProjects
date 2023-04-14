import requests
import re
import base64
from lxml import etree


class Handler:
    API_BASE_URL = ""
    base_url = "https://prod.ceidg.gov.pl"
    NICK_NAME = "prod.ceidg.gov.pl"
    FETCH_TYPE = ""
    TAG_RE = re.compile(r"<[^>]+>")

    session = requests.Session()
    browser_header = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.109 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
    }

    def Execute(self, searchquery, fetch_type, action, API_BASE_URL):
        self.FETCH_TYPE = fetch_type
        self.API_BASE_URL = API_BASE_URL

        if fetch_type is None or fetch_type == "":
            pages = self.get_pages(searchquery)

            if pages is not None:
                data = self.parse_pages(pages)
            else:
                data = []
            dataset = data
        else:
            data = self.fetchByField(searchquery)
            dataset = [data]
        return dataset

    def get_pages(self, searchquery):
        search_url = self.base_url + "/CEIDG/CEIDG.Public.UI/Search.aspx"
        r = self.session.get(search_url, headers=self.browser_header)

        data, tree = self.prepare_data(r, searchquery)
        r = self.session.post(search_url, data=data, headers=self.browser_header)
        data, tree = self.prepare_data(r, searchquery)
        links = []
        for i in range(0, 10):
            try:
                link = tree.xpath(
                    f'//*[@id="MainContent_DataListEntities_hrefDetails_{i}"]'
                )[0].get("href")
                rlink = self.base_url + "/CEIDG/CEIDG.Public.UI/" + link
                links.append(rlink)
            except:
                break
        return links

    def fetchByField(self, link):
        link_list = base64.b64decode(link).decode("utf-8")
        link = link_list.split("?reg_no=")[0]
        res = self.parse(link)
        return res

    def parse_pages(self, pages):
        rlist = []
        for link in pages:
            res = self.parse(link)
            if res is not None:
                rlist.append(res)
                if len(rlist) == 10:
                    break
        return rlist

    def prepare_data(self, r, searchquery):
        tree = etree.HTML(r.content)
        data = {i.get("name"): i.get("value", "") for i in tree.xpath("//input")}
        data["ctl00$MainContent$txtName"] = f"{searchquery}"
        data["ctl00$MainContent$cbIncludeCeased"] = "on"
        data["ctl00$MainContent$btnSearch"] = "Find"
        data.pop("ctl00$MainContent$btnClear")
        data.pop("ctl00$versionDetails$btnClose")
        return data, tree

    def check_parse_firm_name(self, firm_name):
        splitted_name = re.split("[\d]+[.)] ?", firm_name)
        if len(splitted_name) == 1:
            return firm_name.strip(), ""
        else:
            aka = list(map(self.pretify_string, splitted_name[2:]))
            return self.pretify_string(splitted_name[1]), aka

    def pretify_string(self, text):
        remove_list = ["\n", ";", ",", " "]
        while True:
            if text[-1] in remove_list:
                text = text[:-1]
            else:
                break
        return text

    def get_business_classifier(self, tree):
        classes = [i.text for i in tree.xpath('//*[@field="PKD2007"]')]
        test = tree.xpath('//div[contains(text(), "Type of major activity")]/..//b')
        try:
            description = test[1].text
        except Exception as e:
            description = ""
        result_list = []
        temp_dict = {}
        if classes:
            temp_dict["code"] = classes[0]
        else:
            temp_dict["code"] = ""
        temp_dict["description"] = description
        temp_dict["label"] = "Polish Classification of Activities"
        result_list.append(temp_dict)
        for i in classes[1:]:
            temp_dict = {}
            temp_dict["code"] = i
            temp_dict["description"] = ""
            temp_dict["label"] = "Polish Classification of Activities"
            result_list.append(temp_dict)
        return result_list

    def get_address(self, tree):
        address = {"country": "Poland"}
        try:
            fulladdress = tree.xpath(
                '//*[@id="MainContent_lblPlaceOfBusinessAddress"]'
            )[0].text
            if fulladdress:
                address["fullAddress"] = fulladdress
        except:
            pass
        return address

    def get_postal_address(self, tree):
        address = {"country": "Poland"}
        try:
            fulladdress = tree.xpath('//*[@id="MainContent_lblCorrespondenceAddress"]')[
                0
            ].text
            if fulladdress:
                address["fullAddress"] = fulladdress
        except:
            pass
        return address

    def get_identifiers(self, tree):
        identifiers = {}
        try:
            vat_tax_number = tree.xpath('//*[@id="MainContent_lblNip"]')[0].text
            if vat_tax_number:
                identifiers["vat_tax_number"] = vat_tax_number
        except:
            pass

        try:
            trade_register_number = tree.xpath('//*[@id="MainContent_lblRegon"]')[
                0
            ].text
            if trade_register_number:
                identifiers["trade_register_number"] = trade_register_number
        except:
            pass
        return identifiers

    def check_dict(self, dictionary):
        for key, value in dictionary.copy().items():
            if value == "" or value == "-":
                dictionary.pop(key)
        return dictionary

    def parse(self, link):
        self.session.cookies.set("ceidgLangSetting", "EN", domain="prod.ceidg.gov.pl")
        r = self.session.get(link)
        tree = etree.HTML(r.content)
        edd = {}

        if self.FETCH_TYPE == "overview" or self.FETCH_TYPE == "":
            company = {
                "vcard:organization-name": (
                    self.check_parse_firm_name(
                        tree.xpath('//*[@id="MainContent_lblName"]')[0].text
                    )
                )[0],
                "hasActivityStatus": "Active",
            }
            aka = self.check_parse_firm_name(
                tree.xpath('//*[@id="MainContent_lblName"]')[0].text
            )[1]
            if aka:
                company["bst:aka"] = aka

            businessClassifier = self.get_business_classifier(tree)
            if businessClassifier:
                company["bst:businessClassifier"] = businessClassifier

            try:
                hasURL = tree.xpath('//*[@id="MainContent_lblWebstite"]/a')[0].text
                if hasURL:
                    company["hasURL"] = hasURL
            except:
                pass

            try:
                email = tree.xpath('//*[@id="MainContent_lblEmail"]/a')[0].text
                if email:
                    company["bst:email"] = email
            except:
                pass

            company["isDomiciledIn"] = "PL"

            address = self.get_address(tree)
            if address:
                company["mdaas:RegisteredAddress"] = address

            PostalAddress = self.get_postal_address(tree)
            if PostalAddress:
                company["mdaas:PostalAddress"] = PostalAddress

            try:
                hasRegisteredPhoneNumber = tree.xpath(
                    '//*[@id="MainContent_lblPhone"]'
                )[0].text
                if hasRegisteredPhoneNumber:
                    company[
                        "tr-org:hasRegisteredPhoneNumber"
                    ] = hasRegisteredPhoneNumber
            except:
                pass

            try:
                hasLatestOrganizationFoundedDate = tree.xpath(
                    '//*[@id="MainContent_lblDateOfCommencementOfBusiness"]'
                )[0].text
                if hasLatestOrganizationFoundedDate:
                    company[
                        "hasLatestOrganizationFoundedDate"
                    ] = hasLatestOrganizationFoundedDate
            except:
                pass

            try:
                dissolutionDate = tree.xpath(
                    '//*[@id="MainContent_lblDateOfCessationOfBusinessActivity"]'
                )[0].text
                if dissolutionDate:
                    company["dissolutionDate"] = dissolutionDate
            except:
                pass

            try:
                regExpiryDate = tree.xpath(
                    '//*[@id="MainContent_lblDateOfCancellationOfBusinessActivity"]'
                )[0].text
                if regExpiryDate:
                    company["regExpiryDate"] = regExpiryDate
            except:
                pass

            identifiers = self.get_identifiers(tree)
            if identifiers:
                company["identifiers"] = identifiers
            company["bst:registryURI"] = link

            company = self.check_dict(company)

            edd["overview"] = company

        id = tree.xpath('//*[@id="MainContent_lblRegon"]')[0].text

        link = link + "?reg_no=" + id
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
        return data
