import datetime
import hashlib
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
    base_url = "https://smida.gov.ua/"

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

    fields = [
        "overview",
        "officership",
        "graph:shareholders",
    ]

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
            '//table[@class="xsTableReport"]//tr/td[2]/a/@href'
        )

        companies = ["https://smida.gov.ua" + i for i in companies]
        return companies

    def get_initial_page(self, searchquery, add=None):
        link = f"https://smida.gov.ua/db/emitent/search"
        requestOptions = {"url": link, "method": "GET", "returnType": "tree"}
        self.getDataFromPage(requestOptions)

        data = {
            "find[edrpou]": searchquery,
            "page": "0",
        }
        requestOptions = {
            "url": link,
            "method": "POST",
            "data": data,
            "returnType": "tree",
        }
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
            j = html.fromstring(content.decode("utf-8"))
            self.extractedData = j

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

        fetchedFields = {
            "identifiers": {
                "trade_register_number": [
                    '//text()[contains(., "ЄДРПОУ:")]/../following-sibling::td[1]/text()'
                ],
                "other_company_id_number": [
                    '//text()[contains(., "КОАТУУ:")]/../following-sibling::td[1]/text()',
                    lambda x: x.split(" ")[0].split("-")[-1] if x else None,
                ],
            },
            "lei:legalForm": {
                "code": [""],
                "label": [
                    '//h2[@class="first"]/text()',
                    lambda x: x.split('"')[0].split(" - ")[-1] if x else None,
                ],
            },
            "vcard:organization-name": [
                '//text()[contains(., "Cкорочена назва:")]/../following-sibling::td[1]/text()'
            ],
            "mdaas:RegisteredAddress": {
                "fullAddress": [
                    '//text()[contains(., "Юридична адреса:")]/../following-sibling::td[1]/text()'
                ],
            },
            "bst:aka": [
                '//text()[contains(., "Cкорочена назва:")]/../following-sibling::td[1]/text()',
                lambda x: [x] if x else None,
            ],
            "bst:registrationId": [
                '//text()[contains(., "КОАТУУ:")]/../following-sibling::td[1]/text()',
                lambda x: x.split(" ")[0].split("-")[-1] if x else None,
            ],
        }

        hardcodedFields = {
            "isDomiciledIn": "UA",
            "regulator_name": "Агентство з розвитку інфраструктури фондового ринку України",
            "regulationStatus": "Authorised",
            "bst:registryURI": link,
            "regulationStatusEffectiveDate": "1993-06-24",
        }

        try:
            result = self.extract_data(
                fetchedFields, hardcodedFields, self.extractedData
            )
        except Exception as e:
            print(e)

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
            extractedResult["mdaas:RegisteredAddress"]["fullAddress"] = " ".join(
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
        return value

    def get_officership(self, link):
        requestOptions = {"url": link, "method": "GET", "returnType": "tree"}
        self.getDataFromPage(requestOptions)

        officersElements = self.get_elements_list_by_path(
            '//text()[contains(., "Керівник:")]/../following-sibling::td[1]/text()'
        )

        if not officersElements:
            return []

        fetchedFields = {
            "name": [
                '//text()[contains(., "Керівник:")]/../following-sibling::td[1]/text()',
                lambda x: x.split(", ")[0] if x else None,
            ],
            "occupation": [
                '//text()[contains(., "Керівник:")]/../following-sibling::td[1]/text()',
                lambda x: x.split(", ")[1] if x else None,
            ],
            "officer_role": [
                '//text()[contains(., "Керівник:")]/../following-sibling::td[1]/text()',
                lambda x: x.split(", ")[0] if x else None,
            ],
        }

        hardcodedFields = {
            "type": "Individual",
            "status": "Active",
            "country": "Rwanda",
            "information_source": self.base_url,
            "information_provider": "Stock Market Infrastructure Development Agency ofUkraine",
        }

        return self.extract_officers(fetchedFields, hardcodedFields, self.extractedData)

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

    def get_shareholders(self, link):
        requestOptions = {"url": link, "method": "GET", "returnType": "tree"}
        self.getDataFromPage(requestOptions)
        edd = {}
        shareholders = {}
        sholdersl1 = {}

        company = self.get_overview(link)
        company_name_hash = hashlib.md5(
            company["vcard:organization-name"].encode("utf-8")
        ).hexdigest()

        holdersRows = self.extractedData.xpath('//div[@id="owners"]//tr')
        if not holdersRows:
            return edd, sholdersl1
        holdersnames = [
            i.xpath("./td[2]/text()")[0]
            for i in holdersRows[2:]
            if i.xpath("./td[2]/text()")
        ]
        print(holdersnames)
        for holder, n in zip(holdersRows[2:], holdersnames):
            holder_name_hash = hashlib.md5(n.encode("utf-8")).hexdigest()

            fetch = {
                "@sourceReferenceID": ["./td[1]/text()"],
                "vcard:organization-name": ["./td[2]/text()"],
                "relation": {
                    "totalPercentage": ["./td[8]/text()"],
                },
            }
            hard = {
                "isDomiciledIn": "UA",
                "natureOfControl": "SHH",
            }
            holderInfo = self.extract_data(fetch, hard, holder)
            shareholders[holder_name_hash] = holderInfo
            basic_in = {"vcard:organization-name": n, "isDomiciledIn": "UA"}

            sholdersl1[holder_name_hash] = {"basic": basic_in, "shareholders": {}}
            edd[company_name_hash] = {"basic": company, "shareholders": shareholders}

        return edd, sholdersl1
