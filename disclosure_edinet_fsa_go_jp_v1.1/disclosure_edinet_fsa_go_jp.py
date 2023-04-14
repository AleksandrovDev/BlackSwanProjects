import datetime
import hashlib
import json
import re


from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = "http://www.disclosure.edinet-fsa.go.jp"
    NICK_NAME = "disclosure.edinet-fsa.go.jp"
    fields = ["overview", "documents"]

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
            "https://disclosure.edinet-fsa.go.jp/E01EW/BLMainController.jsp?uji.verb=W1E63010CXW1E6A010DSPSch&uji.bean=ee.bean.parent.EECommonSearchBean&TID=W1E63011&PID=W1E63010&SESSIONKEY=1640674393419&lgKbn=2&pkbn=0&skbn=0&dskb=&dflg=0&iflg=0&preId=1&row=100&idx=0&syoruiKanriNo=&mul=%E9%8A%80%E8%A1%8C&fls=on&cal=1&era=R&yer=&mon=&pfs=4",
            headers=self.header,
        )
        url = f"https://disclosure.edinet-fsa.go.jp/E01EW/BLMainController.jsp?uji.verb=W1E63010CXW1E6A010DSPSch&uji.bean=ee.bean.parent.EECommonSearchBean&TID=W1E63011&PID=W1E63010&SESSIONKEY=1640674393419&lgKbn=2&pkbn=0&skbn=0&dskb=&dflg=0&iflg=0&preId=1&row=100&idx=0&syoruiKanriNo=&mul={searchquery}&fls=on&cal=1&era=R&yer=&mon=&pfs=4"
        tree = self.get_tree(url, headers=self.header)
        names = self.get_by_xpath(tree, "//tr/td[3]/div/text()[1]", return_list=True)
        comp_names = self.get_by_xpath(
            tree, "//tr/td[4]/div/text()[1]", return_list=True
        )
        docs_no = self.get_by_xpath(tree, "//tr/td[2]/a/@onclick", return_list=True)

        if names:
            names = [i.replace("\r\n\r\n\t\t\t\t", "") for i in names]
            names = [i.strip() for i in names]
            names = [i.split("/")[0] for i in names if i != ""]
        if docs_no:
            docs_no = [i.split("return clickDocNameForNotPaper('")[-1] for i in docs_no]
            docs_no = [i.split("'")[0] for i in docs_no]
        res_list = []
        for name in names:
            if name not in res_list:
                res_list.append(name)
        return res_list

    def get_overview(self, link_name):
        company_name = link_name
        tree = self.get_tree(
            "https://disclosure.edinet-fsa.go.jp/E01EW/BLMainController.jsp?uji.verb=W1E63010CXW1E6A010DSPSch&uji.bean=ee.bean.parent.EECommonSearchBean&TID=W1E63011&PID=W1E63010&SESSIONKEY=1640674393419&lgKbn=2&pkbn=0&skbn=0&dskb=&dflg=0&iflg=0&preId=1&row=100&idx=0&syoruiKanriNo=&mul=%E9%8A%80%E8%A1%8C&fls=on&cal=1&era=R&yer=&mon=&pfs=4",
            headers=self.header,
        )
        url = f"https://disclosure.edinet-fsa.go.jp/E01EW/BLMainController.jsp?uji.verb=W1E63010CXW1E6A010DSPSch&uji.bean=ee.bean.parent.EECommonSearchBean&TID=W1E63011&PID=W1E63010&SESSIONKEY=1640674393419&lgKbn=2&pkbn=0&skbn=0&dskb=&dflg=0&iflg=0&preId=1&row=100&idx=0&syoruiKanriNo=&mul={company_name}&fls=on&cal=1&era=R&yer=&mon=&pfs=4"

        tree = self.get_tree(url, headers=self.header)
        names = self.get_by_xpath(tree, "//tr/td[3]/div/text()[1]", return_list=True)[
            -1
        ]
        comp_name_text = self.get_by_xpath(tree, "//tr/td[4]/text()", return_list=True)
        comp_name = self.get_by_xpath(tree, "//tr/td[4]/a/text()", return_list=True)[0]
        docs_no = self.get_by_xpath(tree, "//tr/td[2]/a/@onclick", return_list=True)
        if comp_name_text:
            comp_name_text = [i for i in comp_name_text if i != ""]
            comp_name_text = [i.replace("\r\n\t\t\t/", "") for i in comp_name_text]
        if docs_no:
            docs_no = [i.split("return clickDocNameForNotPaper('")[-1] for i in docs_no]
            docs_no = [i.split("'")[0] for i in docs_no]
        doc_no = docs_no[-1]

        company = {}

        try:
            if comp_name_text:
                orga_name = comp_name_text[0].split("/")[0]
            else:
                orga_name = comp_name
        except:
            return None
        if orga_name:
            company["vcard:organization-name"] = orga_name.strip()
        company["isDomiciledIn"] = "JP"
        company["bst:registryURI"] = url

        company["bst:registrationId"] = company_name

        url = f"https://disclosure.edinet-fsa.go.jp/E01EW/BLMainController.jsp?uji.verb=W00Z1010initialize&uji.bean=ek.bean.EKW00Z1010Bean&TID=W00Z1010&PID=W1E63011&SESSIONKEY=1640778503882&lgKbn=2&pkbn=0&skbn=1&dskb=&askb=&dflg=0&iflg=0&preId=1&mul=%E9%8A%80%E8%A1%8C&fls=on&cal=1&era=R&yer=&mon=&pfs=4&row=100&idx=0&str=&kbn=1&flg=&syoruiKanriNo={doc_no}"

        tree = self.get_tree(url, headers=self.header)
        script = tree.xpath("//script/text()")
        link = re.findall('formObject.action = ".+"', script[0])[0]
        post_link = (
            "https://disclosure.edinet-fsa.go.jp"
            + link.split('formObject.action = "')[-1][:-2]
        )
        data = {
            "PID": "W00Z1010",
            "syoruiKanriNo": doc_no,
            "publicKbn": "1",
            "riyousyaKbn": "E",
            "SESSIONKEY": "1640778503882",
            "privateDocumentIndicateFlg": "",
            "teisyutuEngCheckResult": "false",
            "keyword1": "",
            "keyword2": "",
            "keyword3": "",
            "keyword4": "",
            "keyword5": "",
            "be.keyword": "",
            "be.keyword": "",
            "be.keyword": "",
            "be.keyword": "",
            "be.keyword": "",
            "lgKbn": "2",
            "uji.verb": "W00Z1010initialize",
            "uji.bean": "ek.bean.EKW00Z1010Bean",
            "TID": "W00Z1010_01",
        }
        tree = self.get_tree(post_link, headers=self.header, method="POST", data=data)
        h1 = self.get_by_xpath(tree, "//h1/text()")
        try:
            id_c = re.findall("\d\d\d\d\d\d+", h1)[0]
            if id_c:
                company["identifiers"] = {"other_company_id_number": id_c}
        except:
            pass

        url = f"https://disclosure.edinet-fsa.go.jp/E01EW/BLMainController.jsp?PID=W00Z1010&syoruiKanriNo={doc_no}&publicKbn=1&riyousyaKbn=E&SESSIONKEY=1640800180502&privateDocumentIndicateFlg=&teisyutuEngCheckResult=false&keyword1=&keyword2=&keyword3=&keyword4=&keyword5=&be.keyword=&be.keyword=&be.keyword=&be.keyword=&be.keyword=&lgKbn=2&uji.verb=W00Z1010init&uji.bean=ek.bean.EKW00Z1010Bean&TID=W00Z1010_10"
        tree = self.get_tree(url, headers=self.header)
        script = tree.xpath("//script/text()")

        bean_id = re.findall("be\.bean\.id=\d+", script[0])[0]
        download_id = re.findall("/E01EW/download\?\d+", script[0])[0]
        bean_id = bean_id.split("=")[-1]
        download_id = download_id.split("?")[-1]

        post2_link = "https://disclosure.edinet-fsa.go.jp/E01EW/download?" + download_id

        data = {
            "uji.verb": "W00Z1010Document",
            "be.bean.id": bean_id,
            "be.target": "2",
            "be.request": "0",
            "SESSIONKEY": "1640778503882",
            "PID": "W00Z1010",
        }
        tree = self.get_tree(post2_link, headers=self.header, method="POST", data=data)

        phones = self.get_by_xpath(
            tree,
            '//td/p//text()[contains(., "【電話番号】")]/../../following-sibling::td/p//text()',
            return_list=True,
        )
        if not phones:
            phones = self.get_by_xpath(
                tree,
                '//td/p//text()[contains(., "【電話番号】")]/../../../following-sibling::td/p//text()',
                return_list=True,
            )

        if phones:
            phones = [i for i in phones if i != ""]
            phones = ["".join(re.findall("\d", i)) for i in phones]
            phones = [i for i in phones if i != ""]

            company["tr-org:hasRegisteredPhoneNumber"] = "".join(
                re.findall("\d", phones[-1])
            )
        addres = self.get_by_xpath(
            tree,
            '//td/p//text()[contains(., "【最寄りの連絡場所】")]/../../following-sibling::td//p//text()',
            return_list=True,
        )
        if not addres:
            addres = self.get_by_xpath(
                tree,
                '//td/p//text()[contains(., "【最寄りの連絡場所】")]/../../../following-sibling::td//p//text()',
                return_list=True,
            )
        if not addres:
            addres = self.get_by_xpath(
                tree,
                '//td/p//text()[contains(., "連絡場所")]/../../../following-sibling::td//p//text()',
                return_list=True,
            )
        if not addres:
            addres = self.get_by_xpath(
                tree,
                '//td/p//text()[contains(., "連絡場所")]/../../following-sibling::td//p//text()',
                return_list=True,
            )

        if addres:
            company["mdaas:RegisteredAddress"] = {
                "country": "Japan",
                "fullAddress": " ".join(addres),
            }
        eng_name = self.get_by_xpath(
            tree,
            '//td/p//text()[contains(., "【英訳名】")]/../../following-sibling::td//p//text()',
            return_list=True,
        )
        if not eng_name:
            eng_name = self.get_by_xpath(
                tree,
                '//td/p//text()[contains(., "【英訳名】")]/../../../following-sibling::td//p//text()',
                return_list=True,
            )

        company["@source-id"] = self.NICK_NAME

        return company

    def get_documents(self, link_name):
        company_name = link_name
        tree = self.get_tree(
            "https://disclosure.edinet-fsa.go.jp/E01EW/BLMainController.jsp?uji.verb=W1E63010CXW1E6A010DSPSch&uji.bean=ee.bean.parent.EECommonSearchBean&TID=W1E63011&PID=W1E63010&SESSIONKEY=1640674393419&lgKbn=2&pkbn=0&skbn=0&dskb=&dflg=0&iflg=0&preId=1&row=100&idx=0&syoruiKanriNo=&mul=%E9%8A%80%E8%A1%8C&fls=on&cal=1&era=R&yer=&mon=&pfs=4",
            headers=self.header,
        )
        url = f"https://disclosure.edinet-fsa.go.jp/E01EW/BLMainController.jsp?uji.verb=W1E63010CXW1E6A010DSPSch&uji.bean=ee.bean.parent.EECommonSearchBean&TID=W1E63011&PID=W1E63010&SESSIONKEY=1640674393419&lgKbn=2&pkbn=0&skbn=0&dskb=&dflg=0&iflg=0&preId=1&row=100&idx=0&syoruiKanriNo=&mul={company_name}&fls=on&cal=1&era=R&yer=&mon=&pfs=4"

        tree = self.get_tree(url, headers=self.header)
        names = self.get_by_xpath(tree, "//tr/td[3]/div/text()[1]", return_list=True)[
            -1
        ]
        comp_name_text = self.get_by_xpath(tree, "//tr/td[4]/text()", return_list=True)[
            0
        ]
        comp_name = self.get_by_xpath(tree, "//tr/td[4]/a/text()", return_list=True)[0]
        docs_no = self.get_by_xpath(tree, "//tr/td[2]/a/@onclick", return_list=True)
        if docs_no:
            docs_no = [i.split("return clickDocNameForNotPaper('")[-1] for i in docs_no]
            docs_no = [i.split("'")[0] for i in docs_no]
        doc_no = docs_no[-1]

        links = self.get_by_xpath(tree, "//tr/td[6]/div/a/@href", return_list=True)
        dates = self.get_by_xpath(tree, "//tr/td[1]/div/text()", return_list=True)

        dates = [i.split("\u00a0")[0] for i in dates if i != ""]

        dates = [f'2021-{date.split(".")[1]}-{date.split(".")[2]}' for date in dates]

        names = self.get_by_xpath(tree, "//tr/td[2]/a/text()", return_list=True)

        docs = []
        for date, link, name in zip(dates, links, names):
            temp_dict = {"date": date, "description": name, "url": self.base_url + link}
            docs.append(temp_dict)
        return docs
