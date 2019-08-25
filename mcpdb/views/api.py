import functools
import random
import string
import logging
from typing import Type, List

from flask import Blueprint, request, jsonify, g, abort

from mcpdb import require_user, db
from mcpdb.exc import *
from mcpdb.models import *
from mcpdb.permissions import *

api = Blueprint('api', __name__, url_prefix='/api')

sysrand = random.SystemRandom()
valid_token_chars = string.digits + string.ascii_letters

mcpdb_api_token_header = 'MCPDB-API-Token'


@api.route('/token')
@require_user
def get_tokens():
    user: Users = g.user
    return jsonify([{
        'id': t.id,
        'description': t.description,
        'permissions': [p.name for p in t.permissions]
    } for t in user.tokens])


@api.route('/token', methods=["POST"])
@require_user
def new_token():
    user: Users = g.user
    perms: List[str] = request.json['permissions']
    descr: str = request.json['description']

    if not perms or not descr:
        return abort(400, "Json properties 'permissions' and 'description' are required")

    bad_perms = list(filter(lambda p: p not in all_permissions, perms))
    if bad_perms:
        raise BadRequest(f"Requested permissions are not valid: {bad_perms}")

    bad_perms = list(filter(lambda p: p not in [up.name for up in user.permissions], perms))
    if bad_perms:
        raise Forbidden(f"Can only add permissions you have: {bad_perms}")

    # Generate a secure random string
    token_string = ''.join(sysrand.choices(valid_token_chars, k=24))

    token = Tokens(
        user=user,
        description=descr,
        token=token_string,
        permissions=[TokenPermissions(p) for p in perms])

    user.tokens.append(token)
    db.session.commit()

    return jsonify(
        token_id=token.id,
        token=token.token,
        description=token.description
    )


@api.route('/token', methods=["DELETE"])
@require_user
def del_token():
    try:
        token_id = request.json['token_id']
    except KeyError:
        raise BadRequest("Bad user input: token_id is required")

    user: Users = g.user
    token = Tokens.query.filter_by(user=user, id=token_id).one_or_none()

    if token is None:
        raise NotFound(f"No token with id {token_id}")

    db.session.delete(token)

    return jsonify(
        token_id=token.id
    )


@api.before_request
def authorize_token():
    if mcpdb_api_token_header in request.headers:
        token = Tokens.query.filter_by(github_token=request.headers[mcpdb_api_token_header]).first()
        if token is None:
            raise Forbidden("Invalid API token")
        g.token = token


def require_token(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        if g.token is None:
            raise Unauthorized("Endpoint requires authorization.")
        return func(*args, **kwargs)

    return decorator


@api.route('/class/<version:version>/<name>')
def get_class_info(version, name):
    info = Classes.query.filter_by(version=version, name=name.replace('.', '/')).one_or_none()

    if info is None:
        raise NotFound("Class does not exist.")
    return jsonify(info.to_json())


def _init_endpoints():
    def init_endpoint(name, table, history):
        @api.route(f'/{name}/<version:version>/<srg>', endpoint=f'get_{name}_info')
        def _get_info(version, srg):
            return get_info(version, srg, table)

        @api.route(f'/{name}/<version:version>/<srg>', methods=["PUT"], endpoint=f'set_{name}_info')
        @require_token
        def _set_info(version, srg):
            return set_info(version, srg, table, history)

        @api.route(f'/{name}/<version:version>/<srg>/history', endpoint=f'get_{name}_history')
        def _get_history(version, srg):
            return get_history(version, srg, history)

    methods = ("method", Methods, MethodHistory)
    fields = ("field", Fields, FieldHistory)
    params = ("param", Parameters, ParameterHistory)

    for endpoint in methods, fields, params:
        # Wrap definitions in another function to prevent variable changes
        init_endpoint(*endpoint)


_init_endpoints()
del _init_endpoints

Table = Union[Fields, Methods, Parameters]
History = Union[FieldHistory, MethodHistory, ParameterHistory]


def get_info(version, srg, table: Type[Table]):
    info = table.query.filter_by(version=version, srg=srg).one_or_none()

    if info is None:
        raise NotFound("SRG name does not exist or has no name")
    return jsonify(info.to_json())


def set_info(version, srg, table: Type[Table], history: Type[History]):
    try:
        mcp = request.json['name']
        force = request.json.get('force', False)
    except KeyError:
        raise BadRequest("Bad user input")

    token: Tokens = g.token

    if force and not check_permission(token, overwrite_name):
        raise Forbidden("Only admins can use the force parameter")

    info = table.query.filter_by(version=version, srg=srg).one_or_none()
    if info is None:
        raise NotFound("SRG name does not exist or has no name")

    if info.locked and not force:
        raise Forbidden('This name is locked and can only be changed by an admin')

    old_mcp = info.mcp

    if info.mcp == mcp:
        return jsonify(
            changed=False,
            old_name=old_mcp
        )

    info.last_changed = history(
        version=version,
        srg=srg,
        mcp=mcp,
        changed_by=token.user
    )

    return jsonify(
        changed=True,
        old_name=old_mcp,
    )


def get_history(version, srg, table: Type[History]):
    history = table.query.filter_by(version=version, srg=srg).all()
    return jsonify([m.to_json() for m in history])


@api.errorhandler(BaseHttpError)
def bad_request(e: BaseHttpError):
    return e.response


@api.errorhandler(Exception)
def handle_server_error(error: Exception):
    logging.exception("Caught exception while processing request")
    return InternalServerError(f"An exception occurred while processing the request. {error}").response
