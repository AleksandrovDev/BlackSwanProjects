import datetime
import json
import re
import math

import pycountry

from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://www.dnb.nl"

    fields = [
        "overview",
    ]

    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;"
        "q=0.8,application/signed-exchange;v=b3;q=0.9;application/json;application/json;odata=verbose",
        "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }

    NICK_NAME = base_url.split("//")[-1]

    resultData = {}
    extractedData = None

    def getpages(self, searchquery):
        link = "https://www.dnb.nl/en/public-register/"

        content = self.get_content(link, method="GET", headers=self.header)
        link_search = "https://www.dnb.nl/api/publicregister/search"

        cont = self.get_content(link, self.header, method="GET")
        dataId = str(cont.content).split('dataId="')[-1].split('"')[0]

        data = {
            "phrase": searchquery,
            "page": "1",
            "language": "en",
            "filterData": "{}",
            "type": "",
            "identifier": dataId,
            "limit": "20",
        }

        cfg = {"method": "POST", "data": data, "link": link_search}

        content = self.get_content(
            link_search, method="POST", headers=self.header, data=data
        )
        content = json.loads(content.content)

        companies = self.get_companies_list_by_path("resultData", content)
        res = []
        for company in companies:
            res.append(self.get_dict_value_by_path("url", company))

        res = [self.base_url + i for i in res]
        return res

    def transfer_to_json(self):
        self.extractedRawDict = json.loads(self.extractedData)

    def get_companies_list_by_path(self, pathToResultList, dicData):
        companiesData = self.get_dict_value_by_path(pathToResultList, dicData)
        return companiesData

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

    def isKeyExists(self, key, companyDictionary):
        return key in companyDictionary.keys()

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

    def get_company_value(self, linkPath):
        companyLinks = []
        for company in self.companiesData:
            x = self.get_dict_value_by_path(linkPath, company)
            if x:
                companyLinks.append(x)
        return companyLinks

    def get_overview(self, link):
        requiredFields = {
            "vcard:organization-name": '//div[@class="content-component contact-details"]/h2[1]/text()',
            "bst:businessClassifier": '//span/text()[contains(., "Category:")]/../following-sibling::span[1]/text()',
            "bst:registrationId": '//span/text()[contains(., "Relation number DNB:")]/../following-sibling::span[1]/text()',
            "lei": '//span/text()[contains(., "LEI code:")]/../following-sibling::span[1]/text()',
            "tradeRegisterNumber": '//span/text()[contains(., "Chamber of Commerce:")]/../following-sibling::span[1]/text()',
            "vcard:organization-tradename": '//span/text()[contains(., "Trade name:")]/../following-sibling::span[1]/text()',
        }

        hardcodedFields = {
            "hasActivityStatus": "Active",
            "regulator_name": "De Nederlandsche Bank",
            "regulatorAddress": {
                "fullAddress": "De Nederlandsche Bank, Postbus 98, 1000 AB Amsterdam",
                "city": "Amsterdam",
                "country": "Netherlands",
            },
            "regulator_url": self.base_url,
            "regulationStatus": "Authorized",
            "bst:registryURI": link,
        }

        maps = {
            "hardCodedFields": hardcodedFields,
            "requiredFieldsMap": requiredFields,
        }

        cfg = {
            "link": link,
        }

        self.extractedData = self.get_tree(
            link, headers=self.header, method="GET", data=None
        )

        res = self.get_result(maps)

        streetAddr = self.extractedData.xpath(
            '//h3/text()[contains(., "Business address")]/../following-sibling::ul[1]//span/text()[contains(., "Adress:")]/../following-sibling::span[1]/text()'
        )
        postalCode = self.extractedData.xpath(
            '//h3/text()[contains(., "Business address")]/../following-sibling::ul[1]//span/text()[contains(., "Postal code:")]/../following-sibling::span[1]/text()'
        )
        city = self.extractedData.xpath(
            '//h3/text()[contains(., "Business address")]/../following-sibling::ul[1]//span/text()[contains(., "Place of residence:")]/../following-sibling::span[1]/text()'
        )
        country = self.extractedData.xpath(
            '//h3/text()[contains(., "Business address")]/../following-sibling::ul[1]//span/text()[contains(., "Country:")]/../following-sibling::span[1]/text()'
        )

        fullAddr = ""
        if streetAddr:
            if not res.get("mdaas:RegisteredAddress"):
                res["mdaas:RegisteredAddress"] = {}
            res["mdaas:RegisteredAddress"]["streetAddress"] = streetAddr[0]
            fullAddr += streetAddr[0]

        if postalCode:
            if not res.get("mdaas:RegisteredAddress"):
                res["mdaas:RegisteredAddress"] = {}
            res["mdaas:RegisteredAddress"]["zip"] = postalCode[0]
            fullAddr += ", " + postalCode[0]

        if city:
            if not res.get("mdaas:RegisteredAddress"):
                res["mdaas:RegisteredAddress"] = {}
            res["mdaas:RegisteredAddress"]["city"] = city[0]
            fullAddr += ", " + city[0]

        if country:
            if not res.get("mdaas:RegisteredAddress"):
                res["mdaas:RegisteredAddress"] = {}
            res["mdaas:RegisteredAddress"]["country"] = country[0]
            fullAddr += ", " + country[0]

        if res.get("mdaas:RegisteredAddress"):
            res["mdaas:RegisteredAddress"]["fullAddress"] = fullAddr

            res["mdaas:OperationalAddress"] = dict(res["mdaas:RegisteredAddress"])

            p = (
                res["mdaas:OperationalAddress"]["fullAddress"]
                .replace(res["mdaas:OperationalAddress"]["zip"], "")
                .replace(", , ", ", ")
            )

            res["mdaas:OperationalAddress"]["fullAddress"] = p

            del res["mdaas:OperationalAddress"]["zip"]

        streetAddr = self.extractedData.xpath(
            '//h3/text()[contains(., "Mailing address")]/../following-sibling::ul[1]//span/text()[contains(., "Adress:")]/../following-sibling::span[1]/text()'
        )
        postalCode = self.extractedData.xpath(
            '//h3/text()[contains(., "Mailing address")]/../following-sibling::ul[1]//span/text()[contains(., "Postal code:")]/../following-sibling::span[1]/text()'
        )
        city = self.extractedData.xpath(
            '//h3/text()[contains(., "Mailing address")]/../following-sibling::ul[1]//span/text()[contains(., "Place of residence:")]/../following-sibling::span[1]/text()'
        )
        country = self.extractedData.xpath(
            '//h3/text()[contains(., "Mailing address")]/../following-sibling::ul[1]//span/text()[contains(., "Country:")]/../following-sibling::span[1]/text()'
        )

        fullAddr = ""
        if streetAddr:
            if not res.get("mdaas:PostalAddress"):
                res["mdaas:PostalAddress"] = {}
            res["mdaas:PostalAddress"]["streetAddress"] = streetAddr[0]
            fullAddr += streetAddr[0]

        if postalCode:
            if not res.get("mdaas:PostalAddress"):
                res["mdaas:PostalAddress"] = {}
            res["mdaas:PostalAddress"]["zip"] = postalCode[0]
            fullAddr += ", " + postalCode[0]

        if city:
            if not res.get("mdaas:PostalAddress"):
                res["mdaas:PostalAddress"] = {}
            res["mdaas:PostalAddress"]["city"] = city[0]
            fullAddr += ", " + city[0]

        if country:
            if not res.get("mdaas:PostalAddress"):
                res["mdaas:PostalAddress"] = {}
            res["mdaas:PostalAddress"]["country"] = country[0]
            fullAddr += ", " + country[0]

        if res.get("mdaas:PostalAddress"):
            res["mdaas:PostalAddress"]["fullADdress"] = fullAddr

        try:
            el = res["mdaas:RegisteredAddress"]["country"]
            country = pycountry.countries.search_fuzzy(el)
            if country:
                res["isDomiciledIn"] = country[0].alpha_2
        except:
            pass

        self.fill_overview_identifiers(
            xpathTradeRegistry='//span/text()[contains(., "Chamber of Commerce:")]/../following-sibling::span[1]/text()',
            xpathLegalEntityIdentifier='//span/text()[contains(., "LEI code:")]/../following-sibling::span[1]/text()',
            xpathOtherCompanyId='//span/text()[contains(., "Relation number DNB:")]/../following-sibling::span[1]/text()',
        )

        upda = self.extractedData.xpath('//span/text()[contains(., "Last update: ")]')
        if upda:
            date = upda[0].split("Last update: ")[-1][:-6]
            try:
                res["sourceDate"] = self.reformat_date(date, "%d %b %Y")
            except:
                res["sourceDate"] = self.reformat_date(date, "%d %B %Y")

        return res

    def get_result(self, maps):
        self.extract_data(maps)
        return self.resultData

    def extract_data(self, maps):
        for k, v in maps["requiredFieldsMap"].items():
            self.fill_field(k, v)

        for k, v in maps["hardCodedFields"].items():
            self.resultData[k] = v

    def fill_field(self, fieldName, dataPath=None, reformatDate=None, el=None):
        if fieldName == "bst:businessClassifier":
            self.fill_business_classifier(xpathDesc=dataPath)
        else:
            dataType = self.get_path_type(dataPath)
            if dataType == "xpath":
                el = self.get_by_xpath(dataPath)
            if dataType == "key":
                el = self.get_by_api(dataPath)
            if dataType == "defaultFill":
                el = dataPath
            if el:
                if len(el) == 1:
                    el = el[0]
                el = self.reformat_date(el, reformatDate) if reformatDate else el

                if fieldName == "isDomiciledIn":
                    country = pycountry.countries.search_fuzzy(el)
                    if country:
                        self.resultData[fieldName] = country[0].alpha_2
                    else:
                        self.resultData[fieldName] = el

                elif fieldName == "vcard:organization-tradename":
                    self.resultData[fieldName] = [el]

                elif fieldName == "Service":
                    if type(el) == list:
                        el = ", ".join(el)
                    self.resultData[fieldName] = {"serviceType": el}

                elif fieldName == "vcard:organization-tradename":
                    self.resultData[fieldName] = el.split("\n")[0].strip()

                elif fieldName == "bst:aka":
                    names = el.split(" D/B/A ")
                    if len(names) > 1:
                        names = [i.strip() for i in names]
                        self.resultData[fieldName] = names
                    else:
                        self.resultData[fieldName] = names

                elif fieldName == "lei:legalForm":
                    self.resultData[fieldName] = {"code": "", "label": el}

                elif fieldName == "map":
                    self.resultData[fieldName] = el[0] if type(el) == list else el

                elif fieldName == "previous_names":
                    el = el.strip()
                    el = el.split("\n")
                    if len(el) < 1:
                        self.resultData[fieldName] = {"name": [el[0].strip()]}
                    else:
                        el = [i.strip() for i in el]
                        res = []
                        for i in el:
                            temp = {"name": i}
                            res.append(temp)
                        self.resultData[fieldName] = res

                elif fieldName == "bst:description":
                    if type(el) == list:
                        el = ", ".join(el)
                    self.resultData[fieldName] = el

                elif fieldName == "hasURL" and el != "http://":
                    if "www" in el:
                        el = el.split(", ")[-1]
                    if "http:" not in el:
                        el = "http://" + el.strip()
                    if "www" in el:
                        self.resultData[fieldName] = el

                elif fieldName == "tr-org:hasRegisteredPhoneNumber":
                    if type(el) == list and len(el) > 1:
                        el = el[0]
                    self.resultData[fieldName] = el

                elif fieldName == "bst:stock_info":
                    if type(el) == list:
                        el = el[0]
                    self.resultData[fieldName] = {"main_exchange": el}
                elif fieldName == "agent":
                    self.resultData[fieldName] = {
                        "name": el.split("\n")[0],
                        "mdaas:RegisteredAddress": self.get_address(
                            returnAddress=True,
                            addr=" ".join(el.split("\n")[1:]),
                            zipPattern="[A-Z]\d[A-Z]\s\d[A-Z]\d",
                        ),
                    }

                elif fieldName == "logo":
                    self.resultData["logo"] = self.sourceConfig.base_url + el

                elif fieldName == "hasRegisteredFaxNumber":
                    if type(el) == list and len(el) > 1:
                        el = el[0]
                    self.resultData[fieldName] = el
                else:
                    self.resultData[fieldName] = el

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

    def make_dict_from_string(self, link_dict):
        link_dict = (
            link_dict.replace("'", '"').replace("None", '"None"').replace('""', '"')
        )
        return json.loads(link_dict)

    def reformat_date(self, date, format):
        date = datetime.datetime.strptime(date.strip(), format).strftime("%Y-%m-%d")
        return date

    def get_path_type(self, dataPath):
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
            self.resultData["mdaas:RegisteredAddress"] = temp

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
            self.resultData["mdaas:OperationalAddress"] = temp

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
            self.resultData["regulatorAddress"] = temp

    def get_prev_names(self, tree):
        prev = []
        names = self.get_by_xpath(
            tree,
            '//table[@id="tblPreviousCompanyNames"]//tr[@class="row"]//tr[@class="row"]//td[1]/text() | //table[@id="tblPreviousCompanyNames"]//tr[@class="row"]//tr[@class="rowalt"]//td[1]/text()',
            return_list=True,
        )
        dates = self.get_by_xpath(
            tree,
            '//table[@id="tblPreviousCompanyNames"]//tr[@class="row"]//tr[@class="row"]//td[2]/span/text() | //table[@id="tblPreviousCompanyNames"]//tr[@class="row"]//tr[@class="rowalt"]//td[2]/span/text()',
            return_list=True,
        )
        print(names)
        if names:
            names = [i for i in names if i != ""]
        if names and dates:
            for name, date in zip(names, dates):
                temp = {"name": name, "valid_to": date}
                prev.append(temp)
        return prev

    def fill_overview_identifiers(
        self,
        xpathTradeRegistry=None,
        xpathOtherCompanyId=None,
        xpathInternationalSecurIdentifier=None,
        xpathLegalEntityIdentifier=None,
    ):
        try:
            temp = self.resultData["identifiers"]
        except:
            temp = {}

        if xpathTradeRegistry:
            trade = self.get_by_xpath(xpathTradeRegistry)
            if trade:
                temp["trade_register_number"] = trade[0]
        if xpathOtherCompanyId:
            other = self.get_by_xpath(xpathOtherCompanyId)
            if other:
                temp["other_company_id_number"] = other[0]
        if xpathInternationalSecurIdentifier:
            el = self.get_by_xpath(xpathInternationalSecurIdentifier)
            temp["international_securities_identifier"] = el[0]
        if xpathLegalEntityIdentifier:
            el = self.get_by_xpath(xpathLegalEntityIdentifier)
            if el:
                temp["legal_entity_identifier"] = el[0]

        if temp:
            self.resultData["identifiers"] = temp

    def fill_business_classifier(
        self, xpathCodes=None, xpathDesc=None, xpathLabels=None, api=False
    ):
        res = []
        length = None
        codes, desc, labels = None, None, None

        if xpathCodes:
            codes = (
                self.get_by_xpath(xpathCodes)
                if not api
                else [self.get_by_api(xpathCodes)]
            )
            if codes:
                length = len(codes)
        if xpathDesc:
            desc = (
                self.get_by_xpath(xpathDesc)
                if not api
                else [self.get_by_api(xpathDesc)]
            )
            if desc:
                length = len(desc)
        if xpathLabels:
            labels = (
                self.get_by_xpath(xpathLabels)
                if not api
                else [self.get_by_api(xpathLabels)]
            )
            if labels:
                length = len(labels)

        if length:
            for i in range(length):
                temp = {
                    "code": codes[i] if codes else "",
                    "description": desc[i] if desc else "",
                    "label": labels[i] if labels else "",
                }
                res.append(temp)
        if res:
            self.resultData["bst:businessClassifier"] = res

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
            self.resultData["rating_summary"] = temp

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
            self.resultData["aggregateRating"] = temp

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
            self.resultData["review"] = res

    def get_officership(self, link):
        off = []
        link = "https://aleph.occrp.org/api/2/entities/" + link
        expandedLink = link + "/expand"
        self.apiFetcher.extract_data(expandedLink)
        self.apiFetcher.transfer_to_json()
        y = self.apiFetcher.get_companies_list_by_path("results")
        for i in y:
            if i["property"] == "ownershipAsset":
                entities = i["entities"]
                for ent in entities:
                    if ent["schema"] == "LegalEntity":
                        owner = ent["properties"]["name"]
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
