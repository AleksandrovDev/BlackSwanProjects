import datetime
import hashlib
import json
import re
from lxml import etree


from geopy import Nominatim

from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages

import pycountry


class Handler(Extract, GetPages):
    base_url = "https://www.iiroc.ca"
    NICK_NAME = base_url.split("//")[-1]
    fields = ["overview"]
    overview = {}
    tree = None
    api = None

    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9;application/json;application/json;odata=verbose",
        "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }

    def getpages(self, searchquery):
        link = f"https://www.iiroc.ca/investors/dealers-we-regulate"
        self.get_working_tree_api(link, "tree")

        data = {
            "view_path": "/node/12001",
            "combine": searchquery,
            "view_name": "dealers_we_regulate",
            "view_display_id": "block_dealers_we_regulate",
            "view_args": "",
            "view_path": "/node/12001",
            "view_base_path": "",
            "view_dom_id": "415e11ea97c329ca06f8a59ee587955f901718dd728ac1aada83ba38124df1b6",
            "pager_element": "0",
            "_drupal_ajax": "1",
            "ajax_page_state[theme]": "de_theme",
            "ajax_page_state[theme_token]": "",
            "ajax_page_state[libraries]": "anchor_link/drupal.anchor_link,better_exposed_filters/general,ckeditor_indentblock/indentblock,classy/base,classy/messages,cohesion/coh-module,cohesion/coh-theme,cohesion/element_templates.drupal-menu,cohesion/element_templates.image,cohesion/element_templates.link,cohesion/element_templates.row-for-columns,cohesion/global_libraries.cohMatchHeights,cohesion/global_libraries.jquery_ui_effect_blind,cohesion/global_libraries.jquery_ui_effect_fade,cohesion/global_libraries.jquery_ui_effect_none,cohesion/global_libraries.matchHeight,cohesion/global_libraries.parallax_scrolling,cohesion/global_libraries.windowscroll,core/drupal.collapse,core/normalize,de_theme/base,de_theme/fonts,extlink/drupal.extlink,footnotes/footnotes,iiroc_same_tab/iiroc_same_tab,obfuscate_email/default,responsive_menu/responsive_menu.config,responsive_menu/responsive_menu.mmenu,responsive_menu/responsive_menu.styling,system/base,views/views.ajax,views/views.module",
        }
        link = "https://www.iiroc.ca/views/ajax?_wrapper_format=drupal_ajax"
        self.get_working_tree_api(link, "api", data=data, method="POST")
        self.tree = etree.HTML(self.api[2]["data"])
        companies = self.get_by_xpath(
            '//table[@class="views-table views-view-table cols-2"]//tr/td[1]//text()'
        )

        result = companies

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
                splittedAddr = addr[:-1].copy()

                addr = ", ".join(addr[:-1])

            temp = {"fullAddress": addr, "country": "Canada"}
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
                temp["streetAddress"] = ", ".join(splittedAddr[:-1]).split(" P.O")[0]

            except:
                pass
            try:
                temp["city"] = splittedAddr[-1].split(" ")[0]

            except:
                pass

            temp["fullAddress"] = temp["fullAddress"].replace(".,", ",") + ", Canada"
            if returnAddress:
                return temp
            self.overview["mdaas:RegisteredAddress"] = temp

    def get_address_provider(
        self, xpath=None, zipPattern=None, key=None, returnAddress=False, addr=None
    ):
        if xpath:
            addr = self.get_by_xpath(xpath)
        if key:
            addr = self.get_by_api(key)
        if addr:
            if type(addr) == list:
                addr = [i for i in addr if ("T +" not in i and "F +" not in i)]

                addr = ", ".join(addr)

            if "\n" in addr:
                splitted_addr = addr.split("\n")
            if ", " in addr:
                splitted_addr = addr.split(", ")

            addr = addr.replace("\n", " ")
            addr = addr[0] if type(addr) == list else addr

            print(addr)
            temp = {"fullAddress": addr, "country": addr.split(", ")[-1]}
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
                zip = "".join(addr.split(", ")[-2].split(" ")[:-1])
                temp["zip"] = zip
            except:
                pass

            try:
                street = addr.split("Street")

                if len(street) == 2:
                    temp["streetAddress"] = street[0] + "Street"
                else:
                    temp["streetAddress"] = "".join(addr.split(",")[0:2])

            except:
                pass
            try:
                temp["city"] = addr.split(", ")[-2].split(" ")[-1]

            except:
                pass

            temp["fullAddress"] = temp["fullAddress"].replace(".,", ",")
            if returnAddress:
                return temp
            self.overview["mdaas:RegisteredAddress"] = temp

    def get_address_brokers(
        self, xpath=None, zipPattern=None, key=None, returnAddress=False, addr=None
    ):
        if xpath:
            addr = self.get_by_xpath(xpath)
        if key:
            addr = self.get_by_api(key)
        if addr:
            if type(addr) == list:
                addr = [i for i in addr if ("T +" not in i and "F +" not in i)]

                addr = ", ".join(addr)

            if "\n" in addr:
                splitted_addr = addr.split("\n")
            if ", " in addr:
                splitted_addr = addr.split(", ")

            addr = addr.replace("\n", " ")
            addr = addr[0] if type(addr) == list else addr

            print(addr)
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
                zip = re.findall("[\d+A-Z]{2,}\s*[\d+A-Z]{2,}", addr.split(", ")[-1])

                temp["zip"] = zip[0]
            except:
                pass

            try:
                temp["streetAddress"] = addr.split(", ")[0]

            except:
                pass
            try:
                temp["city"] = addr.split(", ")[-1].split(temp["zip"])[-1]
                if not temp["city"]:
                    temp["city"] = addr.split(", ")[-1].split(temp["zip"])[0]

            except:
                pass

            temp["fullAddress"] = temp["fullAddress"].replace(".,", ",")
            try:
                temp["zip"] = temp["zip"].strip()
                temp["city"] = temp["city"].strip()
            except:
                pass
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

            if fieldName == "available_products":
                self.overview[fieldName] = el

            if fieldName == "hasActivityStatus":
                self.overview[fieldName] = el

            if fieldName == "size":
                self.overview["size"] = el

            if fieldName == "isDomiciledIn":
                name = [
                    country.alpha_2
                    for country in pycountry.countries
                    if country.name == el
                ]
                if name:
                    el = name[0]
                self.overview["isDomiciledIn"] = el

            if fieldName == "bst:registrationId":
                self.overview[fieldName] = el

            if fieldName == "Service":
                if type(el) == list:
                    el = ", ".join(el)
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

            if fieldName == "hasLatestOrganizationFoundedDate":
                self.overview[fieldName] = el

            if fieldName == "isIncorporatedIn":
                self.overview[fieldName] = el

            if fieldName == "dissolutionDate":
                self.overview[fieldName] = el

            if fieldName == "sourceDate":
                self.overview[fieldName] = self.reformat_date(el, "%d.%m.%Y")
            if fieldName == "regExpiryDate":
                self.overview[fieldName] = el

            if fieldName == "bst:description":
                self.overview[fieldName] = el

            if fieldName == "hasURL" and el != "http://":
                self.overview[fieldName] = el
            if fieldName == "bst:email":
                if type(el) == list:
                    el = el[0]
                self.overview["bst:email"] = el

            if fieldName == "tr-org:hasRegisteredPhoneNumber":
                if type(el) == list and len(el) > 1:
                    el = el[-1]
                    rega = re.findall("[\d-]{2,}", el)
                    if rega:
                        self.overview[fieldName] = rega[0]

            if fieldName == "agent":
                self.overview[fieldName] = {
                    "name": el.split("\n")[0],
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
                if "F" in el:
                    el = el[2:]
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
                temp["other_company_id_number"] = other[0].split("Market Maker ID: ")[
                    -1
                ]
            else:
                other = self.get_by_xpath('//text()[contains(., "Member ID")]')
                if other:
                    temp["other_company_id_number"] = other[0].split("Member ID: ")[-1]

        if xpathInternationalSecurIdentifier:
            el = self.get_by_xpath(xpathInternationalSecurIdentifier)
            temp["international_securities_identifier"] = el[0]
        if xpathLegalEntityIdentifier:
            el = self.get_by_xpath(xpathLegalEntityIdentifier)
            if el:
                temp["legal_entity_identifier"] = el[0].split(
                    "Legal Entity Identifier (LEI): "
                )[-1]

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
                    link_name, headers=self.header, method=method, data=data
                )
            else:
                self.api = self.get_content(
                    link_name, headers=self.header, method=method
                )
            self.api = json.loads(self.api.content[10:-11])

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
        searchquery = link_name.lower().replace(" ", "+")
        link = f"https://www.iiroc.ca/investors/dealers-we-regulate"
        self.get_working_tree_api(link, "tree")

        data = {
            "view_path": "/node/12001",
            "combine": link_name,
            "view_name": "dealers_we_regulate",
            "view_display_id": "block_dealers_we_regulate",
            "view_args": "",
            "view_path": "/node/12001",
            "view_base_path": "",
            "view_dom_id": "415e11ea97c329ca06f8a59ee587955f901718dd728ac1aada83ba38124df1b6",
            "pager_element": "0",
            "_drupal_ajax": "1",
            "ajax_page_state[theme]": "de_theme",
            "ajax_page_state[theme_token]": "",
            "ajax_page_state[libraries]": "anchor_link/drupal.anchor_link,better_exposed_filters/general,ckeditor_indentblock/indentblock,classy/base,classy/messages,cohesion/coh-module,cohesion/coh-theme,cohesion/element_templates.drupal-menu,cohesion/element_templates.image,cohesion/element_templates.link,cohesion/element_templates.row-for-columns,cohesion/global_libraries.cohMatchHeights,cohesion/global_libraries.jquery_ui_effect_blind,cohesion/global_libraries.jquery_ui_effect_fade,cohesion/global_libraries.jquery_ui_effect_none,cohesion/global_libraries.matchHeight,cohesion/global_libraries.parallax_scrolling,cohesion/global_libraries.windowscroll,core/drupal.collapse,core/normalize,de_theme/base,de_theme/fonts,extlink/drupal.extlink,footnotes/footnotes,iiroc_same_tab/iiroc_same_tab,obfuscate_email/default,responsive_menu/responsive_menu.config,responsive_menu/responsive_menu.mmenu,responsive_menu/responsive_menu.styling,system/base,views/views.ajax,views/views.module",
        }
        link = "https://www.iiroc.ca/views/ajax?_wrapper_format=drupal_ajax"
        self.get_working_tree_api(link, "api", data=data, method="POST")
        self.tree = etree.HTML(self.api[2]["data"])

        companies = self.get_by_xpath(
            '//table[@class="views-table views-view-table cols-2"]//tr/td[1]//text()'
        )

        try:
            self.fillField(
                "vcard:organization-name",
                xpath='//table[@class="views-table views-view-table cols-2"]//tr/td[1]//text()',
            )
        except:
            return None

        self.overview["bst:sourceLinks"] = [
            "https://www.iiroc.ca/investors/dealers-we-regulate"
        ]

        self.fillField(
            "hasURL",
            xpath='//table[@class="views-table views-view-table cols-2"]//tr//td[2]//a/@href',
        )

        self.fillField(
            "tr-org:hasRegisteredPhoneNumber",
            xpath='//table[@class="views-table views-view-table cols-2"]//tr//td[2]//p//text()',
        )
        self.overview[
            "regulator_name"
        ] = "Investment Industry Regulatory Organization of Canada"
        self.overview["regulatorAddress"] = {
            "fullAddress": "“Suite 2000, 121 King Street West Toronto, Ontario, M5H 3T9",
            "city": "Toronto",
            "country": "Canada",
        }
        self.overview["regulator_url"] = self.base_url
        self.overview["RegulationStatus"] = "Authorized"
        self.overview["@source-id"] = self.NICK_NAME

        self.get_address(
            '//table[@class="views-table views-view-table cols-2"]//tr//td[2]//p//text()',
            zipPattern="[\dA-Z]{3}\s[\dA-Z]{3}",
        )
        self.overview["isDomiciledIn"] = "CA"

        return self.overview
