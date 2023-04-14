import time
import unicodedata
import sys

sys.path.append("/home/ubuntu/environment/be-sources/data-sources-id-gen1-srv")

from src.bstsouecepkg.extract import GetPages, Extract, Parse


class Handler(Extract, GetPages, Parse):
    base_url = "https://www.dnb.com"
    NICK_NAME = "dnb.com"
    fields = ["overview", "officership", "documents"]

    searchUrl1 = "https://www.dnb.com/de-de/firmensuche/?search={}&comid="

    browser_header = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.88 Mobile Safari/537.36",
    }

    proxies = {
        "https": "http://189.193.225.6:999",
    }

    def getpages(self, searchquery):
        link_list = []
        searchquery = searchquery.replace(" ", "+")
        searchUrl1_de = (
            f"https://www.dnb.com/de-de/firmensuche/?search={searchquery}&comid="
        )

        params = {"search": searchquery, "comid": ""}

        try:
            content = self.get_content(
                searchUrl1_de,
                headers=self.browser_header,
                proxies=self.proxies,
                verify=False,
            )

            tree = self.get_tree(
                searchUrl1_de, headers=self.browser_header, proxies=self.proxies
            )
        except Exception as e:
            print(f"Error in getting responses {e}")
            pass

        try:
            link = tree.xpath('//*[@class="hover--state"]/@href')

            for row in link:
                url = "https://www.dnb.com" + row

                link_list.append(url)

        except Exception as e:
            print(f"Error in getting links {e}")
            pass

        print(link_list)
        return link_list

    def get_overview(self, link):
        company = {}
        print(link)
        tree = self.get_tree(link, headers=self.browser_header)

        try:
            org_name = tree.xpath('//h1[@class="company--name"]/text()')[0].strip()
            company["vcard:organization-name"] = org_name
        except Exception as e:
            print(e)

        company["bst:sourceLinks"] = [link]
        company["bst:registryURI"] = link

        try:
            bst_classifier = []
            classifier = tree.xpath(
                '//div[contains(text(),"Branche")]/following-sibling::div//p/text()'
            )[0]
            descrip = (
                unicodedata.normalize("NFKD", classifier).encode("ascii", "ignore")
            ).decode("utf-8")
            bus_classifier = {"code": "", "description": descrip, "label": ""}
            bst_classifier.append(bus_classifier)
            if len(bus_classifier):
                company["bst:businessClassifier"] = bst_classifier
        except:
            pass

        try:
            company_number = tree.xpath('//*[@class="company--subtitle"]//text()')[0]
            id_number = company_number.replace("HR-Nr.:", "").strip()
            if len(company_number):
                identifier = {"other_company_id_number": id_number}
                company["identifiers"] = identifier
        except:
            pass

        try:
            company_address = tree.xpath(
                '//div[contains(text(),"Adresse")]/following-sibling::div/text()'
            )[0]
            address = company_address.strip("\n")
            reg_address = {
                "zip": address.split(" ", 1)[0],
                "country": "Germany",
                "city": address.split(" ", 1)[1],
                "fullAddress": address + ", " + "Germany",
            }
            if address:
                company["mdaas:RegisteredAddress"] = reg_address
        except:
            pass

        company["isDomiciledIn"] = "DE"

        try:
            website = tree.xpath(
                '//*[contains(text(),"Homepage")]/following-sibling::div//text()'
            )[0]
            if len(website):
                company["hasURL"] = website
        except:
            pass

        try:
            size = tree.xpath(
                '//*[contains(text(),"Anzahl der Mitarbeiter")]/following-sibling::div//text()'
            )[0]
            if len(size):
                company["size"] = size
        except:
            pass

        try:
            source_date = tree.xpath(
                '//*[contains(text(),"Letzte Bilanz von")]/following-sibling::div//text()'
            )[0]
            if len(source_date):
                company["sourceDate"] = source_date
        except:
            pass

        try:
            el = tree.xpath(
                '//*[contains(text(),"Firmenname")]/following-sibling::div//text()'
            )[0]
            company["vcard:organization-tradename"] = el
        except:
            pass

        return company

    def get_officership(self, link):
        officers = []
        print(link)
        tree = self.get_tree(
            link, headers=self.browser_header, proxies=self.proxies, verify=False
        )

        try:
            role = tree.xpath('//*[@title="Name des Geschäftsführers"]/text()')[0]

            name = tree.xpath(
                '//*[@title="Name des Geschäftsführers"]/following-sibling::div/text()'
            )[0]
            officer = {
                "name": name,
                "type": "individual",
                "officer_role": role,
                "occupation": role,
                "information_source": self.base_url + "/de-de/",
                "information_provider": "Dun and Bradstreet (Germany)",
            }
            officers.append(officer)
        except:
            pass

        return officers

    def get_documents(self, link):
        document = {}
        tree = self.get_tree(
            link, headers=self.browser_header, proxies=self.proxies, verify=False
        )

        try:
            url = (
                "https://www.dnb.com"
                + tree.xpath('//a[contains(text(),"Beispieldaten ansehen")]/@href')[0]
            )
            if len(url):
                document["description"] = "Beispieldaten ansehen"
                document["url"] = url
        except:
            pass

        try:
            url2 = (
                "https://www.dnb.com"
                + tree.xpath('//a[contains(text(),"Beispielbericht öffnen")]/@href')[0]
            )
            if len(url2):
                document["description"] = "Beispielbericht öffnen"
                document["url"] = url2
        except:
            pass

        return document
