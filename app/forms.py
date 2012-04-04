from wtforms.ext.appengine.db import model_form
from wtforms import form, fields, validators
from models import Style, Invitation, Site

SiteForm = model_form(Site, only=['name'])

StyleForm = model_form(Style, only=['name'])

InviteForm = model_form(Invitation, only=['email', 'admin'])

def add_protocol(url):
    if not url.startswith('http://') and not url.startswith('https://'):
        return 'http://' + url
    else:
        return url

class PageForm(form.Form):
    name = fields.TextField('Name', [validators.required(), validators.length(max=500)])
    url = fields.TextField('URL', [validators.required(), validators.URL(require_tld=False), validators.length(max=1024)])
    preview_urls = fields.FieldList(fields.TextField('Additional preview URLs', [validators.URL(require_tld=False), validators.length(max=1024)]))

    def validate(self):
        self.url.data = add_protocol(self.url.data)
        for ix in range(len(self.preview_urls)):
            self.preview_urls[ix].data = add_protocol(self.preview_urls[ix].data)
        return form.Form.validate(self)
