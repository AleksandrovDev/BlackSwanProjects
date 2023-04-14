import datetime
import hashlib
import json
import re

# from geopy import Nominatim

from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://cado.eservices.gov.nl.ca"
    NICK_NAME = "cado.eservices.gov.nl.ca"
    fields = ["overview", "officership"]

    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    def get_by_xpath(self, tree, xpath, return_list=False):
        try:
            el = tree.xpath(xpath)
        except Exception as e:
            print(e)
            return None
        if el:
            if return_list:
                return [i.strip() for i in el]
            else:
                return el[0].strip()
        else:
            return None

    def check_tree(self, tree):
        print(tree.xpath("//text()"))

    def check_create(self, tree, xpath, title, dictionary, date_format=None):
        item = self.get_by_xpath(tree, xpath)
        if item:
            if date_format:
                item = self.reformat_date(item, date_format)
            dictionary[title] = item.strip()

    def getpages(self, searchquery):
        tree = self.get_tree(
            "https://cado.eservices.gov.nl.ca/CADOInternet/Main.aspx",
            headers=self.header,
        )
        tree = self.get_tree(
            "https://cado.eservices.gov.nl.ca/CADOInternet/Company/CompanyMain.aspx",
            headers=self.header,
        )
        tree = self.get_tree(
            "https://cado.eservices.gov.nl.ca/CADOInternet/Company/CompanyNameNumberSearch.aspx",
            headers=self.header,
        )
        url = "https://cado.eservices.gov.nl.ca/CADOInternet/Company/CompanyNameNumberSearch.aspx"
        hid_val = self.get_by_xpath(
            tree, '//input[@type="hidden"]/@value', return_list=True
        )
        hid_name = self.get_by_xpath(
            tree, '//input[@type="hidden"]/@name', return_list=True
        )
        data = {
            "__VIEWSTATE": hid_val[0],
            "txtNameKeywords1": searchquery[:28],
            "txtNameKeywords2": "",
            "txtCompanyNumber": "",
            "btnSearch.x": "4",
            "btnSearch.y": "4",
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
        }
        tree = self.get_tree(url, headers=self.header, data=data, method="POST")
        names = self.get_by_xpath(
            tree,
            '//table[@id="tableSearchResults"]//tr[@class="row"]//td//a//text()[1] | //table[@id="tableSearchResults"]//tr[@class="rowalt"]//td//a//text()[1]',
            return_list=True,
        )
        if names:
            return names
        return []

    def reformat_date(self, date, format):
        date = datetime.datetime.strptime(date.strip(), format).strftime("%Y-%m-%d")
        return date

    def get_business_class(self, tree):
        res = []
        codes = self.get_by_xpath(
            tree,
            '//div/text()[contains(.,"Atividade Econômica Principal")]/../following-sibling::div//tr/td[1]/small/text()',
            return_list=True,
        )
        desc = self.get_by_xpath(
            tree,
            '//div/text()[contains(.,"Atividade Econômica Principal")]/../following-sibling::div//tr/td[2]/small/text()',
            return_list=True,
        )
        for c, d in zip(codes, desc):
            temp = {"code": c, "description": d}
            res.append(temp)
        return res

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
        # print(addr)
        # print(len(addr))
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

    def get_address(self, tree):
        addr = self.get_by_xpath(
            tree, '//span[@id="RegisteredOffice"]/..//text()', return_list=True
        )
        if addr:
            addr = [
                i
                for i in addr
                if i != ""
                and i != "Registered Office:"
                and i != "Registered Office in NL:"
            ]
            if addr[0] == "No address on file":
                return None

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
        # print(len(addr))
        # print(addr)
        if len(addr) == 4:
            temp["city"] = addr[-3]
            temp["streetAddress"] = addr[0]
        if len(addr) == 5:
            temp["city"] = addr[-4].split(",")[0]
            temp["streetAddress"] = addr[0]
        if len(addr) == 6:
            temp["city"] = addr[-4]
            temp["streetAddress"] = ", ".join(addr[:2])
        if len(addr) == 7:
            temp["city"] = addr[-4]
            temp["streetAddress"] = ", ".join(addr[:4])
        if len(addr) == 2:
            temp["city"] = addr[-1].split(",")[0]
            temp["streetAddress"] = addr[0]
        if len(addr) == 8:
            temp["city"] = addr[-4]
            temp["streetAddress"] = ", ".join(addr[:5])
        return temp

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
        if names:
            names = [i for i in names if i != ""]
        if names and dates:
            for name, date in zip(names, dates):
                temp = {"name": name, "valid_to": date}
                prev.append(temp)
        return prev

    def get_overview(self, link_name):
        # print(link_name)
        tree = self.get_tree(
            "https://cado.eservices.gov.nl.ca/CADOInternet/Main.aspx",
            headers=self.header,
        )
        self.get_tree(
            "https://cado.eservices.gov.nl.ca/CADOInternet/Company/CompanyMain.aspx",
            headers=self.header,
        )
        tree = self.get_tree(
            "https://cado.eservices.gov.nl.ca/CADOInternet/Company/CompanyNameNumberSearch.aspx",
            headers=self.header,
        )

        url = "https://cado.eservices.gov.nl.ca/CADOInternet/Company/CompanyNameNumberSearch.aspx"
        hid_val = self.get_by_xpath(
            tree, '//input[@type="hidden"]/@value', return_list=True
        )
        hid_name = self.get_by_xpath(
            tree, '//input[@type="hidden"]/@name', return_list=True
        )
        data = {
            "__VIEWSTATE": hid_val[0],
            "txtNameKeywords1": link_name[:28],
            "txtNameKeywords2": "",
            "txtCompanyNumber": "",
            "btnSearch.x": "4",
            "btnSearch.y": "4",
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
        }
        tree = self.get_tree(url, headers=self.header, data=data, method="POST")

        name = self.get_by_xpath(
            tree,
            '//table[@id="tableSearchResults"]//tr[@class="row"]//td//a//text()[1] | //table[@id="tableSearchResults"]//tr[@class="rowalt"]//td//a//text()[1]',
        )

        company = {}
        try:
            orga_name = self.get_by_xpath(
                tree,
                '//table[@id="tableSearchResults"]//tr[@class="row"]//td//a//text()[1] | //table[@id="tableSearchResults"]//tr[@class="rowalt"]//td//a//text()[1]',
            )
        except:
            return None
        if orga_name:
            company["vcard:organization-name"] = orga_name.strip()
        company["isDomiciledIn"] = "CA"
        hid_val = self.get_by_xpath(
            tree, '//input[@type="hidden"]/@value', return_list=True
        )
        hid_name = self.get_by_xpath(
            tree, '//input[@type="hidden"]/@name', return_list=True
        )
        comp_id = self.get_by_xpath(
            tree, f'//a/text()[contains(., "{link_name}")]/../@id'
        )
        idd = re.findall("_ctl\d+", comp_id)

        data = {
            "__EVENTTARGET": f"rptCompanyNameSearchResults:{idd[0]}:lbtCompanyNumber",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": hid_val[2],
            "txtNameKeywords1": link_name.replace(" ", "+"),
            "txtNameKeywords2": "",
            "txtCompanyNumber": "",
        }
        tree = self.get_tree(
            "https://cado.eservices.gov.nl.ca/CADOInternet/Company/CompanyNameNumberSearch.aspx",
            headers=self.header,
            method="POST",
            data=data,
        )
        self.check_create(
            tree, '//span[@id="lblStatus"]/text()', "hasActivityStatus", company
        )
        self.check_create(
            tree,
            '//span[@id="lblIncorporationDate"]/text()',
            "isIncorporatedIn",
            company,
        )
        other_id = self.get_by_xpath(tree, '//span[@id="lblCompanyNumber"]/text()')
        if other_id:
            company["identifiers"] = {"other_company_id_number": other_id}
        lf = self.get_by_xpath(tree, '//span[@id="lblFilingType"]/text()')
        if lf:
            company["lei:legalForm"] = {"code": "", "label": lf}
        prev = self.get_prev_names(tree)
        if prev:
            company["previous_names"] = prev
        company[
            "bst:registryURI"
        ] = "https://cado.eservices.gov.nl.ca/CadoInternet/Company/CompanyDetails.aspx"
        if company["identifiers"]:
            company["bst:registrationId"] = company["identifiers"][
                "other_company_id_number"
            ]
        reg_addr = self.get_address(tree)
        if reg_addr:
            company["mdaas:RegisteredAddress"] = reg_addr
        post_addr = self.get_post_addr(tree)
        if post_addr:
            if post_addr == "Same":
                company["mdaas:PostalAddress"] = company["mdaas:RegisteredAddress"]
            else:
                company["mdaas:PostalAddress"] = post_addr

        company["@source-id"] = self.NICK_NAME
        # print(company['mdaas:RegisteredAddress'])
        # print(company['mdaas:PostalAddress'])

        return company

    def get_officership(self, link_name):
        tree = self.get_tree(
            "https://cado.eservices.gov.nl.ca/CADOInternet/Main.aspx",
            headers=self.header,
        )
        self.get_tree(
            "https://cado.eservices.gov.nl.ca/CADOInternet/Company/CompanyMain.aspx",
            headers=self.header,
        )
        tree = self.get_tree(
            "https://cado.eservices.gov.nl.ca/CADOInternet/Company/CompanyNameNumberSearch.aspx",
            headers=self.header,
        )

        url = "https://cado.eservices.gov.nl.ca/CADOInternet/Company/CompanyNameNumberSearch.aspx"
        hid_val = self.get_by_xpath(
            tree, '//input[@type="hidden"]/@value', return_list=True
        )
        hid_name = self.get_by_xpath(
            tree, '//input[@type="hidden"]/@name', return_list=True
        )
        data = {
            "__VIEWSTATE": hid_val[0],
            "txtNameKeywords1": link_name[:28],
            "txtNameKeywords2": "",
            "txtCompanyNumber": "",
            "btnSearch.x": "4",
            "btnSearch.y": "4",
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
        }
        tree = self.get_tree(url, headers=self.header, data=data, method="POST")
        hid_val = self.get_by_xpath(
            tree, '//input[@type="hidden"]/@value', return_list=True
        )
        hid_name = self.get_by_xpath(
            tree, '//input[@type="hidden"]/@name', return_list=True
        )
        comp_id = self.get_by_xpath(
            tree, f'//a/text()[contains(., "{link_name}")]/../@id'
        )
        idd = re.findall("_ctl\d+", comp_id)

        data = {
            "__EVENTTARGET": f"rptCompanyNameSearchResults:{idd[0]}:lbtCompanyNumber",
            "__EVENTARGUMENT": "",
            "__VIEWSTATE": hid_val[2],
            "txtNameKeywords1": link_name.replace(" ", "+"),
            "txtNameKeywords2": "",
            "txtCompanyNumber": "",
        }
        tree = self.get_tree(
            "https://cado.eservices.gov.nl.ca/CADOInternet/Company/CompanyNameNumberSearch.aspx",
            headers=self.header,
            method="POST",
            data=data,
        )
        # self.check_tree(tree)

        names = self.get_by_xpath(
            tree,
            '//table[@id="tblCurrentDirectors"]//tr//tr[@class="row"]/td[@colspan="2"]/text()',
            return_list=True,
        )
        names = [i.replace("\r\n\t\t\t\t\t\t\t\t\t\t\t", " ") for i in names]
        off = []
        for n in names:
            home = {
                "name": n,
                "type": "individual",
                "officer_role": "Director",
                "occupation": "Director",
                "status": "Active",
                "information_source": self.base_url,
                "nformation_provider": "Newfoundland and Labrador: Department of Government Services",
            }
            off.append(home)
        return off
