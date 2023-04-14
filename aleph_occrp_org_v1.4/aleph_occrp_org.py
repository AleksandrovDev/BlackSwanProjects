import datetime
import json
import re
import math

import pycountry
from lxml import etree

from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://aleph.occrp.org"

    fields = ["overview", "officership", "documents"]

    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;"
        "q=0.8,application/signed-exchange;v=b3;q=0.9;application/json;application/json;odata=verbose",
        "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }

    NICK_NAME = base_url.split("//")[-1]
    method = "GET"
    data = None
    returnType = "api"

    overview = {}

    extractedData = None

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

    forbiddenValues = ["NULL", "None Supplied"]

    badSymbols = ["\\u00"]

    def getpages(self, searchquery):
        link = (
            "https://aleph.occrp.org/api/2/entities?facet=schema&facet_size%3Aschema=1000&facet_total%3Aschema=true"
            f"&filter%3Aschema=Company&filter%3Aschemata=Thing&highlight=true&limit=30&q={searchquery}"
        )

        requestOptions = {
            "url": link,
            "method": "",
            "headers": "",
            "data": "",
        }

        extractedData = self.getDataFromPage(requestOptions)
        companies = self.get_result_list_by_path("results", extractedData)
        ids = self.get_companies_value("id", companies)

        return ids

    def getDataFromPage(self, requestOptions):
        def getUrl(self, requestOptions):
            url = requestOptions.get("url")
            if not url:
                url = self.base_url
            return url

        def getMethod(self, requestOptions):
            method = requestOptions.get("method")
            if not method:
                method = self.method
            return method

        def getHeaders(self, requestOptions):
            headers = requestOptions.get("headers")
            if not headers:
                headers = self.header
            return headers

        def getReturnType(self, requestOptions):
            returnType = requestOptions.get("returnType")
            if not returnType:
                returnType = self.returnType
            return returnType

        def getData(self, requestOptions):
            data = requestOptions.get("data")
            if not data:
                data = self.data
            return data

        url = getUrl(self, requestOptions)
        method = getMethod(self, requestOptions)
        headers = getHeaders(self, requestOptions)
        returnType = getReturnType(self, requestOptions)
        data = getData(self, requestOptions)

        content = self.get_content(url, headers, data, method).content

        if returnType == "tree":
            return etree.HTML(content)

        return json.loads(content)

    def get_result_list_by_path(self, pathToResultList, dictionaryData):
        return self.get_dict_value_by_path(pathToResultList, dictionaryData)

    def get_dict_value_by_path(self, path, dictData):
        resultValue = dict(dictData)
        path = path.split("/")

        if path == [""]:
            return [self.extractedRawDict]
        for i in path:
            if type(resultValue) == list:
                resultValue = resultValue[0]
            else:
                resultValue = resultValue.get(i)
                if not resultValue:
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
        linkExtract = "https://aleph.occrp.org/api/2/entities/" + link

        def extraHandlingCode(codeOrigin):
            code = codeOrigin.split(" - ")[0]
            code = re.findall("\d{3,} ", code)
            if code:
                return code
            return ""

        def extraHandlingDescription(description):
            return description.split(" - ")[-1]

        def extraHandlingLabel(description):
            return description

        fetchedFields = {
            "vcard:organization-name": "properties/name",
            "isDomiciledIn": "properties/jurisdiction",
            "hasActivityStatus": "properties/status",
            "previous_names": [
                {
                    "name": "properties/previousName",
                },
                [None],
                "list",
                "notShowEmpty",
            ],
            "hasURL": "properties/website",
            "bst:businessClassifier": [
                {
                    "code": "properties/classification",
                    "description": "properties/classification",
                    "label": "",
                },
                [extraHandlingCode, extraHandlingDescription, extraHandlingLabel],
                "list",
                "showEmpty",
            ],
            "mdaas:RegisteredAddress": [
                {
                    "country": "properties/country",
                    "customAddress": "properties/address",
                    "entityAddress": "properties/addressEntity/properties",
                },
                [None, None, None],
                "",
                "notShowEmpty",
            ],
            "mdaas:RegisteredAddressCountry": "properties/country",
            "mdaas:RegisteredAddressAddress": "properties/address",
            "mdaas:RegisteredAddressAddressEntity": "properties/addressEntity/properties",
            "identifiers": [
                {
                    "swift_code": "properties/swiftBic",
                    "other_company_id_number": "properties/registrationNumber",
                },
                [None, None],
                "",
                "notShowEmpy",
            ],
            "isIncorporatedIn": "properties/incorporationDate",
            "lei:legalForm": [
                {
                    "code": "",
                    "label": "properties/legalForm",
                },
                [None, None],
                "",
                "showEmpty",
            ],
            "bst:registrationId": "properties/registrationNumber",
            "sourceDate": "properties/modifiedAt",
        }
        hardcodedFields = {
            "@source-id": self.base_url,
            "bst:registryURI": f"{self.base_url}/entities/{link}",
            "bst:sourceLinks": [f"{self.base_url}/entities/{link}"],
        }

        requestOptions = {
            "url": linkExtract,
        }
        self.extract_data(fetchedFields, hardcodedFields, requestOptions)

        return self.overview

    def extract_data(self, fetchedFields, hardCodedFields, requestOptions):
        self.extractedData = self.getDataFromPage(requestOptions)

        for k, v in fetchedFields.items():
            self.fill_field(k, v)

        for k, v in hardCodedFields.items():
            self.overview[k] = v

    def fill_field(self, fieldName, dataPath=None, reformatDate=None, el=None):
        dataType = self.get_path_type(dataPath)

        if fieldName == "bst:businessClassifier":
            self.fill_dictionary_field(
                dataPath[0], dataPath[1], fieldName, dataPath[2], dataPath[3], dataType
            )
        elif fieldName == "lei:legalForm":
            self.fill_dictionary_field(
                dataPath[0], dataPath[1], fieldName, dataPath[2], dataPath[3], dataType
            )
        elif fieldName == "identifiers":
            self.fill_dictionary_field(
                dataPath[0], dataPath[1], fieldName, dataPath[2], dataPath[3], dataType
            )
        elif fieldName == "previous_names":
            self.fill_dictionary_field(
                dataPath[0], dataPath[1], fieldName, dataPath[2], dataPath[3], dataType
            )
        elif fieldName == "mdaas:RegisteredAddress":
            addr = self.get_formatted_address(
                address=self.get_dict_value_by_path(
                    dataPath[0]["customAddress"], self.extractedData
                ),
                country=self.get_dict_value_by_path(
                    dataPath[0]["country"], self.extractedData
                ),
                addrEntity=self.get_dict_value_by_path(
                    dataPath[0]["entityAddress"], self.extractedData
                ),
            )
            if addr:
                self.overview[fieldName] = addr

        elif dataType == "xpath":
            el = self.get_by_xpath(dataPath)
        elif dataType == "key":
            el = self.get_dict_value_by_path(dataPath, self.extractedData)
        else:
            el = dataPath

        if el:
            if len(el) == 1 and type(el) == list:
                el = el[0]
            el = self.reformat_date(el, reformatDate) if reformatDate else el
            el = self.getCleanValues(el)
            if fieldName == "isDomiciledIn":
                country = pycountry.countries.search_fuzzy(el)

                if country:
                    self.overview[fieldName] = country[0].alpha_2
                else:
                    self.overview[fieldName] = el

            elif fieldName == "Service":
                if type(el) == list:
                    el = ", ".join(el)
                self.overview[fieldName] = {"serviceType": el}

            elif fieldName == "vcard:organization-tradename":
                self.overview[fieldName] = el.split("\n")[0].strip()

            elif fieldName == "bst:aka":
                names = el.split(" D/B/A ")
                if len(names) > 1:
                    names = [i.strip() for i in names]
                    self.overview[fieldName] = names
                else:
                    self.overview[fieldName] = names

            elif fieldName == "lei:legalForm":
                self.overview[fieldName] = {"code": "", "label": el}

            elif fieldName == "map":
                self.overview[fieldName] = el[0] if type(el) == list else el

            elif fieldName == "previous_names":
                self.overview[fieldName] = self.get_formatted_previous_names(el)

            elif fieldName == "bst:description":
                if type(el) == list:
                    el = ", ".join(el)
                self.overview[fieldName] = el

            elif fieldName == "hasURL" and el != "http://":
                if "www" in el:
                    el = el.split(", ")[-1]
                if "http:" not in el:
                    el = "http://" + el.strip()
                if "www" in el:
                    self.overview[fieldName] = el

            elif fieldName == "tr-org:hasRegisteredPhoneNumber":
                if type(el) == list and len(el) > 1:
                    el = el[0]
                self.overview[fieldName] = el

            elif fieldName == "bst:stock_info":
                if type(el) == list:
                    el = el[0]
                self.overview[fieldName] = {"main_exchange": el}
            elif fieldName == "agent":
                self.overview[fieldName] = {
                    "name": el.split("\n")[0],
                    "mdaas:RegisteredAddress": self.get_address(
                        returnAddress=True,
                        addr=" ".join(el.split("\n")[1:]),
                        zipPattern="[A-Z]\d[A-Z]\s\d[A-Z]\d",
                    ),
                }

            elif fieldName == "logo":
                self.overview["logo"] = self.sourceConfig.base_url + el

            elif fieldName == "hasRegisteredFaxNumber":
                if type(el) == list and len(el) > 1:
                    el = el[0]
                self.overview[fieldName] = el

            elif fieldName == "bst:sourceLinks":
                self.overview[fieldName] = [el]

            elif fieldName == "bst:businessClassifier":
                self.overview[fieldName] = [el]

            elif fieldName == "vcard:organization-name":
                if type(el) == list:
                    el = el[0]
                self.overview[fieldName] = el

            else:
                self.overview[fieldName] = el

    def formatFields(self, fieldsData):
        cleanFormattedResult = {}
        for field, fieldValue in fieldsData.items():
            if self.config[field] == str and type(fieldValue) == list:
                cleanFormattedResult[field] = fieldValue[0]
            elif self.config[field] == list and type(fieldValue) == str:
                cleanFormattedResult[field] = [fieldValue]
            else:
                cleanFormattedResult[field] = fieldValue

            if field == "previous_names":
                cleanFormattedResult[field] = self.get_formatted_previous_names(
                    fieldValue
                )
            if field == "lei:legalForm":
                cleanFormattedResult[field] = self.get_formatted_lei(
                    cleanFormattedResult[field]
                )
            if field == "bst:businessClassifier":
                cleanFormattedResult[field] = self.get_formatted_busClassifier(
                    cleanFormattedResult[field]
                )
            if field == "mdaas:RegisteredAddressCountry":
                cleanFormattedResult[field] = cleanFormattedResult[field].upper()

            if field == "mdaas:RegisteredAddressAddress":
                cleanFormattedResult[
                    "mdaas:RegisteredAddress"
                ] = self.get_formatted_address(
                    cleanFormattedResult[field],
                    cleanFormattedResult["mdaas:RegisteredAddressCountry"],
                )

            if field == "mdaas:RegisteredAddressAddressEntity":
                cleanFormattedResult[
                    "mdaas:RegisteredAddress"
                ] = self.get_address_from_entity(cleanFormattedResult[field])

            if field == "identifiersBic":
                try:
                    cleanFormattedResult[
                        "identifiers"
                    ] = self.get_formatted_identifiers(
                        cleanFormattedResult[field],
                        cleanFormattedResult["bst:registrationId"],
                    )
                except:
                    cleanFormattedResult[
                        "identifiers"
                    ] = self.get_formatted_identifiers(cleanFormattedResult[field])

        return cleanFormattedResult

    def get_formatted_address(self, address=None, country=None, addrEntity=None):
        if address:
            address = address[0]

            fullAddress = ""

            temp = {"fullAddress": self.getCleanValues(address)}

            return temp
        if addrEntity:
            return self.get_address_from_entity(addrEntity)
        return {}

    def get_address_from_entity(self, entityAddress):
        try:
            temp = {
                "city": self.getCleanValues((entityAddress["city"][0])),
                "country": self.getCleanValues(
                    self.get_country_name_by_iso_code(entityAddress["country"][0])
                ),
                "streetAddress": self.getCleanValues(entityAddress["street"][0]),
                "fullAddress": self.getCleanValues((entityAddress["full"][0])),
            }
        except:
            pass
        return temp

    def get_country_name_by_iso_code(self, isoCode):
        countryName = pycountry.countries.get(alpha_2=isoCode)
        return countryName.name

    def make_dict_from_string(self, link_dict):
        link_dict = (
            link_dict.replace("'", '"').replace("None", '"None"').replace('""', '"')
        )
        return json.loads(link_dict)

    def reformat_date(self, date, format):
        date = datetime.datetime.strptime(date.strip(), format).strftime("%Y-%m-%d")
        return date

    def get_path_type(self, dataPath):
        if type(dataPath) == dict:
            dataPath = list(dataPath.values())[0]
        if dataPath[:2] == "//":
            return "xpath"
        elif dataPath == "defaultFill":
            return "defaultFill"
        else:
            return "key"

    def get_address(
        self, xpath=None, zipPattern=None, key=None, returnAddress=False, addr=None
    ):
        if xpath:
            addr = self.get_by_xpath(xpath)
        if key:
            addr = self.get_by_api(key)
        if addr:
            if type(addr) == list:
                splittedAddr = addr
                addr = ", ".join(addr)

            addr = addr.replace("\n", " ")
            addr = addr[0] if type(addr) == list else addr
            temp = {"country": splittedAddr[-2]}
            if zipPattern:
                zip = re.findall(zipPattern, addr)
                if zip:
                    temp["zip"] = zip[0]

            try:
                temp["zip"] = splittedAddr[-1]
            except:
                pass
            try:
                temp["city"] = splittedAddr[-3]
            except:
                pass
            try:
                temp["streetAddress"] = " ".join(splittedAddr[:-3])
            except:
                pass
            try:
                temp["fullAddress"] = " ".join(splittedAddr)
            except:
                pass
            try:
                patterns = ["Suite\s\d+"]
                for pattern in patterns:
                    pat = re.findall(pattern, addr)
                    if pat:
                        first_part = addr.split(pat[0])
                        temp["streetAddress"] = first_part[0] + pat[0]
            except:
                pass

            if returnAddress:
                return temp
            self.overview["mdaas:RegisteredAddress"] = temp

    def get_operational_address(
        self, xpath=None, zipPattern=None, key=None, returnAddress=False, addr=None
    ):
        if xpath:
            addr = self.get_by_xpath(xpath)
        if key:
            addr = self.get_by_api(key)
        if addr:
            if type(addr) == list:
                splittedAddr = addr
                addr = ", ".join(addr)

            addr = addr.replace("\n", " ")
            addr = addr[0] if type(addr) == list else addr
            temp = {"country": splittedAddr[-2]}
            if zipPattern:
                zip = re.findall(zipPattern, addr)
                if zip:
                    temp["zip"] = zip[0]

            try:
                temp["zip"] = splittedAddr[-1]
            except:
                pass
            try:
                temp["city"] = splittedAddr[-3]
            except:
                pass
            try:
                temp["streetAddress"] = " ".join(splittedAddr[:-3])
            except:
                pass
            try:
                temp["fullAddress"] = " ".join(splittedAddr)
            except:
                pass
            try:
                patterns = ["Suite\s\d+"]
                for pattern in patterns:
                    pat = re.findall(pattern, addr)
                    if pat:
                        first_part = addr.split(pat[0])
                        temp["streetAddress"] = first_part[0] + pat[0]
            except:
                pass

            if returnAddress:
                return temp
            self.overview["mdaas:OperationalAddress"] = temp

    def get_post_addr(self, tree):
        addr = self.get_by_xpath(
            tree, '//span[@id="lblMailingAddress"]/..//text()', return_list=True
        )
        if addr:
            addr = [
                i
                for i in addr
                if i != ""
                and i != "Mailing Address:"
                and i != "Inactive"
                and i != "Registered Office outside NL:"
            ]
            if addr[0] == "No address on file":
                return None
            if (
                addr[0] == "Same as Registered Office"
                or addr[0] == "Same as Registered Office in NL"
            ):
                return "Same"
            fullAddr = ", ".join(addr)
            temp = {
                "fullAddress": fullAddr
                if "Canada" in fullAddr
                else (fullAddr + " Canada"),
                "country": "Canada",
            }
            replace = re.findall("[A-Z]{2},\sCanada,", temp["fullAddress"])
            if not replace:
                replace = re.findall("[A-Z]{2},\sCanada", temp["fullAddress"])
            if replace:
                torepl = replace[0].replace(",", "")
                temp["fullAddress"] = temp["fullAddress"].replace(replace[0], torepl)
            try:
                zip = re.findall("[A-Z]\d[A-Z]\s\d[A-Z]\d", fullAddr)
                if zip:
                    temp["zip"] = zip[0]
            except:
                pass

        if len(addr) == 4:
            temp["city"] = addr[-3]
            temp["streetAddress"] = addr[0]
        if len(addr) == 5:
            temp["city"] = addr[-4]
            temp["streetAddress"] = addr[0]
        if len(addr) == 6:
            temp["city"] = addr[-4]
            temp["streetAddress"] = ", ".join(addr[:2])

        return temp

    def fill_regulator_address(
        self, xpath=None, zipPattern=None, key=None, returnAddress=False, addr=None
    ):
        if xpath:
            addr = self.get_by_xpath(xpath)[1:-2]
        if key:
            addr = self.get_by_api(key)
        if addr:
            if type(addr) == list:
                addr = ", ".join(addr)
            if "\n" in addr:
                splitted_addr = addr.split("\n")
            if ", " in addr:
                splitted_addr = addr.split(", ")

            addr = addr.replace("\n", " ")
            addr = addr[0] if type(addr) == list else addr
            temp = {"fullAddress": addr, "country": "USA"}
            if zipPattern:
                zip = re.findall(zipPattern, addr)
                if zip:
                    temp["zip"] = zip[0]
            try:
                patterns = ["Suite\s\d+"]
                for pattern in patterns:
                    pat = re.findall(pattern, addr)
                    if pat:
                        first_part = addr.split(pat[0])
                        temp["streetAddress"] = first_part[0] + pat[0]
            except:
                pass
            try:
                street = addr.split("Street")
                if len(street) == 2:
                    temp["streetAddress"] = street[0] + "Street"
                temp["streetAddress"] = addr.split(",")[0]

            except:
                pass
            try:
                temp["city"] = addr.split(", ")[-2].replace(".", "")

            except:
                pass
            temp["fullAddress"] += f', {temp["country"]}'
            temp["fullAddress"] = temp["fullAddress"].replace(".,", ",")
            if returnAddress:
                return temp
            self.overview["regulatorAddress"] = temp

    def fill_overview_identifiers(
        self,
        xpathTradeRegistry=None,
        xpathOtherCompanyId=None,
        xpathInternationalSecurIdentifier=None,
        xpathLegalEntityIdentifier=None,
    ):
        try:
            temp = self.overview["identifiers"]
        except:
            temp = {}

        if xpathTradeRegistry:
            trade = self.get_by_xpath(xpathTradeRegistry)
            if trade:
                temp["trade_register_number"] = re.findall("HR.*", trade[0])[0]
        if xpathOtherCompanyId:
            other = self.get_by_xpath(xpathOtherCompanyId)
            if other:
                temp["other_company_id_number"] = other[0]
        if xpathInternationalSecurIdentifier:
            el = self.get_by_xpath(xpathInternationalSecurIdentifier)
            temp["international_securities_identifier"] = el[0]
        if xpathLegalEntityIdentifier:
            el = self.get_by_xpath(xpathLegalEntityIdentifier)
            temp["legal_entity_identifier"] = el[0]

        if temp:
            self.overview["identifiers"] = temp

    def fill_dictionary_field(
        self,
        dataPaths,
        handlingFunctions,
        fieldName,
        returnType=None,
        showEmpty=None,
        api=None,
    ):
        dictKeys = list(dataPaths.keys())
        paths = []
        for key in dictKeys:
            paths.append(dataPaths.get(key) or None)

        res = []
        length = None

        results = []
        for path in paths:
            if path:
                values = (
                    self.get_by_xpath(path)
                    if not api
                    else self.get_dict_value_by_path(path, self.extractedData)
                )

                if values:
                    values = self.getCleanValues(values)
                    results.append(values)
                    length = len(values)
                else:
                    results.append(None)
            else:
                results.append(None)

        if length:
            for i in range(length):
                temp = {}
                for subFieldIndex in range(len(dictKeys)):
                    if handlingFunctions[subFieldIndex] is not None:
                        finalRes = (
                            handlingFunctions[subFieldIndex](results[subFieldIndex][i])
                            if results[subFieldIndex]
                            else ""
                        )
                    else:
                        finalRes = (
                            results[subFieldIndex][i] if results[subFieldIndex] else ""
                        )

                    if showEmpty == "showEmpty" or finalRes:
                        temp[dictKeys[subFieldIndex]] = finalRes
                res.append(temp)
        if res:
            if returnType == "list":
                self.overview[fieldName] = res
            else:
                self.overview[fieldName] = res[0]

    def fill_leiLegalForm(self, dataPaths, api=False):
        pass

    def fill_rating_summary(self, xpathRatingGroup=None, xpathRatings=None):
        temp = {}
        if xpathRatingGroup:
            group = self.get_by_xpath(xpathRatingGroup)
            if group:
                temp["rating_group"] = group[0]
        if xpathRatings:
            rating = self.get_by_xpath(xpathRatings)
            if rating:
                temp["ratings"] = rating[0].split(" ")[0]
        if temp:
            self.overview["rating_summary"] = temp

    def fill_agregate_rating(self, xpathReview=None, xpathRatingValue=None):
        temp = {}
        if xpathReview:
            review = self.get_by_xpath(xpathReview)
            if review:
                temp["reviewCount"] = review[0].split(" ")[0]
        if xpathRatingValue:
            value = self.get_by_xpath(xpathRatingValue)
            if value:
                temp["ratingValue"] = "".join(value)

        if temp:
            temp["@type"] = "aggregateRating"
            self.overview["aggregateRating"] = temp

    def fill_reviews(
        self, xpathReviews=None, xpathRatingValue=None, xpathDate=None, xpathDesc=None
    ):
        res = []
        try:
            reviews = self.tree.xpath(xpathReviews)
            for i in range(len(reviews)):
                temp = {}
                if xpathRatingValue:
                    ratingsValues = len(
                        self.tree.xpath(
                            f"//async-list//review[{i + 1}]" + xpathRatingValue
                        )
                    )
                    if ratingsValues:
                        temp["ratingValue"] = ratingsValues
                if xpathDate:
                    date = self.tree.xpath(f"//async-list//review[{i + 1}]" + xpathDate)
                    if date:
                        temp["datePublished"] = date[0].split("T")[0]

                if xpathDesc:
                    desc = self.tree.xpath(f"//async-list//review[{i + 1}]" + xpathDesc)
                    if desc:
                        temp["description"] = desc[0]
                if temp:
                    res.append(temp)
        except:
            pass
        if res:
            self.overview["review"] = res

    def get_mapped_required_data(self, config, dictionary=None):
        mappedResults = {}
        if dictionary:
            for k, v in config.items():
                x = self.get_dict_value_by_path(v, dictionary)
                if x:
                    mappedResults[k] = x
            return mappedResults
        for company in self.companiesData:
            for k, v in config.items():
                x = self.get_dict_value_by_path(v, company)
                if x:
                    mappedResults[k] = x
        return mappedResults

    def get_company_value(self, linkPath):
        companyLinks = []
        for company in self.companiesData:
            x = self.get_dict_value_by_path(linkPath, company)
            if x:
                companyLinks.append(x)
        return companyLinks

    def getCleanValues(self, values):
        cleanValues = []
        if type(values) == list:
            for value in values:
                if not self.isForbiddenValue(value):
                    value = self.removeBadSymbols(value)
                    cleanValues.append(value)
        else:
            if not self.isForbiddenValue(values):
                value = self.removeBadSymbols(values)

                return value

        return cleanValues

    def isForbiddenValue(self, value):
        return value in self.forbiddenValues

    def removeBadSymbols(self, value):
        string_encode = value.encode("ascii", "ignore")
        string_decode = string_encode.decode()
        return string_decode
        for symbol in self.badSymbols:
            if symbol in value:
                print(symbol)
                value = value.replace(symbol, "")
        return string_decode

    def get_officership(self, link):
        off = []
        link = "https://aleph.occrp.org/api/2/entities/" + link
        link = link + "/expand"

        requestOptions = {
            "url": link,
            "method": "",
            "headers": "",
            "data": "",
        }

        extractedData = self.getDataFromPage(requestOptions)
        companies = self.get_result_list_by_path("results", extractedData)

        for i in companies:
            if i["property"] == "ownershipAsset":
                entities = i["entities"]

                for ent in entities:
                    owner = ""
                    if ent["schema"] == "LegalEntity":
                        owner = ent["properties"]["name"]
                    if ent["schema"] == "Person":
                        owner = [
                            ent["properties"]["firstName"][0]
                            + ent["properties"]["lastName"][0]
                        ]
                    if owner:
                        off.append(
                            {
                                "name": owner[0],
                                "type": "individual",
                                "officer_role": "owner",
                                "status": "Active",
                                "occupation": "owner",
                            }
                        )
        return off

    def get_documents(self, link):
        docs = []
        link = f"https://aleph.occrp.org/api/2/entities?filter%3Aproperties.resolved={link}&filter%3Aschemata=Mention&limit=30"

        requestOptions = {
            "url": link,
            "method": "",
            "headers": "",
            "data": "",
        }

        extractedData = self.getDataFromPage(requestOptions)
        companies = self.get_result_list_by_path("results", extractedData)

        for doc in companies:
            name = doc["properties"]["document"][0]["properties"]["fileName"]
            link = doc["properties"]["document"][0]["id"]
            link = self.base_url + "/entities/" + link
            docs.append({"description": name[0], "url": link})

        return docs

    def get_officer_from_page(self, link, officerType):
        self.set_working_tree_api(link, "tree")
        temp = {}
        temp["name"] = self.get_by_xpath(
            '//div[@class="form-group"]//strong[2]/text()'
        )[0]

        temp["type"] = officerType
        addr = ",".join(
            self.get_by_xpath('//div[@class="MasterBorder"]//div[2]//div/text()')[:-1]
        )
        if addr:
            temp["address"] = {
                "address_line_1": addr,
            }
            zip = re.findall("\d\d\d\d\d-\d\d\d\d", addr)[0]
            if zip:
                temp["address"]["postal_code"] = zip
                temp["address"]["address_line_1"] = addr.split(zip)[0]

        temp["officer_role"] = "PRODUCER" if officerType == "individual" else "COMPANY"

        temp["status"] = self.get_by_xpath(
            '//td//text()[contains(., "License Status")]/../../following-sibling::td//text()'
        )[0]

        temp["information_source"] = self.base_url
        temp["information_provider"] = "Idaho department of Insurance"
        return temp if temp["status"] == "Active" else None
