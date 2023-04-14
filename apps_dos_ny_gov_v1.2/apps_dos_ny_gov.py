import datetime
import hashlib
import json
import re


from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://apps.dos.ny.gov/"
    NICK_NAME = "apps.dos.ny.gov"
    fields = ["overview", "officership"]

    header = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Mobile Safari/537.36",
        "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
        "Content-Type": "application/json;charset=UTF-8",
    }

    def get_by_xpath(self, tree, xpath, return_list=False):
        try:
            el = tree.xpath(xpath)
        except Exception as e:
            print(e)
            return None
        if el:
            if return_list:
                return el
            else:
                return el[0].strip()
        else:
            return None

    def getpages(self, searchquery):
        url3 = "https://apps.dos.ny.gov/PublicInquiryWeb/api/PublicInquiry/GetComplexSearchMatchingEntities"
        data = {
            "searchValue": f"{searchquery}",
            "searchByTypeIndicator": "EntityName",
            "searchExpressionIndicator": "Contains",
            "entityStatusIndicator": "AllStatuses",
            "entityTypeIndicator": [
                "Corporation",
                "LimitedLiabilityCompany",
                "LimitedPartnership",
                "LimitedLiabilityPartnership",
            ],
            "listPaginationInfo": {"listStartRecord": 1, "listEndRecord": 500},
        }
        d = json.dumps(data)
        con = self.get_content(url3, method="POST", data=d, headers=self.header)
        res = json.loads(con.content)
        result_links = []
        for i in res["entitySearchResultList"]:
            result_links.append(i["dosID"])

        return result_links

    def get_address(self, res):
        try:
            address = res["sopAddress"]["address"]
        except:
            return None
        temp_dict = {}
        zip = address.get("zipCode")
        country = address.get("country")
        street = address.get("streetAddress")
        city = address.get("city")
        if zip and country and street and city:
            temp_dict = {
                "zip": address.get("zipCode"),
                "country": address.get("country"),
                "streetAddress": address.get("streetAddress"),
                "city": address.get("city"),
            }
            temp_dict[
                "fullAddress"
            ] = f"{temp_dict['streetAddress']}, {temp_dict['zip']}, {temp_dict['city']}, {temp_dict['country']}"
        if temp_dict:
            return temp_dict
        else:
            return None

    def get_prev_names(self, tree):
        previous_names = []

        company_id = self.get_by_xpath(
            tree, '//div/text()[contains(., "Company Title Changes")]/../../@ng-click'
        ).split(",")[-1]
        id_clean = re.findall("\w+", company_id)[0]
        url = f"https://www.kap.org.tr/en/BildirimSgbfApproval/UNV/{id_clean}"
        tree = self.get_tree(url)

        js = tree.xpath("//text()")[0]
        if js:
            for i in json.loads(js):
                temp_dict = {
                    "name": i["basic"]["companyName"],
                    "valid_to": self.reformat_date(
                        i["basic"]["publishDate"], "%d.%m.%y %H:%M"
                    ),
                }
                previous_names.append(temp_dict)

        if previous_names:
            return previous_names
        return None

    def get_reg_agent(self, res):
        try:
            agent = res["registeredAgent"]
            if agent["name"] != "":
                temp_dict = {
                    "name": agent["name"],
                    "mdaas:RegisteredAddress": {
                        "zip": agent["address"]["zipCode"],
                        "streetAddress": agent["address"]["streetAddress1"]
                        + " "
                        + agent["address"]["streetAddress2"],
                        "city": agent["address"]["city"],
                        "country": agent["address"]["countryCode"],
                    },
                }
                temp_addr = temp_dict["mdaas:RegisteredAddress"]
                temp_addr[
                    "fullAddress"
                ] = f"{temp_addr['streetAddress']}, {temp_addr['zip']}, {temp_addr['city']}, {temp_addr['country']}"
                return temp_dict
            else:
                return None
        except:
            return None

    def getPreviousNames(self, id, name):
        result_list = []
        url = "https://apps.dos.ny.gov/PublicInquiryWeb/api/PublicInquiry/GetNameHistoryByID"
        data = {
            "SearchID": f"{id}",
            "AssumedNameFlag": "false",
            "ListSortedBy": "ALL",
            "listPaginationInfo": {"listStartRecord": 1, "listEndRecord": 50},
        }
        ress = self.get_content(
            url, headers=self.header, data=json.dumps(data), method="POST"
        )
        ress = json.loads(ress.content)
        try:
            names = ress["nameHistoryResultList"]
            for i in names:
                if i["entityName"] != name:
                    temp_dict = {
                        "name": i["entityName"],
                        "valid_from": i["fileDate"].split("T")[0],
                    }
                    result_list.append(temp_dict)
            if result_list:
                return result_list
            else:
                return None
        except:
            return None

    def get_overview(self, link):
        url = "https://apps.dos.ny.gov/PublicInquiryWeb/api/PublicInquiry/GetEntityRecordByID"
        data = {"SearchID": link, "AssumedNameFlag": "false"}
        d = json.dumps(data)
        con = self.get_content(url, headers=self.header, data=d, method="POST")
        res = json.loads(con.content)
        company = {}
        try:
            orga_name = res["entityGeneralInfo"]["entityName"]
        except:
            return None
        if orga_name:
            company["vcard:organization-name"] = orga_name.strip()
        company["isDomiciledIn"] = "US"

        if res.get("stockShareInfoList") is not None:
            company["shareCount"] = str(
                int(float(res["stockShareInfoList"][0].get("quantity")))
            )
        if res["entityGeneralInfo"].get("entityStatus") is not None:
            company["hasActivityStatus"] = res["entityGeneralInfo"].get("entityStatus")
        if res["entityGeneralInfo"].get("dosID") is not None:
            company["identifiers"] = {
                "other_company_id_number": res["entityGeneralInfo"].get("dosID")
            }
        if res["entityGeneralInfo"].get("jurisdiction") is not None:
            company["registeredIn"] = (
                res["entityGeneralInfo"].get("jurisdiction").split(",")[0]
            )
        if res["entityGeneralInfo"].get("effectiveDateInitialFiling") is not None:
            company["isIncorporatedIn"] = (
                res["entityGeneralInfo"].get("effectiveDateInitialFiling").split("T")[0]
            )
        address = self.get_address(res)
        if address:
            company["mdaas:RegisteredAddress"] = address
        prevNames = self.getPreviousNames(link, company["vcard:organization-name"])
        if prevNames:
            company["previous_names"] = prevNames

        if res["entityGeneralInfo"].get("entityType") is not None:
            company["lei:legalForm"] = {
                "label": res["entityGeneralInfo"].get("entityType"),
                "code": "",
            }

        try:
            if res["latestDateDissolution"] != "":
                company["dissolutionDate"] = res["latestDateDissolution"].split("T")[0]
        except:
            pass

        reg_agent = self.get_reg_agent(res)

        if reg_agent:
            company["agent"] = reg_agent

        company["@source-id"] = self.NICK_NAME

        return company

    def get_officership(self, link):
        url = "https://apps.dos.ny.gov/PublicInquiryWeb/api/PublicInquiry/GetEntityRecordByID"
        data = {"SearchID": link, "AssumedNameFlag": "false"}
        d = json.dumps(data)
        con = self.get_content(url, headers=self.header, data=d, method="POST")
        res = json.loads(con.content)

        officers = []
        try:
            address = res["ceo"]["address"]
            addr = f"{address['addressLine2']}, {address['city']}, {address['country']}"
            temp_dict = {
                "name": res["ceo"]["name"],
                "officer_role": "Chief Executive Officer",
                "status": "Active",
                "country_of_residence": "United States",
                "occupation": "Chief Executive Officer",
                "information_source": "https://apps.dos.ny.gov",
                "information_provider": "New York Division of Corporations (UDA)",
                "address": {
                    "address_line_1": addr,
                    "postal_code": res["ceo"]["address"]["zipCode"],
                },
            }
            officers.append(temp_dict)
        except:
            pass
        return officers
