from logging import Formatter, Filter, StreamHandler
import scss
import settings
import json
from datetime import datetime
from StringIO import StringIO
from google.appengine.ext import db
from google.appengine.api import users as gae_users
from google.appengine.api import taskqueue
from google.appengine.api import channel as gae_channels
from google.appengine.api import files
from google.appengine.api.datastore_errors import BadKeyError
from flask import abort, url_for, render_template

def dt_handler(obj):
    if isinstance(obj, datetime):
        return obj.isoformat() + 'Z'
    return None

class ExceptionFilter(Filter):
    def filter(self, record):
        if record.getMessage().lower().startswith('exception'):
            return 0
        return 1

# Old and dead...
class UserGroup(db.Model):
    name = db.StringProperty(required=True)
    users = db.ListProperty(gae_users.User)
    admins = db.ListProperty(gae_users.User)

class SchemaVersion(db.Model):
    version = db.IntegerProperty(required=True, default=0)

class Site(db.Model):
    name = db.StringProperty(required=True)
    owner = db.UserProperty()
    users = db.ListProperty(gae_users.User)
    admins = db.ListProperty(gae_users.User)
    example = db.BooleanProperty(default=False)

    def delete(self):
        for page in self.page_set.fetch(10000):
            page.delete()
        db.delete(self)

    @staticmethod
    def get_or_404(id):
        site = Site.get_by_id(id)
        if not site or gae_users.get_current_user() not in site.users:
            abort(404)
        return site

    @staticmethod
    def get_admin_or_404(id):
        site = Site.get_by_id(id)
        if not site or gae_users.get_current_user() not in site.admins:
            abort(404)
        return site

class Invitation(db.Model):
    hash = db.StringProperty(required=True)
    site = db.ReferenceProperty(Site, required=True)
    email = db.EmailProperty(required=True)
    admin = db.BooleanProperty(default=False)
    inviter = db.UserProperty(required=True)
    has_been_logged_out = db.BooleanProperty(default=False)

