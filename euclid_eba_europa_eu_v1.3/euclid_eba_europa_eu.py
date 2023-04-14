import datetime
import hashlib
import json
import re
import math
import urllib
from unidecode import unidecode

import pycountry
import requests
from geopy import Nominatim
from lxml import etree
import time

from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages
from lxml import html


class Handler(Extract, GetPages):
    base_url = "https://euclid.eba.europa.eu/"

    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive",
        "Content-Type": "application/json",
        "Host": "euclid.eba.europa.eu",
        "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="101", "Google Chrome";v="101"',
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Origin": "https://euclid.eba.europa.eu",
        "Referer": "https://euclid.eba.europa.eu/register/cir/search",
        "Cookie": "cookieLawSeen=true",
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
        "branches",
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

    badSymbols = [
        "\\u00",
        "\\u00e9",
        "\\u00e0",
        "\\u00e8",
        "\\u00",
        "\\u00e1",
        "\\u010",
    ]

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

        companies = [i.get("_payload") for i in self.extractedData]

        companies = [
            f'https://euclid.eba.europa.eu/register/api/entity/read/CRD_CRE_INS.{i.get("EntityCode")}'
            if i.get("EntityCode") is not None and i["EntityType"] == "CRD_CRE_INS"
            else f'https://euclid.eba.europa.eu/register/api/entity/read/CRD_EEA_BRA.{i.get("EntityCode")}'
            for i in companies
        ]

        return companies

    def get_initial_page(self, searchquery, add=None):
        currentTime = str(time.time())[:-4].replace(".", "")

        currentTime = str(time.time())[:-4].replace(".", "")
        link = (
            f"https://euclid.eba.europa.eu/register/api/search/entities?t={currentTime}"
        )

        data = {
            "$and": [
                {"_messagetype": "EUCLIDMD"},
                {
                    "_searchkeys": {
                        "$elemMatch": {
                            "T": "P",
                            "K": {"$in": ["ENT_NAM", "ENT_NAM_NON_LAT"]},
                            "V": {"$regex": f"{searchquery.lower()}"},
                        }
                    }
                },
            ]
        }
        requestOptions = {
            "url": link,
            "method": "POST",
            "data": json.dumps(data),
            "returnType": "api",
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
        def handleDomicled(address):
            try:
                c = self.get_country_from_address(address)
                return self.get_iso_by_country(c)
            except Exception as e:
                print(e, "handleDomicled")
                pass

        def handleFounded(date):
            if date:
                dt = re.findall("in \d\d\d\d", date)
                if dt:
                    return dt[0][3:]
            return None

        def handleZip(zip):
            if zip:
                zip = re.findall("\d\d\d\d+", zip)
                if zip:
                    return zip[0]
            return None

        res = {}
        requestOptions = {"url": link, "returnType": "api"}
        self.getDataFromPage(requestOptions)

        try:
            d = self.extractedData[0]["_payload"]

            res["vcard:organization-name"] = [
                i["ENT_NAM"] for i in d["Properties"] if list(i.keys())[0] == "ENT_NAM"
            ][0]
        except:
            return {}

        requestOptions = {
            "url": "https://euclid.eba.europa.eu/register/cir-api/metadata",
            "method": "GET",
            "returnType": "api",
        }

        metadata = self.getDataFromPage(requestOptions)[0]
        rel = metadata["Relationships"][0]["ParentEntities"][0]

        try:
            res["isDomiciledIn"] = d["CA_OwnerID"][:2]
        except:
            pass

        try:
            res["localName"] = unidecode(
                [
                    i["ENT_NAM_NON_LAT"]
                    for i in d["Properties"]
                    if list(i.keys())[0] == "ENT_NAM_NON_LAT"
                ][0]
            )
        except:
            pass

        try:
            if d["EntityType"] == "CRD_CRE_INS":
                res["lei:legalForm"] = {"code": "", "label": "CRD Credit Institution"}
            else:
                raise Exception()

        except:
            pass

        try:
            res["mdaas:OperationalAddress"] = {
                "country": pycountry.countries.get(
                    alpha_2=[
                        i["ENT_COU_RES"]
                        for i in d["Properties"]
                        if i.get("ENT_COU_RES")
                    ][0]
                ).official_name,
                "city": [
                    i["ENT_TOW_CIT_RES"]
                    for i in d["Properties"]
                    if i.get("ENT_TOW_CIT_RES")
                ][0],
            }
            res["mdaas:OperationalAddress"]["fullAddress"] = (
                res["mdaas:OperationalAddress"]["city"]
                + ", "
                + res["mdaas:OperationalAddress"]["country"]
            )
        except:
            pass

        try:
            res["identifiers"] = {
                "legal_entity_identifier": [
                    i["ENT_COD"] for i in d["Properties"] if i.get("ENT_COD")
                ][0],
                "other_company_id_number": [
                    i["ENT_NAT_REF_COD"]
                    for i in d["Properties"]
                    if i.get("ENT_NAT_REF_COD")
                ][0],
            }

        except:
            pass

        res["@sourcce-id"] = "eba.europa.eu"
        try:
            res["sourceDate"] = (
                d["__EBA_EntityVersion"][:4]
                + "-"
                + d["__EBA_EntityVersion"][4:6]
                + "-"
                + d["__EBA_EntityVersion"][6:8]
            )
        except:
            pass

        return res

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

    def get_country_from_address(self, address):
        geolocator = Nominatim(user_agent="asdasfsdfewfwefwefwesdfdasd")
        geoloc = str(geolocator.geocode(address))
        if geoloc:
            return geoloc.split(", ")[-1]
        return None

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
            address.get("streetAddress") if address.get("streetAddress") else None
        )
        totalAddress.append(address.get("zip") if address.get("zip") else None)
        totalAddress.append(address.get("city") if address.get("city") else None)
        totalAddress.append(address.get("country") if address.get("country") else None)
        totalAddress = [i for i in totalAddress if i is not None]
        if totalAddress:
            if len(totalAddress) == 1:
                extractedResult["mdaas:RegisteredAddress"][
                    "fullAddress"
                ] = totalAddress[0]
            else:
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
        self.getDataFromPage(
            {"url": link.replace("quote.html", "profile/profile.html")}
        )

        officersElements = self.get_elements_list_by_path(
            '//h3/text()[contains(., "Top Executives")]/../following-sibling::table//tr'
        )
        if not officersElements:
            return []

        fetchedFields = {
            "name": ["./td[1]/text()"],
            "occupation": ["./td[2]/text()"],
            "officer_role": ["./td[2]/text()"],
        }

        hardcodedFields = {
            "type": "Individual",
            "status": "Active",
            "information_source": self.base_url,
            "information_provider": "Cnn Finance",
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

    def get_shareholders(self, link):
        self.getDataFromPage(
            {"url": link.replace("quote.html", "shareholders/shareholders.html")}
        )
        print(
            self.extractedData.xpath(
                '//script/text()[contains(., "wsod_insiderTrading")]'
            )
        )
        print(
            self.extractedData.xpath(
                '//script/text()[contains(., "wsod_insiderTrading")]'
            )[0]
            .replace("=", ":")
            .split(";wsod_insiderTrading")[1:]
        )
        holdersRows = (
            self.extractedData.xpath(
                '//script/text()[contains(., "wsod_insiderTrading")]'
            )[0]
            .replace("=", ":")
            .split(";wsod_insiderTrading")[1:]
        )
        edd = {}
        shareholders = {}
        sholdersl1 = {}

        company = self.get_overview(link)
        print(company)
        company_name_hash = hashlib.md5(
            company["vcard:organization-name"].encode("utf-8")
        ).hexdigest()

        print(holdersRows)
        if not holdersRows:
            return edd, sholdersl1

        holderNames = []
        for sh in holdersRows:
            n = re.findall(',n:".+",ti', sh)[0].split('"')[1]
            if n in holderNames:
                continue
            holderNames.append(n)
            print(sh[4:])

            holder_name_hash = hashlib.md5(n.encode("utf-8")).hexdigest()
            holderInfo = {
                "vcard:organization-name": n,
                "hasURL": self.base_url,
                "mdaas:RegisteredAddress": company["mdaas:RegisteredAddress"],
                "relation": {
                    "natureOfControl": "SSH",
                    "source": self.NICK_NAME,
                    "date": datetime.datetime.today().strftime("%Y-%m-%d"),
                },
            }
            shareholders[holder_name_hash] = holderInfo
            basic_in = {
                "vcard:organization-name": n,
                "isDomiciledIn": company["isDomiciledIn"],
            }
            sholdersl1[holder_name_hash] = {"basic": basic_in, "shareholders": {}}
            edd[company_name_hash] = {"basic": company, "shareholders": shareholders}

        return edd, sholdersl1

    def get_financial_information(self, link):
        self.getDataFromPage({"url": link})

        def handleDate(date):
            if date:
                date = date.split("As of ")[-1]
                curY = datetime.datetime.today().strftime("%Y")
                date = self.reformat_date(date + " " + curY, "%b %d %Y")
                return date
            return None

        temp = {}
        sumFin = {}
        sumFin["source"] = "Cnn Finance"

        cur = "USD"
        summary = {}
        coded = {}
        fetched = {
            "date": ['//div[@class="wsod_quoteLabelAsOf"]/text()', handleDate],
            "market_capitalization": [
                '//td/text()[contains(., "Market cap")]/../following-sibling::td[1]/text()'
            ],
        }
        balance_sheet = self.extract_data(fetched, coded, self.extractedData)

        fetched = {
            "total_assets": [
                '//tr[@class="totalRow"]/td/text()[contains(., "Total Assets")]/../following-sibling::td[4]/text()'
            ],
            "current_assets": [
                '//tr[@class="totalRow"]/td/text()[contains(., "Current Assets")]/../following-sibling::td[4]/text()'
            ],
            "total_liabilities": [
                '//tr[@class="totalRow"]/td/text()[contains(., "Total Liabilities")]/../following-sibling::td[4]/text()'
            ],
            "current_liabilities": [
                '//tr[@class="totalRow"]/td/text()[contains(., "Other Liabilities")]/../following-sibling::td[4]/text()'
            ],
            "authorized_share_capital": [
                '//td/text()[contains(., "Common Shares Outstanding")]/../following-sibling::td[4]/text()'
            ],
        }

        finPage = self.getDataFromPage(
            {
                "url": link.replace("quote.html", "financials/financials.html")
                + "&dataSet=BS"
            }
        )
        balance_sheetFin = self.extract_data(fetched, coded, finPage)

        balance_sheet.update(balance_sheetFin)

        try:
            balance_sheet["non_current_liabilities"] = (
                str(
                    float(balance_sheet["total_liabilities"][:-1])
                    - float(balance_sheet["current_liabilities"][:-1])
                )
                + balance_sheet["total_liabilities"][-1]
            )
        except:
            pass

        fetched = {
            "period": [
                '//tr[@id="periodHeaders"]/th[4]/text()',
                lambda x: f"{x}-01-01-{x}-12-31",
            ],
            "profit": [
                '//text()[contains(., "Résultat net (Bénéfice ou Perte)")]/../following-sibling::td[2]/text()'
            ],
        }

        incSt = self.extract_data(fetched, coded, self.extractedData)

        incPage = self.getDataFromPage(
            {
                "url": link.replace("quote.html", "financials/financials.html")
                + "&dataSet=IS"
            }
        )
        fetched = {
            "revenue": [
                '//tr[@class="totalRow"]/td/text()[contains(., "Net Revenues")]/../following-sibling::td[4]/text()'
            ],
            "profit": [
                '//tr[@class="totalRow"]/td/text()[contains(., "Net Income")]/../following-sibling::td[4]/text()'
            ],
            "cash_flow_from_operations": [
                '//tr[@class="totalRow"]/td/text()[contains(., "Total Operating Expenses")]/../following-sibling::td[4]/text()'
            ],
        }

        incInc = self.extract_data(fetched, coded, incPage)

        incSt.update(incInc)

        if incSt:
            summary["income_statement"] = incSt

        if balance_sheet:
            summary["balance_sheet"] = balance_sheet
        if summary:
            sumFin["summary"] = summary
        temp["Summary_Financial_data"] = [sumFin]

        sumFinStatements = {}

        balSheet = []
        fetched = {
            "date": [
                '//tr[@id="periodHeaders"]/th[4]/text()',
                lambda x: f"{x}-12-31" if x else None,
            ],
            "line_item_desc": [
                '//text()[contains(., "Cash & Short Term Investments")]'
            ],
            "line_item_amount": [
                '//text()[contains(., "Cash & Short Term Investments")]/../following-sibling::td[4]/text()'
            ],
        }
        coded = {
            "section": "Assets",
        }
        tBalSheet = self.extract_data(fetched, coded, finPage)
        if tBalSheet.get("line_item_desc"):
            balSheet.append(tBalSheet)

        fetched = {
            "date": [
                '//tr[@id="periodHeaders"]/th[4]/text()',
                lambda x: f"{x}-12-31" if x else None,
            ],
            "line_item_desc": [
                '//td[@class="sectionHeader"]/text()[contains(., "Assets")][1]/../following-sibling::td[1]//text()[contains(., "Cash")]'
            ],
            "line_item_amount": [
                '//td[@class="sectionHeader"]/text()[contains(., "Assets")][1]/../following-sibling::td[5]/text()',
                lambda x: x[0] if type(x) == list else None,
            ],
        }
        tBalSheet = self.extract_data(fetched, coded, finPage)
        if tBalSheet.get("line_item_desc"):
            balSheet.append(tBalSheet)

        fetched = {
            "date": [
                '//tr[@id="periodHeaders"]/th[4]/text()',
                lambda x: f"{x}-12-31" if x else None,
            ],
            "line_item_desc": [
                '//td[@class="text"]/text()[contains(., "Short Term Investment Cash")]'
            ],
            "line_item_amount": [
                '//td[@class="text"]/text()[contains(., "Short Term Investment Cash")]/../following-sibling::td[4]/text()'
            ],
        }
        tBalSheet = self.extract_data(fetched, coded, finPage)
        if tBalSheet.get("line_item_desc"):
            balSheet.append(tBalSheet)

        coded = {
            "section": "Receivables",
        }
        fetched = {
            "date": [
                '//tr[@id="periodHeaders"]/th[4]/text()',
                lambda x: f"{x}-12-31" if x else None,
            ],
            "line_item_desc": [
                '//td[@class="text"]/text()[contains(., "Receivables")]'
            ],
            "line_item_amount": [
                '//td[@class="text"]/text()[contains(., "Receivables")]/../following-sibling::td[4]/text()'
            ],
        }
        tBalSheet = self.extract_data(fetched, coded, finPage)
        if tBalSheet.get("line_item_desc"):
            balSheet.append(tBalSheet)

        coded = {
            "section": "Inventories",
        }
        fetched = {
            "date": [
                '//tr[@id="periodHeaders"]/th[4]/text()',
                lambda x: f"{x}-12-31" if x else None,
            ],
            "line_item_desc": [
                '//td[@class="text"]/text()[contains(., "Inventories")]'
            ],
            "line_item_amount": [
                '//td[@class="text"]/text()[contains(., "Inventories")]/../following-sibling::td[4]/text()'
            ],
        }
        tBalSheet = self.extract_data(fetched, coded, finPage)
        if tBalSheet.get("line_item_desc"):
            balSheet.append(tBalSheet)

        coded = {
            "section": "Current Assets",
        }
        fetched = {
            "date": [
                '//tr[@id="periodHeaders"]/th[4]/text()',
                lambda x: f"{x}-12-31" if x else None,
            ],
            "line_item_desc": [
                '//td[@class="text"]/text()[contains(., "Other Current Assets")]'
            ],
            "line_item_amount": [
                '//td[@class="text"]/text()[contains(., "Other Current Assets")]/../following-sibling::td[4]/text()'
            ],
        }
        tBalSheet = self.extract_data(fetched, coded, finPage)
        if tBalSheet.get("line_item_desc"):
            balSheet.append(tBalSheet)

        fetched = {
            "date": [
                '//tr[@id="periodHeaders"]/th[4]/text()',
                lambda x: f"{x}-12-31" if x else None,
            ],
            "line_item_desc": [
                '//td[@class="text"]/text()[contains(., "Current Assets")]',
                lambda x: x[1] if type(x) == list else None,
            ],
            "line_item_amount": [
                '//td[@class="text"]/text()[contains(., "Current Assets")]/../following-sibling::td[4]/text()',
                lambda x: x[1] if type(x) == list else None,
            ],
        }
        tBalSheet = self.extract_data(fetched, coded, finPage)
        if tBalSheet.get("line_item_desc"):
            balSheet.append(tBalSheet)

        coded = {
            "section": "Total Assets",
        }
        fetched = {
            "date": [
                '//tr[@id="periodHeaders"]/th[4]/text()',
                lambda x: f"{x}-12-31" if x else None,
            ],
            "line_item_desc": [
                '//td[@class="text"]/text()[contains(., "Property, Plant and Equipment - Gross")]'
            ],
            "line_item_amount": [
                '//td[@class="text"]/text()[contains(., "Property, Plant and Equipment - Gross")]/../following-sibling::td[4]/text()'
            ],
        }
        tBalSheet = self.extract_data(fetched, coded, finPage)
        if tBalSheet.get("line_item_desc"):
            balSheet.append(tBalSheet)

        fetched = {
            "date": [
                '//tr[@id="periodHeaders"]/th[4]/text()',
                lambda x: f"{x}-12-31" if x else None,
            ],
            "line_item_desc": [
                '//td[@class="text"]/text()[contains(., "Depreciation")]'
            ],
            "line_item_amount": [
                '//td[@class="text"]/text()[contains(., "Depreciation")]/../following-sibling::td[4]/text()'
            ],
        }
        tBalSheet = self.extract_data(fetched, coded, finPage)
        if tBalSheet.get("line_item_desc"):
            balSheet.append(tBalSheet)

        fetched = {
            "date": [
                '//tr[@id="periodHeaders"]/th[4]/text()',
                lambda x: f"{x}-12-31" if x else None,
            ],
            "line_item_desc": [
                '//td[@class="text"]/text()[contains(., "Intangible Assets")]'
            ],
            "line_item_amount": [
                '//td[@class="text"]/text()[contains(., "Intangible Assets")]/../following-sibling::td[4]/text()'
            ],
        }
        tBalSheet = self.extract_data(fetched, coded, finPage)
        if tBalSheet.get("line_item_desc"):
            balSheet.append(tBalSheet)

        fetched = {
            "date": [
                '//tr[@id="periodHeaders"]/th[4]/text()',
                lambda x: f"{x}-12-31" if x else None,
            ],
            "line_item_desc": [
                '//td[@class="text"]/text()[contains(., "Other Assets")]'
            ],
            "line_item_amount": [
                '//td[@class="text"]/text()[contains(., "Other Assets")]/../following-sibling::td[4]/text()'
            ],
        }
        tBalSheet = self.extract_data(fetched, coded, finPage)
        if tBalSheet.get("line_item_desc"):
            balSheet.append(tBalSheet)

        fetched = {
            "date": [
                '//tr[@id="periodHeaders"]/th[4]/text()',
                lambda x: f"{x}-12-31" if x else None,
            ],
            "line_item_desc": [
                '//td[@class="text"]/text()[contains(., "Total Assets")]'
            ],
            "line_item_amount": [
                '//td[@class="text"]/text()[contains(., "Total Assets")]/../following-sibling::td[4]/text()'
            ],
        }
        tBalSheet = self.extract_data(fetched, coded, finPage)
        if tBalSheet.get("line_item_desc"):
            balSheet.append(tBalSheet)

        self.get_financial_statement(
            finPage,
            section="Liabilities",
            substate="Accounts Payable",
            resultArray=balSheet,
        )
        self.get_financial_statement(
            finPage,
            section="Liabilities",
            substate="Short Term Debt",
            resultArray=balSheet,
        )
        self.get_financial_statement(
            finPage,
            section="Liabilities",
            substate="Other Current Liabilities",
            resultArray=balSheet,
        )
        self.get_financial_statement(
            finPage,
            section="Liabilities",
            substate="Other Liabilities",
            resultArray=balSheet,
            uniqNumber=1,
        )

        self.get_financial_statement(
            finPage,
            section="Total Liabilities",
            substate="Long Term Debt",
            resultArray=balSheet,
        )
        self.get_financial_statement(
            finPage,
            section="Total Liabilities",
            substate="Deferred Taxes",
            resultArray=balSheet,
        )
        self.get_financial_statement(
            finPage,
            section="Total Liabilities",
            substate="Other Liabilities",
            resultArray=balSheet,
            uniqNumber=1,
        )
        self.get_financial_statement(
            finPage,
            section="Total Liabilities",
            substate="Total Liabilities",
            resultArray=balSheet,
        )

        incSheet = []

        self.get_financial_statement_inc(
            incPage, substate="Net Revenues", resultArray=incSheet
        )
        self.get_financial_statement_inc(
            incPage, substate="Cost of Goods Sold", resultArray=incSheet
        )
        self.get_financial_statement_inc(
            incPage, substate="Depreciation And Amortization", resultArray=incSheet
        )
        self.get_financial_statement_inc(
            incPage, substate="Gross Income", resultArray=incSheet
        )
        self.get_financial_statement_inc(
            incPage, substate="General Expenses", resultArray=incSheet
        )
        self.get_financial_statement_inc(
            incPage, substate="Research And Development", resultArray=incSheet
        )
        self.get_financial_statement_inc(
            incPage, substate="Research And Development", resultArray=incSheet
        )
        self.get_financial_statement_inc(
            incPage, substate="Total Operating Expenses", resultArray=incSheet
        )
        self.get_financial_statement_inc(
            incPage, substate="Operating Income", resultArray=incSheet
        )
        self.get_financial_statement_inc(
            incPage, substate="Extraordinary Credit", resultArray=incSheet
        )
        self.get_financial_statement_inc(
            incPage, substate="Extraordinary Charge", resultArray=incSheet
        )
        self.get_financial_statement_inc(
            incPage, substate="Other Expenses", resultArray=incSheet
        )
        self.get_financial_statement_inc(
            incPage, substate="Pre-Tax Equity Earnings", resultArray=incSheet
        )
        self.get_financial_statement_inc(
            incPage, substate="Interest Expense On Debt", resultArray=incSheet
        )
        self.get_financial_statement_inc(
            incPage, substate="Pre-Tax Income", resultArray=incSheet
        )
        self.get_financial_statement_inc(
            incPage, substate="Income Taxes", resultArray=incSheet
        )
        self.get_financial_statement_inc(
            incPage, substate="Minority Interest", resultArray=incSheet
        )
        self.get_financial_statement_inc(
            incPage, substate="Net Income", resultArray=incSheet
        )
        self.get_financial_statement_inc(
            incPage,
            substate="Shares To Calculate EPS",
            resultArray=incSheet,
            uniqNumber=1,
        )
        self.get_financial_statement_inc(
            incPage, substate="Shares To Calculate EPS Diluted", resultArray=incSheet
        )
        self.get_financial_statement_inc(
            incPage, substate="EPS", resultArray=incSheet, uniqNumber=1
        )
        self.get_financial_statement_inc(
            incPage, substate="EPS Diluted", resultArray=incSheet, uniqNumber=1
        )

        cfPage = self.getDataFromPage(
            {
                "url": link.replace("quote.html", "financials/financials.html")
                + "&dataSet=CFS"
            }
        )
        cfArray = []
        self.get_financial_statement_inc(
            cfPage, substate="Net Income / Starting Line", resultArray=cfArray
        )
        self.get_financial_statement_inc(
            cfPage, substate="Depreciation", resultArray=cfArray
        )
        self.get_financial_statement_inc(
            cfPage, substate="Total Other Cash Flow", resultArray=cfArray
        )
        self.get_financial_statement_inc(
            cfPage, substate="Funds From Operations", resultArray=cfArray
        )
        self.get_financial_statement_inc(
            cfPage,
            substate="Funds From/For Other Operating Expenses",
            resultArray=cfArray,
        )
        self.get_financial_statement_inc(
            cfPage, substate="Net Cash Flow - Operating Activities", resultArray=cfArray
        )
        self.get_financial_statement_inc(
            cfPage, substate="Increase In Investments", resultArray=cfArray
        )
        self.get_financial_statement_inc(
            cfPage, substate="Decrease In Investments", resultArray=cfArray
        )
        self.get_financial_statement_inc(
            cfPage, substate="Capital Expenditures", resultArray=cfArray
        )
        self.get_financial_statement_inc(
            cfPage, substate="Fixed Asset Disposal", resultArray=cfArray
        )
        self.get_financial_statement_inc(
            cfPage, substate="Net Cash Flow Investing", resultArray=cfArray
        )

        sumFinStatements["balance_sheet"] = balSheet
        sumFinStatements["income_statement"] = incSheet
        sumFinStatements["cash_flow_statement"] = cfArray

        if sumFinStatements:
            temp["financial_statements"] = sumFinStatements

        stockInfo = {}

        quotePgae = self.getDataFromPage({"url": link})

        fetch = {
            "open_price": [
                '//td/text()[contains(., "Today’s open")]/../following-sibling::td[1]/text()'
            ],
            "volume": [
                '//td/text()[contains(., "Volume")]/../following-sibling::td[1]/text()'
            ],
            "day_range": [
                '//td/text()[contains(., "Day’s range")]/../following-sibling::td[1]/text()'
            ],
            "market_capitalization": [
                '//td/text()[contains(., "Market cap")]/../following-sibling::td[1]/text()'
            ],
            "pe_ratio": [
                '//td/text()[contains(., "P/E ratio")]/../following-sibling::td[1]/text()'
            ],
        }
        coded = {
            "data_date": datetime.datetime.today().strftime("%y-%m-%d"),
            "exchange_currency": "usd",
        }

        stockInfoCurr = self.extract_data(fetch, coded, quotePgae)

        if stockInfoCurr:
            try:
                stockInfoCurr["52_week_range"] = (
                    quotePgae.xpath('//div[@class="val lo"]/text()')[0]
                    + " - "
                    + quotePgae.xpath('//div[@class="val hi"]/text()')[0]
                )
            except:
                pass

            temp["stocks_information"] = [
                {"stock_id": "Cnn Finance", "current": stockInfoCurr}
            ]

        return temp

    def get_financial_statement(
        self, page, section, substate, resultArray, uniqNumber=""
    ):
        coded = {
            "section": section,
        }

        fetched = {
            "date": [
                '//tr[@id="periodHeaders"]//th[4]/text()',
                lambda x: f"{x}-12-31" if x else None,
            ],
            "line_item_desc": [
                f'//td[@class="text"]/text()[contains(., "{substate}")]',
                lambda x: x[uniqNumber] if uniqNumber and type(x) == list else x,
            ],
            "line_item_amount": [
                f'//td[@class="text"]/text()[contains(., "{substate}")]/../following-sibling::td[4]/text()',
                lambda x: x[uniqNumber] if uniqNumber and type(x) == list else x,
            ],
        }
        tBalSheet = self.extract_data(fetched, coded, page)
        if tBalSheet.get("line_item_desc"):
            resultArray.append(tBalSheet)
        return resultArray

    def get_financial_statement_inc(self, page, substate, resultArray, uniqNumber=""):
        coded = {}
        fetched = {
            "period": [
                '//tr[@id="periodHeaders"]//th[4]//text()',
                lambda x: f"{x}-01-01-{x}-12-31" if x else None,
            ],
            "line_item_desc": [
                f'//td[@class="text"]/text()[contains(., "{substate}")]',
                lambda x: x[uniqNumber] if uniqNumber and type(x) == list else x,
            ],
            "line_item_amount": [
                f'//td[@class="text"]/text()[contains(., "{substate}")]/../following-sibling::td[4]/text()',
                lambda x: x[uniqNumber] if uniqNumber and type(x) == list else x,
            ],
        }
        tBalSheet = self.extract_data(fetched, coded, page)
        if tBalSheet.get("line_item_desc"):
            resultArray.append(tBalSheet)
        return resultArray

    def get_branches(self, link):
        link = f'https://euclid.eba.europa.eu/register/cir-api/relatedEntities/{link.split("/")[-1]}'
        requestOptions = {"url": link, "returnType": "api"}
        self.getDataFromPage(requestOptions)

        try:
            chi = self.extractedData["children"]

            r = []
            for c in chi:
                temp = {}
                temp["@sourceReferenceID"] = [
                    i["ENT_NAT_REF_COD"]
                    for i in c["Properties"]
                    if i.get("ENT_NAT_REF_COD")
                ][0]
                temp["entity_type"] = "Q"
                temp["vcard:organization-name"] = [
                    i["ENT_NAM"] for i in c["Properties"] if i.get("ENT_NAM")
                ][0]
                temp["isDomiciledIn"] = [
                    i["ENT_COU_RES"] for i in c["Properties"] if i.get("ENT_COU_RES")
                ][0]

                temp["mdaas:RegisteredAddress"] = {
                    "country": pycountry.countries.get(
                        alpha_2=[
                            i["ENT_COU_RES"]
                            for i in c["Properties"]
                            if i.get("ENT_COU_RES")
                        ][0]
                    ).name,
                    "city": [
                        i["ENT_TOW_CIT_RES"]
                        for i in c["Properties"]
                        if i.get("ENT_TOW_CIT_RES")
                    ][0],
                }
                temp["mdaas:RegisteredAddress"]["fullAddress"] = (
                    temp["mdaas:RegisteredAddress"]["city"]
                    + ", "
                    + temp["mdaas:RegisteredAddress"]["country"]
                )

                r.append(temp)
            return r
        except:
            return []

        print(self.extractedData)
        exit()
