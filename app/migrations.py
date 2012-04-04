import logging
import traceback
from models import StyleRevision, UserGroup, Site, Style, Page, Credential

_migrations = []
def migration(f):
    _migrations.append(f)
    return f

@migration
def initial_migration():
    pass

@migration
def fix_css_naming():
    for rev in StyleRevision.all():
        if hasattr(rev, 'css'):
            rev.update(rev.css)

@migration
def rename_usergroup_site():
    for group in UserGroup.all():
        site = Site(name=group.name.replace(' - User Group', ''), users=group.users, admins=group.admins)
        site.put()
        for style in group.style_set:
            style.site = site
            style.put()

@migration
def add_pages():
    for style in Style.all():
        page = Page(
            name = style.name,
            url = style.url,
            site = style.site,
            _styles = [style.key()],
        )
        page.put()

@migration
def add_channels_to_pages():
    for page in Page.all():
        page.channels = []
        page.put()

@migration
def add_example_sites():
    for site in Site.all():
        site.owner = site.admins[0]
        site.put()

@migration
def queue_preview_imgs():
    for page in Page.all():
        page.queue_preview()

@migration
def add_creds():
    cred = Credential(name='empty')
    cred.put()

def get_migrations():
    return [f.func_name for f in _migrations]

def migrate(schema):
    for i in range(schema.version+1, len(_migrations)):
        f_migration = _migrations[i]
        try:
            f_migration()
            schema.version = i
            schema.put()
        except Exception, e:
            logging.error('Failed while running migration #%d `%s`', i, f_migration.func_name)
            logging.error(e)
            logging.error(traceback.format_exc())
            raise

