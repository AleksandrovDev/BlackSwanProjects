import datetime
import json
import re
import math
import urllib

import pycountry
from lxml import etree

from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "http://www.rra.gov.rw/"

    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;"
        "q=0.8,application/signed-exchange;v=b3;q=0.9;application/json;application/json;odata=verbose",
        "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8; text/html;",
        "Host": "rwandatrade.rw",
        "Referer": "https://rwandatrade.rw/Contacts?search=bank&l=en",
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
    ]

    NICK_NAME = base_url.split("//")[-1][:-1]

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

    def getpages(self, searchquery):
        self.get_initial_page(searchquery)
        companies = self.get_result_list_by_path(
            '//div[@class="directory-thumb-list"]//div[@class="item"]/a[2]/@href'
        )
        companies = ["https://rwandatrade.rw" + i for i in companies]
        return companies

    def get_initial_page(self, searchquery):
        searchquery = self.makeUrlFriendlySearchQuery(searchquery)

        link = f"https://rwandatrade.rw/Contacts?search={searchquery}&l=en"
        requestOptions = {
            "url": link,
            "method": "GET",
        }
        self.getDataFromPage(requestOptions)

    def makeUrlFriendlySearchQuery(self, searchquery):
        return urllib.parse.quote_plus(searchquery)

    def getDataFromPage(self, requestOptions):
        currentRequestOptions = self.createCurrentRequestOptions(requestOptions)

        content = self.get_content(
            currentRequestOptions["url"],
            currentRequestOptions["headers"],
            currentRequestOptions["data"],
            currentRequestOptions["method"],
        ).content

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
        requestOptions = {"url": link}
        self.getDataFromPage(requestOptions)

        path = f"//div[@class='row']//table//tr/td[2]//b[1]//text()[contains(., '{link}')]/../../.."

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
            if country == "":
                return "Rwanda"

        def extraHandlingStreetAddress(addr):
            add = addr.split(", ")
            if add:
                return add[0]
            else:
                return ""

        def extraHandlingCity(addr):
            add = addr.split(", ")
            if add:
                return add[-1]
            else:
                return ""

        def extraHandlingFullAddress(fullAddress):
            if fullAddress:
                return fullAddress + ", Rwanda"
            else:
                return "Rwanda"

        fetchedFields = {
            "tr-org:hasRegisteredPhoneNumber": [
                '//div[@class="content"]//div[@class="text"]//i[@class="fal fa-phone"]/following-sibling::div//text()',
                lambda x: x[-1] if type(x) == list else x,
            ],
            "vcard:organization-name": ['//div[@class="content"]//h4/text()'],
            "hasURL": [
                '//div[@class="content"]//div[@class="text"]//i[@class="fal fa-globe"]/following-sibling::div//text()'
            ],
            "bst:email": [
                '//div[@class="content"]//div[@class="text"]//i[@class="fal fa-envelope"]/following-sibling::div//text()'
            ],
            "mdaas:RegisteredAddress": {
                "country": ["", extraHandlingCountry],
                "streetAddress": [
                    '//div[@class="content"]//div[@class="text"]//i[@class="fal fa-home"]/following-sibling::div//text()'
                ],
                "fullAddress": [
                    '//div[@class="content"]//div[@class="text"]//i[@class="fal fa-home"]/following-sibling::div//text()',
                    extraHandlingFullAddress,
                ],
            },
        }

        hardcodedFields = {
            "@source-id": self.base_url,
            "isDomiciledIn": "RW",
            "bst:registryURI": link,
            "bst:sourceLinks": [link],
        }

        temp = self.extract_data(fetchedFields, hardcodedFields, companyInformation)

        temp[
            "map"
        ] = "https://www.google.com/maps/search/" + self.makeUrlFriendlySearchQuery(
            temp["vcard:organization-name"]
        )

        return temp

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
                if type(v) == dict:
                    value = self.recursive_filling_dict(v)
                else:
                    value = self.get_filled_value(v)
                if value:
                    newDict[k] = value
            return newDict
        else:
            value = self.get_filled_value(data)
            return value

    def get_filled_value(self, data):
        extractingPath = data[0]

        typeOfData = self.get_path_type(extractingPath)

        element = self.extract_element_based_on_type(typeOfData, extractingPath)

        if len(data) == 2:
            handlingFunction = data[1]
            element = handlingFunction(element)
        return element

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
            "information_source": link,
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
