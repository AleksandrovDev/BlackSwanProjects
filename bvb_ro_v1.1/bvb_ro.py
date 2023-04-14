import datetime
import hashlib
import json
import re


from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://m.bvb.ro"
    NICK_NAME = base_url.split("//")[-1]
    fields = ["overview", "officership", "documents", "Financial_Information"]
    overview = {}
    tree = None
    api = None

    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9;application/json",
        "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
        "Content-Type": "application/json; application/x-www-form-urlencoded; charset=UTF-8",
    }

    def getpages(self, searchquery):
        result = []
        self.tree = self.get_tree("https://m.bvb.ro/", headers=self.header)

        url = f"https://bvb.ro/Default.aspx/GetInstrumentsList"
        data = {"searchtext": searchquery}
        self.get_working_tree_api(url, "api", method="POST", data=data)

        for company in self.api["d"]:
            result.append(
                f'https://m.bvb.ro/FinancialInstruments/Details/FinancialInstrumentsDetails.aspx?s={company["Symbol"]}'
            )
        return result

    def get_by_xpath(self, xpath):
        try:
            el = self.tree.xpath(xpath)
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

    def reformat_date(self, date, format):
        date = datetime.datetime.strptime(date.strip(), format).strftime("%Y-%m-%d")
        return date

    def fill_business_classifier(
        self, xpathCodes=None, xpathDesc=None, xpathLabels=None
    ):
        res = []
        length = None
        codes, desc, labels = None, None, None
        if xpathCodes:
            codes = self.get_by_xpath(xpathCodes)
            if codes:
                length = len(codes)
        if xpathDesc:
            desc = self.get_by_xpath(xpathDesc)
            if desc:
                length = len(desc)
        if xpathLabels:
            labels = self.get_by_xpath(xpathLabels)
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
            self.overview["bst:businessClassifier"] = res

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

    def get_address(
        self, xpath=None, zipPattern=None, key=None, returnAddress=False, addr=None
    ):
        if xpath:
            addr = self.get_by_xpath(xpath)
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
            temp = {
                "fullAddress": addr,
            }
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
            print(addr)
            try:
                city = addr.split(", ")[-2].replace(".", "")
                if city == "-":
                    temp["city"] = addr.split(", ")[-3].replace(".", "")

            except:
                pass

            temp["country"] = addr.split(", ")[-1]

            temp["fullAddress"] = temp["fullAddress"].replace(".,", ",")
            if returnAddress:
                return temp
            self.overview["mdaas:RegisteredAddress"] = temp

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

    def get_by_api(self, key):
        try:
            el = self.api[key]
            return el
        except:
            return None

    def fillField(self, fieldName, key=None, xpath=None, test=False, reformatDate=None):
        if xpath:
            el = self.get_by_xpath(xpath)
        if key:
            el = self.get_by_api(key)
        if test:
            print(el)
        if el:
            if len(el) == 1:
                el = el[0]
            el = self.reformat_date(el, reformatDate) if reformatDate else el
            if fieldName == "vcard:organization-name":
                self.overview[fieldName] = el.split("(")[0].strip()

            if fieldName == "hasActivityStatus":
                self.overview[fieldName] = el

            if fieldName == "bst:registrationId":
                self.overview[fieldName] = el

            if fieldName == "Service":
                self.overview[fieldName] = {"serviceType": el}

            if fieldName == "vcard:organization-tradename":
                self.overview[fieldName] = el.split("\n")[0].strip()

            if fieldName == "bst:aka":
                names = el.split("\n")
                names = el.split(" D/B/A ")
                if len(names) > 1:
                    names = [i.strip() for i in names]
                    self.overview[fieldName] = names
                else:
                    self.overview[fieldName] = names

            if fieldName == "lei:legalForm":
                self.overview[fieldName] = {"code": "", "label": el}

            if fieldName == "map":
                self.overview[fieldName] = el[0] if type(el) == list else el

            if fieldName == "previous_names":
                el = el.strip()
                el = el.split("\n")
                if len(el) < 1:
                    self.overview[fieldName] = {"name": [el[0].strip()]}
                else:
                    el = [i.strip() for i in el]
                    res = []
                    for i in el:
                        temp = {"name": i}
                        res.append(temp)
                    self.overview[fieldName] = res

            if fieldName == "isIncorporatedIn":
                if reformatDate:
                    self.overview[fieldName] = self.reformat_date(el, reformatDate)
                else:
                    self.overview[fieldName] = el

            if fieldName == "sourceDate":
                self.overview[fieldName] = self.reformat_date(el, "%d.%m.%Y")
            if fieldName == "regExpiryDate":
                self.overview[fieldName] = el

            if fieldName == "bst:description":
                self.overview[fieldName] = el

            if fieldName == "hasURL" and el != "http://":
                if "http:" not in el:
                    el = "http:" + el
                self.overview[fieldName] = el
            if fieldName == "bst:email":
                self.overview["bst:email"] = el

            if fieldName == "tr-org:hasRegisteredPhoneNumber":
                if type(el) == list and len(el) > 1:
                    el = el[0]
                self.overview[fieldName] = el

            if fieldName == "agent":
                self.overview[fieldName] = {
                    "name": el.split("\n")[0],
                    "mdaas:RegisteredAddress": self.get_address(
                        returnAddress=True,
                        addr=" ".join(el.split("\n")[1:]),
                        zipPattern="[A-Z]\d[A-Z]\s\d[A-Z]\d",
                    ),
                }
            if fieldName == "RegulationStatusEffectiveDate":
                self.overview["RegulationStatusEffectiveDate"] = el

            if fieldName == "logo":
                self.overview["logo"] = (
                    "https://m.bvb.ro/FinancialInstruments/Details/" + el
                )

            if fieldName == "hasRegisteredFaxNumber":
                if type(el) == list and len(el) > 1:
                    el = el[0]
                self.overview[fieldName] = el

    def fill_identifiers(
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

    def check_tree(self):
        print(self.tree.xpath("//text()"))

    def get_working_tree_api(self, link_name, type, method="GET", data=None):
        if type == "tree":
            if data:
                self.tree = self.get_tree(
                    link_name, headers=self.header, method=method, data=data
                )
            else:
                self.tree = self.get_tree(link_name, headers=self.header, method=method)
        if type == "api":
            if data:
                self.api = self.get_content(
                    link_name, headers=self.header, method=method, data=json.dumps(data)
                )
            else:
                self.api = self.get_content(
                    link_name, headers=self.header, method=method
                )
            self.api = json.loads(self.api.content)

    def fillRatingSummary(self, xpathRatingGroup=None, xpathRatings=None):
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

    def fillAgregateRating(self, xpathReview=None, xpathRatingValue=None):
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

    def fillReviews(
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
                            f"//async-list//review[{i+1}]" + xpathRatingValue
                        )
                    )
                    if ratingsValues:
                        temp["ratingValue"] = ratingsValues
                if xpathDate:
                    date = self.tree.xpath(f"//async-list//review[{i+1}]" + xpathDate)
                    if date:
                        temp["datePublished"] = date[0].split("T")[0]

                if xpathDesc:
                    desc = self.tree.xpath(f"//async-list//review[{i+1}]" + xpathDesc)
                    if desc:
                        temp["description"] = desc[0]
                if temp:
                    res.append(temp)
        except:
            pass
        if res:
            self.overview["review"] = res

    def fillRegulatorAddress(
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

    def getOfficerFromPage(self, link, officerType):
        self.get_working_tree_api(link, "tree")
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

    def getHiddenValuesASP(self):
        names = self.get_by_xpath('//input[@type="hidden"]/@name')
        temp = {}
        for name in names:
            value = self.get_by_xpath(
                f'//input[@type="hidden"]/@name[contains(., "{name}")]/../@value'
            )
            temp[name] = value[0] if value else ""
        return temp

    def get_overview(self, link_name):
        self.overview = {}
        self.get_working_tree_api(link_name, "tree")

        try:
            self.fillField(
                "vcard:organization-name",
                xpath='//div[@class="col-xs-12 col-sm-6 col-md-5 col-lg-5 pRight0"]/div[1]/h2[1]/text()',
            )
        except:
            return None

        self.overview["isDomiciledIn"] = "DE"

        self.fill_identifiers(
            xpathInternationalSecurIdentifier='//td//text()[contains(., "ISIN:")]/../following-sibling::td//text()',
        )

        try:
            self.overview["classOfShares"] = [
                {
                    "class": "outstandingShares",
                    "count": self.get_by_xpath(
                        '//td//text()[contains(., "Total no. of shares")]/../following-sibling::td//text()'
                    )[0],
                }
            ]
        except:
            pass

        self.fillField(
            "logo", xpath='//img[@id="ctl00_body_HeaderControl_imglogo"]/@src'
        )
        self.overview["bst:sourceLinks"] = [link_name]
        self.fillField(
            "hasActivityStatus",
            xpath='//td//text()[contains(., "Status:")]/../following-sibling::td//text()',
        )

        issueTab = self.get_by_xpath(
            '//a/text()[contains(., "Issuer profile")]/../@href'
        )

        if issueTab:
            number = re.findall("ctl00\$body\$IFTabsControlDetails\$lb\d", issueTab[0])
            if number:
                number = str(number[0][-1])
        data = self.getHiddenValuesASP()
        data[
            "ctl00$MasterScriptManager"
        ] = f"ctl00$body$IFTabsControlDetails$ctl00|ctl00$body$IFTabsControlDetails$lb{number}"
        data["__EVENTTARGET"] = f"ctl00$body$IFTabsControlDetails$lb{number}"
        data["__ASYNCPOST"] = "true"
        data["ctl00$body$ctl02$NewsBySymbolControl$chOutVolatility"] = "on"
        data["ctl00$body$ctl02$NewsBySymbolControl$chOutInsiders"] = "on"
        data["gv_length"] = "10"
        data["autocomplete-form-mob"] = ""
        self.header["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        self.get_working_tree_api(link_name, "tree", method="POST", data=data)

        self.fillField(
            "hasURL",
            xpath='//td//text()[contains(., "Website")]/../following-sibling::td/a/@href',
        )
        self.fillField(
            "bst:email",
            xpath='//td//text()[contains(., "E-mail")]/../following-sibling::td//text()',
        )
        self.get_address(
            '//td//text()[contains(., "Address")]/../following-sibling::td//text()',
            zipPattern="\d\d\d\d\d",
        )
        self.fillField(
            "tr-org:hasRegisteredPhoneNumber",
            xpath='//td//text()[contains(., "Phone")]/../following-sibling::td//text()',
        )
        self.fillField(
            "hasRegisteredFaxNumber",
            xpath='//td//text()[contains(., "Fax")]/../following-sibling::td//text()',
        )

        self.overview["bst:registryURI"] = link_name
        self.overview["@source-id"] = self.NICK_NAME

        self.overview["bst:stock_info"] = {
            "mic_code": "XRSI",
            "main_exchange": "Bucharest Stock Exchange",
            "ticket_symbol": link_name.split("s=")[-1],
        }

        self.fill_identifiers(
            xpathLegalEntityIdentifier='//td//text()[contains(., "LEI Code")]/../following-sibling::td//text()',
            xpathOtherCompanyId='//td//text()[contains(., "Fiscal / Unique Code")]/../following-sibling::td//text()',
        )
        try:
            self.overview["bst:registrationId"] = self.overview["identifiers"][
                "other_company_id_number"
            ]
        except:
            pass

        try:
            self.overview["Service"] = {
                "serviceType": self.get_by_xpath(
                    '//td//text()[contains(., "Field of activity")]/../following-sibling::td//text()'
                )[0]
            }
        except:
            pass

        return self.overview

    def get_officership(self, link_name):
        off = []
        self.get_working_tree_api(link_name, "tree")

        issueTab = self.get_by_xpath(
            '//a/text()[contains(., "Issuer profile")]/../@href'
        )

        if issueTab:
            number = re.findall("ctl00\$body\$IFTabsControlDetails\$lb\d", issueTab[0])
            if number:
                number = str(number[0][-1])
        data = self.getHiddenValuesASP()
        data[
            "ctl00$MasterScriptManager"
        ] = f"ctl00$body$IFTabsControlDetails$ctl00|ctl00$body$IFTabsControlDetails$lb{number}"
        data["__EVENTTARGET"] = f"ctl00$body$IFTabsControlDetails$lb{number}"
        data["__ASYNCPOST"] = "true"
        data["ctl00$body$ctl02$NewsBySymbolControl$chOutVolatility"] = "on"
        data["ctl00$body$ctl02$NewsBySymbolControl$chOutInsiders"] = "on"
        data["gv_length"] = "10"
        data["autocomplete-form-mob"] = ""
        self.header["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        self.get_working_tree_api(link_name, "tree", method="POST", data=data)

        try:
            t1 = self.tree.xpath(
                '//table[@id="ctl00_body_ctl02_CompanyProfile_dvIssCA"]//tr/td/table//tr[2]/td/text()'
            )[0]
            n1 = self.tree.xpath(
                '//table[@id="ctl00_body_ctl02_CompanyProfile_dvIssCA"]//tr/td/table//tr[3]/td/text()'
            )[0]
            t2 = self.tree.xpath(
                '//table[@id="ctl00_body_ctl02_CompanyProfile_dvIssCA"]//tr/td/table//tr[6]/td/text()'
            )[0]
            n2 = self.tree.xpath(
                '//table[@id="ctl00_body_ctl02_CompanyProfile_dvIssCA"]//tr/td/table//tr[7]/td/text()'
            )[0]
            off.append(
                {
                    "name": n1,
                    "type": "individual",
                    "officer_role": t1,
                    "status": "Active",
                    "occupation": t1,
                    "information_source": self.base_url,
                    "information_provider": "Bucharest Stock Exchange",
                }
            )
            if n1 != n2:
                off.append(
                    {
                        "name": n2,
                        "type": "individual",
                        "officer_role": t2,
                        "status": "Active",
                        "occupation": t2,
                        "information_source": self.base_url,
                        "information_provider": "Bucharest Stock Exchange",
                    }
                )
        except:
            pass

        return off

    def get_documents(self, link_name):
        docs = []

        self.get_working_tree_api(link_name, "tree")

        issueTab = self.get_by_xpath(
            '//a/text()[contains(., "Issuer profile")]/../@href'
        )

        if issueTab:
            number = re.findall("ctl00\$body\$IFTabsControlDetails\$lb\d", issueTab[0])
            if number:
                number = str(number[0][-1])
        data = self.getHiddenValuesASP()
        data[
            "ctl00$MasterScriptManager"
        ] = f"ctl00$body$IFTabsControlDetails$ctl00|ctl00$body$IFTabsControlDetails$lb{number}"
        data["__EVENTTARGET"] = f"ctl00$body$IFTabsControlDetails$lb{number}"
        data["__ASYNCPOST"] = "true"
        data["ctl00$body$ctl02$NewsBySymbolControl$chOutVolatility"] = "on"
        data["ctl00$body$ctl02$NewsBySymbolControl$chOutInsiders"] = "on"
        data["gv_length"] = "10"
        data["autocomplete-form-mob"] = ""
        self.header["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        self.get_working_tree_api(link_name, "tree", method="POST", data=data)

        texts = self.tree.xpath(
            '//div/text()[contains(., "Issuer documents")]/following-sibling::div[1]/div//td//text()'
        )
        texts = [i.strip() for i in texts]
        texts = [i for i in texts if i]

        links = self.tree.xpath(
            '//div/text()[contains(., "Issuer documents")]/following-sibling::div[1]/div//td/a/@href'
        )
        links = [self.base_url + i for i in links]

        for doc, link in zip(texts, links):
            temp = {"url": link, "description": doc}
            docs.append(temp)
        return docs

    def get_financial_information(self, link_name):
        self.get_working_tree_api(link_name, "tree")
        fin = {}
        temp = {"stock_id": link_name.split("s=")[-1]}

        try:
            temp["stock_name"] = self.get_by_xpath(
                '//div[@class="col-xs-12 col-sm-6 col-md-5 col-lg-5 pRight0"]/div[1]/h2[1]/text()'
            )[0]
        except:
            pass

        curr = {
            "data_date": datetime.datetime.strftime(
                datetime.datetime.today(), "%Y-%m-%d"
            )
        }
        open = self.get_by_xpath(
            '//td//text()[contains(., "Open price")]/../following-sibling::td//text()'
        )
        if open:
            curr["open_price"] = open[0]

        min = self.get_by_xpath(
            '//td//text()[contains(., "Low price")]/../following-sibling::td//text()'
        )
        max = self.get_by_xpath(
            '//td//text()[contains(., "High price")]/../following-sibling::td//text()'
        )

        if min and max:
            curr["day_range"] = f"{min[0]}-{max[0]}"

        vol = self.get_by_xpath(
            '//td//text()[contains(., "Total no. of shares")]/../following-sibling::td//text()'
        )
        if vol:
            curr["volume"] = vol[0]

        prClose = self.get_by_xpath(
            '//td//text()[contains(., "Last price")]/../following-sibling::td//text()'
        )
        if prClose:
            curr["prev_close_price"] = prClose[0]

        cap = self.get_by_xpath(
            '//td//text()[contains(., "Market cap")]/../following-sibling::td//text()'
        )
        if cap:
            curr["market_capitalization"] = cap[0]

        min52 = self.get_by_xpath(
            '//td//text()[contains(., "52 weeks low")]/../following-sibling::td//text()'
        )
        max52 = self.get_by_xpath(
            '//td//text()[contains(., "52 weeks high")]/../following-sibling::td//text()'
        )
        if min52 and max52:
            curr["52_week_range"] = f"{min52[0]}-{max52[0]}"

        temp["current"] = curr
        fin["stocks_information"] = [temp]

        return fin
