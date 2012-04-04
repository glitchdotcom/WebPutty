import logging
import os
from datetime import datetime, timedelta
from hashlib import sha1
from base64 import b32encode
from urlparse import urlparse
from flask import Response, Module, request, session, url_for, redirect, abort, flash, render_template, render_template_string, jsonify, make_response, send_from_directory
from google.appengine.ext.db import GqlQuery, Blob, Link
from google.appengine.api import channel as gae_channels
from google.appengine.api import users, mail, memcache
from google.appengine.api.users import User
from livecount.counter import PeriodType, LivecountCounter
from jsmin import jsmin
from fogbugz import FogBugz
import settings
from extensions import context_processor
from models import SchemaVersion, Style, StyleRevision, Site, Invitation, Page, PageChannel, UserSettings
from tasks import queue_import
from tasks import IMPORT_DONE, CAN_IMPORT
from proxy import get_html, check_for_tags
from count import count_view, get_period_and_count
from forms import StyleForm, InviteForm, PageForm, SiteForm
from decorators import requires_auth, requires_admin
from docs import doc_list

views = Module(__name__, 'views')

views.app_context_processor(context_processor)

def _localeselector():
    locale = UserSettings.get_locale() or session.get('locale', None)
    if locale:
        return locale
    locale = request.accept_languages.best_match([locale[0] for locale in settings.available_locales])
    if locale:
        return locale
    return 'en' # Default if we still have no match.

def _timezoneselector():
    return None

def _etag(data):
    if not isinstance(data, Blob):
        data = data.encode('utf-8')
    etag = sha1(data).hexdigest()
    return etag

def _send_file(content, content_type, etag=None):
    if not etag:
        etag = _etag(content)
    if request.headers.get('If-None-Match', '') == etag:
        return 'Not Modified', 304
    headers = {'ETag': etag}
    return Response(content, headers=headers, content_type=content_type)

def _create_example_site(user):
    site = Site(
        name='Example Site',
        owner = user,
        users = [user],
        admins = [user],
        example = True,
    )
    site.put()

    for v in [4, 5]:
        name = 'Html%d Example' % v
        style = Style(site=site, name=name)
        style.put()
        rev = StyleRevision(parent=style, rev=0)
        rev.put()
        rev.update(render_template('examples/blog-html%d.css' % v))
        style.published_rev = rev
        rev = StyleRevision(parent=style, rev=1)
        rev.put()
        rev.update(render_template('examples/blog-html%d-preview.css' % v))
        style.preview_rev = rev
        style.put()
        page = Page(site=site, name=name, url=url_for('example%d' % v, page_key=0, _external=True), _styles=[style.key()])
        page.put()
        page.url = url_for('example%d' % v, page_key=page.key(), _external=True)
        page.put()
        page.queue_refresh()

@views.route('/')
def index():
    user = users.get_current_user()
    if user:
        if not UserSettings.has_seen_example() and GqlQuery('SELECT __key__ FROM Site WHERE owner=:1 AND example=true', user).count(1) == 0:
            _create_example_site(user)
            UserSettings.mark_example_as_seen()
        sites = Site.gql('WHERE users=:1 ORDER BY name', user)
        site_form = PageForm()
        page_form = PageForm()
        return render_template('index.html', sites=sites, new_site_form=site_form, page_form=page_form)
    else:
        return home()

@views.route('/site/<int:site_id>') # site_id will be handled by javascript.
def site(site_id):
    return index()

@views.route('/home')
def home():
    return render_template('home.html')

@views.route('/credits')
def credits():
    return render_template('credits.html')

@views.route('/release_notes')
def release_notes():
    UserSettings.mark_version_as_seen(settings.appversion_raw)
    return render_template('release_notes.html')

@views.route('/docs', defaults={'doc_key': 'toc'})
@views.route('/docs/<doc_key>')
def docs(doc_key):
    matches = [doc for doc in doc_list if doc[0] == doc_key]
    doc_slug, doc_title, link_title = matches[0] if len(matches) else doc_list[0]
    doc_title = render_template_string(doc_title) # in case it contains things like {{ appname }}
    return render_template('docs/%s.html' % doc_slug, doc_title=doc_title, doc_list=doc_list, link_title=link_title)

