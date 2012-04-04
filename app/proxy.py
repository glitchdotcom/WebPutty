from urlparse import urljoin
from flask import url_for
from google.appengine.api import urlfetch
from BeautifulSoup import BeautifulSoup, Tag

def _update_links(soup, attr, base):
    kwargs = {}
    kwargs[attr] = True
    for el in soup.findAll(**kwargs):
        el[attr] = urljoin(base, el[attr])

class FetchException(Exception):
    pass

def get_soup(url):
    if not (url.startswith('http://') or url.startswith('https://')):
        url = 'http://' + url
    result = urlfetch.fetch(url, deadline=10)
    return BeautifulSoup(result.content), result.status_code

def get_html(url, append_head=None):
    soup, status = get_soup(url)
    if status == 200:
        _update_links(soup, 'href', url)
        _update_links(soup, 'src', url)
        if append_head:
            for o in append_head:
                soup.head.append(Tag(soup, o['name'], attrs=o['attrs']))
    return soup.prettify(), status

def check_for_tags(url, page_key):
    if not (url.startswith('http://') or url.startswith('https://')):
        url = 'http://' + url
    resp = dict(url=url, page_key=page_key, has_link=False, has_script=False)
    soup, status = get_soup(url)
    link_url = url_for('css', page_key=page_key, _external=True)
    script_url = url_for('js', page_key=page_key, _external=True)
    if status == 200:
        for link in soup.findAll('link'):
            if link.get('href', '') == link_url:
                resp['has_link'] = True
        for script in soup.findAll('script'):
            if script.get('src', '') == script_url:
                resp['has_script'] = True
    return resp
