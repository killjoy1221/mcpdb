import functools

from flask import Flask, Blueprint, request, url_for, flash, redirect, g, make_response, abort
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
        if g.user is None:
            raise abort(401)

        return func(*args, **kwargs)

    return decorator


def require_token(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        if g.token is None:
            raise abort(401)
        return func(*args, **kwargs)

    return decorator


from .models import *

# Import later to prevent import errors
from .util import *

app.url_map.converters['version'] = VersionConverter
app.url_map.converters['srgtype'] = SrgTypeConverter
from .api import api_bp

app.register_blueprint(api_bp)

github_token_cookie = 'GitHubToken'
mcpdb_api_token_header = 'MCPDB-API-Token'


@app.before_request
def load_user():
    g.user = None
    if github_token_cookie in request.cookies:
        user = Users.query.filter_by(github_token=request.cookies[github_token_cookie]).first()
        if user is None:
            raise abort(403)
        g.user = user


@app.before_request
def authorize_token():
    if mcpdb_api_token_header in request.headers:
        token = Tokens.query.filter_by(github_token=request.headers[mcpdb_api_token_header]).first()
        if token is None:
            raise abort(403)
        g.token = token


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
