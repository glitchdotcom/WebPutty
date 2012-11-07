import json
from functools import wraps
from flask import Response, redirect, request
from google.appengine.api import users

def requires_auth(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not users.get_current_user():
            return redirect(users.create_login_url(request.path))
        return func(*args, **kwargs)
    return wrapper

def requires_admin(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not users.get_current_user() or not users.is_current_user_admin():
            return redirect(users.create_login_url(request.path))
        return func(*args, **kwargs)
    return wrapper

def as_json(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        if isinstance(res, Response):
            return res
        return json.dumps(res)
    return wrapper
