import datetime
import hashlib
import json
import re


from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "https://www.sijilat.bh/"
    NICK_NAME = "sijilat.bh"
    fields = ["overview", "officership"]

    header = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
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

    def getpages(self, searchquery):
        res_list = []
        page_flags = ["BU", "BA", "GO", "PR", "IN", "PN"]

        for flag in page_flags:
            data = {"hid_page_flag": f"{flag}", "hid_menu_id": "01140000"}
            tree = self.get_tree(
                "https://www.sijilat.bh/APP/PUB/public_enty_list.aspx",
                headers=self.header,
                verify=False,
                data=data,
                method="POST",
            )
            if flag == "PR":
                tree = self.get_tree(
                    "https://www.sijilat.bh/APP/PUB/public_pb_list.aspx",
                    headers=self.header,
                    verify=False,
                    data=data,
                    method="POST",
                )
            hidden = tree.xpath('//input[@type="hidden"]/@value')[1:]
            name = tree.xpath('//input[@type="hidden"]/@name')[1:]
            data = dict(zip(name, hidden))

            data["ctl00$uc_header_app1$uc_login_topbar1$btnLoggedSearch1"] = "Search.."

            data[
                "__EVENTTARGET"
            ] = "ctl00$BodyPlaceHolder$UC_Biz_Pager1$View1000RecordsList"
            if flag == "IN":
                data[
                    "__EVENTTARGET"
                ] = "ctl00$BodyPlaceHolder$UC_Biz_Pager2$View1000RecordsList"
            tree = self.get_tree(
                "https://www.sijilat.bh/APP/PUB/public_enty_list.aspx",
                headers=self.header,
                verify=False,
                data=data,
                method="POST",
            )
            if flag == "PR":
                tree = self.get_tree(
                    "https://www.sijilat.bh/APP/PUB/public_pb_list.aspx",
                    headers=self.header,
                    verify=False,
                    data=data,
                    method="POST",
                )
            names = self.get_by_xpath(
                tree,
                f'//div[@class="bs_gridArea"]//tr//td[1]/text()[contains(translate(., "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{searchquery.lower()}")]',
                return_list=True,
            )
            if names:
                names = [i + "?=" + flag for i in names]
                res_list.extend(names)
        return res_list

    def get_overview(self, link_name):
        company_name = link_name.split("?=")[0]
        flag = link_name.split("?=")[-1]
        data = {"hid_page_flag": f"{flag}", "hid_menu_id": "01140000"}
        tree = self.get_tree(
            "https://www.sijilat.bh/APP/PUB/public_enty_list.aspx",
            headers=self.header,
            verify=False,
            data=data,
            method="POST",
        )
        if flag == "PR":
            tree = self.get_tree(
                "https://www.sijilat.bh/APP/PUB/public_pb_list.aspx",
                headers=self.header,
                verify=False,
                data=data,
                method="POST",
            )
        hidden = tree.xpath('//input[@type="hidden"]/@value')[1:]
        name = tree.xpath('//input[@type="hidden"]/@name')[1:]
        data = dict(zip(name, hidden))
        data["ctl00$uc_header_app1$uc_login_topbar1$btnLoggedSearch1"] = "Search.."

        data[
            "__EVENTTARGET"
        ] = "ctl00$BodyPlaceHolder$UC_Biz_Pager1$View1000RecordsList"
        if flag == "IN":
            data[
                "__EVENTTARGET"
            ] = "ctl00$BodyPlaceHolder$UC_Biz_Pager2$View1000RecordsList"
        tree = self.get_tree(
            "https://www.sijilat.bh/APP/PUB/public_enty_list.aspx",
            headers=self.header,
            verify=False,
            data=data,
            method="POST",
        )
        if flag == "PR":
            tree = self.get_tree(
                "https://www.sijilat.bh/APP/PUB/public_pb_list.aspx",
                headers=self.header,
                verify=False,
                data=data,
                method="POST",
            )
        base_row = f'//div[@class="bs_gridArea"]//tr//td[1]/text()[contains(., "{company_name}")]/../..'

        company = {}

        try:
            orga_name = self.get_by_xpath(tree, base_row + "/td[1]/text()")
        except:
            return None

        headers = self.get_by_xpath(
            tree, f'//div[@class="bs_gridArea"]//tr[1]//th//text()', return_list=True
        )
        headers = [i for i in headers if i != ""]

        if orga_name:
            company["vcard:organization-name"] = orga_name.strip()
        company["isDomiciledIn"] = "BH"
        if "Name (Arabic)" in headers:
            loc_name = self.get_by_xpath(
                tree,
                f'//div[@class="bs_gridArea"]//tr[1]//th//text()[contains(., "Name (Arabic)")]/../../../../../..//tr//td/text()[contains(., "{company_name}")]/../../td[{headers.index("Name (Arabic)") + 1}]/text()',
            )
            if loc_name and loc_name != "N/A":
                company["localName"] = loc_name
        if "Website" in headers:
            url = self.get_by_xpath(
                tree,
                f'//div[@class="bs_gridArea"]//tr[1]//th//text()[contains(., "Website")]/../../../../../..//tr//td/text()[contains(., "{company_name}")]/../../td[{headers.index("Website") + 1}]/text()',
            )
            if url:
                company["hasURL"] = url
        if "Email" in headers:
            email = self.get_by_xpath(
                tree,
                f'//div[@class="bs_gridArea"]//tr[1]//th//text()[contains(., "Email")]/../../../../../..//tr//td/text()[contains(., "{company_name}")]/../../td[{headers.index("Email") + 1}]/text()',
            )
            if email and email != "N/A":
                email = email.replace("\\", "/")
                email = email.replace("/", " ")
                company["bst:email"] = email.split(" ")[0].strip()

        if "Phone No." in headers:
            phone = self.get_by_xpath(
                tree,
                f'//div[@class="bs_gridArea"]//tr[1]//th//text()[contains(., "Phone No.")]/../../../../../..//tr//td/text()[contains(., "{company_name}")]/../../td[{headers.index("Phone No.") + 1}]/text()',
            )
            if phone and phone != "N/A":
                phone = phone.replace(",", "/")
                company["tr-org:hasRegisteredPhoneNumber"] = phone.split("/")[0].strip()
        if "Fax No." in headers:
            fax = self.get_by_xpath(
                tree,
                f'//div[@class="bs_gridArea"]//tr[1]//th//text()[contains(., "Fax No.")]/../../../../../..//tr//td/text()[contains(., "{company_name}")]/../../td[{headers.index("Fax No.") + 1}]/text()',
            )
            if fax and fax != "N/A":
                company["hasRegisteredFaxNumber"] = fax
        if "Incubator / Accelerator" in headers:
            serv = self.get_by_xpath(
                tree,
                f'//div[@class="bs_gridArea"]//tr[1]//th//text()[contains(., "Incubator / Accelerator")]/../../../../../..//tr//td/text()[contains(., "{company_name}")]/../../td[{headers.index("Incubator / Accelerator") + 1}]/text()',
            )
            if serv:
                company["Service"] = {"areaServed": "", "serviceType": serv}
        company["regulationStatus"] = "Authorised"
        company["regulator_name"] = "Sijilat Commercial Registration Portal"
        company["regulator_url"] = self.base_url
        company["@source-id"] = self.NICK_NAME

        return company

    def get_officership(self, link_name):
        company_name = link_name.split("?=")[0]
        flag = link_name.split("?=")[-1]
        if flag != "IN":
            return []
        data = {"hid_page_flag": f"{flag}", "hid_menu_id": "01140000"}
        tree = self.get_tree(
            "https://www.sijilat.bh/APP/PUB/public_enty_list.aspx",
            headers=self.header,
            verify=False,
            data=data,
            method="POST",
        )
        if flag == "PR":
            tree = self.get_tree(
                "https://www.sijilat.bh/APP/PUB/public_pb_list.aspx",
                headers=self.header,
                verify=False,
                data=data,
                method="POST",
            )
        hidden = tree.xpath('//input[@type="hidden"]/@value')[1:]
        name = tree.xpath('//input[@type="hidden"]/@name')[1:]
        data = dict(zip(name, hidden))
        data["ctl00$uc_header_app1$uc_login_topbar1$btnLoggedSearch1"] = "Search.."

        data[
            "__EVENTTARGET"
        ] = "ctl00$BodyPlaceHolder$UC_Biz_Pager1$View1000RecordsList"
        if flag == "IN":
            data[
                "__EVENTTARGET"
            ] = "ctl00$BodyPlaceHolder$UC_Biz_Pager2$View1000RecordsList"
        tree = self.get_tree(
            "https://www.sijilat.bh/APP/PUB/public_enty_list.aspx",
            headers=self.header,
            verify=False,
            data=data,
            method="POST",
        )
        if flag == "PR":
            tree = self.get_tree(
                "https://www.sijilat.bh/APP/PUB/public_pb_list.aspx",
                headers=self.header,
                verify=False,
                data=data,
                method="POST",
            )
        base_row = f'//div[@class="bs_gridArea"]//tr//td[1]/text()[contains(., "{company_name}")]/../..'
        headers = self.get_by_xpath(
            tree, f'//div[@class="bs_gridArea"]//tr[1]//th//text()', return_list=True
        )
        headers = [i for i in headers if i != ""]
        officers = []

        if "Contact Person" in headers:
            names = self.get_by_xpath(
                tree,
                f'//div[@class="bs_gridArea"]//tr[1]//th//text()[contains(., "Contact Person")]/../../../../../..//tr//td/text()[contains(., "{company_name}")]/../../td[{headers.index("Contact Person") + 1}]/text()',
            )
            if names:
                names = names.split("/")
                names = [i.strip() for i in names]

        if "Position" in headers:
            pos = self.get_by_xpath(
                tree,
                f'//div[@class="bs_gridArea"]//tr[1]//th//text()[contains(., "Position")]/../../../../../..//tr//td/text()[contains(., "{company_name}")]/../../td[{headers.index("Position") + 1}]/text()',
            )
            if pos:
                pos = pos.split("/")
                pos = [i.strip() for i in pos]
        if len(names) == len(pos) and names and pos:
            for name, poss in zip(names, pos):
                temp_dict = {
                    "name": name,
                    "type": "Individual",
                    "officer_role": poss,
                    "status": "Active",
                    "occupation": poss,
                    "information_source": self.base_url,
                    "information_provider": "Sijilat Commercial Registration Portal",
                }
                officers.append(temp_dict)
        return officers
