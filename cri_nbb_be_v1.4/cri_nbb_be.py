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


class Handler(Extract, GetPages):
    base_url = "https://cri.nbb.be/"
    sourceId = base_url.split("https://")[-1][:-1]

    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;"
        "q=0.8,application/signed-exchange;v=b3;q=0.9;application/json;application/json;odata=verbose",
        "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8; text/html; text/xml;charset=UTF-8",
    }

    defaultRequestOptions = {
        "url": None,
        "method": "GET",
        "headers": header,
        "data": None,
        "returnType": "tree",
        "allow_redirects": True,
    }

    fields = [
        "overview",
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

        companies1 = self.get_result_list_by_path(
            '//div[@class="dataMain dataMainReadOnlyTable"]//tr/td[2]//text()'
        )
        companies = self.get_result_list_by_path(
            '//div[@class="dataMain dataMainReadOnlyTable"]//tr/td[3]//text()'
        )
        if companies:
            companies = [i.replace(".", "") for i in companies]

        if not companies:
            self.session.close()
            self.session = requests.Session()
            self.get_initial_page_for_one(searchquery)
            companies = self.extractedData.xpath(
                '//div[@class="fieldset level1 plain block"]//tr/td[1]/text()[contains(., "Company number")]/../following-sibling::td[1]/text()'
            )

            if companies:
                companies = [i.replace(".", "") for i in companies]
            return companies
        return companies

    def get_initial_page(self, searchquery, add=None):
        link = f"https://cri.nbb.be/bc9/web/companyfile?execution=e1s1"
        requestOptions = {
            "url": link,
            "method": "GET",
        }
        self.getDataFromPage(requestOptions)

        link = self.last_link + "?execution=e1s1"

        data = {
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": "page_searchForm:actions:0:button",
            "javax.faces.partial.execute": "page_searchForm",
            "javax.faces.partial.render": "page_searchForm page_listForm pageMessagesId",
            "page_searchForm:actions:0:button": "page_searchForm:actions:0:button",
            "page_searchForm": "page_searchForm",
            "page_searchForm:j_id3:generated_number_2_component": "",
            "page_searchForm:j_id3:generated_name_4_component": f"{searchquery}",
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

        if currentRequestOptions["method"] == "POST":
            content = self.session.post(
                url=currentRequestOptions["url"],
                headers=currentRequestOptions["headers"],
                data=currentRequestOptions["data"],
                allow_redirects=currentRequestOptions["allow_redirects"],
            )
        else:
            content = self.session.get(
                url=currentRequestOptions["url"],
                headers=currentRequestOptions["headers"],
                allow_redirects=currentRequestOptions["allow_redirects"],
            )

        for resp in content.history:
            self.last_link = resp.url

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
        path = path.split("/")
        if path == [""]:
            return [self.extractedRawDict]
        for i in path:
            if type(resultValue) == list:
                resultValue = resultValue[0]
            try:
                resultValue = resultValue[i]
            except Exception as e:
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
        try:
            self.session = requests.Session()
            cont = self.get_initial_page2(link)

            self.session.close()
            self.extractedData = etree.HTML(cont)
        except:
            pass

        companyInformation = self.extractedData

        def extraHandlingCode(code):
            return code.split(" - ")[0]

        def extraHandlingDescription(description):
            return description.split(" - ")[-1]

        def extraHandlingLabel(description):
            return description

        def extraHandlingLeiLabel(label):
            if label == "":
                return "Sole"
            return label[2:]

        def extraHandlingIsIncorporatedIn(date):
            return date.split("T")[0]

        def extraHandlingCountry(country):
            if country == "" or not country or country is None:
                return "Belgium"
            else:
                addr = country.split(" ")[0]
                country = self.get_country_name_by_iso_code(addr)
            return country

        def extraHandlingStreetAddress(addr):
            add = addr.split(", ")
            if add:
                return add[0]
            else:
                return ""

        def extraHandlingCity(addr):
            if addr == "" or not addr or addr is None:
                return ""
            add = addr.split(" ")
            if add:
                return add[-1]
            else:
                return ""

        def extraHandlingZip(zip):
            if zip and zip is not None:
                zip = re.findall("\d\d\d\d", zip)
                return zip[0]
            return ""

        def extraHandlingFullAddress(fullAddress):
            if fullAddress:
                return fullAddress
            else:
                return "Belgium"

        def extraHandlingIsIncorporatedIn(isIncorporatedIn):
            if isIncorporatedIn:
                return self.reformat_date(isIncorporatedIn.split(" ")[-1], "%d/%m/%Y")
            return ""

        fetchedFields = {
            "identifiers": {
                "trade_register_number": [
                    '//div[@class="fieldset level1 plain block"]//tr/td[1]/text()[contains(., "Company number")]/../following-sibling::td[1]/text()'
                ]
            },
            "isIncorporatedIn": [
                '//div[@class="fieldset level1 plain block"]//tr/td[2]/text()[contains(., "Since")]',
                extraHandlingIsIncorporatedIn,
            ],
            "lei:legalForm": {
                "code": [""],
                "label": [
                    '//div[@class="fieldset level1 plain block"]//tr/td[1]/text()[contains(., "Legal form")]/../following-sibling::td[1]/text()'
                ],
            },
            "vcard:organization-name": [
                '//div[@class="fieldset level1 plain block"]//tr/td[1]/text()[contains(., "Name")]/../following-sibling::td[1]/text()'
            ],
            "hasActivityStatus": [
                '//div[@class="fieldset level1 plain block"]//tr/td[1]/text()[contains(., "Legal situation")]/../following-sibling::td[1]/text()'
            ],
            "bst:businessClassifier": {
                "code": [
                    '//div[@class="fieldset level1 plain block"]//tr/td[1]//text()[contains(., "Activity code")]/../../following-sibling::td[1]/text()',
                    lambda x: x.split(" ")[0] if x else "",
                ],
                "description": [
                    '//div[@class="fieldset level1 plain block"]//tr//td[1]//text()[contains(., "Activity code")]/../../following-sibling::td[1]/text()',
                    lambda x: x.split("- ")[-1] if x else "",
                ],
                "label": [
                    '//div[@class="fieldset level1 plain block"]//tr/td[1]//text()[contains(., "Activity code")]',
                    lambda x: x.split("(")[-1].split(")")[0] if x else "",
                ],
            },
            "mdaas:RegisteredAddress": {
                "country": [
                    '//div[@class="fieldset level1 plain block"]//tr//td[1]//text()[contains(., "Address")]/../../following-sibling::tr[1]/td[2]//text()',
                    extraHandlingCountry,
                ],
                "streetAddress": [
                    '//div[@class="fieldset level1 plain block"]//tr//td[1]//text()[contains(., "Address")]/../following-sibling::td[1]/text()'
                ],
                "city": [
                    '//div[@class="fieldset level1 plain block"]//tr//td[1]//text()[contains(., "Address")]/../../following-sibling::tr[1]/td[2]//text()',
                    extraHandlingCity,
                ],
                "zip": [
                    '//div[@class="fieldset level1 plain block"]//tr//td[1]//text()[contains(., "Address")]/../../following-sibling::tr[1]/td[2]//text()',
                    extraHandlingZip,
                ],
            },
        }

        hardcodedFields = {
            "@source-id": self.sourceId,
            "regulator_name": "The National Bank of Belgium",
            "regulatorAddress": {
                "fullAddress": "de Berlaimontlaan 14 1000 Brussel",
                "city": "Brussel",
                "country": "Belgium",
            },
            "regulator_url": self.base_url,
        }

        result = self.extract_data(fetchedFields, hardcodedFields, companyInformation)

        result = self.fill_full_address(result)
        result = self.fill_is_domicled_in_based_on_country(result)
        try:
            if (
                result["mdaas:RegisteredAddress"].get("city")
                or result["mdaas:RegisteredAddress"].get("zip")
                or result["mdaas:RegisteredAddress"].get("streetAddress")
            ):
                pass
            else:
                result.pop("mdaas:RegisteredAddress")

        except:
            pass
        try:
            result["bst:businessClassifier"] = [result["bst:businessClassifier"]]
            if (
                result["bst:businessClassifier"][0].get("code") is None
                or result["bst:businessClassifier"][0].get("code") == "-"
            ):
                result.pop("bst:businessClassifier")
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
            fetchedFieldsData[k] = v

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
            totalAddress = []
            totalAddress.append(
                address.get("streetAddress") if address.get("streetAddress") else ""
            )
            totalAddress.append(address.get("zip") if address.get("zip") else "")
            totalAddress.append(address.get("city") if address.get("city") else "")
            totalAddress.append(
                address.get("country") if address.get("country") else ""
            )
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
        string_encode = value.encode("ascii", "ignore")
        string_decode = string_encode.decode()

        value = string_decode.split(" ")
        value = [i.strip() for i in value if i.strip()]
        value = " ".join(value)
        return value

    def get_officership(self, link):
        requestOptions = {"url": link}
        self.getDataFromPage(requestOptions)

        officersElements = self.get_elements_list_by_path('//div[@class="item-person"]')

        if not officersElements:
            return []

        fetchedFields = {
            "name": ['./div/div[@class="contacts-unit-title"]/text()'],
            "occupation": ['./div/div[@class="proffession"]/text()'],
            "officer_role": ['./div/div[@class="proffession"]/text()'],
        }

        hardcodedFields = {
            "type": "Individual",
            "status": "Active",
            "country": "Rwanda",
            "information_source": self.base_url,
            "information_provider": "RRA Rwanda Revenue Authority",
        }

        return self.extract_officers(fetchedFields, hardcodedFields, officersElements)

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
