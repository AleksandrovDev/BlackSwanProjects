import datetime
import hashlib
import re

from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://www.businessregistries.gov.ws/"
    NICK_NAME = "businessregistries.gov.ws"
    fields = ["overview", "officership", "graph:shareholders", "documents"]

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

    def get_tree_after_search(self, searchquery):
        search_url = "https://www.businessregistries.gov.ws/samoa-master/relay.html?url=https%3A%2F%2Fwww.businessregistries.gov.ws%2Fsamoa-br-companies%2Fservice%2Fcreate.html%3FtargetAppCode%3Dsamoa-master%26targetRegisterAppCode%3Dsamoa-br-companies%26service%3DregisterItemSearch&target=samoa-br-companies"
        r = self.get_content(search_url)
        cbnode = re.findall('appNotReadOnly appIndex2" id="nodeW\d+"', r.text)[0].split(
            "W"
        )[1][:-1]
        id = re.findall('update.html\?id=[\d\w]+"', r.text)[0].split("=")[1][:-1]
        data = {
            "QueryString": searchquery,
            "_CBNODE_": f"W{cbnode}",
            "_CBNAME_": "buttonPush",
        }
        sc_url = f"https://www.businessregistries.gov.ws/samoa-br-companies/viewInstance/update.html?id={id}"
        tree = self.get_tree(sc_url, method="POST", data=data)
        return tree, id

    def getpages(self, searchquery):
        names = []
        tree, _ = self.get_tree_after_search(searchquery)
        try:
            names = self.get_by_xpath(
                tree,
                '//a[@class="registerItemSearch-results-page-line-ItemBox-resultLeft-viewMenu appMenu appMenuItem appMenuDepth0 appItemSearchResult noSave viewInstanceUpdateStackPush appReadOnly appIndex0"]//span[2]/text()',
                return_list=True,
            )
        except:
            pass
        return names

    def reformat_date(self, date, format):
        date = datetime.datetime.strptime(date, format).strftime("%Y-%m-%d")
        return date

    def get_previous_names(self, tree):
        temp_list = []
        prev_name = self.get_by_xpath(
            tree,
            '//span[text()[contains(., "Previous Name")]]/../../following-sibling::div/text()',
        )
        prev_name_start = self.get_by_xpath(
            tree,
            '//span[text()[contains(., "Start Date")]]/../../following-sibling::div/text()',
        )
        prev_name_end = self.get_by_xpath(
            tree,
            '//span[text()[contains(., "End Date")]]/../../following-sibling::div/text()',
        )
        temp_dict = {}
        if prev_name:
            temp_dict["name"] = prev_name
            if prev_name_start:
                temp_dict["valid_from"] = self.reformat_date(
                    prev_name_start, "%d-%b-%Y %H:%M:%S"
                )
            if prev_name_end:
                temp_dict["valid_to"] = self.reformat_date(
                    prev_name_end, "%d-%b-%Y %H:%M:%S"
                )
            temp_list.append(temp_dict)
        if temp_list:
            return temp_list
        else:
            return None

    def get_business_classifier(self, tree):
        temp_list = []
        temp_dict = {}
        business_activity = self.get_by_xpath(
            tree,
            '//span[text()[contains(., "Business Activity")]]/../../following-sibling::div/text()',
        )
        if business_activity:
            temp_dict["code"] = ""
            temp_dict["description"] = business_activity
            temp_dict["label"] = ""
            temp_list.append(temp_dict)
        if temp_list:
            return temp_list
        else:
            return None

    def get_address(self, tree):
        temp_dict = {}
        address = self.get_by_xpath(
            tree,
            '//span[text()[contains(., "Registered Office Address")]]/../../following-sibling::div/text()',
        ).split(",")
        if address:
            temp_dict["country"] = address[-1]
            temp_dict["city"] = address[-3]
            temp_dict["streetAddress"] = (
                address[0] if "Unit" not in address[1] else "".join(address[:2])
            )
            temp_dict["fullAddress"] = "".join(address)
            return temp_dict
        else:
            return None

    def get_postal_address(self, tree):
        temp_dict = {}
        address = self.get_by_xpath(
            tree,
            '//span[text()[contains(., "Postal Address")]]/../../following-sibling::div/text()',
        ).split(",")
        if address:
            temp_dict["country"] = address[-1]
            temp_dict["city"] = address[-2]
            temp_dict["streetAddress"] = (
                address[0] if "Unit" not in address[1] else "".join(address[:2])
            )
            temp_dict["fullAddress"] = "".join(address)
            return temp_dict
        else:
            return None

    def get_identifiers(self, tree):
        temp_dict = {}
        identifier = self.get_by_xpath(
            tree,
            '//div[@class="appSingleLine appSingleLineNonBlank brViewLocalCompany-companyContextBox appAttribute companyContextBox appNonBlankAttribute appEntityContextBox appReadOnly appIndex0 appChildCount3"]/div[2]/text()',
        )
        if identifier:
            number = re.findall("(\d+)", identifier)[0]
            temp_dict["other_company_id_number"] = number
            return temp_dict
        else:
            return None

    def get_lei(self, tree):
        temp_dict = {}
        lei = self.get_by_xpath(
            tree,
            '//span[text()[contains(., "Company Type")]]/../../following-sibling::div/text()',
        )
        if lei:
            temp_dict["code"] = ""
            temp_dict["label"] = lei
            return temp_dict
        else:
            return None

    def get_holder_address(self, address):
        temp_dict = {}
        address = address.split(",")
        if address:
            temp_dict["country"] = address[-1]
            temp_dict["city"] = address[-3]
            temp_dict["streetAddress"] = (
                address[0] if "Unit" not in address[1] else "".join(address[:2])
            )
            temp_dict["fullAddress"] = "".join(address)
            return temp_dict
        else:
            return None

    def get_overview(self, link):
        tree, id = self.get_tree_after_search(link)
        sc_url = f"https://www.businessregistries.gov.ws/samoa-br-companies/viewInstance/update.html?id={id}"
        node = self.get_by_xpath(
            tree,
            '//div[@class="appMinimalMenu viewMenu appItemSearchResult noSave viewInstanceUpdateStackPush"]/a/@id',
        )
        node = node.split("e")[1]

        data = {"_CBNODE_": node, "_CBNAME_": "invokeMenuCb"}
        tree = self.get_tree(sc_url, method="POST", data=data)
        company = {}
        company_name = self.get_by_xpath(
            tree,
            '//span[text()[contains(., "Company Name")]]/../../following-sibling::div/text()',
        )
        if company_name:
            company["vcard:organization-name"] = company_name
            company["isDomiciledIn"] = "WS"
        else:
            return None

        trade_as = self.get_by_xpath(
            tree,
            '//span[text()[contains(., "Trading As")]]/../../following-sibling::div/text()',
        )
        if trade_as:
            company["vcard:organization-tradename"] = trade_as

        status = self.get_by_xpath(
            tree,
            '//span[text()[contains(., "Company Status")]]/../../following-sibling::div/text()',
        )
        if status:
            company["hasActivityStatus"] = status

        prev_names = self.get_previous_names(tree)
        if prev_names:
            company["previous_names"] = prev_names

        email = self.get_by_xpath(
            tree,
            '//span[text()[contains(., "Email")]]/../../following-sibling::div/text()',
        )
        if email:
            company["bst:email"] = email

        business_class = self.get_business_classifier(tree)
        if business_class:
            company["bst:businessClassifier"] = business_class

        link_new = tree.xpath('//form[@id="viewInstanceForm"]/@action')[0]
        text = "".join(tree.xpath("//div/@id"))
        node = re.findall("AsyncWrapperW\d+", text)[1].split("er")[1]

        data = {
            "_CBNODE_": node,
            "_CBNAME_": "tabSelect",
            "_CBVALUE_": "1",
            "_CBHTMLFRAG_": "true",
        }

        address_tree = self.get_tree(link_new, method="POST", data=data)

        address = self.get_address(address_tree)
        if address:
            company["mdaas:RegisteredAddress"] = address

        operational_address = self.get_by_xpath(
            address_tree,
            '//span[text()[contains(., "Address for Service")]]/../../following-sibling::div/text()',
        )
        if operational_address == "Same as Registered Office Address":
            company["mdaas:OperationalAddress"] = address.copy()
        elif operational_address:
            company["mdaas:OperationalAddress"] = self.get_address(address_tree)

        postal_address = self.get_postal_address(address_tree)
        if postal_address:
            company["mdaas:PostalAddress"] = postal_address

        identifiers = self.get_identifiers(tree)
        if identifiers:
            company["identifiers"] = identifiers

        isIncorporatedIn = self.get_by_xpath(
            tree,
            '//span[text()[contains(., "Incorporation Date")]]/../../following-sibling::div/text()',
        )
        if isIncorporatedIn:
            company["isIncorporatedIn"] = self.reformat_date(
                isIncorporatedIn, "%d-%b-%Y"
            )

        phone = self.get_by_xpath(
            tree,
            '//span[text()[contains(., "Telephone")]]/../../following-sibling::div/text()',
        )
        if phone:
            company["tr-org:hasRegisteredPhoneNumber"] = phone

        fax = self.get_by_xpath(
            tree,
            '//span[text()[contains(., "Fax")]]/../../following-sibling::div/text()',
        )
        if fax:
            if fax != "[Not Provided]":
                company["hasRegisteredFaxNumber"] = fax

        company["bst:registrationId"] = company["identifiers"][
            "other_company_id_number"
        ]

        lei = self.get_lei(tree)
        if lei:
            company["lei:legalForm"] = lei

        company["@source-id"] = self.NICK_NAME

        data = {
            "_CBNODE_": node,
            "_CBNAME_": "tabSelect",
            "_CBVALUE_": "3",
            "_CBHTMLFRAG_": "true",
        }

        shares_tree = self.get_tree(link_new, method="POST", data=data)
        shareCount = self.get_by_xpath(
            shares_tree,
            '//span[text()[contains(., "Total Shares")]]/../../following-sibling::div/text()',
        )
        if shareCount:
            company["shareCount"] = shareCount

        return company

    def get_shareholders(self, link):
        tree, id = self.get_tree_after_search(link)
        sc_url = f"https://www.businessregistries.gov.ws/samoa-br-companies/viewInstance/update.html?id={id}"
        node = self.get_by_xpath(
            tree,
            '//div[@class="appMinimalMenu viewMenu appItemSearchResult noSave viewInstanceUpdateStackPush"]/a/@id',
        )
        node = node.split("e")[1]

        data = {"_CBNODE_": node, "_CBNAME_": "invokeMenuCb"}
        tree = self.get_tree(sc_url, method="POST", data=data)

        link_new = tree.xpath('//form[@id="viewInstanceForm"]/@action')[0]
        text = "".join(tree.xpath("//div/@id"))
        node = re.findall("AsyncWrapperW\d+", text)[1].split("er")[1]
        data = {
            "_CBNODE_": node,
            "_CBNAME_": "tabSelect",
            "_CBVALUE_": "3",
            "_CBHTMLFRAG_": "true",
        }
        shares_tree = self.get_tree(link_new, method="POST", data=data)
        data = {
            "_CBNODE_": node,
            "_CBNAME_": "tabSelect",
            "_CBVALUE_": "4",
            "_CBHTMLFRAG_": "true",
        }
        shareParcels_tree = self.get_tree(link_new, method="POST", data=data)

        edd = {}
        shareholders = {}
        sholdersl1 = {}
        company = self.get_overview(link)
        company_name_hash = hashlib.md5(
            company["vcard:organization-name"].encode("utf-8")
        ).hexdigest()

        holders = self.get_by_xpath(
            shares_tree,
            '//div[@class="appCategory Current"]//span[contains(text(),"Name")]/../../following-sibling::div/text()',
            return_list=True,
        )
        addresses = self.get_by_xpath(
            shares_tree,
            '//div[@class="appCategory Current"]//span[contains(text(),"Registered Office Address")]/../../following-sibling::div/text()',
            return_list=True,
        )

        shares_name = self.get_by_xpath(
            shareParcels_tree,
            '//span[contains(text(),"Name")]/../../following-sibling::div/text()',
            return_list=True,
        )
        shares_name = [i.strip() for i in shares_name]
        shares = self.get_by_xpath(
            shareParcels_tree,
            '//span[contains(text(),"Number of shares")]/../../following-sibling::div/text()',
            return_list=True,
        )

        temp_dict = dict(zip(shares_name, shares))

        holders = [i.strip() for i in holders]

        for i in range(len(holders)):
            holder_name_hash = hashlib.md5(holders[i].encode("utf-8")).hexdigest()
            shareholders[holder_name_hash] = {
                "natureOfControl": "SSH",
                "source": "Ministry of Commerce, Industry & Labour",
                "totalPercentage": str(
                    round(
                        int(temp_dict[holders[i]]) / int(company["shareCount"]) * 100, 2
                    )
                )
                + "%",
            }

            basic_in = {
                "vcard:organization-name": holders[i],
                "isDomiciledIn": "WS",
                "mdaas: RegisteredAddress": self.get_holder_address(addresses[i]),
            }
            sholdersl1[holder_name_hash] = {"basic": basic_in, "shareholders": {}}
        edd[company_name_hash] = {
            "basic": company,
            "entity_type": "C",
            "shareholders": shareholders,
        }

        return edd, sholdersl1

    def get_documents(self, link):
        documents_list = []
        tree, id = self.get_tree_after_search(link)
        sc_url = f"https://www.businessregistries.gov.ws/samoa-br-companies/viewInstance/update.html?id={id}"
        node = self.get_by_xpath(
            tree,
            '//div[@class="appMinimalMenu viewMenu appItemSearchResult noSave viewInstanceUpdateStackPush"]/a/@id',
        )
        node = node.split("e")[1]

        data = {"_CBNODE_": node, "_CBNAME_": "invokeMenuCb"}
        tree = self.get_tree(sc_url, method="POST", data=data)

        link_new = tree.xpath('//form[@id="viewInstanceForm"]/@action')[0]
        text = "".join(tree.xpath("//div/@id"))
        node = re.findall("AsyncWrapperW\d+", text)[1].split("er")[1]
        data = {
            "_CBNODE_": node,
            "_CBNAME_": "tabSelect",
            "_CBVALUE_": "5",
            "_CBHTMLFRAG_": "true",
        }
        documents_tree = self.get_tree(link_new, method="POST", data=data)

        nodes = self.get_by_xpath(
            documents_tree,
            '//div[@class="appRepeaterContent"]//div[@class="appFiling" and contains(@id, "nodeW")]/@id',
            return_list=True,
        )
        nodes = [i.split("e")[1] for i in nodes]
        doc_names = self.get_by_xpath(
            documents_tree,
            '//div[@class="appFilingName"]/a/span/text()',
            return_list=True,
        )

        for doc, doc_name in zip(nodes, doc_names):
            data = {
                "_CBNODE_": doc,
                "_CBNAME_": "openFiling",
                "_CBVALUE_": "openFiling",
                "_CBHTMLFRAG_": "true",
            }

            document_tree = self.get_tree(link_new, method="POST", data=data)
            date = self.get_by_xpath(
                document_tree,
                '//div[@class="appFilingDetailDate appAttribute appReadOnly"]/div[2]/text()',
            )
            date = self.reformat_date(date, "%d-%b-%Y %H:%M:%S")
            links = self.get_by_xpath(
                document_tree,
                '//a[contains(@class, "appResourceLink")]//@href',
                return_list=True,
            )
            description = doc_name
            for i in links:
                temp_dict = {"date": date, "description": description, "url": i}
                documents_list.append(temp_dict)
        return documents_list

    def get_officership(self, link):
        officers = []

        tree, id = self.get_tree_after_search(link)
        sc_url = f"https://www.businessregistries.gov.ws/samoa-br-companies/viewInstance/update.html?id={id}"
        node = self.get_by_xpath(
            tree,
            '//div[@class="appMinimalMenu viewMenu appItemSearchResult noSave viewInstanceUpdateStackPush"]/a/@id',
        )
        node = node.split("e")[1]

        data = {"_CBNODE_": node, "_CBNAME_": "invokeMenuCb"}
        tree = self.get_tree(sc_url, method="POST", data=data)

        link_new = tree.xpath('//form[@id="viewInstanceForm"]/@action')[0]
        text = "".join(tree.xpath("//div/@id"))
        node = re.findall("AsyncWrapperW\d+", text)[1].split("er")[1]
        data = {
            "_CBNODE_": node,
            "_CBNAME_": "tabSelect",
            "_CBVALUE_": "2",
            "_CBHTMLFRAG_": "true",
        }
        officership_tree = self.get_tree(link_new, method="POST", data=data)
        names = self.get_by_xpath(
            officership_tree,
            '//div[@class="appCategory Current"]//span[text()[contains(., "Name")]]/../../following-sibling::div/text()',
            return_list=True,
        )
        names = [i.strip() for i in names]
        addresses = self.get_by_xpath(
            officership_tree,
            '//div[@class="appCategory Current"]//span[text()[contains(., "Residential Address")]]/../../following-sibling::div/text()',
            return_list=True,
        )

        for name, address in zip(names, addresses):
            officer = {
                "name": name,
                "type": "individual",
                "address": {"address_line_1": address},
                "officer_role": "director",
                "status": "Active",
                "country_of_residence": address.split(",")[-1].strip(),
                "occupation": "director",
                "information_source": sc_url,
                "information_provider": self.NICK_NAME,
            }
            officers.append(officer)

        return officers
