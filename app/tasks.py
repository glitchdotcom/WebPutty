import re
from datetime import datetime
import logging
from urlparse import urljoin, urlparse
from BeautifulSoup import BeautifulSoup
from flask import Module, request, render_template, url_for
from flaskext.csrf import csrf_exempt
from google.appengine.ext.db import GqlQuery
from google.appengine.api import urlfetch, taskqueue
from cssutils import CSSParser
from livecount import counter
from livecount.counter import PeriodType
from extensions import url2png
from models import Page, Importer, StyleRevision
from count import count_view

tasks = Module(__name__, 'tasks')

# Import states
NO_IMPORT = 0
IMPORTING = 1
IMPORT_DONE = 2
CAN_IMPORT = 4

WEBPUTTY_LIST_ID = 'f734b59b78'

@tasks.route('/tasks/stats')
@csrf_exempt
def stats_cron():
    current_user_count = GqlQuery('SELECT __key__ FROM UserSettings').count(None)
    current_site_count = GqlQuery('SELECT __key__ FROM Site WHERE example=false').count(None)
    now = datetime.now()
    saved_user_count = counter.load_and_get_count('user:all', period_type=PeriodType.DAY, period=now) or 0
    saved_site_count = counter.load_and_get_count('site:all', period_type=PeriodType.DAY, period=now) or 0
    count_view('user:all', delta=(current_user_count - saved_user_count), batch_size=None, period=now)
    count_view('site:all', delta=(current_site_count - saved_site_count), batch_size=None, period=now)
    return render_template('_stats_cron.html', current_user_count=current_user_count, current_site_count=current_site_count, saved_user_count=saved_user_count, saved_site_count=saved_site_count)

@tasks.route('/tasks/fetch_preview', methods=['POST'])
@csrf_exempt
def fetch_preview():
    page = Page.get_or_404(request.form.get('page_key', ''))
    if 'localhost' in page.url or '127.0.0.1' in page.url:
        return 'OK'
    url = 'http:' + url2png(page.url)
    result = urlfetch.fetch(url, deadline=10)
    if result.status_code == 200:
        page.preview_img = result.content
        page.put()
        return 'OK'
    else:
        msg = 'Error while fetching preview image from %s\nStatus %s\nHeaders\n%s\nFinal Url: "%s"' % (url, result.status_code, result.headers, getattr(result, 'final_url', ''))
        logging.warn(msg)
        return msg, 500

def queue_import(page, first_time=False):
    if first_time:
        page.import_state = IMPORTING
        page.put()
    taskqueue.add(
        url = url_for('tasks.do_import'),
        queue_name = 'importer',
        params = {'page_key': page.key()},
    )

def create_importer(page):
    importer = Importer(page=page, style='')
    resp = urlfetch.fetch(page.url, deadline=10)
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.content)
        parser = CSSParser()
        for tag in soup.findAll(re.compile(r'^(link|style)$')):
            if tag.name == 'link':
                if tag.get('href', None) and tag.get('rel', 'stylesheet').lower() == 'stylesheet':
                    url = urljoin(page.url, tag['href'])
                    if urlparse(url).netloc != urlparse(request.url).netloc:
                        importer.urls.append(url)
            elif tag.name == 'style':
                media = tag.get('media', None)
                sheet = parser.parseString(''.join(tag.contents).strip('\n'), href=url)
                style = sheet.cssText
                if media:
                    style = '@media %s {\n%s\n}' % (media, style)
                style = '/* Imported directly from %s */\n%s\n' % (page.url, style)
                importer.style += style
        # Patch around AppEngine's frame inspection
        del parser

        importer.put()
        queue_import(page)

@tasks.route('/tasks/import', methods=['POST'])
@csrf_exempt
def do_import():
    page = Page.get(request.form.get('page_key', ''))
    if not page or page.import_state != IMPORTING:
        return 'NO_IMPORTER' # We're done
    importer = Importer.gql('WHERE page=:1', page.key()).get()
    if not importer:
        # This requires a request to fetch the page and parse the URLs.
        # It also enqueues the next run.
        create_importer(page)
        return 'CREATED'
    if importer.urls:
        url = importer.urls.pop(0)
        parser = None
        try:
            resp = urlfetch.fetch(url, deadline=10)
            if resp.status_code == 200:
                parser = CSSParser()
                sheet = parser.parseString(resp.content, href=url)
                style = sheet.cssText
                importer.style += '\n\n/* Imported from %s */\n%s' % (url, style)
            else:
                raise Exception('Error fetching %s' % url)
        except Exception, e:
            import traceback
            importer.errors.append('Error importing %s' % url)
            logging.error('Error importing for Page %s from %s:\n%s\n%s', page.key().id(), url, e, traceback.format_exc())
        finally:
            # Patch around AppEngine's frame inspection
            if parser:
                del parser

        importer.put()
        queue_import(page)
        return 'IMPORTED'
    else:
        page.import_state = IMPORT_DONE
        style = page.styles[0]
        errors = ''
        if importer.errors:
            errors = 'Errors:\n%s\n\n' % ('\n'.join(importer.errors))
        existing_rev = style.preview_rev if style.preview_rev else style.published_rev
        existing_scss = existing_rev.raw
        rev = style.preview_rev
        if not rev:
            rev = StyleRevision(parent=page.styles[0])
            rev.put()
            style.preview_rev = rev
            style.put()
        rev.raw = '%s\n\n%s/* End of imported styles */\n\n%s' % (importer.style, errors, existing_scss)
        rev.put()
        page.put()
        importer.delete()
        return 'DONE'

@tasks.route('/tasks/upload_style', methods=['GET', 'POST'])
@csrf_exempt
def upload_style():
    page_key = request.form.get('page_key', None)
    if page_key:
        page = Page.get(page_key)
        page.upload_to_cdn()
    return 'OK'

@tasks.route('/tasks/set_on_cdn', methods=['GET', 'POST'])
@csrf_exempt
def set_on_cdn():
    cursor = request.form.get('cursor', None)
    pages = Page.all()
    if cursor:
        pages.with_cursor(start_cursor=cursor)
    requeue = False
    for page in pages.fetch(100):
        requeue = True
        page.on_cdn = False
        page.put()
        page.queue_upload()
    if requeue:
        taskqueue.add(url=url_for('tasks.set_on_cdn'), params={'cursor': pages.cursor()})
    return 'OK'

