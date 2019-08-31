from datetime import datetime, timedelta, timezone

from flask import request, abort, jsonify, g
from flask_httpauth import HTTPTokenAuth
from flask_restplus import Resource, fields
from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)

from . import api
from .. import app
from ..models import Users

__all__ = (
    "auth",
)

auth = HTTPTokenAuth()

login_model = api.model('Login', {
    'username': fields.String,
    'password': fields.String
})


def gen_auth_token(user: Users, expiration):
    s = Serializer(app.config['SECRET_KEY'], expires_in=expiration)
    return s.dumps({'id': user.id})


@auth.error_handler
def auth_failed():
    return jsonify(message='Unauthorized Access')


@auth.verify_token
def verify_auth_token(token):
    s = Serializer(app.config['SECRET_KEY'])
    try:
        data = s.loads(token)
    except SignatureExpired:
        # Token good, but expired
        return None
    except BadSignature:
        # Bad token
        return None
    g.user = Users.query.get(data['id'])
    return g.user


@api.route('/login')
class LoginResource(Resource):

    @api.expect(login_model)
    def post(self):
        username = request.json.get('username')
        password = request.json.get('password')
        if username is None or password is None:
            abort(400)
        user: Users = Users.query.filter_by(username=username).one_or_none()
        if user is None:
            abort(401, "Username or password was incorrect.")

        if user.password != password:
            abort(401, "Username or password was incorrect.")

        duration = 2.628e+6
        token = gen_auth_token(user, duration)

        delta = timedelta(seconds=duration)
        exp_date = datetime.utcnow() + delta
        exp_date.replace(tzinfo=timezone.utc)

        return '', 204, {
            'Authorization': b"Bearer " + token,
            'Expires': format(exp_date, '%a %s %h %Y %H:%M:%S %Z')
        }


@api.route('/testtoken')
class TestResource(Resource):
    @auth.login_required
    def get(self):
        return {'message': 'Success!'}