@views.route('/css/<page_key>')
def css(page_key):
    preview = ('preview' in request.args) and (request.args.get('preview') != '0')
    pretty = ('pretty' in request.args) and (request.args.get('pretty') != '0')

    if not preview and not pretty:
        count_view('css:all')
        if request.referrer:
            count_view('css:page:%s:%s' % (urlparse(request.referrer).netloc, page_key))
        etag = memcache.get(page_key + '-css-etag')
        if etag and request.headers.get('If-None-Match', '') == etag:
            return 'Not Modified', 304
        css = memcache.get(page_key + '-css')
        if not css or not etag:
            page = Page.get_or_404(page_key)
            css = page.compressed_css(False)
            etag = _etag(css)
            expires = 24 * 60 * 60
            memcache.set(page_key + '-css-etag', etag, time=expires)
            memcache.set(page_key + '-css', css, time=expires)
        return _send_file(css, 'text/css', etag)
    else:
        page = Page.get_or_404(page_key)
        if pretty:
            css = page.uncompressed_css(preview)
        else:
            css = page.compressed_css(preview)
        return _send_file(css, 'text/css')

@views.route('/js/<file_name>.js')
@views.route('/js/<page_key>/<file_name>.js')
def templatejs(file_name, page_key=None):
    page = None
    if page_key:
        page = Page.get_or_404(page_key)
    js = render_template('js/%s.js' % (file_name), page=page)
    if not settings.debug or '__no_debug__' in request.args:
        js = jsmin(js)
    return Response(js, content_type='text/javascript')

@views.route('/js/<page_key>')
def js(page_key):
    cache_key = '%s-js' % os.environ['CURRENT_VERSION_ID']
    js = memcache.get(cache_key)
    if not js or settings.debug: # don't use memcache in the dev environment to make testing changes to et.js easier
        js = render_template('js/et.js', page_key='{{ page_key }}', preview_url='{{ url_for("views.css", page_key=page_key, preview=1, _external=True) }}')
        if not settings.debug:
            js = jsmin(js)
        memcache.set(cache_key, js)
    js = render_template_string(js, page_key=page_key)
    return _send_file(js, 'text/javascript')

@views.route('/invitation/<hash>')
def invitation(hash):
    user = users.get_current_user()
    invite = Invitation.gql('WHERE hash=:1', hash).get()
    if not invite:
        return render_template('invitation_expired.html')
    # We want the user to be logged out once before coming here so they can choose which account the invite applies to.
    if not invite.has_been_logged_out:
        invite.has_been_logged_out = True
        invite.put()
        if user:
            return redirect(users.create_logout_url(request.path))
    if not user:
        return redirect(users.create_login_url(request.path))
    site = invite.site
    if user not in site.users:
        site.users.append(user)
    if invite.admin and user not in site.admins:
        site.admins.append(user)
    site.put()
    for invite in Invitation.gql('WHERE email=:1 AND site=:2', invite.email, invite.site):
        invite.delete()
    return render_template('invitation.html', site=site)

@views.route('/invite/<int:site_id>', methods=['POST'])
@requires_auth
def invite(site_id):
    user = users.get_current_user()
    site = Site.get_admin_or_404(site_id)
    form = InviteForm(request.form)
    if form.validate():
        invite_hash = sha1()
        invite_hash.update(str(site.key()))
        invite_hash.update(os.urandom(8))
        invite_hash.update(form.email.data)
        invite_hash = b32encode(invite_hash.digest()).lower()
        invite = Invitation(
            hash=invite_hash,
            email=form.email.data,
            site=site,
            admin=form.admin.data,
            inviter=user
        )
        invite.put()
        mail.send_mail(
            sender = settings.invite_sender_email,
            to = invite.email,
            subject = '%s invited you to join them on %s' % (user.email(), settings.appname),
            body = render_template('invite_email.txt', invite=invite),
            html = render_template('invite_email.html', invite=invite),
        )
        if request.is_xhr:
            return 'OK'
        flash('Invitation Sent!', 'success')
    else:
        errors = sum(form.errors.values(), [])
        if request.is_xhr:
            return ', '.join(errors)
        for error in errors:
            flash(error, 'error')
        flash(form.email.data, 'error')
    return redirect(url_for('edit_siteusers', site_id=site_id))

