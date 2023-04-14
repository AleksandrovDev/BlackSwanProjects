import datetime
import hashlib
import json
import re



from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages



class Handler(Extract, GetPages):
    base_url = 'https://www.kap.org.tr'
    NICK_NAME = 'kap.org.tr'
    fields = ['overview', 'officership', 'graph:shareholders', 'documents', 'Finacial_Information']

    header = {
        'User-Agent':
            'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/95.0.4638.69 Mobile Safari/537.36',
        'Accept':
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'accept-language': 'en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7'
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
        result_links = []
        url_list = ['https://www.kap.org.tr/en/bist-sirketler',
                    'https://www.kap.org.tr/en/sirketler/YK',
                    'https://www.kap.org.tr/en/sirketler/PYS',
                    'https://www.kap.org.tr/en/sirketler/BDK',
                    'https://www.kap.org.tr/en/sirketler/DCS',
                    'https://www.kap.org.tr/en/sirketler/DK',
                    'https://www.kap.org.tr/en/sirketler/KSE?kseSirketTipi=IGS']
        class_names_list = ['BIST Companies',
                            'Investment Firms',
                            'Portfolio Management Companies',
                            'Independent Audit Companies',
                            'Rating Companies',
                            'Other PDP Members',
                            'Old KAP Members']
        for url, className in zip(url_list, class_names_list):
            tree = self.get_tree(url, headers=self.header)
            links = self.get_by_xpath(tree,
                                      f'//div[@id="printAreaDiv"]//div//div/a/text()[contains(., "{searchquery}")]/../@href',
                                      return_list=True)

            if links:
                links = [self.base_url + link for link in links]
                for link in links:
                    if link not in result_links:
                        result_links.append(link + '?=' + className)
        return result_links

    def get_business_classifier(self, tree):
        final_list = []
        classifier_ids = self.get_by_xpath(tree,
                                           '//table//th/text()[contains(., "Activity Details")]/../../../..//tr/td[1]/text()',
                                           return_list=True)
        classifier_names = self.get_by_xpath(tree,
                                             '//table//th/text()[contains(., "Activity Details")]/../../../..//tr/td[2]/text()',
                                             return_list=True)

        ministry_ids = self.get_by_xpath(tree,
                                         '//table//th/text()[contains(., "Activities Registered Under")]/../../../..//td[1]/text()',
                                         return_list=True)
        ministry_names = self.get_by_xpath(tree,
                                           '//table//th/text()[contains(., "Activities Registered Under")]/../../../..//td[2]/text()',
                                           return_list=True)

        if classifier_ids and classifier_names:
            for i in range(len(classifier_ids)):
                temp_dict = {
                    'code': classifier_ids[i],
                    'description': classifier_names[i],
                    'label': ''
                }
                final_list.append(temp_dict)
        if ministry_ids and ministry_names:
            for i in range(len(ministry_ids)):
                temp_dict = {
                    'code': ministry_ids[i],
                    'description': ministry_names[i],
                    'label': ''
                }
                final_list.append(temp_dict)

        if final_list:
            return final_list
        else:
            return None

    def get_address(self, tree, postal=False):
        address = self.get_by_xpath(tree,
                                    '//div/text()[contains(., "Head Office Address")]/../following-sibling::div/text()')
        zip = re.findall('\d\d\d\d\d', address)
        city = address.split('/')[-1]
        temp_dict = {
            'streetAddress': ' '.join(address.split(' ')[:-1]),
            'country': 'Turkey',
            'fullAddress': address + ', Turkey'
        }
        if zip:
            temp_dict['zip'] = zip[-1]

        if city:
            temp_dict['city'] = city
        return temp_dict

    def reformat_date(self, date, format):
        date = datetime.datetime.strptime(date.strip(), format).strftime('%Y-%m-%d')
        return date

    def check_create(self, tree, xpath, title, dictionary, date_format=None):
        item = self.get_by_xpath(tree, xpath)
        if item:
            if date_format:
                item = self.reformat_date(item, date_format)
            dictionary[title] = item.strip()

    def get_regulator_address(self, tree):
        address = self.get_by_xpath(tree,
                                    '//div[@class="custom_contactinfo"]/p/text()',
                                    return_list=True)
        address[1] = address[1].split(' - ')[-1]
        temp_dict = {
            'fullAddress': ' '.join([i.strip() for i in address[1:-3]]),
            'city': address[3].split(',')[-1].strip(),
            'country': 'Saint Kitts and Nevis'
        }
        return temp_dict

    def get_prev_names(self, tree):
        previous_names = []

        company_id = \
        self.get_by_xpath(tree, '//div/text()[contains(., "Company Title Changes")]/../../@ng-click').split(',')[-1]
        id_clean = re.findall('\w+', company_id)[0]
        url = f'https://www.kap.org.tr/en/BildirimSgbfApproval/UNV/{id_clean}'
        tree = self.get_tree(url)

        
        js = tree.xpath('//text()')[0]
        if js:
            for i in json.loads(js):
                temp_dict = {
                    'name': i['basic']['companyName'],
                    'valid_to': self.reformat_date(i['basic']['publishDate'], '%d.%m.%y %H:%M')
                }
                previous_names.append(temp_dict)

        if previous_names:
            return previous_names
        return None

    def get_overview(self, link_name):
        className = link_name.split('?=')[-1]
        link = link_name.split('?=')[0]

        tree = self.get_tree(link, headers=self.header)

        company = {}

        try:
            orga_name = self.get_by_xpath(tree,
                                          '//h1/text()')
        except:
            return None
        if orga_name: company['vcard:organization-name'] = orga_name.strip()

        company['isDomiciledIn'] = 'TR'
        logo = self.get_by_xpath(tree, '//img[@class="comp-logo"]/@src')
        if logo: company['logo'] = self.base_url + logo

        prev_names = self.get_prev_names(tree)
        if prev_names:
            company['previous_names'] = prev_names

        self.check_create(tree,
                          '//div/text()[contains(., "Web-site")]/../following-sibling::div/text()',
                          'hasURL',
                          company)

        self.check_create(tree,
                          '//div/text()[contains(., "E-mail Adress")]/../following-sibling::div/text()',
                          'bst:email',
                          company)

        businessClassifier = self.get_by_xpath(tree, '//div/text()[contains(., "Sector of Company")]/../following-sibling::div/text()')
        if businessClassifier:
            company['bst:businessClassifier'] = [{
                'code': '',
                'description': businessClassifier + ', ' + className,
                'label': ''
            }]

        self.check_create(tree,
                          '//div/text()[contains(., "E-mail Adress")]/../following-sibling::div/text()',
                          'bst:email',
                          company)


        address = self.get_address(tree)
        if address: company['mdaas:RegisteredAddress'] = address

        general_url = link.replace('ozet', 'genel')
        general_tree = self.get_tree(general_url)



        

        self.check_create(general_tree,
                          '//div/text()[contains(., "Registration Date")]/../../following-sibling::div[1]/p/text()',
                          'isIncorporatedIn',
                          company, '%d/%m/%Y')

        self.check_create(general_tree,
                          '//div/text()[contains(., "Phone")]/../../following-sibling::div/div[2]/text()',
                          'tr-org:hasRegisteredPhoneNumber',
                          company)

        self.check_create(general_tree,
                          '//div/text()[contains(., "Phone")]/../../following-sibling::div/div[3]/text()',
                          'hasRegisteredFaxNumber',
                          company)


        vat = self.get_by_xpath(general_tree, '//div/text()[contains(., "Registration Date")]/../../following-sibling::div[3]/p/text()')
        if vat:
            company['identifiers'] = {
                'trade_register_number': vat,
                'vat_tax_number': self.get_by_xpath(general_tree, '//div/text()[contains(., "Registration Date")]/../../following-sibling::div[5]/p/text()')
            }


        company['bst:registryURI'] = link
        company['bst:registrationId'] = company['identifiers']['vat_tax_number']

        service = self.get_by_xpath(general_tree, '//div/text()[contains(., "Scope of Activities of Company")]/../../following-sibling::div/p/text()')


        if service:
            company['Service'] = {
                'serviceType': service
            }
        company['@source-id'] = self.NICK_NAME

        return company

    def get_officership(self, link):
        link = link.split('?=')[0]
        general_url = link.replace('ozet', 'genel')
        tree = self.get_tree(general_url)
        names = []
        positions = []


        officers1 = len(tree.xpath('//div/text()[contains(., "Investor Relations Department or Contact People")]/../../following-sibling::div/div/div')) - 1

        for officer in range(officers1):
            name = self.get_by_xpath(tree, f'//div/text()[contains(., "Investor Relations Department or Contact People")]/../../following-sibling::div/div/div[{officer + 2}]/div[1]/text()')
            position = self.get_by_xpath(tree, f'//div/text()[contains(., "Investor Relations Department or Contact People")]/../../following-sibling::div/div/div[{officer + 2}]/div[2]/text()')
            names.append(name)
            positions.append(position)

        officers2 = len(tree.xpath('//div/text()[contains(., "Board Members")]/../../following-sibling::div[1]/div/div/div[1]'))

        for officer in range(officers2):
            name = self.get_by_xpath(tree, f'//div/text()[contains(., "Board Members")]/../../following-sibling::div[1]/div/div[{officer + 2}]/div[1]/text()')
            position = self.get_by_xpath(tree, f'//div/text()[contains(., "Board Members")]/../../following-sibling::div[1]/div/div[{officer + 2}]/div[4]/text()')

            if name != 'Name-Surname' and name and name not in names:
                names.append(name)
                positions.append(position)



        officers3 = len(tree.xpath('//div/text()[contains(., "Board Members")]/../../following-sibling::div[3]/div/div/div[1]'))
        for officer in range(officers3):
            name = self.get_by_xpath(tree, f'//div/text()[contains(., "Board Members")]/../../following-sibling::div[3]/div/div[{officer + 2}]/div[1]/text()')
            position = self.get_by_xpath(tree, f'//div/text()[contains(., "Board Members")]/../../following-sibling::div[3]/div/div[{officer + 2}]/div[2]/text()')

            if name != 'Name-Surname' and name and name not in names:
                names.append(name)
                positions.append(position)

        officers = []

        for i in range(len(names)):
            temp_dict = {
                'name': names[i],
                'officer_role': positions[i],
                'status': 'Active',
                'occupation': positions[i],
                'information_source': 'https://www.kap.org.tr',
                'information_provider': 'KAP'
            }
            officers.append(temp_dict)

        return officers

    def get_shareholders(self, link):

        edd = {}
        shareholders = {}
        sholdersl1 = {}

        company = self.get_overview(link)
        company_name_hash = hashlib.md5(company['vcard:organization-name'].encode('utf-8')).hexdigest()


        link = link.split('?=')[0]
        general_url = link.replace('ozet', 'genel')
        tree = self.get_tree(general_url)
        try:
            holders = self.get_by_xpath(tree, '//div/text()[contains(., "Sharehold")]/../../following-sibling::div[1]/div/div/div[1]/text()', return_list=True)[1:-1]
            totalPercentages = self.get_by_xpath(tree, '//div/text()[contains(., "Sharehold")]/../../following-sibling::div[1]/div/div/div[3]/text()', return_list=True)[1:-1]
            votingPercentage = self.get_by_xpath(tree, '//div/text()[contains(., "Sharehold")]/../../following-sibling::div[1]/div/div/div[4]/text()', return_list=True)[1:-1]
            if totalPercentages[0] == 'TRY':
                totalPercentages = votingPercentage





            for i in range(len(holders)):
                holder_name_hash = hashlib.md5(holders[i].encode('utf-8')).hexdigest()
                shareholders[holder_name_hash] = {
                    "natureOfControl": "SHH",
                    "source": 'KAP',
                    "totalPercentage": totalPercentages[i],
                }
                if totalPercentages[i] != votingPercentage[i]:
                    shareholders[holder_name_hash]['votingPercentage']: votingPercentage[i]
                basic_in = {
                    "vcard:organization-name": holders[i],
                    'isDomiciledIn': 'TR'
                }
                sholdersl1[holder_name_hash] = {
                    "basic": basic_in,
                    "shareholders": {}
                }
        except:
            pass

        edd[company_name_hash] = {
            "basic": company,
            "entity_type": "C",
            "shareholders": shareholders
        }
        print(sholdersl1)
        return edd, sholdersl1

    def get_documents(self, link):
        documents = {}
        link = link.split('?=')[0]
        tree = self.get_tree(link)
        article = self.get_by_xpath(tree, '//div/text()[contains(., "Articles of Association")]/../../@href')
        if article != '
            documents['description'] = 'Articles of Association'
            documents['url'] = self.base_url + article
        return documents

    def get_financial_information(self, link):
        fin = {}
        link = link.split('?=')[0]
        general_url = link.replace('ozet', 'genel')
        tree = self.get_tree(general_url)
        paidIn = self.get_by_xpath(tree, '//div/text()[contains(., "Paid-in")]/../../following-sibling::div[1]/p/text()')

        issued = self.get_by_xpath(tree, '//div/text()[contains(., "Authorized Capital")]/../../following-sibling::div[1]/p/text()')
        if paidIn:
            fin['Summary_Financial_data'] = [{
                'source': 'KAP',
                'summary': {
                    'balance_sheet': {
                        'authorized_share_capital': str(paidIn),
                        'paid_up_share_capital': '',
                        'issued_share_capital': str(issued),
                    }
                }
            }]
        return fin