class Page(db.Model):
    name = db.StringProperty(required=True)
    url = db.LinkProperty(required=True)
    site = db.ReferenceProperty(Site)
    _styles = db.ListProperty(db.Key)
    channels = db.ListProperty(db.Key)
    preview_img = db.BlobProperty(required=False, default=None)
    preview_urls = db.ListProperty(db.Link, default=None) # *additional* preview urls
    import_state = db.IntegerProperty(default=0)
    on_cdn = db.BooleanProperty(default=False)

    _style_cache = None
    def _set_styles(self, styles):
        self._style_cache = styles
        self._styles = [style.key() for style in styles]
    def _get_styles(self):
        if not self._style_cache:
            self._style_cache = [Style.get(k) for k in self._styles]
        return self._style_cache
    styles = property(_get_styles, _set_styles)

    def delete(self):
        for key in self.channels:
            channel = PageChannel.get(key)
            if channel:
                channel.send_message({'cmd': 'lock'})
                channel.delete()
        for style in self.styles:
            style.delete()
        db.delete(self)

    def clean_channels(self):
        stale = []
        for key in self.channels:
            channel = PageChannel.get(key)
            if not channel or channel.is_stale():
                stale.append(key)
        if stale:
            for key in stale:
                self.channels.remove(key)
                channel = PageChannel.get(key)
                if channel:
                    # If the channel is still here, it's probably stale.
                    # Send 'lock' and remove, so it can't clobber anyone else.
                    channel.send_message({'cmd': 'lock'})
                    channel.delete()
            self.put()

    def get_channels(self):
        channels = []
        stale = []
        for key in self.channels:
            channel = PageChannel.get(key)
            if channel:
                channels.append(channel)
            else:
                stale.append(key)
        if stale:
            for key in stale:
                self.channels.remove(key)
            self.put()
        return channels

    def update_locks(self):
        owner = None
        channels = self.get_channels()
        if channels:
            owner_user = channels[0].user
            owner = dict(name=owner_user.nickname(), email=owner_user.email())
            channels[0].send_message(dict(cmd='unlock', user=owner))
        lock_msg = dict(cmd='lock', user=owner)
        for channel in channels[1:]:
            channel.send_message(lock_msg)

    def add_channel(self, channel):
        self.remove_channel(channel)
        self.channels.append(channel.key())
        self.put()

    def add_channel_first(self, channel):
        self.remove_channel(channel)
        self.channels.insert(0, channel.key())
        self.put()

    def remove_channel(self, channel, delete=False):
        if channel.key() in self.channels:
            self.channels.remove(channel.key())
            self.put()
        if delete:
            channel.delete()

    def put(self, *args, **kwargs):
        self._set_styles(self.styles)
        super(Page, self).put(*args, **kwargs)

    def queue_preview(self):
        taskqueue.add(queue_name='fetch-preview', url=url_for('tasks.fetch_preview'), params={'page_key': self.key()})

    def queue_upload(self):
        taskqueue.add(queue_name='upload-css', url=url_for('tasks.upload_style'), params={'page_key': self.key()})

    def queue_refresh(self):
        self.queue_upload()
        self.queue_preview()

    def _css(self, preview, compress):
        css = StringIO()
        for style in self.styles:
            rev = style.preview_rev if (preview and style.preview_rev) else style.published_rev
            if compress:
                css.write(rev.compressed)
            else:
                css.write(scss.Scss().compile('@option compress:no;' + rev.raw))
        return css.getvalue()

    def compressed_css(self, preview):
        return self._css(preview, compress=True)

    def uncompressed_css(self, preview):
        return self._css(preview, compress=False)

    def last_modified(self, preview):
        max_last_edit = datetime.min
        for style in self.styles:
            rev = style.preview_rev if (preview and style.preview_rev) else style.published_rev
            max_last_edit = max(max_last_edit, rev.dt_last_edit)
        return max_last_edit

    def styles_json(self):
        # NOTE: It is okay to return an array here because we only display this
        # to users via editor.html. If we ever return this directly as the
        # response, we'll want to wrap it to avoid the exploit described at
        # http://haacked.com/archive/2009/06/25/json-hijacking.aspx
        styles_obj = [style.json_obj() for style in self.styles]
        return json.dumps(styles_obj, default=dt_handler, sort_keys=True, indent=4*' ' if settings.debug else None)

    def upload_to_cdn(self):
        if not settings.use_google_cloud_storage:
            return
        path = files.gs.create('/gs/%s/%s.css' % (settings.google_bucket, str(self.key())), mime_type='text/css', acl='public-read', cache_control='private,max-age=300')
        try:
            fd = files.open(path, 'a')
            fd.write(self.compressed_css(False).encode('utf-8'))
            self.on_cdn = True
            self.save()
        except Exception:
            self.on_cdn = False
            self.save()
            raise
        finally:
            fd.close()
            files.finalize(path)

    @staticmethod
    def get_or_404(key):
        page = None
        if isinstance(key, int) or (isinstance(key, basestring) and key.isdigit()):
            page = Page.get_by_id(int(key))
        else:
            try:
                key_obj = db.Key(key)
            except BadKeyError:
                abort(404)
            if(key_obj.kind() == 'Style'):
                page = Page.gql('WHERE _styles=:1', key_obj).get()
            else:
                page = Page.get(key)
        if not page:
            abort(404)
        return page

    @staticmethod
    def get_edit_or_404(page_id):
        page = Page.get_or_404(page_id)
        if gae_users.get_current_user() not in page.site.users:
            abort(404)
        return page
    
    @staticmethod
    def get_admin_or_404(page_id):
        page = Page.get_or_404(page_id)
        site = page.site
        if not site or gae_users.get_current_user() not in site.admins:
            abort(404)
        return page

    @staticmethod
    def new_page(site, name, url):
        '''
        Do all the work in adding a new page to a site.
        '''
        style = Style(name = name, site = site)
        style.put()
        first_rev = StyleRevision(parent=style)
        first_rev.raw = render_template('first_run.css')
        first_rev.put()
        style.published_rev = first_rev
        style.put()
        page = Page(
            name = name,
            url = url,
            site = site,
            _styles = [style.key()]
        )
        page.put()
        page.queue_refresh()
        return page

class StyleRevision(db.Model):
    # parent = Style
    rev = db.IntegerProperty(required=True, default=0)
    dt_created = db.DateTimeProperty(auto_now_add=True)
    dt_last_edit = db.DateTimeProperty(auto_now=True)
    raw = db.TextProperty(required=False, default='')
    compressed = db.TextProperty(required=False, default=None)
    # Old and dead...
    css = db.TextProperty(required=False)
    _cached = db.TextProperty(required=False)

    def update(self, raw):
        self.raw = raw
        log = StringIO()
        handler = StreamHandler(log)
        handler.addFilter(ExceptionFilter())
        handler.setFormatter(Formatter('<span class="level">%(levelname)s</span>: <span class="message">%(message)s</span><br />'))
        scss.log.addHandler(handler)
        self.compressed = scss.Scss().compile(self.raw)
        scss.log.removeHandler(handler)
        handler.flush()
        self.put()
        return log.getvalue()

