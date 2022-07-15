from bs4 import BeautifulSoup
import urllib
import urllib.request
import re
import ast
import random
import pickle
from diskcache import Cache

CACHE = Cache('cache')
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36'}


def cache(func):
    """
    Decorator for caching the results of a function
    """

    def wrapper(self):
        soup = self.soup
        title = self.title
        seasons_filter = self.seasons_filter

        if func.__name__ == 'get_seasons':
            key = f'{func.__name__}[{title}]{seasons_filter}'
        else:
            key = f'{func.__name__}[{title}]'

        with Cache(CACHE.directory) as reference:
            if key in reference and not self.ignore_cache:
                print(f'Fetching from cache! - {func.__name__}')
                return pickle.loads(CACHE[key])
            else:
                print(f'Setting cache! - {func.__name__}')
                result = func(self)
                CACHE[key] = pickle.dumps(result)
                return result
    return wrapper


class ImdbCrawler:
    def __init__(self, imdb_url, seasons_filter='', ignore_cache=False):
        self.imdb_url = imdb_url
        if 'm.imdb.com/' in self.imdb_url:
            self.imdb_url = self.imdb_url.replace('m.imdb.com/', 'www.imdb.com/')

        self.seasons_filter = seasons_filter
        self.ignore_cache = ignore_cache
        self.cache = CACHE

        print(self.imdb_url)
        markup = urllib.request.urlopen(self.imdb_url)
        self.soup = BeautifulSoup(markup, 'html.parser')
        self.season_soup = False
        self.winner = dict()

    @property
    def title(self) -> str:
        if self.season_soup:
            return self.season_soup.find('title').text
        else:
            return self.soup.find('title').text

    def get_winner(self) -> dict:
        """
        Parse url and get the winner
        """
        winner = self.winner
        imdb_url = self.imdb_url

        if 'imdb.com/title/' in imdb_url:
            self.imdb_url = imdb_url.split('?')[0]
            if imdb_url[-1] != '/':
                imdb_url += '/'
            seasons, seasons_selected = self.get_seasons()
            winner['SEASON'] = random.randrange(0, len(seasons))
            winner['EPISODE'] = random.randrange(
                0, len(seasons[winner['SEASON']]))
            winner['URL'] = seasons[winner['SEASON']][winner['EPISODE']]
            winner['SEASON'] = seasons_selected[winner['SEASON']]
            winner['EPISODE'] += 1
        else:
            if 'imdb.com/chart/' in imdb_url:
                movie_list = self.get_chart()
            else:
                movie_list = self.get_watchlist()
            print(f'Choosing from {len(movie_list)} titles.')
            winner['URL'] = random.choice(movie_list)

        winner['link'] = f'https://www.imdb.com/title/{winner["URL"]}/'
        print(winner['link'])
        winner_markup = urllib.request.urlopen(winner['link'])
        winner_soup = BeautifulSoup(winner_markup, 'html.parser')
        winner_title = winner_soup.find('title').text
        winner['title'] = winner_title.replace(' - IMDb', '')
        winner_titleblock = winner_soup.find(
            'div', {'class': re.compile('sc.+cMYixt')})
        winner['length'] = winner_titleblock.find_all(
            'li', {'class': 'ipc-inline-list__item'})[1].text
        winner['image'] = winner_soup.find(
            'img', {'class': 'ipc-image'})['src']
        winner['plot'] = winner_soup.find(
            'span', {'class': re.compile('sc.+fMPjMP')}).text

        winner_genrechips = winner_soup.find_all(
            'li', {'class': re.compile('ipc-inline-list__item ipc-chip__text')})
        winner['genre'] = [
            i.text for i in winner_genrechips]

        cast = winner_soup.find_all(
            'div', {'class': re.compile('sc.+eVsQmt')})
        winner['cast'] = [cast_member.find('a', {'class': re.compile('sc.+gJhRzH')}).text
                          for cast_member in cast]
        winner_credits_container = winner_soup.find(
            'ul', {'class': re.compile('ipc-metadata-list ipc-metadata-list--dividers-all.+fEgKYH.+?')})
        # Lambda function to get exact match on class
        winner_credits = winner_credits_container.find_all(
            lambda tag: tag.name == 'li' and tag.get('class') == ['ipc-metadata-list__item'])
        winner['credits'] = {
            i.find(
                ['span', 'a'],
                {'class': 'ipc-metadata-list-item__label'}).text:
            [i.text for i in i.find_all(
                'a',
                {'class': "ipc-metadata-list-item__list-content-item ipc-metadata-list-item__list-content-item--link"})]
            for i in winner_credits
        }

        imdb_rating = winner_soup.find(
            'span', {'class': re.compile('sc.+jGRxWM')}).text
        try:
            meta_rating = winner_soup.find(
                'span', {'class': 'score-meta'}).text
        except:
            meta_rating = 'N/A'
        winner['score'] = f'IMDb Score: {imdb_rating}   Metacritic Score: {meta_rating}'

        return winner

    @cache
    def get_watchlist(self) -> list[str]:
        """
        Returns a list of IMDB IDs from the watchlist

        Won't raise an exception if the url is a public watchlist

        Args:
            soup (BeautifulSoup): BeautifulSoup object
        """
        soup = self.soup

        list_widget = soup.find('span', {'class': 'ab_widget'})
        script = list_widget.find('script').string
        target = '"starbars":{.+},"ribbons":'
        movie_list_search = re.search(target, script)
        # scraping movie list from script starbars sections
        cleaned_movie_list = movie_list_search[0].lstrip(
            '"starbars":').rstrip(',"ribbons":')
        movie_list_dict = ast.literal_eval(cleaned_movie_list)
        movie_list = [key for key in movie_list_dict]

        return movie_list

    @cache
    def get_chart(self) -> list[str]:
        """
        Returns a list of IMDB IDs from the chart

        Won't raise an exception if the url is a chart

        Args:
            soup (BeautifulSoup): BeautifulSoup object
        """
        soup = self.soup

        list_widget = soup.find('span', {'class': 'ab_widget'})
        titles_td = list_widget.find_all('td', {'class': 'titleColumn'})
        movie_list = [title.find('a')['href'].split('?')[0].strip(
            '/').replace('title/', '') for title in titles_td]

        title = list_widget.find('h1', {'class': 'header'}).text
        print(f'Choosing from chart: {title}')

        return movie_list

    @cache
    def get_episodes(self) -> list[str]:
        """
        Returns a list of IMDB IDs from the episodes

        Won't raise an exception if the url is a tv show page

        Args:
            season_soup (BeautifulSoup): BeautifulSoup object
        """
        season_soup = self.season_soup

        list_widget = season_soup.find('div', {'class': 'list detail eplist'})
        episodes = list_widget.find_all('div', {'class': 'list_item'})
        episode_list = [episode.find('a')['href'].replace(
            '/title/', '').rstrip('/') for episode in episodes]

        return episode_list

    @cache
    def get_seasons_number_imdb(self) -> int:
        """
        Returns the number of seasons of a TV show from an IMDb TV show page

        Args:
            soup (BeautifulSoup): BeautifulSoup object
        """
        soup = self.soup

        seasons_number = soup.find(
            'select', {'id': 'browse-episodes-season'})['aria-label']
        # remove non-digits
        seasons_number = int(re.sub('\D', '', seasons_number))
        return seasons_number

    @cache
    def get_seasons_number_google(self) -> int:
        """
        Returns the number of seasons of a TV show from a google search

        Args:
            soup (BeautifulSoup): BeautifulSoup object
        """
        soup = self.soup
        show_title = self.title

        show_title_cleaned = show_title.split('(')[-2].strip()
        search_query = f'how many seasons does {show_title_cleaned} have%3F'
        search_query_encoded = search_query.replace(' ', '+')
        google_search = f'https://www.google.com/search?q={search_query_encoded}'
        google_request = urllib.request.Request(google_search, headers=HEADERS)
        markup = urllib.request.urlopen(google_request)
        google_soup = BeautifulSoup(markup, 'html.parser')
        google_search_result = google_soup.find('div', {'class': 'Z0LcW'}).text
        seasons_number = int(google_search_result)
        return seasons_number

    @cache
    def get_seasons(self) -> list[list[str]]:
        """
        Returns a list of seasons with episodes from an IMDb TV show page

        Won't raise an exception if the url is a tv show page

        Example:
        https://www.imdb.com/title/tt0472954/
        which supports episodes?season postfix like so:
        https://www.imdb.com/title/tt0472954/episodes?season=1

        Returns:
            seasons (list): List of seasons

        Args:
            soup (BeautifulSoup): BeautifulSoup object
            imdb_url (str): IMDb TV Show Title URL
        """
        soup = self.soup
        imdb_url = self.imdb_url
        seasons_filter = self.seasons_filter

        seasons = []

        if seasons_filter:
            seasons_selected = []
            filter_list = seasons_filter.split(',')
            for cur_filter in filter_list:
                if '-' in cur_filter:
                    season_filter = cur_filter.split('-')
                    season_filter_list = range(
                        int(season_filter[0]), int(season_filter[1]) + 1)
                    for season_filter in season_filter_list:
                        seasons_selected.append(int(season_filter))
                else:
                    season_filter = int(cur_filter)
                    seasons_selected.append(season_filter)
        else:
            try:
                print('Getting seasons from IMDb')
                seasons_numbers = self.get_seasons_number_imdb()
            except Exception as e:
                print('Exception: ' + e)
                print('Trying to fetch seasons number through Google search')
                seasons_numbers = self.get_seasons_number_google()
            finally:
                seasons_selected = range(1, seasons_numbers + 1)

        # MAYBE MAKE THIS ASYNC?
        for season_num in seasons_selected:
            season_url = f'{imdb_url}episodes?season={season_num}'
            markup = urllib.request.urlopen(season_url)
            self.season_soup = BeautifulSoup(markup, 'html.parser')
            seasons.append(self.get_episodes())
            self.season_soup = False

        return seasons, seasons_selected