@views.route('/site/new', methods=['GET', 'POST'])
@requires_auth
def new_site():
    user = users.get_current_user()
    form = PageForm(request.form)
    if request.method == 'POST':
        if form.validate():
            site = Site(
                name = form.name.data,
                owner = user,
                users = [user],
                admins = [user],
            )
            site.put()
            page = Page.new_page(site, form.name.data, form.url.data)
            new_url = url_for('editor', page_id=page.key().id())
            if request.is_xhr:
                return jsonify(dict(type='success', redirect=new_url))
            else:
                return redirect(new_url)
        elif request.is_xhr:
            return jsonify(dict(type='error', errors=render_template('form_errors.html', form=form)))
    if request.is_xhr:
        return render_template('site_creator.html', form=form)
    return render_template('new_site.html', form=form)

@views.route('/site/<int:site_id>/edit', methods=['GET', 'POST'])
@requires_auth
def edit_site(site_id):
    site = Site.get_admin_or_404(site_id)
    form = SiteForm(request.form, site)
    if request.method == 'POST':
        if form.validate():
            site.name = form.name.data
            site.put()
            if request.is_xhr:
                return 'OK'
        elif request.is_xhr:
            return render_template('form_errors.html', form=form)
    if request.is_xhr:
        return render_template('site_editor.html', form=form, site=site)
    return render_template('edit_site.html', form=form, site=site)

@views.route('/site/<int:site_id>/editusers')
@requires_auth
def edit_siteusers(site_id):
    site = Site.get_admin_or_404(site_id)
    invite_form = InviteForm()
    if request.is_xhr:
        return render_template('siteusers_editor.html', site=site, invite_form=invite_form)
    return render_template('edit_siteusers.html', site=site, invite_form=invite_form)

@views.route('/site/leave', methods=['POST'])
@requires_auth
def leave_site():
    site_id = int(request.form.get('site_id', -1))
    site = Site.get_or_404(site_id)
    user = users.get_current_user()
    them = [u for u in site.users if u.user_id() == user.user_id()]
    for user in them:
        site.users.remove(user)
        if user in site.admins:
            site.admins.remove(user)
    site.put()
    return 'OK'

@views.route('/site/delete', methods=['POST'])
@requires_auth
def delete_site():
    site_id = int(request.form.get('site_id', -1))
    site = Site.get_admin_or_404(site_id)
    site.delete()
    return 'OK'

@views.route('/site/<int:site_id>/remove_user', methods=['POST'])
@requires_auth
def remove_user(site_id):
    site = Site.get_admin_or_404(site_id)
    admin = users.get_current_user()
    user_id = request.form.get('user_id', None)
    if not user_id or admin.user_id() == user_id:
        abort(400)
    remove_admin_only = request.form.get('remove_admin_only', False)
    them = [u for u in site.users if u.user_id() == user_id]
    for user in them:
        if not remove_admin_only:
            site.users.remove(user)
        if user in site.admins:
            site.admins.remove(user)
    site.put()
    return 'OK'

@views.route('/site/<int:site_id>/page/new', methods=['GET', 'POST'])
@requires_auth
def new_page(site_id):
    site = Site.get_admin_or_404(site_id)
    form = PageForm(request.form, site=site)
    if request.method == 'POST':
        if form.validate():
            page = Page.new_page(site, form.name.data, form.url.data)
            new_url = url_for('editor', page_id=page.key().id())
            if request.is_xhr:
                return jsonify(dict(type='success', redirect=new_url))
            return redirect(new_url)
        elif request.is_xhr:
            return jsonify(dict(type='error', errors=render_template('form_errors.html', form=form)))
    if request.is_xhr:
        return render_template('page_creator.html', form=form, site=site)
    return render_template('new_page.html', form=form, site=site)

