from typing import Any, Dict, Optional

from bs4 import BeautifulSoup
from tqdm import tqdm
import pandas as pd
import requests



def get_soup(url: str) -> BeautifulSoup:
    ''' Returns soup for the given url. '''
    return BeautifulSoup(requests.get(url).text, 'html.parser')



class MillerScraper:
    '''
    Class for scraping the Miller Center webpage to get data about US presidents. 

    Particularly, it serves for scraping data on facts and characteristics (self.fast_facts), 
    brief description (self.descriptions), famous quotes (self.famous_quotes), and count of 
    notable events happened during the president's office (self.key_events_counts).
    '''

    def __init__(self):
        ''' Initializes the scraping class. '''
        self.origin: str = 'https://millercenter.org/'

        self.subdirectories: Optional[Dict[str, Any]] = None

        self.fast_facts: Optional[Dict[str, Any]] = None
        self.descriptions: Optional[Dict[str, Any]] = None
        self.famous_quotes: Optional[Dict[str, Any]] = None
        self.key_events_counts: Optional[Dict[str, Any]] = None

        self.all_presidents_data: Optional[pd.DataFrame()] = None


    def get_subdirectories(self) -> None:
        '''
        Creates a dictionary with the presidents' names as keys and their respective 
        subdirectories as values, then saves the dictionary to self.subdirectories.
        '''
        # parse the given origin (web address) utilizing BeautifulSoup 
        soup = get_soup(self.origin) 
        # enter the main navigation panel and find submenu that contains the links 
        # (subdirectories) to individual pages of US presidents
        navigation_menu = soup.find('nav', {'aria-labelledby':'block-mainnavigation-3-menu'})
        submenu = navigation_menu.find_all('ul', {'class':'submenu'})[1]
        a_blocks = submenu.find_all('a')

        subdirectories = {}
        for a_block in tqdm(a_blocks): 
            # each a_block represents one president, extract the subdirectory and save 
            # it under the president's name
            subdirectories[a_block.text] = a_block['href']

        self.subdirectories = subdirectories


    def get_fast_facts(self) -> None:
        '''
        Iterates over the subdirectories to get on the individual page of the respective 
        president and save the relevant fast facts into self.fast_facts. 
        '''
        fast_facts = {}
        for president, subdirectory in tqdm(self.subdirectories.items()):
            # parse the given path (web address) utilizing BeautifulSoup
            soup = get_soup(self.origin + subdirectory)
            # navigate through the soup to get to the part relevant for fast facts
            president_page = soup.find('div', {'class':'president-main-wrapper'})
            fast_facts_dashboard = president_page.find('div', {'class':'fast-facts-wrapper'})   

            # avoiding redundant elements (containing '\n')
            relevant_fast_facts = [x for x in fast_facts_dashboard.children if x != '\n']
            # popping the first element which contains just the 'Fast Facts' heading
            relevant_fast_facts.pop(0)

            fast_facts[president] = {}
            for fast_fact in relevant_fast_facts:
                # save the fast fact under its label into the dict of the given president
                fast_facts[president][fast_fact.label.text] = fast_fact.div.text

        self.fast_facts = fast_facts


    def get_descriptions(self) -> None:
        '''
        Iterates over the subdirectories to get on the individual page of the respective 
        president and save the relevant description into self.descriptions. 
        '''
        descriptions = {}
        for president, subdirectory in tqdm(self.subdirectories.items()):
            # parse the given path (web address) utilizing BeautifulSoup
            soup = get_soup(self.origin + subdirectory)
            # navigate through the soup to get to the part relevant for the description
            description_paragraph = soup.find('div', {'class':'copy-wrapper'})

            # save the description into the dict with descriptions
            descriptions[president] = description_paragraph.p.text

        self.descriptions = descriptions


    def get_famous_quotes(self) -> None:
        '''
        Iterates over the subdirectories to get on the individual page of the respective 
        president and save the relevant famous quote into self.famous_quotes. 
        '''
        famous_quotes = {}
        for president, subdirectory in tqdm(self.subdirectories.items()):
            # parse the given path (web address) utilizing BeautifulSoup
            soup = get_soup(self.origin + subdirectory)
            # navigate through the soup to get to the part relevant for the famous quote
            famous_quote_paragraph = soup.find('blockquote', {'class':'president-quote'})

            # save the famous quote into the dict with famous quotes
            famous_quotes[president] = str(famous_quote_paragraph.contents[0])

        self.famous_quotes = famous_quotes


    def get_key_events_counts(self) -> None:
        '''
        Iterates over the subdirectories to get on the individual page of the respective 
        president and save the relevant key events count into self.key_events_counts. 
        '''
        key_events_counts = {}
        for president, subdirectory in tqdm(self.subdirectories.items()):
            # parse the given path (web address) utilizing BeautifulSoup
            soup = get_soup(self.origin + subdirectory + '/key-events')
            # navigate through the soup to get to the part relevant for key events
            key_events_overview = soup.find('div', {'class':'article-wysiwyg-body'})

            try:
                # count of all events ('titles' highlighted in bold)
                key_events_count_bold = len(key_events_overview.find_all('strong'))
                # count of all events ('titles' no longer highlighted in bold)
                key_events_count_not_bold = len(key_events_overview.find_all('b'))
                # sum both counts
                key_events_count = key_events_count_bold + key_events_count_not_bold
            # D. Trump page has no information about major events, hence the exception 
            except AttributeError:
                key_events_count = 0
                pass

            # save the key events count into the dict with key events counts
            key_events_counts[president] = key_events_count

        self.key_events_counts = key_events_counts


    def correct_Grover_Cleveland_data(self) -> None:
        '''
        Corrects Grover Cleveland's data. 
        
        Because, due to Grover Cleveland being in office 2 non-consecutive times, the 
        'Inauguration Date', 'Date Ended' and 'President Number' facts are present twice 
        in the data.

        Also, duplicates other Grover Cleveland's data so that it is entered for each of
        his terms.
        '''
        # assert that 'Grover Cleveland 2' entry doesn't exist already
        assert 'Grover Cleveland 2' not in self.fast_facts.keys()

        # create entries for Cleveland's second term
        self.fast_facts['Grover Cleveland 2'] = {
            key: value for key, value in self.fast_facts['Grover Cleveland'].items()
        }
        for attribute in [self.descriptions, self.famous_quotes, self.key_events_counts]:
            attribute['Grover Cleveland 2'] = attribute['Grover Cleveland']

        # input corrected entries
        for entry_name in ['Inauguration Date', 'Date Ended', 'President Number']:
            double_entry = self.fast_facts['Grover Cleveland'][entry_name]
            second_entry_index = 2 if entry_name == 'President Number' else 3

            entry_1 = double_entry.split('\n')[1]
            entry_2 = double_entry.split('\n')[second_entry_index]

            self.fast_facts['Grover Cleveland'][entry_name] = entry_1
            self.fast_facts['Grover Cleveland 2'][entry_name] = entry_2



