import logging
import simplejson
import os

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp

from gae_mini_profiler import profiler

register = webapp.template.create_template_register()

@register.simple_tag
def profiler_includes_request_id(request_id, show_immediately = False):
    if not request_id:
        return ""

    path = os.path.join(os.path.dirname(__file__), "templates/headjs_includes.html")
    return template.render(path, {
        "request_id_js": simplejson.dumps(request_id),
        "js_path": "/gae_mini_profiler/static/js/profiler.js",
        "css_path": "/gae_mini_profiler/static/css/profiler.css",
        "show_immediately_js": simplejson.dumps(show_immediately),
    })

@register.simple_tag
def profiler_includes():
    return profiler_includes_request_id(profiler.request_id)
