import datetime
import hashlib
import json
import re



from src.bstsouecepkg.extract import Extract
from src.bstsouecepkg.extract import GetPages


class Handler(Extract, GetPages):
    base_url = 'https://charities.sos.ms.gov'
    NICK_NAME = base_url.split('//')[-1]
    fields = ['overview', 'Financial_Information']
    overview = {}
    tree = None
    api = None

    header = {
        'User-Agent':
            'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0',
        'Accept':
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9;application/json',
        'accept-language': 'en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7',
        'Content-Type': 'application/json'
    }

    def getResultListFromResponse(self, response, type):
        if type == 'API':
            data = json.loads(response.content)
            result = []
            try:
                companies = data['data'][1]['data']['rowData']
                for company in companies:
                    code = company['cellData'][1]['value']
                    
                    
                    result.append(code)
                return result
            except:
                return None

    def getpages(self, searchquery):
        result = []
        data = {
            "searchType": "Charity_Services_IFSSearchResults",
            "entityName": searchquery,
            "fileNumber": "",
            "filingClassId": "00000000-0000-0000-0000-000000000000"
        }
        url = 'https://charities.sos.ms.gov/online/Services/Common/IFSServices.asmx/ExecuteSearch'
        self.get_working_tree_api(url, 'api', method='POST', data=data)
        g = self.api['d']
        d = json.loads(g)
        self.api = d['Table']
        for company in self.api:
            if searchquery in company['EntityName']:
                result.append(company['EntityName'])
        return result

    def get_by_xpath(self, xpath):
        try:
            el = self.tree.xpath(xpath)
        except Exception as e:
            print(e)
            return None
        if el:
            el = [i.strip() for i in el]
            el = [i for i in el if i != '']
            return el
        else:
            return None

    def reformat_date(self, date, format):
        date = datetime.datetime.strptime(date.strip(), format).strftime('%Y-%m-%d')
        return date

    def get_business_class(self, xpathCodes=None, xpathDesc=None, xpathLabels=None):
        res = []
        if xpathCodes:
            codes = self.get_by_xpath(xpathCodes)
        if xpathDesc:
            desc = self.get_by_xpath(xpathDesc)
        if xpathLabels:
            labels = self.get_by_xpath(xpathLabels)

        for c, d, l in zip(codes, desc, labels):
            temp = {
                'code': c.split(' (')[0],
                'description': d,
                'label': l.split('(')[-1].split(')')[0]
            }
            res.append(temp)
        if res:
            self.overview['bst:businessClassifier'] = res

    def get_post_addr(self, tree):
        addr = self.get_by_xpath(tree, '//span[@id="lblMailingAddress"]/..//text()', return_list=True)
        if addr:
            addr = [i for i in addr if
                    i != '' and i != 'Mailing Address:' and i != 'Inactive' and i != 'Registered Office outside NL:']
            if addr[0] == 'No address on file':
                return None
            if addr[0] == 'Same as Registered Office' or addr[0] == 'Same as Registered Office in NL':
                return 'Same'
            fullAddr = ', '.join(addr)
            temp = {
                'fullAddress': fullAddr if 'Canada' in fullAddr else (fullAddr + ' Canada'),
                'country': 'Canada',

            }
            replace = re.findall('[A-Z]{2},\sCanada,', temp['fullAddress'])
            if not replace:
                replace = re.findall('[A-Z]{2},\sCanada', temp['fullAddress'])
            if replace:
                torepl = replace[0].replace(',', '')
                temp['fullAddress'] = temp['fullAddress'].replace(replace[0], torepl)
            try:
                zip = re.findall('[A-Z]\d[A-Z]\s\d[A-Z]\d', fullAddr)
                if zip:
                    temp['zip'] = zip[0]
            except:
                pass
        
        
        if len(addr) == 4:
            temp['city'] = addr[-3]
            temp['streetAddress'] = addr[0]
        if len(addr) == 5:
            temp['city'] = addr[-4]
            temp['streetAddress'] = addr[0]
        if len(addr) == 6:
            temp['city'] = addr[-4]
            temp['streetAddress'] = ', '.join(addr[:2])

        return temp

    def get_address(self, xpath=None, zipPattern=None, key=None, returnAddress=False, addr=None):
        if xpath:
            addr = self.get_by_xpath(xpath)
        if key:
            addr = self.get_by_api(key)
        if addr:
            if len(addr) > 1:
                splittedAddr = addr
                addr = ', '.join(addr)
            else:
                addr = addr[0]
            
            if '\n' in addr:
                splitted_addr = addr.split('\n')
            if ', ' in addr:
                splitted_addr = addr.split(', ')

            addr = addr.replace('\n', ' ')
            addr = addr[0] if type(addr) == list else addr
            temp = {
                'fullAddress': addr,
                'country': 'United States'
            }
            zip = re.findall(zipPattern, addr)
            if zip:
                temp['zip'] = zip[0]
            try:
                patterns = ['Suite\s\d+']
                for pattern in patterns:
                    pat = re.findall(pattern, addr)
                    if pat:
                        first_part = addr.split(pat[0])
                        temp['streetAddress'] = first_part[0] + pat[0]
            except:
                pass
            try:
                temp['streetAddress'] = splittedAddr[0]
            except:
                pass
            try:
                
                
                
                
                temp['city'] = splittedAddr[1].split(',')[0]
                
            except:
                pass
            temp['fullAddress'] += ', United States'
            if returnAddress:
                return temp
            self.overview['mdaas:RegisteredAddress'] = temp

    def get_prev_names(self, tree):
        prev = []
        names = self.get_by_xpath(tree,
                                  '//table[@id="tblPreviousCompanyNames"]//tr[@class="row"]//tr[@class="row"]//td[1]/text() | //table[@id="tblPreviousCompanyNames"]//tr[@class="row"]//tr[@class="rowalt"]//td[1]/text()',
                                  return_list=True)
        dates = self.get_by_xpath(tree,
                                  '//table[@id="tblPreviousCompanyNames"]//tr[@class="row"]//tr[@class="row"]//td[2]/span/text() | //table[@id="tblPreviousCompanyNames"]//tr[@class="row"]//tr[@class="rowalt"]//td[2]/span/text()',
                                  return_list=True)
        print(names)
        if names:
            names = [i for i in names if i != '']
        if names and dates:
            for name, date in zip(names, dates):
                temp = {
                    'name': name,
                    'valid_to': date
                }
                prev.append(temp)
        return prev

    def getFrombaseXpath(self, tree, baseXpath):
        pass

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
            if fieldName == 'vcard:organization-name':
                self.overview[fieldName] = el.split('(')[0].strip()

            if fieldName == 'hasActivityStatus':
                self.overview[fieldName] = el

            if fieldName == 'bst:registrationId':
                self.overview[fieldName] = el

            if fieldName == 'Service':
                self.overview[fieldName] = {'serviceType': el}

            if fieldName == 'regExpiryDate':
                self.overview[fieldName] = self.reformat_date(el, reformatDate) if reformatDate else el

            if fieldName == 'vcard:organization-tradename':
                self.overview[fieldName] = el.split('\n')[0].strip()

            if fieldName == 'bst:aka':
                names = el.split('\n')
                names = el.split(' D/B/A ')
                if len(names) > 1:
                    names = [i.strip() for i in names]
                    self.overview[fieldName] = names
                else:
                    self.overview[fieldName] = names

            if fieldName == 'lei:legalForm':
                self.overview[fieldName] = {
                    'code': '',
                    'label': el}

            if fieldName == 'identifiers':
                self.overview[fieldName] = {
                    'other_company_id_number': el
                }
            if fieldName == 'map':
                self.overview[fieldName] = el[0] if type(el) == list else el

            if fieldName == 'previous_names':
                el = el.strip()
                el = el.split('\n')
                if len(el) < 1:
                    self.overview[fieldName] = {'name': [el[0].strip()]}
                else:
                    el = [i.strip() for i in el]
                    res = []
                    for i in el:
                        temp = {
                            'name': i
                        }
                        res.append(temp)
                    self.overview[fieldName] = res

            if fieldName == 'isIncorporatedIn':
                if reformatDate:
                    self.overview[fieldName] = self.reformat_date(el, reformatDate)
                else:
                    self.overview[fieldName] = el

            if fieldName == 'sourceDate':
                self.overview[fieldName] = self.reformat_date(el, '%d.%m.%Y')
            if fieldName == 'regExpiryDate':
                self.overview[fieldName] = self.reformat_date(el, '%m/%d/%Y')

            if fieldName == 'bst:description':
                self.overview[fieldName] = el

            if fieldName == 'hasURL' and el != 'http://':
                self.overview[fieldName] = el

            if fieldName == 'tr-org:hasRegisteredPhoneNumber':
                if type(el) == list and len(el) > 1:
                    el = el[0]
                self.overview[fieldName] = el

            if fieldName == 'agent':
                
                self.overview[fieldName] = {
                    'name': el.split('\n')[0],
                    'mdaas:RegisteredAddress': self.get_address(returnAddress=True, addr=' '.join(el.split('\n')[1:]),
                                                                zipPattern='[A-Z]\d[A-Z]\s\d[A-Z]\d')
                }
                
                

    def check_tree(self):
        print(self.tree.xpath('//text()'))

    def get_working_tree_api(self, link_name, type, method='GET', data={}):
        if type == 'tree':
            self.tree = self.get_tree(link_name,
                                      headers=self.header, method=method, data=json.dumps(data))
        if type == 'api':
            self.api = self.get_content(link_name,
                                        headers=self.header, method=method, data=json.dumps(data))
            self.api = json.loads(self.api.content)

    def removeQuotes(self, text):
        text = text.replace('"', '')
        return text

    def get_overview(self, link_name):
        data = {
            "searchType": "Charity_Services_IFSSearchResults",
            "entityName": link_name,
            "fileNumber": "",
            "filingClassId": "00000000-0000-0000-0000-000000000000"
        }
        url = 'https://charities.sos.ms.gov/online/Services/Common/IFSServices.asmx/ExecuteSearch'
        self.get_working_tree_api(url, 'api', method='POST', data=data)
        g = self.api['d']
        d = json.loads(g)
        self.api = d['Table'][0]
        url = f'https://charities.sos.ms.gov/online/portal/ch/page/charities-search/~/ViewXSLTFileByName.aspx?providerName=CH_EntityBasedFilingDetails&FilingId={self.api["FilingId"]}'
        self.get_working_tree_api(url, 'tree')

        

        self.overview = {}

        try:
            self.fillField('vcard:organization-name', key='EntityName')
        except:
            return None

        self.overview['isDomiciledIn'] = 'US'
        self.fillField('hasActivityStatus', key='FilingStatusName')
        self.fillField('bst:aka',
                       xpath='//div[@class="sectionHeader"]/text()[contains(., "Contact Information")]/../following-sibling::div[1]//tr[1]/td[2]/text()')

        self.get_address(
            xpath='//div[@class="sectionHeader"]/text()[contains(., "Address")]/../following-sibling::div[1]//text()',
            zipPattern='\d\d\d\d\d+')
        self.fillField('isIncorporatedIn', xpath='//td/text()[contains(., "Effective Date")]/../following-sibling::td/text()', reformatDate='%m/%d/%Y')
        self.fillField('hasURL',
                       xpath='//div[@class="sectionHeader"]/text()[contains(., "Contact")]/../following-sibling::div[1]//td//text()[contains(., "Web Address")]/../following-sibling::td[1]/a/@href')
        self.fillField('tr-org:hasRegisteredPhoneNumber',
                       xpath='//div[@class="sectionHeader"]/text()[contains(., "Contact")]/../following-sibling::div[1]//td//text()[contains(., "Business Phone")]/../following-sibling::td[1]/text()')
        self.fillField('bst:description',
                       xpath='//div[@class="sectionHeader"]/text()[contains(., "Purpose")]/../following-sibling::div[1]/text()')
        self.overview['registeredIn'] = 'Mississippi'

        self.fillField('identifiers',
                       xpath='//div[@class="sectionHeader"]/text()[contains(., "Filing Information")]/../following-sibling::div[1]//td/text()[contains(., "Filing Number")]/../following-sibling::td/text()')
        self.fillField('bst:registrationId',
                       xpath='//div[@class="sectionHeader"]/text()[contains(., "Filing Information")]/../following-sibling::div[1]//td/text()[contains(., "Filing Number")]/../following-sibling::td/text()')
        if self.overview['bst:registrationId']:
            self.overview['bst:registrationId'] = self.overview['bst:registrationId']
        self.overview['regulator_name'] = 'Michal watson - Mississippi Secretary of State'
        self.overview['regulatorAddress'] = {
            'fullAddress': 'New Capitol Room 105 Jackson, Mississippi 39201, United state',
            'city': 'Jackson',
            'country': 'United States'
        }
        self.overview['regulator_url'] = 'https://www.sos.ms.gov/contact-us/capitol-office'
        self.overview['RegulationStatus'] = 'Active'
        self.overview[
            'bst:registryURI'] = 'https://charities.sos.ms.gov/online/portal/ch/page/charities-search/Portal.aspx
        self.overview['Service'] = {
            'areaServed': 'Mississippi',
            'serviceType': 'charity'
        }
        self.fillField('regExpiryDate',
                       xpath='//div[@class="sectionHeader"]/text()[contains(., "Filing Information")]/../following-sibling::div[1]//td/text()[contains(., "Expiration Date")]/../following-sibling::td/text()')

        self.overview['@source-id'] = self.NICK_NAME
        
        

        
        
        
        
        

        
        

        
        
        
        
        
        
        
        

        
        
        
        
        
        

        
        
        
        
        
        
        
        
        

        

        
        return self.overview

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

    
    
    
    
    
    
    
    
    
    
    
    
    

    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

    def get_financial_information(self, link):
        data = {
            "searchType": "Charity_Services_IFSSearchResults",
            "entityName": link,
            "fileNumber": "",
            "filingClassId": "00000000-0000-0000-0000-000000000000"
        }
        url = 'https://charities.sos.ms.gov/online/Services/Common/IFSServices.asmx/ExecuteSearch'
        self.get_working_tree_api(url, 'api', method='POST', data=data)
        g = self.api['d']
        d = json.loads(g)
        self.api = d['Table'][0]
        url = f'https://charities.sos.ms.gov/online/portal/ch/page/charities-search/~/ViewXSLTFileByName.aspx?providerName=CH_EntityBasedFilingDetails&FilingId={self.api["FilingId"]}'
        self.get_working_tree_api(url, 'tree')

        period = self.get_by_xpath('//div[@class="sectionHeader"]/text()[contains(., "Financial Information")]/../following-sibling::div/div/text()')
        revenue = self.get_by_xpath('//div[@class="sectionHeader"]/text()[contains(., "Financial Information")]/../following-sibling::div/div//td/text()[contains(., "Total Revenue")]/../following-sibling::td/text()')
        temp = {}
        if period and revenue:
            period = [self.reformat_date(i.split(': ')[-1], '%m/%d/%Y') for i in period]
            revenue = [i[2:] for i in revenue]
            tempList = []
            for p, r in zip(period, revenue):
                tempList.append({
                    'period': p,
                    'revenue': r
                })

            temp['Summary_Financial_data'] = [{
                'source': 'Michael Watson Secretory of state',
                'summary': {
                    'currency': 'USD',
                    'income_statement': tempList[0]
                }
            }]
        
        return temp
