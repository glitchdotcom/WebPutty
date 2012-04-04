"""
Flask Documentation:       http://flask.pocoo.org/docs/
Jinja2 Documentation:      http://jinja.pocoo.org/2/documentation/
Werkzeug Documentation:    http://werkzeug.pocoo.org/documentation/
GAE Python Documentation:  http://code.google.com/appengine/docs/python/

This file creates your application.
"""

from flask import Flask
from views import views, _localeselector, _timezoneselector
from rpc import rpc
from tasks import tasks
import settings
from flaskext.babel import Babel


def create_app():
    """
    Create your application. Files outside the app directory can import
    this function and use it to recreate your application -- both
    bootstrap.py and the `tests` directory do this.
    """
    app = Flask(__name__)
    app.config.from_object(settings)
    babel = Babel(app, configure_jinja=True)
    babel.localeselector(_localeselector)
    babel.timezoneselector(_timezoneselector)
    app.register_module(views)
    app.register_module(rpc)
    app.register_module(tasks)
    app.secret_key = settings.secret_key
    return app
