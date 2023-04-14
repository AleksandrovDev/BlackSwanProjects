import base64
import datetime
import hashlib
import json
import re


from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://www.lursoft.lv/"
    NICK_NAME = base_url.split("//")[-1]
    fields = ["overview", "graph:shareholders"]
    overview = {}
    tree = None
    api = None

    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9;application/json;application/json;odata=verbose",
        "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
        "Content-Type": "application/json; application/x-www-form-urlencoded; charset=UTF-8",
    }

    def getpages(self, searchquery):
        result = []

        self.get_working_tree_api(
            f'https://www.lursoft.lv/meklet?q={searchquery.replace(" ", "+")}', "tree"
        )

        result = self.get_by_xpath(
            '//table[@class="lurs-search lurs-search--responsive lurs-search--body"]//tr/td[3]//a/@href'
        )
        result = ["https:" + i for i in result]
        result = [i.replace("/lv/", "/en/") for i in result]

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
        self, xpathCodes=None, xpathDesc=None, xpathLabels=None, api=False
    ):
        res = []
        length = None
        codes, desc, labels = None, None, None

        try:
            text = (
                self.get_by_xpath(xpathCodes)
                if not api
                else [self.get_by_api(xpathCodes)]
            )

            text = " ".join(text[1:-1])
            text = text.split("version")[:-1]
            text = [i.replace("(Source: ", "") for i in text]

            desc = [re.findall("[A-Z][a-z]+\s[a-z\s]+", i)[0].strip() for i in text]
            codes = [re.findall("\d\d\.\d\d*", i)[0].strip() for i in text]

            length = len(desc)
        except:
            pass

        if length:
            for i in range(length):
                temp = {
                    "code": codes[i] if codes else "",
                    "description": desc[i] if desc else "",
                    "label": "NACE",
                }
                res.append(temp)
        if res:
            self.overview["bst:businessClassifier"] = res

    def get_post_address(
        self, xpath=None, zipPattern=None, key=None, returnAddress=False, addr=None
    ):
        if xpath:
            addr = self.get_by_xpath(xpath)
        if key:
            addr = self.get_by_api(key)
        if addr:
            addr = addr[1:]

            if type(addr) == list:
                addr = ", ".join(addr)
            if "\n" in addr:
                splitted_addr = addr.split("\n")
            if ", " in addr:
                splitted_addr = addr.split(", ")

            addr = addr.replace("\n", " ")
            addr = addr[0] if type(addr) == list else addr
            temp = {"fullAddress": addr, "country": "Latvia"}
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
                else:
                    temp["streetAddress"] = addr.split(",")[0].strip()

            except:
                pass
            try:
                temp["city"] = addr.split(", ")[1].replace(".", "")

            except:
                pass
            temp["fullAddress"] += f', {temp["country"]}'

            temp["fullAddress"] = temp["fullAddress"].replace(".,", ",")
            if returnAddress:
                return temp
            self.overview["mdaas:PostalAddress"] = temp

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
            temp = {"fullAddress": addr, "country": "Latvia"}
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
                else:
                    temp["streetAddress"] = addr.split(",")[1].strip()

            except:
                pass
            try:
                temp["city"] = addr.split(", ")[0].replace(".", "")

            except:
                pass
            temp["fullAddress"] += f', {temp["country"]}'

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

            if fieldName == "vcard:organization-name":
                self.overview[fieldName] = el.split("(")[0].strip().replace('"', "")

            if fieldName == "hasActivityStatus":
                self.overview[fieldName] = el

            if fieldName == "bst:registrationId":
                self.overview[fieldName] = el.split(", ")[0]

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
                    self.overview[fieldName] = self.reformat_date(
                        el.split(", ")[-1], reformatDate
                    )
                else:
                    self.overview[fieldName] = el.split("T")[0]

            if fieldName == "sourceDate":
                self.overview[fieldName] = self.reformat_date(el, "%d.%m.%Y")
            if fieldName == "regExpiryDate":
                self.overview[fieldName] = el

            if fieldName == "bst:description":
                self.overview[fieldName] = el

            if fieldName == "hasURL" and el != "http://":
                if "http:" not in el:
                    el = "http://" + el
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
                self.overview["logo"] = el

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
        xpathVat=None,
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
            if el:
                temp["legal_entity_identifier"] = el[0]
        if xpathVat:
            el = self.get_by_xpath(xpathVat)
            if el:
                temp["vat_tax_number"] = el[0]

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
                xpath='//td[@class="infotag responsive_hide"]/text()[contains(., "Name")]/../following-sibling::td[1]//span[2]/text()',
            )
        except:
            return None

        self.overview["isDomiciledIn"] = "LV"

        self.fill_business_classifier(
            xpathCodes='//td[@class="infotag responsive_hide"]/text()[contains(., "Activity code (NACE)")]/../following-sibling::td[1]//text()'
        )

        self.get_address(
            xpath='//td[@class="infotag responsive_hide"]/text()[contains(., "Legal address")]/../following-sibling::td[1]//span/a/span/text()',
            zipPattern="[A-Z]{2}-\d\d\d\d\d*",
        )
        self.get_post_address(
            xpath='//td[@class="infotag responsive_hide"]/text()[contains(., "Postal address")]/../following-sibling::td[1]//text()',
            zipPattern="[A-Z]{2}-\d\d\d\d\d*",
        )

        self.fillField(
            "isIncorporatedIn",
            xpath='//td[@class="infotag responsive_hide"]/text()[contains(., "Registration number, date")]/../following-sibling::td[1]//span[2]/text()',
            reformatDate="%d.%m.%Y",
        )

        self.fillField(
            "tr-org:hasRegisteredPhoneNumber",
            xpath='//td[@class="infotag"]/text()[contains(., "Phone")]/../following-sibling::td[1]/text()',
            reformatDate="%d.%m.%Y",
        )
        self.fill_identifiers(
            xpathOtherCompanyId='//td[@class="infotag responsive_hide"]/text()[contains(., "SEPA identifier")]/../following-sibling::td[1]/text()',
            xpathVat='//td[@class="info-header"]/text()[contains(., "VAT identification number")]/../../following-sibling::tr[1]/td/text()',
        )

        self.fillField(
            "lei:legalForm",
            xpath='//td[@class="infotag responsive_hide"]/text()[contains(., "Legal form")]/../following-sibling::td[1]/text()',
        )

        self.fillField(
            "bst:registrationId",
            xpath='//td[@class="infotag responsive_hide"]/text()[contains(., "Registration number, date")]/../following-sibling::td[1]//span[2]/text()',
        )

        self.fillField("map", xpath='//img[@class="visible-print w100p"]/@src')

        self.get_working_tree_api(
            f'https://www.lursoft.lv/zo_get.php?code={link_name.split("/")[-1][1:-1]}&language=en',
            "tree",
        )

        self.fillField("hasURL", xpath='//div[@class="vizitka_contact_web"]/a/@href')

        try:
            mail = self.get_by_xpath(
                '//div[@class="vizitka_contact_web"]/script/text()'
            )[0]
            mail = mail.split('("')[-1].split('")')[0]
            mail = base64.b64decode(mail).decode("utf-8")
            mail = mail.split("mailto:")[-1].split('">')[0]
            self.overview["bst:email"] = mail
        except:
            pass
        self.fillField("logo", xpath='//div[@class="vizitka_logo"]//img/@src')

        self.overview["bst:sourceLinks"] = [link_name]
        self.overview["bst:registryURI"] = self.overview["bst:sourceLinks"][0]
        self.overview["@source-id"] = self.NICK_NAME

        return self.overview

    def get_shareholders(self, link_name):
        edd = {}
        shareholders = {}
        sholdersl1 = {}

        company = self.get_overview(link_name)

        company_name_hash = hashlib.md5(
            company["vcard:organization-name"].encode("utf-8")
        ).hexdigest()
        self.get_working_tree_api(link_name, "tree")

        try:
            names = self.get_by_xpath(
                '//td[@class="info-header toogle-block"]/text()[contains(., "List of shareholders")]/../../../following-sibling::tbody/tr/td/span/span/strong//text()'
            )
            for name in names:
                holder_name_hash = hashlib.md5(name.encode("utf-8")).hexdigest()

                shareholders[holder_name_hash] = {
                    "natureOfControl": "SHH",
                    "source": "lursoft",
                }

                try:
                    totPer = self.tree.xpath(
                        f'//td[@class="info-header toogle-block"]/text()[contains(., "List of shareholders")]/../../../following-sibling::tbody/tr/td/span/span/strong/a/text()[contains(., "{name}")]/../../../../../../following-sibling::tr[1]/td[5]/text()'
                    )
                    if not totPer:
                        totPer = self.tree.xpath(
                            f'//td[@class="info-header toogle-block"]/text()[contains(., "List of shareholders")]/../../../following-sibling::tbody/tr/td/span/span/strong/text()[contains(., "{name}")]/../../../../../following-sibling::tr[1]/td[5]/text()'
                        )
                    totPer = totPer[0].split(" ")[0]
                    shareholders[holder_name_hash]["totalPercentage"] = totPer
                except:
                    pass

                basic_in = {
                    "vcard:organization-name": name,
                    "isDomiciledIn": "LV",
                    "entity_type": "c",
                }

                try:
                    addr = self.tree.xpath(
                        f'//td[@class="info-header toogle-block"]/text()[contains(., "List of shareholders")]/../../../following-sibling::tbody/tr/td/span/span/strong/a/text()[contains(., "{name}")]/../../following-sibling::span[2]/text()'
                    )

                    if not addr:
                        addr = self.tree.xpath(
                            f'//td[@class="info-header toogle-block"]/text()[contains(., "List of shareholders")]/../../../following-sibling::tbody/tr/td/span/span/strong/text()[contains(., "{name}")]/../../following-sibling::span[1]/text()'
                        )
                    addr = addr[0].strip()

                    if addr:
                        temp = {"fullAddress": addr}
                        basic_in["mdaas:RegisteredAddress"] = temp

                except:
                    pass

                try:
                    sid = self.get_by_xpath(
                        f'//td[@class="info-header toogle-block"]/text()[contains(., "List of shareholders")]/../../../following-sibling::tbody/tr/td/span/span/strong//text()[contains(., "{name}")]/../../..//text()[1]'
                    )
                    sid = " ".join(sid)
                    sid = re.findall("\(.+\)", sid)
                    if sid:
                        sid = sid[0].split(" ")[-1][:-1]
                        if sid:
                            basic_in["@sourceReferenceID"] = sid
                except:
                    pass

                try:
                    incDate = self.tree.xpath(
                        f'//td[@class="info-header toogle-block"]/text()[contains(., "List of shareholders")]/../../../following-sibling::tbody/tr/td/span/span/strong/a/text()[contains(., "{name}")]/../../../../../../following-sibling::tr[1]/td[1]/text()'
                    )
                    if not incDate:
                        incDate = self.tree.xpath(
                            f'//td[@class="info-header toogle-block"]/text()[contains(., "List of shareholders")]/../../../following-sibling::tbody/tr/td/span/span/strong/text()[contains(., "{name}")]/../../../../../following-sibling::tr[1]/td[1]/text()'
                        )

                    incDate = incDate[0].split("From ")[-1].strip()
                    basic_in["incorporationDate "] = self.reformat_date(
                        incDate, "%d.%m.%Y"
                    )
                    shareholders[holder_name_hash]["date"] = incDate
                except:
                    pass

                sholdersl1[holder_name_hash] = {"basic": basic_in, "shareholders": {}}

            edd[company_name_hash] = {
                "basic": company,
                "entity_type": "C",
                "shareholders": shareholders,
            }

        except:
            pass

        return edd, sholdersl1
