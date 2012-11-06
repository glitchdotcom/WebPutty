from __future__ import with_statement

import functools
import os
import sys
import webbrowser
import zipfile
from fabric.api import env, local, prompt

import compress

#Some environment information to customize
if os.name == 'posix':
    APPENGINE_PATH = '/Applications/GoogleAppEngineLauncher.app/Contents/Resources/GoogleAppEngine-default.bundle/Contents/Resources/google_appengine'
    PYTHON = '/usr/bin/python2.7'
else:
    APPENGINE_PATH = r'C:\Program Files (x86)\Google\google_appengine'
    PYTHON = r'C:\Python27\python.exe'
APPENGINE_APP_CFG = os.path.join(APPENGINE_PATH, 'appcfg.py')
print APPENGINE_APP_CFG

env.gae_src = os.path.dirname(__file__)

#default values
env.dryrun = False

EXTRA_PATHS = [
  APPENGINE_PATH,
  os.path.join(APPENGINE_PATH, 'lib', 'antlr3'),
  os.path.join(APPENGINE_PATH, 'lib', 'django'),
  os.path.join(APPENGINE_PATH, 'lib', 'fancy_urllib'),
  os.path.join(APPENGINE_PATH, 'lib', 'ipaddr'),
  os.path.join(APPENGINE_PATH, 'lib', 'webob'),
  os.path.join(APPENGINE_PATH, 'lib', 'yaml', 'lib'),
]

sys.path = EXTRA_PATHS + sys.path

from google.appengine.api import appinfo

def _include_appcfg(func):
    '''Decorator that ensures the current Fabric env has a GAE app.yaml config
    attached to it.'''
    @functools.wraps(func)
    def decorated_func(*args, **kwargs):
        if not hasattr(env, 'app'):
            appcfg = appinfo.LoadSingleAppInfo(open(os.path.join(env.gae_src, 'app.yaml')))
            env.app = appcfg
        return func(*args, **kwargs)
    return decorated_func

def dryrun():
    env.dryrun = True

@_include_appcfg
def deploy():
    env.deploy_path = env.gae_src

    compress_js(env.deploy_path)
    compress_css(env.deploy_path)
    ziplibs(env.deploy_path)
    _clean_babel()

    if not env.dryrun:
        print 'Deploying %s' % env.app.version
        local('%s "%s" -A %s -V %s --oauth2 update %s' % (PYTHON, APPENGINE_APP_CFG, env.app.application, env.app.version, env.deploy_path), capture=False)
        webbrowser.open('https://%s.appspot.com/' % env.app.application)
    else:
        print 'This is where we\'d actually deploy to App Engine, but this is a dryrun so we skip that part.'

    clean_packages(env.deploy_path)

def compress_js(path=None):
    if not path: path = env.gae_src
    print 'Compressing JavaScript'
    compress.compress_all_javascript(path)

def compress_css(path=None):
    if not path: path = env.gae_src
    print 'Compressing stylesheets'
    compress.compress_all_stylesheets(path)

def clean_packages(base_path=None):
    compress.revert_js_css_hashes(base_path)

def update_translations():
    local('pybabel extract -F babel.cfg -o app/messages.pot --project=WebPutty --copyright-holder="Fog Creek Software, Inc." --msgid-bugs-address=customer-service@fogcreek.com app')
    local('pybabel update -i app/messages.pot -d app/translations')
    _update_piglatin()
    _update_english()
    local('pybabel compile -d app/translations')

def add_locale():
    prompt('Locale:', 'locale')
    if env.locale:
        local('pybabel init -i app/messages.pot -d app/translations -l %s' % env.locale)
    else:
        print 'You must enter a locale.'

def _update_english():
    from babel.messages.pofile import read_po, write_po
    from babel.messages.catalog import Catalog
    with open('app/messages.pot', 'r') as f:
        template = read_po(f)
    catalog = Catalog()
    for message in template:
        catalog.add(message.id, message.id, locations=message.locations)
    with open('app/translations/en/LC_MESSAGES/messages.po', 'w') as f:
        write_po(f, catalog)
    with open('app/translations/en_US/LC_MESSAGES/messages.po', 'w') as f:
        write_po(f, catalog)

def _update_piglatin():
    from babel.messages.pofile import read_po, write_po
    from babel.messages.catalog import Catalog
    with open('app/messages.pot', 'r') as f:
        template = read_po(f)
    catalog = Catalog()
    for message in template:
        trans = ' '.join([_piglatin_translate(w) for w in message.id.split(' ')])
        catalog.add(message.id, trans, locations=message.locations)
    with open('app/translations/aa/LC_MESSAGES/messages.po', 'w') as f:
        write_po(f, catalog)

def _piglatin_translate(word):
    """ convert one word into pig latin """ 
    word = unicode(word)
    m = len(word)
    vowels = "a", "e", "i", "o", "u", "y" 
    if m < 3 or word == "the" or word.startswith('%'): # short words are not converted 
        return word
    else:
        for i in vowels:
            if word.find(i) < m and word.find(i) != -1:
                m = word.find(i)
        if m==0:
            return word + u"way" 
        else:
            return word[m:] + word[:m] + u"ay" 

def _clean_babel():
    from settings import available_locales
    locale_codes = [t[0] for t in available_locales]
    if not env.deploy_path:
        return
    print 'Cleaning up unused localedata.'
    localedata_dir = os.path.join(env.deploy_path, 'libs', 'babel', 'localedata')
    for name in os.listdir(localedata_dir):
        remove = True
        for code in locale_codes:
            if name.startswith(code):
                remove = False
                break
        if remove:
            os.unlink(os.path.join(localedata_dir, name))

def ziplibs(root_dir=None):
    if not root_dir:
        root_dir = os.path.abspath(os.path.dirname(__file__))
    to_zip = os.path.join(root_dir, 'ziplibs')
    print 'Cleaning %s of pyc files.' % to_zip
    def rem_ext(ext, dirname, names):
        for name in names:
            if name.endswith(ext):
                os.unlink(os.path.join(dirname, name))
    os.path.walk(to_zip, rem_ext, '.pyc')
    print 'Zipping ziplibs.'
    zip_file = zipfile.ZipFile(to_zip + '.zip', 'w', compression=zipfile.ZIP_DEFLATED)
    def add_file(args, dir_name, names):
        zip_file, common_base = args
        for name in names:
            zip_file.write(os.path.join(dir_name, name), os.path.join(dir_name[len(common_base):], name))
    os.path.walk(to_zip, add_file, (zip_file, os.path.dirname(to_zip)))
    zip_file.close()

def lint():
    local('pylint --rcfile=.pylintrc app')