class PotusScraper:
    '''
    Class for scraping the POTUS webpage to get data about US presidents and elections. 

    Particularly, it serves for scraping data on presidential salaries (self.salaries), 
    and election results (self.election_results).
    '''

    def __init__(self):
        ''' Initializes the scraping class. '''
        self.origin: str = 'https://www.potus.com/'

        self.subdirectories: Optional[Dict[str, Any]] = None

        self.salaries: Optional[Dict[str, Any]] = None
        self.election_results: Optional[Dict[str, Any]] = None


    def get_subdirectories(self) -> None:
        '''
        Creates a dictionary with the presidents' names as keys and their respective 
        subdirectories as values, then saves the dictionary to self.subdirectories.
        '''
        # parse the given origin (web address) utilizing BeautifulSoup 
        soup = get_soup(self.origin) 
        # navigate through the soup to get to the part that contains the links 
        # (subdirectories) to individual pages of US presidents
        a_blocks = soup.find_all('a', {'target':'_self'})

        subdirectories = {}
        for a_block in tqdm(a_blocks): 
            # each a_block represents one president, extract the subdirectory and save it 
            # under the president's name
            president_and_name_and_years = a_block.find('img')['alt']
            president_and_name = president_and_name_and_years.split(',')[0]
            name = president_and_name.replace('President ', '')

            subdirectories[name] = a_block['href']

        # popping the first element which contains the 'Facts About the Presidents' section
        subdirectories.pop('Facts About the Presidents')

        self.subdirectories = subdirectories


    def correct_subdirectories(self, miller_scrape: MillerScraper) -> None:
        ''' 
        Converts the names of presidents from self.subdirectories (POTUS) to names of Miller
        subdirectories, because POTUS has got the names wrong.
        '''
        miller_keys = miller_scrape.subdirectories.keys()

        # assert that the surnames match
        president_keys = zip(miller_keys, self.subdirectories.keys())
        for president_miller, president_potus in president_keys:
            assert president_miller.split(' ')[-1] == president_potus.split(' ')[-1]

        president_keys = zip(miller_keys, self.subdirectories.values())

        self.subdirectories = {key: value for key, value in president_keys}


    def get_salaries(self) -> None:
        '''
        Iterates over the subdirectories to get on the individual page of the respective 
        president and save the relevant salary into self.salaries. 
        '''
        salaries = {}
        for president, subdirectory in tqdm(self.subdirectories.items()):
            # parse the given path (web address) utilizing BeautifulSoup
            soup = get_soup(self.origin + subdirectory)
            # navigate through the soup to get to the part relevant for the salary
            try:
                presidential_salary_title = soup.find(string = "Presidential Salary:")
                presidential_salary = presidential_salary_title.find_parent('p').text
            # Benjamin Harrison has space in the string, hence the exception
            except AttributeError:
                presidential_salary_title = soup.find(string = "Presidential Salary: ")
                presidential_salary = presidential_salary_title.find_parent('p').text

            # save the salary into the dict with salaries
            salaries[president] = presidential_salary

        self.salaries = salaries


    def get_election_results(self) -> None:
        '''
        Iterates over the subdirectories to get on the individual page of the respective 
        president and save the relevant salary into self.salaries. 
        '''  
        election_results = {}
        for president, subdirectory in tqdm(self.subdirectories.items()):
            # parse the given path (web address) utilizing BeautifulSoup
            soup = get_soup(self.origin + subdirectory)

            # navigate through the soup to get to the part relevant for election results
            presidential_elections_title = soup.find(string = "Presidential Election Results:")
            presidential_elections = presidential_elections_title.find_parent('div')
            presidential_elections_tables = presidential_elections.find_all('table')

            # extract election results for individual years
            for table in presidential_elections_tables:
                # extract the year
                year = table.find('tr', {'class','row-2'}).find('a').text
                election_results[year] = {}

                # extract the respective electee results
                electee_results = table.find_all('tr')

                for electee in electee_results:
                    try:
                        # extract the name of the candidate
                        electee_name = electee.find('td', {'class':'column-2'}).a.text
                        election_results[year][electee_name] = {}

                        # data contained in tables of early election results do not include the
                        # 'popular votes' column, therefore we include this condition
                        if len(presidential_elections.find('tr').find_all('th')) == 3: 
                            # number of popular votes candidate gained
                            popular_votes = None
                            # number of electoral votes candidate gained
                            electoral_votes = electee.find('td', {'class':'column-3'}).text
                        else:
                            popular_votes = electee.find('td', {'class':'column-3'}).text   
                            electoral_votes = electee.find('td', {'class':'column-4'}).text   

                        # save election results into the dict with election results
                        election_results[year][electee_name]['Popular Votes'] = popular_votes
                        election_results[year][electee_name]['Electoral Votes'] = electoral_votes 
                    # first row is the header, hence the exception
                    except AttributeError:
                        pass

        self.election_results = election_results


    def duplicate_Grover_Cleveland_salary(self) -> None:
        '''
        Duplicates Grover Cleveland's salary, the second entry being recorded for Grover Cleveland's
        second term in office. The second entry was not recorded because the two terms were not 
        consecutive.
        '''
        # assert that 'Grover Cleveland 2' entry doesn't exist already
        assert 'Grover Cleveland 2' not in self.salaries.keys()

        # create an entry for Cleveland's second term
        self.salaries['Grover Cleveland 2'] = self.salaries['Grover Cleveland']
