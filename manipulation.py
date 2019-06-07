from typing import Optional
import functools
import sys

import geopy.geocoders
import geopy.extra.rate_limiter
import numpy as np
import pandas as pd

sys.path.append('../')

import scraping



def get_all_presidents_data_df(
    *,
    miller_scrape: scraping.MillerScraper, 
    potus_scrape: scraping.PotusScraper
) -> pd.DataFrame:
    ''' 
    Merges available data about US presidents from miller_scrape and potus_scrape into one 
    DataFrame.

    Forces keyword arguments to avoid messing-up the order (Miller, POTUS).
    '''
    all_presidents_data = {}
    for president in miller_scrape.fast_facts.keys():
        all_presidents_data[president] = {
            **miller_scrape.fast_facts[president],
            'Description': miller_scrape.descriptions[president],
            'Famous Quote': miller_scrape.famous_quotes[president],
            'Key Events Count': miller_scrape.key_events_counts[president],
            'Salary': potus_scrape.salaries[president]
        }

    return pd.DataFrame(all_presidents_data).T


def get_election_results_df(potus_scrape: scraping.PotusScraper) -> pd.DataFrame:
    ''' 
    Merges available data on election results from potus_scrape into one DataFrame.

    The resulting DataFrame has multiindex columns ('Electoral Votes' and 'Popular Votes'
    for each 'Year').
    '''
    years = []
    election_results = []
    for year, year_results in potus_scrape.election_results.items():
        years.append(year)
        election_results.append(pd.DataFrame(year_results))

    return pd.concat(election_results, keys = years, sort = True).T


def clean_presidents_data(presidents_data: pd.DataFrame) -> pd.DataFrame:
    ''' 
    Replaces problematic strings in the given DataFrame with data about presidents. 
    '''
    PROBLEMATIC_STRINGS = {'\n', '\t', '\r', '\xa0'}

    for problematic_string in PROBLEMATIC_STRINGS:
        presidents_data = presidents_data.applymap(
            lambda x: x.replace(problematic_string, '') if isinstance(x, str) else x
        )

    return presidents_data


def convert_presidents_data(presidents_data: pd.DataFrame) -> pd.DataFrame:
    ''' 
    Converts values in the given DataFrame with data about presidents to appropriate types.
    '''
    STR_VARIABLES = {
        'Birth Place', 
        'Burial Place', 
        'Career', 
        'Children',
        'Description', 
        'Education', 
        'Famous Quote',
        'Full Name',
        'Marriage',
        'Nickname',
        'Political Party', 
        'Religion'
    }
    INT_VARIABLES = {
        'Key Events Count',
        'President Number',
        'Salary'
    }
    TIMESTAMP_VARIABLES = {
        'Birth Date',
        'Date Ended', 
        'Death Date',
        'Inauguration Date'
    }


    def _extract_salary(string: str) -> int:
        ''' Extracts salary from string. '''
        if not isinstance(string, str):
            return string

        base = int(string.split('$')[1].split(',')[0]) * 1_000

        expense_account = 0
        if 'expense' in string:
            if len(string.split('$')) > 3:
                expense_account = int(string.split('$')[3].split(',')[0]) * 1_000
            else:
                expense_account = int(string.split('$')[2].split(',')[0]) * 1_000

        return base + expense_account


    # convert data in respective columns
    for str_variable in STR_VARIABLES:
        presidents_data[str_variable] = presidents_data[str_variable].map(str)
        presidents_data[str_variable] = presidents_data[str_variable].map(
            lambda x: None if x in {'None', 'nan'} else x
        )
    for int_variable in INT_VARIABLES:
        if int_variable == 'Salary':
            presidents_data[int_variable] = presidents_data[int_variable].map(_extract_salary)
        else:
            presidents_data[int_variable] = presidents_data[int_variable].map(int)
    for timestamp_variable in TIMESTAMP_VARIABLES:
        presidents_data[timestamp_variable] = presidents_data[timestamp_variable].map(pd.Timestamp)

    return presidents_data


def convert_elections_data(elections_data: pd.DataFrame) -> pd.DataFrame:
    ''' 
    Converts values in the given DataFrame with data about elections to appropriate types.
    '''
    def _extract_votes(string: str) -> Optional[int]:
        ''' Extracts number of votes from string. '''
        if not isinstance(string, str):
            return string

        try:
            return int(string)
        # votes higher than 999 have the 'millions,thousands,units' format and some votes are 
        # missing, hence the exception
        except ValueError:
            if string in {'None', 'nan', ''}:
                return np.nan

            # convert one Popular Votes entry from 2012 containing '.' instead of ','
            if '.' in string and ',' in string:
                units = int(string.split('.')[-1])
                thousands = int(string.split('.')[-2].split(',')[-1])
                millions = int(string.split(',')[-2])

                return millions * 1_000_000 + thousands * 1_000 + units

            units = int(string.split(',')[-1])
            thousands = int(string.split(',')[-2])
            millions = 0

            if len(string.split(',')) == 3:
                millions = int(string.split(',')[-3])

            return millions * 1_000_000 + thousands * 1_000 + units
           

    # convert data in every cell
    elections_data = elections_data.applymap(str)
    elections_data = elections_data.applymap(_extract_votes)

    return elections_data