@views.route('/page/<int:page_id>/edit', methods=['GET', 'POST'])
@requires_auth
def edit_page(page_id):
    page = Page.get_admin_or_404(page_id)
    form = PageForm(request.form, page)
    if request.method == 'POST':
        if form.validate():
            if form.data['url'] != page.url:
                page.queue_preview()
            page.name = form.name.data
            page.url = form.url.data
            page.preview_urls = [Link(url.data) for url in form.preview_urls]
            page.put()
            if request.is_xhr:
                return 'OK'
        elif request.is_xhr:
            return render_template('form_errors.html', form=form)
    if request.is_xhr:
        return render_template('page_editor.html', form=form, page=page)
    return render_template('edit_page.html', form=form, site=page.site, page=page)

@views.route('/page/<int:page_id>/editor')
@requires_auth
def editor(page_id):
    page = Page.get_edit_or_404(page_id)
    user = users.get_current_user()
    client_id = 'page-%d-%s-%s' % (page_id, user.user_id(), b32encode(os.urandom(10)))
    token = gae_channels.create_channel(client_id)
    channel = PageChannel(user=user, page=page, token=token, client_id=client_id)
    channel.put()
    return render_template('editor.html', page=page, channel_token=token)

@views.route('/page/<int:page_id>/preview')
@requires_auth
def page_preview(page_id):
    page = Page.get_edit_or_404(page_id)
    if page.preview_img:
        return _send_file(page.preview_img, 'image/png')
    else:
        return redirect('/static/img/loading-preview.png')

@views.route('/page/<int:page_id>/import', methods=['GET', 'POST'])
@requires_auth
def page_import(page_id):
    page = Page.get_edit_or_404(page_id)
    if request.method == 'POST':
        if 'fOk' in request.form:
            queue_import(page, first_time=True)
            return redirect(url_for('page_import', page_id=page_id))
        else:
            return redirect(url_for('editor', page_id=page_id))
    else:
        if page.import_state == IMPORT_DONE:
            page.import_state = CAN_IMPORT
            page.put()
            return redirect(url_for('editor', page_id=page_id))
        return render_template('page_import.html', page=page)

@views.route('/page/delete', methods=['POST'])
@requires_auth
def delete_page():
    page_id = int(request.form.get('page_id', -1))
    page = Page.get_admin_or_404(page_id)
    page.delete()
    return 'OK'

@views.route('/page/<int:page_id>/style/new', methods=['GET', 'POST'])
@requires_auth
def new_style(page_id):
    page = Page.get_admin_or_404(page_id)
    form = StyleForm(request.form, site=page.site)
    if request.method == 'POST' and form.validate():
        style = Style(
            name = form.name.data,
            site = page.site,
        )
        style.put()
        return redirect(url_for('editor', page_id=page_id))
    return render_template('new_style.html', form=form)

@views.route('/page/<int:page_id>/styles')
@requires_auth
def page_styles(page_id):
    page = Page.get_edit_or_404(page_id)
    return Response(page.styles_json(), content_type='application/json')

@views.route('/style/delete', methods=['POST'])
@requires_auth
def delete_style():
    style_id = int(request.form.get('style_id', -1))
    style = Style.get_admin_or_404(style_id)
    style.delete()
    return 'OK'

@views.route('/guider/saw', methods=['POST'])
@requires_auth
def saw_guider():
    guider_name = request.form.get('guider_name', '')
    if guider_name:
        UserSettings.mark_guider_as_seen(guider_name)
    return 'OK'

@views.route('/example/4/<page_key>')
def example4(page_key):
    page = Page.get_or_404(page_key)
    return render_template('examples/blog-html4.html', page=page)

@views.route('/example/5/<page_key>')
def example5(page_key):
    page = Page.get_or_404(page_key)
    return render_template('examples/blog-html5.html', page=page)

@views.route('/settings/locale', methods=['GET', 'POST'])
def set_locale():
    if request.method == 'POST':
        locale = request.form.get('locale', None)
        if not locale: # Catch all falsy values and set to None
            locale = None
        session['locale'] = locale
        UserSettings.set_locale(locale)
        return redirect(url_for('index'))
    return render_template('edit_locale.html')

