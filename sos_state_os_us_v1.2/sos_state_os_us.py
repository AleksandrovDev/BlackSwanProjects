import datetime
import json
import random
import re
import math
import time
import urllib

import pycountry
import requests
from geopy import Nominatim
from lxml import etree

from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://www.sos.state.oh.us/"
    NICK_NAME = base_url.split("//")[-1][:-1].replace("www.", "")

    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;"
        "q=0.8,application/signed-exchange;v=b3;q=0.9;application/json;application/json;odata=verbose",
        "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8; text/html;",
    }

    defaultRequestOptions = {
        "url": None,
        "method": "GET",
        "headers": header,
        "data": None,
        "returnType": "api",
        "allow_redirects": True,
    }

    fields = ["overview", "documents"]

    proxiesList = [{"https": "http://60.51.17.107:80"}]

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
        None,
    ]

    badSymbols = ["\\u00", "\\u00e9", "\\u00e0", "\\u00e8"]
    countProxy = 0

    complicatedFields = [
        "bst:businessClassifier",
        "lei:legalForm",
        "identifiers",
        "previous_names",
        "mdaas:RegisteredAddress",
    ]

    def changeProxy(self):
        self.countProxy += 1
        self.session.proxies = self.proxiesList[self.countProxy]
        print(self.session.proxies)

    def getpages(self, searchquery):
        self.session.proxies = self.proxiesList[self.countProxy]
        extractedData = self.get_initial_page(searchquery)
        extractedData = extractedData["data"]

        return extractedData

    def get_initial_page(self, searchquery):
        searchquery = self.makeUrlFriendlySearchQuery(searchquery)

        link = (
            f"https://businesssearchapi.ohiosos.gov/NS_{searchquery}_X?_=1664365502829"
        )

        headers = {
            "authority": "businesssearchapi.ohiosos.gov",
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
            "origin": "https://businesssearch.ohiosos.gov",
            "referer": "https://businesssearch.ohiosos.gov/",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
        }

        requestOptions = {
            "url": link,
            "method": "GET",
            "headers": headers,
            "returnType": "api",
        }
        return self.getDataFromPage(requestOptions)

    def get_companies_identities_from(self, extractedData, path):
        pathType = self.get_path_type(path)
        companiesIdentities = self.extract_element_based_on_type(
            pathType, path, extractedData
        )

        for company in extractedData:
            companiesIdentities.append(company["denomination"])
        return companiesIdentities

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
        return urllib.parse.quote(searchquery)

    def getDataFromPage(self, requestOptions):
        def createCurrentRequestOptions(requestOptions):
            defaultRequestOptions = dict(self.defaultRequestOptions)
            for k, v in requestOptions.items():
                defaultRequestOptions[k] = v
            return defaultRequestOptions

        currentRequestOptions = createCurrentRequestOptions(requestOptions)
        content = self.get_content(
            url=currentRequestOptions["url"],
            headers=currentRequestOptions["headers"],
            data=currentRequestOptions["data"],
            method=currentRequestOptions["method"],
            verify=False,
        )
        if content.status_code == 503:
            self.session.proxies = self.changeProxy()

        if currentRequestOptions["returnType"] == "tree":
            extractedData = etree.HTML(content)
            self.extractedData = extractedData
        if currentRequestOptions["returnType"] == "api":
            print(content, content.content)
            extractedData = json.loads(content.content)
        return extractedData

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

    def get_company_value_by_api_path(self, path, dictData):
        path = path.replace("api: ", "")

        def isListOfDictionaries(dictData):
            return len(dictData) > 1 and type(dictData) == list

        def extractSingleCompanyValueFromApiPath(dictData, path):
            resultValue = dict(dictData)
            path = path.split("/")
            if path == [""]:
                return [dictData]
            for i in path:
                if type(resultValue) == list:
                    resultValue = resultValue[0]
                try:
                    resultValue = resultValue[i]
                except Exception as e:
                    return None
            return resultValue

        def extractMultipleCompaniesValueFromApiPath(dictData, path):
            companiesIdentities = []
            for companyData in dictData:
                companyIdentity = extractSingleCompanyValueFromApiPath(
                    companyData, path
                )
                companiesIdentities.append(companyIdentity)
            return companiesIdentities

        if isListOfDictionaries(dictData):
            companiesIdentities = extractMultipleCompaniesValueFromApiPath(
                dictData, path
            )
            return companiesIdentities
        else:
            companyIdentity = extractSingleCompanyValueFromApiPath(dictData, path)
            return companyIdentity

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
        if type(link) == str:
            link = link.replace("'", '"')
            link = json.loads(link)
        url = f'https://businesssearchapi.ohiosos.gov/VD_{link["charter_num"]}'
        headers = {
            "authority": "businesssearchapi.ohiosos.gov",
            "accept": "application/json, text/javascript, */*; q=0.01",
            "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
            "origin": "https://businesssearch.ohiosos.gov",
            "referer": "https://businesssearch.ohiosos.gov/",
            "sec-ch-ua": '"Google Chrome";v="105", "Not)A;Brand";v="8", "Chromium";v="105"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
        }
        requestOptions = {"url": url, "headers": headers, "returnType": "api"}

        time.sleep(2)
        companyInformation = self.getDataFromPage(requestOptions)

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
            if date:
                date = int(date[:-3])

                return str(datetime.datetime.fromtimestamp(date)).split(" ")[0]
            return ""

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

        fetchedFields = {}

        hardcodedFields = {
            "vcard:organization-name": link["business_name"],
            "@source-id": "businesssearch_ohiosos_gov",
            "isDomiciledIn": "US",
            "bst:sourceLinks": [
                f'https://businesssearch.ohiosos.gov?=businessDetails/{link["charter_num"]}'
            ],
            "hasActivityStatus": link["status"],
            "bst:registryURI": f'https://businesssearch.ohiosos.gov?=businessDetails/{link["charter_num"]}',
            "lei:legalForm": {"code": "", "label": link["business_type"]},
            "identifiers": {"trade_register_number": link["charter_num"]},
            "registeredIn": link["state_name"],
            "isIncorporatedIn": link["effect_date"].split("T")[0],
        }

        result = self.extract_data(fetchedFields, hardcodedFields, companyInformation)

        try:
            result["dissolutionDate"] = link["expiry_date"].split("T")[0]
        except:
            pass

        try:
            prevNames = []
            prevNamesData = companyInformation["data"][0]["olddetails"]
            for name in prevNamesData:
                prevNames.append(
                    {
                        "name": name["old_name"],
                        "valid_from": self.reformat_date(
                            name["effective_date_time"], "%m/%d/%Y"
                        ),
                    }
                )
            if prevNames:
                result["previous_names"] = prevNames

        except:
            pass

        try:
            address = {}
            zip = companyInformation["data"][1]["registrant"][0].get("contact_zip9")
            street = companyInformation["data"][1]["registrant"][0].get(
                "contact_addr1"
            ) + companyInformation["data"][1]["registrant"][0].get("contact_addr2")
            city = companyInformation["data"][1]["registrant"][0].get("contact_city")
            state = companyInformation["data"][1]["registrant"][0].get("contact_state")
            address["zip"] = zip
            address["streetAddress"] = street
            address["city"] = city
            address["state"] = state
            address["country"] = "USA"
            address["fullAddress"] = ", ".join([street, city, state, zip, "USA"])
            result["mdaas:RegisteredAddress"] = address

        except Exception as e:
            pass

        resultCopy = {}
        for k in result.keys():
            if result[k] != "-":
                resultCopy[k] = result[k]

        return resultCopy

    def find_company_on_the_page(self, path):
        elementWithInfo = self.extractedData.xpath(path)
        if elementWithInfo:
            return self.extractedData.xpath(path)[0]
        else:
            return None

    def extract_data(self, extractingFields, hardCodedFields, companyInformation):
        fetchedFieldsData = {}

        fetchedFields = self.recursive_filling_dict(
            extractingFields, companyInformation
        )

        for k, v in hardCodedFields.items():
            fetchedFieldsData[k] = v

        fetchedFieldsData.update(fetchedFields)

        return fetchedFieldsData

    def recursive_filling_dict(self, data, extractedData):
        if type(data) == dict:
            newDict = {}
            for k, v in data.items():
                if type(v) == dict:
                    value = self.recursive_filling_dict(v, extractedData)
                else:
                    value = self.get_filled_value(v, extractedData)[0]
                    typeOfData = self.get_filled_value(v, extractedData)[1]
                if value or typeOfData == "rawElement":
                    newDict[k] = value
            return newDict
        else:
            value = self.get_filled_value(data, extractedData)
            return value

    def get_filled_value(self, data, extractedData):
        extractingPath = data[0]

        typeOfData = self.get_path_type(extractingPath)
        element = self.extract_element_based_on_type(
            typeOfData, extractingPath, extractedData
        )

        if len(data) == 2:
            handlingFunction = data[1]
            element = handlingFunction(element)
        return [element, typeOfData]

    def extract_element_based_on_type(self, typeOfData, extractingPath, extractedData):
        if typeOfData == "tree":
            el = self.get_by_xpath(extractingPath)
        if typeOfData == "api":
            el = self.get_company_value_by_api_path(extractingPath, extractedData)
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
        def removeBadSymbols(value):
            string_encode = value.encode("ascii", "ignore")
            string_decode = string_encode.decode()

            value = string_decode.split(" ")
            value = [i.strip() for i in value if i.strip()]
            value = " ".join(value)
            return value

        cleanValues = []
        if type(values) == int:
            values = str(values)
        if type(values) == str:
            values = [values]

        for value in values:
            if not self.isForbiddenValue(value):
                value = removeBadSymbols(value)
                cleanValues.append(value)

        if type(cleanValues) == list and len(cleanValues) == 1:
            cleanValues = cleanValues[0]
        return cleanValues

    def isForbiddenValue(self, value):
        return value in self.forbiddenValues

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
        if type(link) == str:
            link = link.replace("'", '"')
            link = json.loads(link)

        url = f'https://businesssearchapi.ohiosos.gov/VD_{link["charter_num"]}'
        headers = {
            "authority": "businesssearchapi.ohiosos.gov",
            "accept": "application/json, text/javascript, */*; q=0.01",
            "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
            "origin": "https://businesssearch.ohiosos.gov",
            "referer": "https://businesssearch.ohiosos.gov/",
            "sec-ch-ua": '"Google Chrome";v="105", "Not)A;Brand";v="8", "Chromium";v="105"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36",
        }
        requestOptions = {"url": url, "headers": headers, "returnType": "api"}

        time.sleep(2)
        companyInformation = self.getDataFromPage(requestOptions)

        result = []
        docs = companyInformation["data"][2]["listing"]
        for doc in docs:
            result.append(
                {
                    "description": doc["tran_code_desc"],
                    "date": doc["effect_date"],
                    "url": f'https://bizimage.ohiosos.gov/api/image/pdf/{doc["din"]}',
                }
            )
        return result
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