class Style(db.Model):
    site = db.ReferenceProperty(Site)
    name = db.StringProperty(required=True)
    published_rev = db.ReferenceProperty(StyleRevision, default=None, collection_name='style_published')
    preview_rev = db.ReferenceProperty(StyleRevision, default=None, collection_name='style_preview')

    # Old and dead
    user_group = db.ReferenceProperty(UserGroup)
    url = db.LinkProperty(required=False)

    def delete(self, *args, **kwargs):
        revisions = StyleRevision.all(keys_only=True).ancestor(self).fetch(10000)
        db.delete(revisions)
        db.delete(self)

    def json_obj(self):
        if self.preview_rev:
            preview_rev = self.preview_rev
        else:
            if not self.published_rev:
                rev = StyleRevision(parent=self)
                rev.put()
                self.published_rev = rev
                self.put()
            preview_rev = self.published_rev
        return {
            'id': self.key().id(),
            'name': self.name,
            'preview_scss': preview_rev.raw,
            'preview_dt_last_edit': preview_rev.dt_last_edit,
            'published_scss': self.published_rev.raw,
            'published_dt_last_edit': self.published_rev.dt_last_edit,
        }

    @staticmethod
    def get_or_404(style_id):
        if isinstance(style_id, basestring) and not style_id.isdigit():
            style = Style.get(style_id)
        else:
            style = Style.get_by_id(style_id)
        if not style:
            abort(404)
        return style

    @staticmethod
    def get_edit_or_404(style_id):
        style = Style.get_or_404(style_id)
        if gae_users.get_current_user() not in style.site.users:
            abort(404)
        return style

    @staticmethod
    def get_admin_or_404(style_id):
        style = Style.get_or_404(style_id)
        site = style.site
        if not site or gae_users.get_current_user() not in site.admins:
            abort(404)
        return style

class PageChannel(db.Model):
    user = db.UserProperty(required=True)
    page = db.ReferenceProperty(Page, required=True)
    token = db.StringProperty(required=True)
    client_id = db.StringProperty(required=True)
    dt_connected = db.DateTimeProperty(auto_now_add=True)
    dt_last_update = db.DateTimeProperty(auto_now_add=True)

    def is_stale(self):
        return (datetime.utcnow() - self.dt_last_update).seconds > 3600

    def send_message(self, message):
        if not isinstance(message, basestring):
            message = json.dumps(message, default=dt_handler, sort_keys=True, indent=4*' ' if settings.debug else None)
        gae_channels.send_message(self.client_id, message)

    @staticmethod
    def get_or_404(token=None, client_id=None):
        channel = None
        if token:
            channel = PageChannel.gql('WHERE token=:1', token).get()
        elif client_id:
            channel = PageChannel.gql('WHERE client_id=:1', client_id).get()
        if not channel:
            abort(404)
        return channel

class UserSettings(db.Model):
    user = db.UserProperty(required=True)
    seen_example = db.BooleanProperty(default=False)
    seen_guiders = db.StringListProperty()
    # the last version (list of ints) this person has viewed the release notes for
    seen_version = db.ListProperty(int, default=None)
    locale = db.StringProperty(default=None)
    chimped = db.BooleanProperty(default=False)

    @staticmethod
    def has_seen_example():
        user = gae_users.get_current_user()
        if not user or not user.user_id():
            raise Exception("Logged in user expected")
        settings = UserSettings.get_or_insert(user.user_id(), user=user)
        return settings.seen_example

    @staticmethod
    def mark_example_as_seen():
        user = gae_users.get_current_user()
        if not user or not user.user_id():
            raise Exception("Logged in user expected")
        settings = UserSettings.get_or_insert(user.user_id(), user=user)
        settings.seen_example = True
        settings.put()

    @staticmethod
    def show_guider(guider_name):
        user = gae_users.get_current_user()
        if not user or not user.user_id():
            return False
        settings = UserSettings.get_or_insert(user.user_id(), user=user)
        return (guider_name not in settings.seen_guiders)

    @staticmethod
    def mark_guider_as_seen(guider_name):
        user = gae_users.get_current_user()
        if not user or not user.user_id():
            return
        settings = UserSettings.get_or_insert(user.user_id(), user=user)
        if not guider_name in settings.seen_guiders:
            settings.seen_guiders.append(guider_name)
            settings.put()

    @staticmethod
    def has_seen_version(version):
        user = gae_users.get_current_user()
        if not user or not user.user_id():
            return True # don't bother displaying "new version available" to non-authenticated users
        settings = UserSettings.get_or_insert(user.user_id(), user=user)
        if not settings.seen_version:
            settings.seen_version = [0, 0, 0]
            settings.put()
        return settings.seen_version >= version

    @staticmethod
    def mark_version_as_seen(version):
        user = gae_users.get_current_user()
        if not user or not user.user_id():
            return
        settings = UserSettings.get_or_insert(user.user_id(), user=user)
        settings.seen_version = version
        settings.put()

    @staticmethod
    def get_locale():
        user = gae_users.get_current_user()
        if not user or not user.user_id():
            return None
        settings = UserSettings.get_or_insert(user.user_id(), user=user)
        return settings.locale

    @staticmethod
    def set_locale(locale):
        user = gae_users.get_current_user()
        if not user or not user.user_id():
            return
        settings = UserSettings.get_or_insert(user.user_id(), user=user)
        settings.locale = locale
        settings.put()

class Importer(db.Model):
    page = db.ReferenceProperty(Page)
    urls = db.StringListProperty()
    style = db.TextProperty()
    errors = db.StringListProperty()

class Credential(db.Model):
    name = db.StringProperty()
    user = db.StringProperty(default='')
    passwd = db.StringProperty(default='')
    api_key = db.StringProperty(default='')
