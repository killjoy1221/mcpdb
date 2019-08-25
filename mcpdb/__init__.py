import functools

from flask import Flask, request, url_for, flash, redirect, g, make_response
from flask_github import GitHub
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, instance_relative_config=True)

app.config.from_object('config')
app.config.from_pyfile('config.py')

db = SQLAlchemy(app)
github = GitHub(app)


def require_user(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        print("require_user")
        if g.user is None:
            raise Unauthorized("Endpoint requires authorization")

        return func(*args, **kwargs)

    return decorator


# Import later to prevent import errors
from .util import *
from .exc import *
from .models import *
from .views.api import api

app.url_map.converters['version'] = VersionConverter

app.register_blueprint(api, url_prefix='/api')

github_token_cookie = 'GitHubToken'


@app.before_request
def load_user():
    g.user = None
    if github_token_cookie in request.cookies:
        user = Users.query.filter_by(github_token=request.cookies[github_token_cookie]).first()
        if user is None:
            raise Forbidden("Authorization failed")
        g.user = user


@app.route('/login')
def login():
    return github.authorize()


@app.route('/github-callback')
@github.authorized_handler
def authorized(oauth_token):
    next_url = request.args.get('next') or url_for('index')
    if oauth_token is None:
        flash("Authorization failed")
        return redirect(next_url)

    user = Users.query.filter_by(github_token=oauth_token).first()
    if user is None:
        user = Users(github_token=oauth_token)
        db.session.add(user)

    user.github_token = oauth_token
    db.session.commit()

    resp = make_response(redirect(next_url))
    resp.set_cookie(github_token_cookie, value=oauth_token)
    return resp


@github.access_token_getter
def token_getter():
    user: Users = g.user
    token: Tokens = g.token
    if user is None and token is not None:
        user = token.user
    if user is not None:
        return user.github_token
