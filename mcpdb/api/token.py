import random
import string

from flask import jsonify, g, request, abort
from flask_restplus import Resource, fields

from . import api
from .. import db
from ..util import require_user
from ..models import *

sysrand = random.SystemRandom()
valid_token_chars = string.digits + string.ascii_letters

token_model = api.model("Token", {
    'token': fields.String
})


@api.route('/token')
class TokenResource(Resource):
    @require_user
    @api.marshal_with(token_model)
    def get(self):
        user: Users = g.user
        return jsonify([{
            'token': t.token,
        } for t in user.tokens])

    @require_user
    @api.marshal_with(token_model)
    def post(self):
        user: Users = g.user

        # Generate a secure random string
        token_string = ''.join(sysrand.choices(valid_token_chars, k=24))

        token = Tokens(
            user=user,
            token=token_string)

        user.tokens.append(token)
        db.session.commit()

        return jsonify(
            token=token.token,
            description=token.description
        )

    @require_user
    def delete(self):
        if 'token_id' in request.json:
            token_id = request.json['token_id']
        else:
            raise abort(400)

        user: Users = g.user
        token = Tokens.query.filter_by(user=user, id=token_id).one_or_none()

        if token is None:
            raise abort(404)

        db.session.delete(token)
        db.session.commit()

        abort(204)
