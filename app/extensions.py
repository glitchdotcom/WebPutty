from gettext import gettext as _
import hashlib
from datetime import datetime
import jinja2
from google.appengine.api import users
from flask import request, render_template, render_template_string, url_for
from werkzeug.urls import url_quote
import settings
from app.models import UserSettings
import views
from gae_mini_profiler.templatetags import profiler_includes
from js_css_packages import packages
from docs import doc_list

def context_processor():
    return {
        'users': users,
        'user': users.get_current_user(),
        'debug': settings.debug,
        'debug_profiler_enabled': settings.debug_profiler_enabled,
        'appname': settings.appname,
        'appversion': settings.appversion,
        'url2png': url2png,
        'timesince': timesince,
        'fmt_size': fmt_size,
        'profiler_includes': profiler_includes,
        'guider': render_guider,
        'guider_link': guider_link,
        'js_package': js_package,
        'css_package': css_package,
        'release_notes_flair': release_notes_flair,
        'jquery_url': settings.jquery_url,
        'locale': views._localeselector,
        'available_locales': settings.available_locales,
        'doc_link': doc_link,
        'use_google_cloud_storage': settings.use_google_cloud_storage,
        'google_bucket': settings.google_bucket,
    }

def doc_link(doc_key=None, link_text=None, link_title=None, anchor_name=None, new_window=False):
    if not doc_key:
        doc_key = 'toc'
        if not link_text:
            link_text = _('Documentation')
    slug, text, title = [doc for doc in doc_list if doc[0] == doc_key][0]
    if link_text:
        text = link_text
    if link_title:
        title = link_title
    anchor = target = ''
    if new_window:
        target = ' target="_blank"'
    if anchor_name:
        anchor = '#' + url_quote(anchor_name)
    link = '<a href="%s%s" title="%s"%s>%s</a>' % (url_for('views.docs', doc_key=slug), anchor, title, target, text)
    return jinja2.Markup(render_template_string(link))

def js_package(package_name, scripts_only=False):
    package = packages.javascript[package_name]
    scripts = ""

    if settings.debug:
        list_js = []
        for filename in package["files"]:
            script_path = "'/static/js/%s-package/%s'" % (package_name, filename)
            newscript = "\n"
            # load the last script in this package with a label so callers can wait for it to be loaded.
            # eg. head.js('file1.js', {'my_package': 'last.js'}); allows a template to later do this:
            # head.js('my_package', function() { ... })
            if filename == package["files"][-1]:
                newscript += "{'%s': %s}" % (package_name, script_path)
            else:
                newscript += script_path
            list_js.append(newscript)
        scripts = ",\n".join(list_js)
    else:
        scripts = "{'%s': '/static/js/%s-package/%s'}" % (package_name, package_name, package["hashed-filename"])

    if scripts_only:
        return jinja2.Markup(scripts)
    return jinja2.Markup(("head.js(%s);" % scripts))

def css_package(package_name):
    package = packages.stylesheets[package_name]
    src_dir = "/static/css/%s-package" % package_name

    if settings.debug:
        list_css = []
        for filename in package["files"]:
            list_css.append('<link rel="stylesheet" type="text/css" href="%s/%s" />\n' % (src_dir, filename))
        return jinja2.Markup("".join(list_css))
    else:
        return jinja2.Markup('<link rel="stylesheet" type="text/css" href="%s/%s" />' % (src_dir, package["hashed-filename"]))

def render_guider(guider_name):
    if UserSettings.show_guider(guider_name) or '__on_tour__' in request.args:
        return jinja2.Markup('''
                head('shared', function() {
                    _.delay(show_guider, 250, '%s', true);
                });
        ''' % guider_name)
    else:
        return ''

def guider_link(guider_name, link_text, title_text=''):
    return jinja2.Markup('<a href="#" id="guider_%s" onclick="guiders.hideAll(); show_guider(\'%s\', false); return false;" title="%s">%s</a>' % (guider_name, guider_name, title_text, link_text))

def release_notes_flair():
    if not UserSettings.has_seen_version(settings.appversion_raw):
        return jinja2.Markup(render_template('release_notes_flair.html'))
    return ''

def url2png(url, bounds=None):
    public_key = settings.url2png['user']
    if not bounds:
        bounds = settings.url2png['bounds']
    token = hashlib.md5( "%s+%s" % (settings.url2png['password'], url) ).hexdigest()
    return "//api.url2png.com/v3/%s/%s/%s/%s" % (public_key, token, bounds, url)

def timesince(dt, past_="ago", future_="from now", default="just now"):
    """
    Returns string representing "time since"
    or "time until" e.g.
    3 days ago, 5 hours from now etc.
    """
    now = datetime.utcnow()
    if now > dt:
        diff = now - dt
        dt_is_past = True
    else:
        diff = dt - now
        dt_is_past = False

    periods = (
        (diff.days / 365, "year", "years"),
        (diff.days / 30, "month", "months"),
        (diff.days / 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds / 3600, "hour", "hours"),
        (diff.seconds / 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    )

    for period, singular, plural in periods:
        if period:
            return "%d %s %s" % (period,
                                 singular if period == 1 else plural,
                                 past_ if dt_is_past else future_)

    return default

def fmt_size(num):
    """
    Returns a humanized version of the number of bytes passed in.
    E.g., fmt_size(1024) => '1.0 KB'
    """
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            formatter = '%3.1f %s' if x != 'bytes' else '%3.0f %s'
            return formatter % (num, x)
        num /= 1024.0
