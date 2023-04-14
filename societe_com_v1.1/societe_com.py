import datetime
import json
import re
import math
import urllib

import pycountry
import requests
from lxml import etree

from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages
from lxml import html


class Handler(Extract, GetPages):
    base_url = "https://www.societe.com/"

    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    defaultRequestOptions = {
        "url": None,
        "method": "GET",
        "headers": header,
        "data": None,
        "returnType": "tree",
    }

    fields = ["overview", "officership", "branches", "Financial_Information"]

    NICK_NAME = base_url.split("//")[-1][:-1].replace("www", "")

    overview = {}

    extractedData = None
    companyData = None

    fieldsConfig = {
        "vcard:organization-name": str,
        "bst:sourceLinks": list,
        "bst:registryURI": str,
        "isDomiciledIn": str,
        "hasActivityStatus": str,
        "previous_names": list,
        "bst:businessClassifier": str,
        "mdaas:RegisteredAddressAddress": str,
        "mdaas:RegisteredAddressCountry": str,
        "identifiersRegNum": str,
        "isIncorporatedIn": str,
        "lei:legalForm": str,
        "bst:registrationId": str,
        "hasURL": str,
        "mdaas:RegisteredAddressAddressEntity": dict,
        "identifiersBic": str,
        "sourceDate": str,
    }

    forbiddenValues = [
        "NULL",
        "None Supplied",
        "Telp.",
    ]

    badSymbols = ["\\u00", "\\u00e9", "\\u00e0", "\\u00e8"]

    complicatedFields = [
        "bst:businessClassifier",
        "lei:legalForm",
        "identifiers",
        "previous_names",
        "mdaas:RegisteredAddress",
    ]

    last_link = ""
    next_tag = ""

    def getpages(self, searchquery):
        self.get_initial_page(searchquery)

        companies = self.extractedData.xpath(
            '//div[@id="result_deno_societe"]//a[@class="ResultBloc__link__content"]/@href'
        )
        companies2 = self.extractedData.xpath(
            '//div[@id="result_rs_societe"]//a[@class="ResultBloc__link__content"]/@href'
        )

        companies.extend(companies2)
        companies = ["https://www.societe.com" + i for i in companies]
        return companies

    def get_initial_page(self, searchquery, add=None):
        link = f"https://www.societe.com/cgi-bin/search?champs={searchquery}"
        requestOptions = {"url": link, "method": "GET", "returnType": "tree"}
        self.getDataFromPage(requestOptions)

    def get_initial_page2(self, searchquery, add=None):
        link = f"https://cri.nbb.be/bc9/web/companyfile"
        r = self.session.get(url=link, headers=self.header, allow_redirects=False)
        self.cokis = r.headers.get("Set-Cookie").split("JSESSIONID=")[-1].split(";")[0]

        link = f"https://cri.nbb.be/bc9/web/companyfile;jsessionid={self.cokis}?execution=e1s1"
        r = self.session.get(url=link, headers=self.header, allow_redirects=False)

        link = f"https://cri.nbb.be/bc9/web/companyfile;jsessionid={self.cokis}?execution=e1s1"
        data = {
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": "page_searchForm:actions:0:button",
            "javax.faces.partial.execute": "page_searchForm",
            "javax.faces.partial.render": "page_searchForm page_listForm pageMessagesId",
            "page_searchForm:actions:0:button": "page_searchForm:actions:0:button",
            "page_searchForm": "page_searchForm",
            "page_searchForm:j_id3:generated_number_2_component": searchquery,
            "page_searchForm:j_id3:generated_name_4_component": "",
            "page_searchForm:j_id3:generated_address_zipCode_6_component": "",
            "page_searchForm:j_id3_activeIndex": "0",
            "page_searchForm:j_id2_stateholder": "panel_param_visible;",
            "page_searchForm:j_idt136_stateholder": "panel_param_visible;",
            "javax.faces.ViewState": "e1s1",
        }
        r = self.session.post(
            url=link, headers=self.header, data=data, allow_redirects=False
        )

        r = self.session.get(
            url=f"https://cri.nbb.be/bc9/web/companyfile;jsessionid={self.cokis}?execution=e1s2",
            headers=self.header,
            allow_redirects=False,
        )

        return r.content

    def get_initial_page_for_one(self, searchquery):
        link = f"https://cri.nbb.be/bc9/web/companyfile?execution=e1s1"
        requestOptions = {
            "url": link,
            "method": "GET",
        }
        self.getDataFromPage(requestOptions)
        cookis = self.last_link.split("jsessionid=")[-1]

        link = (
            f"https://cri.nbb.be/bc9/web/companyfile;jsessionid={cookis}?execution=e1s1"
        )
        data = {
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": "page_searchForm:actions:0:button",
            "javax.faces.partial.execute": "page_searchForm",
            "javax.faces.partial.render": "page_searchForm page_listForm pageMessagesId",
            "page_searchForm:actions:0:button": "page_searchForm:actions:0:button",
            "page_searchForm": "page_searchForm",
            "page_searchForm:j_id3:generated_number_2_component": "",
            "page_searchForm:j_id3:generated_name_4_component": searchquery,
            "page_searchForm:j_id3:generated_searchPhoneticFlag_5_component": "on",
            "page_searchForm:j_id3:generated_address_zipCode_6_component": "",
            "page_searchForm:j_id3_activeIndex": "1",
            "page_searchForm:j_id2_stateholder": "panel_param_visible;",
            "page_searchForm:j_idt136_stateholder": "panel_param_visible;",
            "javax.faces.ViewState": "e1s1",
        }
        requestOptions = {
            "url": link,
            "method": "POST",
            "data": data,
            "allow_redirects": True,
        }
        self.getDataFromPage(requestOptions)

        link = (
            f"https://cri.nbb.be/bc9/web/companyfile;jsessionid={cookis}?execution=e1s2"
        )
        requestOptions = {"url": link, "method": "GET", "allow_redirects": True}
        self.getDataFromPage(requestOptions)

    def collect_data_from_several_links(self, links, searchquery):
        companiesList = []
        for link in links:
            self.get_initial_page(searchquery, link)
            companies = self.get_elements_list_by_path(
                f'//div[@class="row"]//table//tr/td[1]/text()[contains(translate(., "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{searchquery.lower()}")]/../..'
            )
            if companies:
                for company in companies:
                    fetchedFields = {
                        "vcard:organization-name": ["./td[1]//text()"],
                        "legislationidentifier": ["./td[3]//text()"],
                    }

                    hardcodedFields = {
                        "@source-id": self.base_url.replace("www.", ""),
                        "isDomiciledIn": "CA",
                        "regulator_name": "Digital Government and Service NL",
                        "regulatorAddress": {
                            "fullAddress": "10th. Floor, East Block Confederation Building St. John’s, NL A1B 4J6, Canada",
                            "city": "NL",
                            "country": "Canada",
                        },
                        "regulator_url": self.base_url,
                    }
                    companyData = self.extract_data(
                        fetchedFields, hardcodedFields, company
                    )
                    companiesList.append(companyData)
        return companiesList

    def get_csrf_token(self, name):
        return self.get_by_xpath(f'//input[@name="{name}"]/@value')

    def makeUrlFriendlySearchQuery(self, searchquery):
        return urllib.parse.quote_plus(searchquery)

    def getDataFromPage(self, requestOptions):
        currentRequestOptions = self.createCurrentRequestOptions(requestOptions)

        content = self.get_content(
            url=currentRequestOptions["url"],
            headers=currentRequestOptions["headers"],
            data=currentRequestOptions["data"],
            method=currentRequestOptions["method"],
        )

        content = content.content

        if currentRequestOptions["returnType"] == "tree":
            self.extractedData = etree.HTML(content)

        if currentRequestOptions["returnType"] == "api":
            self.extractedData = json.loads(content)

        return self.extractedData

    def createCurrentRequestOptions(self, requestOptions):
        defaultRequestOptions = dict(self.defaultRequestOptions)
        for k, v in requestOptions.items():
            defaultRequestOptions[k] = v
        return defaultRequestOptions

    def get_result_list_by_path(self, pathToResultList):
        outputType = self.get_path_type(pathToResultList)
        if outputType == "api":
            pathToResultList = pathToResultList.split("api: ")[-1]
            print("tests")
            return self.get_dict_value_by_path(pathToResultList, self.extractedData)
        if outputType == "tree":
            return self.get_by_xpath(pathToResultList)

    def get_path_type(self, dataPath):
        if type(dataPath) == list:
            dataPath = dataPath[0]
        if type(dataPath) == dict:
            dataPath = list(dataPath.values())
            dataPath = [i for i in dataPath if i != ""]
            if dataPath:
                dataPath = dataPath[0]
        if "/" in dataPath[:2]:
            return "tree"
        if "api: " in dataPath:
            return "api"
        else:
            return "rawElement"

    def get_dict_value_by_path(self, path, dictData):
        resultValue = dict(dictData)
        if "api: " in path:
            path = path.replace("api: ", "")
        path = path.split("/")
        if path == [""]:
            return [self.extractedRawDict]
        for i in path:
            if type(resultValue) == list:
                resultValue = resultValue[0]
            try:
                resultValue = resultValue[i]
            except Exception as e:
                print(e)
                return None
        return resultValue

    def get_companies_value(self, linkPath, listData):
        companyLinks = []
        for company in listData:
            x = self.get_dict_value_by_path(linkPath, company)
            if x:
                companyLinks.append(x)
        return companyLinks

    def get_by_xpath(self, xpath):
        try:
            el = self.extractedData.xpath(xpath)

        except Exception as e:
            print(e)
            return None
        if el:
            if type(el) == str or type(el) == list:
                el = [i.strip() for i in el]
                el = [i for i in el if i != ""]
            if len(el) > 1 and type(el) == list:
                el = list(dict.fromkeys(el))
            return el
        else:
            return None

    def get_hidden_values_ASP(self):
        names = self.get_by_xpath('//input[@type="hidden"]/@name')
        temp = {}
        for name in names:
            value = self.get_by_xpath(
                f'//input[@type="hidden"]/@name[contains(., "{name}")]/../@value'
            )
            temp[name] = value[0] if value else ""
        return temp

    def get_overview(self, link):
        requestOptions = {"url": link, "method": "GET", "returnType": "tree"}
        self.getDataFromPage(requestOptions)

        def parseWorkers(data):
            if data:
                for d in data:
                    workers = re.findall("\d+ et \d+", d)
                    if workers:
                        return workers[0]
            else:
                return None

        fetchedFields = {
            "vcard:organization-name": ['//h1[@id="identite_deno"]/text()'],
            "bst:description": [
                '//div[@class="FichePresentation__synthese break-word"]//p[1]//text()',
                lambda x: " ".join(x) if x else None,
            ],
            "bst:businessClassifier": {
                "code": [
                    '//div[@class="FicheDonnees__libelle"]/text()[contains(., "NAF")]/../following-sibling::div[1]/text()',
                    lambda x: x.split("(")[-1].split(")")[0] if x else None,
                ],
                "description": [
                    '//div[@class="FicheDonnees__libelle"]/text()[contains(., "NAF")]/../following-sibling::div[1]/text()',
                    lambda x: x.split(" (")[0] if x else None,
                ],
                "label": ["NAF"],
            },
            "isIncorporatedIn": [
                '//text()[contains(., "Date création entreprise")]/../following-sibling::td[1]/div/span[1]//text()',
                lambda x: self.reformat_date(x, "%d-%m-%Y") if x else None,
            ],
            "mdaas:RegisteredAddress": {
                "country": [
                    '//div[@class="CompanyIdentity__adress liengmap"]//p[3]/text()'
                ],
                "streetAddress": [
                    '//div[@class="CompanyIdentity__adress liengmap"]//p[1]/text()'
                ],
                "zip": [
                    '//div[@class="CompanyIdentity__adress liengmap"]//p[2]/text()',
                    lambda x: x.split(" ")[0] if x else None,
                ],
                "city": [
                    '//div[@class="CompanyIdentity__adress liengmap"]//p[2]/text()',
                    lambda x: " ".join(x.split(" ")[1:]) if x else None,
                ],
            },
            "identifiers": {
                "other_company_id_number": [
                    '//text()[contains(., "Numéro SIRET")]/../following-sibling::td[1]/div/div[1]/span[1]/text()'
                ],
            },
            "bst:registrationId": [
                '//text()[contains(., "Numéro SIREN")]/../following-sibling::td[1]/div/div[1]/span[1]/text()'
            ],
            "size": [
                '//div[@class="FichePresentation__synthese break-word"]//p[1]//text()',
                parseWorkers,
            ],
        }

        hardcodedFields = {
            "isDomiciledIn": "FR",
            "bst:registryURI": link,
            "lei:legalForm": {"code": "", "label": "Joint stock company"},
        }

        try:
            result = self.extract_data(
                fetchedFields, hardcodedFields, self.extractedData
            )
        except Exception as e:
            print(e)

        result = self.fill_full_address(result)

        try:
            result["bst:businessClassifier"] = [result["bst:businessClassifier"]]
        except:
            pass

        return result

    def find_company_on_the_page(self, path):
        elementWithInfo = self.extractedData.xpath(path)
        if elementWithInfo:
            return self.extractedData.xpath(path)[0]
        else:
            return None

    def extract_data(self, extractingFields, hardCodedFields, companyInformation):
        fetchedFieldsData = {}
        self.extractedData = companyInformation

        fetchedFields = self.recursive_filling_dict(extractingFields)

        for k, v in hardCodedFields.items():
            try:
                fetchedFieldsData[k] = v
            except:
                pass

        fetchedFieldsData.update(fetchedFields)

        return fetchedFieldsData

    def recursive_filling_dict(self, data):
        if type(data) == dict:
            newDict = {}
            for k, v in data.items():
                typeOfData = None
                if type(v) == dict:
                    value = self.recursive_filling_dict(v)
                else:
                    typeOfData = self.get_filled_value(v)[1]
                    value = self.get_filled_value(v)[0]
                if value or typeOfData == "rawElement":
                    newDict[k] = value
            return newDict
        else:
            value = self.get_filled_value(data)[0]
            return value

    def get_filled_value(self, data):
        extractingPath = data[0]
        typeOfData = self.get_path_type(extractingPath)
        element = self.extract_element_based_on_type(typeOfData, extractingPath)

        if len(data) == 2:
            handlingFunction = data[1]
            element = handlingFunction(element)
        return [element, typeOfData]

    def extract_element_based_on_type(self, typeOfData, extractingPath):
        if typeOfData == "tree":
            el = self.get_by_xpath(extractingPath)
        if typeOfData == "api":
            el = self.get_dict_value_by_path(extractingPath, self.extractedData)
        if typeOfData == "rawElement":
            el = extractingPath
        if type(el) == list and len(el) == 1:
            el = el[0]
        if el:
            el = self.getCleanValues(el)

        return el

    def fill_field(self, fieldName, data):
        el = self.recursive_filling_dict(data)
        self.overview[fieldName] = el

    def get_country_name_by_iso_code(self, isoCode):
        countryName = pycountry.countries.get(alpha_2=isoCode)
        return countryName.name

    def get_iso_by_country(self, country):
        country = pycountry.countries.search_fuzzy(country)
        return country[0].alpha_2

    def fill_full_address(self, extractedResult):
        address = extractedResult.get("mdaas:RegisteredAddress")
        if address:
            try:
                if address.get("streetAddress"):
                    if self.extractedData["address_street_type"] == "CL":
                        address["streetAddress"] = "CALLE " + address["streetAddress"]
                    address["streetAddress"] = (
                        address["streetAddress"]
                        + ", "
                        + self.extractedData["address_number"]
                    )
            except:
                pass
        totalAddress = []
        totalAddress.append(
            address.get("streetAddress") if address.get("streetAddress") else ""
        )
        totalAddress.append(address.get("zip") if address.get("zip") else "")
        totalAddress.append(address.get("city") if address.get("city") else "")
        totalAddress.append(address.get("country") if address.get("country") else "")
        if totalAddress:
            extractedResult["mdaas:RegisteredAddress"]["fullAddress"] = ", ".join(
                totalAddress
            )

        return extractedResult

    def fill_is_domicled_in_based_on_country(self, extractedResult):
        address = extractedResult.get("mdaas:RegisteredAddress")
        if address:
            country = address.get("country")
            if country:
                extractedResult["isDomiciledIn"] = self.get_iso_by_country(country)
                return extractedResult
        extractedResult["isDomiciledIn"] = "BE"
        return extractedResult

    def make_dict_from_string(self, link_dict):
        link_dict = (
            link_dict.replace("'", '"').replace("None", '"None"').replace('""', '"')
        )
        return json.loads(link_dict)

    def reformat_date(self, date, format):
        date = datetime.datetime.strptime(date.strip(), format).strftime("%Y-%m-%d")
        return date

    def getCleanValues(self, values):
        cleanValues = []
        if type(values) == str:
            values = [values]

        for value in values:
            if not self.isForbiddenValue(value):
                value = self.removeBadSymbols(value)
                cleanValues.append(value)

        if type(cleanValues) == list and len(cleanValues) == 1:
            cleanValues = cleanValues[0]
        return cleanValues

    def isForbiddenValue(self, value):
        return value in self.forbiddenValues

    def removeBadSymbols(self, value):
        string_encode = value.encode("ascii", "ignore")
        string_decode = string_encode.decode()

        value = string_decode.split(" ")
        value = [i.strip() for i in value if i.strip()]
        value = " ".join(value)
        return value

    def get_officership(self, link):
        link = link.replace("/societe/", "/dirigeants/")
        requestOptions = {"url": link, "method": "GET", "returnType": "tree"}
        self.getDataFromPage(requestOptions)

        president = self.extractedData.xpath(
            '//h4/text()[contains(., "Président")]/../following-sibling::table[1]//tr[1]'
        )

        officersElements = self.get_elements_list_by_path(
            '//h4/text()[contains(., "Directeur général")]/../following-sibling::table[1]//tr'
        )

        if not officersElements:
            return []

        fetchedFields = {
            "name": ["./td[1]/span[1]/a/span//text()"],
            "occupation": [
                "./td[1]//span[2]/text()",
                lambda x: x.split(" ")[0] if x else None,
            ],
            "officer_role": [
                "./td[1]//span[2]/text()",
                lambda x: x.split(" ")[0] if x else None,
            ],
            "startDate": [
                "./td[1]//span[2]/span/text()",
                lambda x: self.reformat_date(x, "%d-%m-%Y") if x else None,
            ],
        }

        hardcodedFields = {
            "type": "Individual",
            "status": "Active",
            "information_source": self.base_url,
            "information_provider": "societe.com",
        }

        hardcodedFieldsPr = {
            "type": "Individual",
            "status": "Active",
            "information_source": self.base_url,
            "information_provider": "societe.com",
        }

        result1 = self.extract_officers(
            fetchedFields, hardcodedFields, officersElements
        )

        presi = self.extract_officers(fetchedFields, hardcodedFieldsPr, president)

        if presi:
            result1.extend(presi)

        return result1

    def get_elements_list_by_path(self, path):
        elements = self.extractedData.xpath(path)
        return elements or None

    def extract_officers(self, fetchedFields, hardcodedFields, officersElements):
        officers = []
        for officerElement in officersElements:
            officer = self.extract_data(fetchedFields, hardcodedFields, officerElement)
            if officer:
                officers.append(officer)
        return officers

    def get_documents(self, link):
        docs = []
        link2 = f"https://aleph.occrp.org/api/2/entities?filter%3Aproperties.resolved={link}&filter%3Aschemata=Mention&limit=30"
        self.apiFetcher.extract_data(link2)
        self.apiFetcher.transfer_to_json()
        y = self.apiFetcher.get_companies_list_by_path("results")
        for doc in y:
            name = doc["properties"]["document"][0]["properties"]["fileName"]
            link = doc["properties"]["document"][0]["id"]
            link = self.base_url + "/entities/" + link
            docs.append({"description": name[0], "url": link})

        return docs

    def get_branches(self, link):
        link = link.replace("/societe/", "/etablissements/")
        requestOptions = {"url": link, "method": "GET", "returnType": "tree"}
        self.getDataFromPage(requestOptions)

        links = self.extractedData.xpath(
            '//text()[contains(., "établissements secondaires")]/../../div/p/a/@href'
        )
        links = ["https://www.societe.com/" + i for i in links if links]

        br = []
        linkas = []

        for b in links:
            requestOptions = {"url": b, "method": "GET", "returnType": "tree"}
            linkas.append(self.getDataFromPage(requestOptions))

        fetched = {
            "@sourceReferenceID": [
                '//text()[contains(., "N° de SIRET")]/../following-sibling::td[1]/text()'
            ],
            "vcard:organization-name": [
                '//text()[contains(., "Enseigne")]/../following-sibling::td[1]/text()'
            ],
            "mdaas:RegisteredAddress": {
                "zip": [
                    '//text()[contains(., "Code postal")]/../following-sibling::td[1]/text()'
                ],
                "country": [
                    '//text()[contains(., "Pays")]/../following-sibling::td[1]/text()'
                ],
                "streetAddress": [
                    '//text()[contains(., "Adresse")]/../following-sibling::td[1]/text()'
                ],
                "city": [
                    '//text()[contains(., "Ville")]/../following-sibling::td[1]/text()'
                ],
            },
        }

        hard = {
            "entity_type": "Q",
            "isDomiciledIn": "FR",
        }

        branches = self.extract_officers(fetched, hard, linkas)
        print(branches)

        return branches

    def get_shareholders(self, link):
        return {}

    def get_financial_information(self, link):
        requestOptions = {"url": link, "method": "GET", "returnType": "tree"}
        self.getDataFromPage(requestOptions)
        temp = {}
        sumFin = {}
        sumFin["source"] = self.base_url
        sumFin["inner_source"] = link
        cur = self.extractedData.xpath(
            '//text()[contains(., "Total du Bilan (Actif / Passif)")]/../following-sibling::td[2]/text()'
        )
        summary = {}
        if cur:
            x = cur[0].split(" ")[-1]
            summary["currency"] = "€" if x == "EU" else x
        coded = {}
        fetched = {
            "total_assets": [
                '//text()[contains(., "Total du Bilan (Actif / Passif)")]/../following-sibling::td[2]/text()'
            ],
            "total_liabilities": [
                '//text()[contains(., "Total du Bilan (Actif / Passif)")]/../following-sibling::td[2]/text()'
            ],
            "shareholders_funds": [
                '//text()[contains(., "dont Capitaux propres")]/../following-sibling::td[2]/text()'
            ],
        }
        balance_sheet = self.extract_data(fetched, coded, self.extractedData)
        fetched = {
            "profit": [
                '//text()[contains(., "Résultat net (Bénéfice ou Perte)")]/../following-sibling::td[2]/text()'
            ]
        }

        incSt = self.extract_data(fetched, coded, self.extractedData)
        if incSt:
            summary["income_statement"] = incSt

        if balance_sheet:
            summary["balance_sheet"] = balance_sheet
        if summary:
            sumFin["summary"] = summary
        temp["Summary_Financial_data"] = [sumFin]
        return temp