def order_presidents_data(presidents_data: pd.DataFrame) -> pd.DataFrame:
    ''' Orders data about presidents by 'Inauguration Date'. '''
    return presidents_data.sort_values('Inauguration Date')


def correct_elections_data_indices(
    elections_data: pd.DataFrame, 
    presidents_data: pd.DataFrame
) -> pd.DataFrame:
    ''' 
    Converts elections_data indicis which correspond to actual presidents to the respective indices
    in presidents_data.
    '''
    elections_index = elections_data.index.tolist()

    for president in presidents_data.index:
        first_name_president = president.split(' ')[0]
        surname_president = president.split(' ')[-1]

        for candidate in elections_data.index:
            first_name_candidate = candidate.split(' ')[0]
            surname_candidate = candidate.split(' ')[-1]

            if first_name_candidate == first_name_president \
                and surname_candidate == surname_president:
                elections_index[elections_index.index(candidate)] = president

    elections_data.index = elections_index

    return elections_data


def compute_years_at_inauguration(presidents_data: pd.DataFrame) -> pd.DataFrame:
    ''' 
    Computes the age in years at inauguration for all presidents and adds it as new columns to the
    DataFrame. 
    '''
    presidents_data['Years at Inauguration'] = (
        presidents_data['Inauguration Date'] - presidents_data['Birth Date']
    ).map(lambda x: x.days / 365)

    return presidents_data


def compute_locations(presidents_data: pd.DataFrame) -> pd.DataFrame:
    ''' 
    Computes the latitude and longitude of birth places of all presidents and adds them as new 
    columns to the DataFrame. 
    '''
    # caching in order to avoid HTTPError for getting too many requests if repeating the
    # computations too many times
    @functools.lru_cache(64)
    def _get_location(place: str) -> geopy.location.Location:
        ''' Find location containing latitude and longitude of the given place. '''
        # first, adjust places which cannot be found on map directly so that they can
        if '(now' in place:
            place_adjusted = place.split('(now')[1].replace(')', '')
            return geocode(place_adjusted + ',' + 'USA')
        elif 'near' in place:
            place_adjusted = place.split('near')[1].replace(')', '')
            return geocode(place_adjusted + ',' + 'USA')
        elif 'Shadwell plantation' in place:
            return geocode('Shadwell, Virginia' + ',' + 'USA')
        elif 'Waxhaw area' in place:
            return geocode('Waxhaw, North Carolina' + ',' + 'USA')

        return geocode(place + ',' + 'USA')


    geolocator = geopy.geocoders.Nominatim(user_agent = "my-application")
    # using the recommended RateLimiter to distribute requests with some small delay
    geocode = geopy.extra.rate_limiter.RateLimiter(geolocator.geocode, 1)
    presidents_data['Birth Place Latitude'] = presidents_data['Birth Place'].map(
        lambda x: print(x) if not _get_location(x) else _get_location(x).latitude
    )
    presidents_data['Birth Place Longitude'] = presidents_data['Birth Place'].map(
        lambda x: None if not _get_location(x) else _get_location(x).longitude
    )

    return presidents_data


def compute_first_electoral_vote_share(
    presidents_data: pd.DataFrame, 
    elections_data: pd.DataFrame
) -> pd.DataFrame:
    ''' 
    Computes the electoral vote share in the first election won for all presidents and adds it as
    new columns to the DataFrame.
    '''
    sums_of_votes = elections_data.sum()

    for president in presidents_data.index:
        inauguration_year = presidents_data.loc[president, 'Inauguration Date'].year
        votes_column_1 = (str(inauguration_year - 1), 'Electoral Votes')
        votes_column_2 = (str(inauguration_year), 'Electoral Votes')

        try:
            president_electoral_votes = elections_data.loc[president, votes_column_1]
            total_electoral_votes = sums_of_votes.loc[votes_column_1]
            electoral_votes_share = president_electoral_votes / total_electoral_votes
            presidents_data.loc[president, 'Electoral Votes Share'] = electoral_votes_share
        # the inauguration year does not always correspond to election year - 1, hence the exception
        except KeyError:
            try:
                president_electoral_votes = elections_data.loc[president, votes_column_2]
                total_electoral_votes = sums_of_votes.loc[votes_column_2]
                electoral_votes_share = president_electoral_votes / total_electoral_votes
                presidents_data.loc[president, 'Electoral Votes Share'] = electoral_votes_share
            # some of the presidents were not voted (succession from the position of vice president 
            # after the death / resignation of the previous president), hence the exception
            except KeyError:
                presidents_data.loc[president, 'Electoral Votes Share'] = np.nan

    return presidents_data


def compute_number_of_children(presidents_data: pd.DataFrame) -> pd.DataFrame:
    ''' 
    Computes the number of children for all presidents and adds it as new columns to the DataFrame. 
    '''
    presidents_data['Number of Children'] = presidents_data['Children'].map(
        lambda x: 0 if x == None else len(x.replace(';', ',').split(','))
    )

    return presidents_data
