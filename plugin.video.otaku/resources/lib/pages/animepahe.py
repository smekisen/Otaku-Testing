import json
import pickle
import requests

from bs4 import BeautifulSoup, SoupStrainer
from resources.lib.ui import control, database, source_utils
from resources.lib.ui.BrowserBase import BrowserBase


class sources(BrowserBase):
    _BASE_URL = 'https://animepahe.ru/'
    _headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.62',
        'Referer': _BASE_URL,
        'Cookie': '__ddg1_=PZYJSmACHBBQGP6auJU9; __ddg2_=hxAe1bBqtlUhMFik'
    }

    def get_sources(self, anilist_id, episode, get_backup):
        show = database.get_show(anilist_id)
        kodi_meta = pickle.loads(show.get('kodi_meta'))
        title = kodi_meta.get('name')
        title = self._clean_title(title)
        etitle = kodi_meta.get('ename')
        etitle = self._clean_title(etitle)
        params = {'m': 'search',
                  'q': title}
        headers = self._headers
        headers.update({'X-Requested-With': 'XMLHttpRequest'})
        r = database.get(
            requests.get,
            8,
            self._BASE_URL + 'api',
            params=params,
            headers=headers
        )
        try:
            sitems = r.json().get('data')
        except json.JSONDecodeError:
            return []

        if not sitems and ':' in title:
            title = title.split(':')[0]
            params.update({'q': title})
            r = database.get(
                requests.get,
                8,
                self._BASE_URL + 'api',
                params=params,
                headers=headers,
            )
            sitems = r.json().get('data')

        all_results = []
        if sitems:
            if title[-1].isdigit():
                items = [x for x in sitems if title.lower() in x.get('title').lower()]
            else:
                items = [x for x in sitems if (title.lower() + '  ') in (x.get('title').lower() + '  ')]
            if not items:
                if etitle[-1].isdigit():
                    items = [x for x in sitems if etitle.lower() in x.get('title').lower()]
                else:
                    items = [x for x in sitems if (etitle.lower() + '  ') in (x.get('title').lower() + '  ')]
            if not items:
                items = sitems
            if items:
                slug = items[0].get('session')
                all_results = self._process_ap(slug, title=title, episode=episode)
        return all_results

    def _process_ap(self, slug, title, episode):
        sources = []
        e_num = int(episode)
        big_series = e_num > 30
        page = 1
        if big_series:
            page += int(e_num / 30)

        headers = self._headers
        headers.update({'X-Requested-With': 'XMLHttpRequest'})
        params = {
            'm': 'release',
            'id': slug,
            'sort': 'episode_asc',
            'page': page
        }
        r = database.get(
            requests.get,
            8,
            self._BASE_URL + 'api',
            data=params,
            headers=headers
        )
        items = r.json().get('data')
        items = sorted(items, key=lambda x: x.get('episode'))

        if items[0].get('episode') > 1 and not big_series:
            e_num = e_num + items[0].get('episode') - 1

        items = [x for x in items if x.get('episode') == e_num]
        if items:
            eurl = self._BASE_URL + 'play/' + slug + '/' + items[0].get('session')
            html = self._get_request(eurl, headers=self._headers)
            mlink = SoupStrainer('div', {'id': 'resolutionMenu'})
            mdiv = BeautifulSoup(html, "html.parser", parse_only=mlink)
            items = mdiv.find_all('button')

            for item in items:
                if any(x in item.get('data-src').lower() for x in control.enabled_embeds()):
                    qual = int(item.get('data-resolution'))
                    if qual < 577:
                        quality = 'SD'
                    elif qual < 721:
                        quality = '720p'
                    elif qual < 1081:
                        quality = '1080p'
                    else:
                        quality = '4K'
                    source = {
                        'release_title': '{0} - Ep {1}'.format(title, episode),
                        'hash': item.get('data-src'),
                        'type': 'embed',
                        'quality': quality,
                        'debrid_provider': '',
                        'provider': 'animepahe',
                        'size': 'NA',
                        'info': [source_utils.get_embedhost(item.get('data-src')), 'DUB' if item.get('data-audio') == 'eng' else 'SUB'],
                        'lang': 2 if item.get('data-audio') == 'eng' else 0
                    }
                    sources.append(source)

        return sources