@views.route('/proxy/<page_key>/<path:url>')
def proxy(page_key, url):
    return get_html(url, append_head=[{'name': 'script', 'attrs': {'src': url_for('js', page_key=page_key, _external=True)}}])

@views.route('/_check_tags/<page_key>/<path:url>')
def _check_tags(page_key, url):
    return jsonify(check_for_tags(url, page_key))

@views.route('/_migrate', methods=['GET', 'POST'])
@requires_admin
def _migrate():
    from migrations import get_migrations
    schema = SchemaVersion.get_or_insert('current')
    old_version = schema.version
    if request.method == 'POST' and 'fGo' in request.form:
        from migrations import migrate
        migrate(schema)
        return render_template('_migrate_result.html', schema=schema, old_version=old_version)
    elif 'fCancel' in request.form:
        return redirect(url_for('index'))
    return render_template('_migrate.html', schema=schema, migrations=get_migrations()[schema.version+1:])

@views.route('/_whois', methods=['GET', 'POST'])
@requires_admin
def _whois():
    key = request.args.get('key', None)
    email = request.args.get('email', None)
    page = None
    user_sites = None
    if key:
        page = Page.get_or_404(key)
    if email:
        user_sites = Site.gql('WHERE users = :1', User(email))
    if key or email:
        return render_template('_whois_result.html', key=key, page=page, email=email, user_sites=user_sites)
    return render_template('_whois.html')

@views.route('/_stats')
@requires_auth
def _stats():
    if not (users.is_current_user_admin() or users.get_current_user().email().endswith('@fogcreek.com') or request.remote_addr in ['127.0.0.1', '71.190.247.30']):
        abort(404)

    user_count = GqlQuery('SELECT __key__ FROM UserSettings').count(None)
    site_count = GqlQuery('SELECT __key__ FROM Site WHERE example=false').count(None)
    now = datetime.now()
    days = list(reversed([now-timedelta(days) for days in range(14)]))
    day_views = [get_period_and_count('css:all', PeriodType.DAY, day) for day in days]
    day_users = [get_period_and_count('user:all', PeriodType.DAY, day) for day in days]
    day_sites = [get_period_and_count('site:all', PeriodType.DAY, day) for day in days]
    # overwrite today's cached numbers with the live count we just got from the database
    day_users[-1] = day_users[-1][0], user_count
    day_sites[-1] = day_sites[-1][0], site_count

    # get the top referrers
    period_type = PeriodType.DAY
    fetch_limit = 50
    query = LivecountCounter.all().order('-count')
    query.filter('period_type = ', period_type)
    query.filter('period = ', PeriodType.find_scope(period_type, datetime.now()))
    top_counters = query.fetch(fetch_limit)
    top_referrers = []
    for counter in top_counters:
        name = counter.name
        if name.startswith('css:page') and not name.startswith('css:page:www.webputty.net'):
            parts = name.split(':')
            page = None
            preview_size = 0
            published_size = 0
            try:
                page = Page.get(parts[3])
            except Exception:
                logging.warn("_stats counldn't find matching page: %s", parts[3])
            if page:
                preview_size = len(page.compressed_css(True))
                published_size = len(page.compressed_css(False))
            top_referrers.append((parts[2], counter.count, parts[3], preview_size, published_size))

    return render_template('_stats.html', user_count=user_count, site_count=site_count, day_views=day_views, day_users=day_users, day_sites=day_sites, top_referrers=top_referrers)

@views.route('/robots.txt')
def robotstxt():
    return Response(render_template('robots.txt'), content_type='text/plain')

@views.route('/_ah/warmup')
def _warmup():
    """
    Do any warmup necessary, such as priming caches.
    """
    return 'OK'

@views.route('/<path:file>.gif')
@views.route('/<path:file>.png')
@views.route('/<path:file>.jpg')
def image_not_found(file):
    response = make_response(send_from_directory(os.path.join(os.path.dirname(__file__), '../static/img'), '404.png'))
    response.status_code = 404 # make sure we set the correct HTTP status
    return response
