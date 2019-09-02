import string

import sqlalchemy.orm.exc
from flask import abort, request, g
from flask_restplus import Resource, fields

from . import api, auth
from .. import db
from ..models import *
from ..util import *

__all__ = ()

base_model = api.model('Srg Named', {
    'version': fields.String,
    'obf_name': fields.String,
    'srg_name': fields.String
})

field_model = api.inherit('Field', base_model, {
    'mcp_name': fields.String(attribute='last_change.mcp_name'),
    'owner': fields.String(attribute='owner.srg_name'),
    'locked': fields.Boolean
})
param_model = api.inherit('Parameter', field_model, {
    'index': fields.Integer,
    'type': fields.String})

method_model = api.inherit('Method', field_model, {
    'descriptor': fields.String,
    'parameters': fields.Nested(param_model)
})

srg_update = api.model('Srg Update', {
    'changed': fields.Boolean,
    'old_name': fields.String
})

srg_input_model = api.model('Srg Input', {
    'mcpname': fields.String,
    'force': fields.Boolean
})

history_model = api.model('History', {
    'srg_name': fields.String,
    'mcp_name': fields.String,
    'changed_by': fields.String(attribute='changed_by.username'),
    'created': fields.DateTime
})


def get_srg_name(table: SrgNamedTable, name: str):
    version = get_version(request.values.get('version', 'latest'))
    if version is None:
        abort(404, "No such version")

    version = version.version

    class_name = None
    if table is Classes:
        class_name = name
    elif '.' in name:
        if table is Parameters:
            abort(400, "Parameters cannot be filtered by class")
        class_name = name[:name.rfind('.')]
        name = name[name.rfind('.') + 1:]

    search = {'version': version}

    if class_name:
        # Special treatment if it is or has a class
        try:
            # No guessing for the class.
            # First, try the obf name.
            class_info = Classes.query.filter_by(version=version, obf_name=class_name).one_or_none()
            if class_info is None:
                # Missed, so try for the srg name
                class_info = Classes.query.filter(Classes.version == version,
                                                  Classes.srg_name.endswith("." + class_name)).one_or_none()
            # reeee, the class doesn't exist!
            if class_info is None:
                abort(404, "Unknown class")

        except sqlalchemy.orm.exc.MultipleResultsFound:
            # Take no chances. Class name should match exactly
            abort(404, "Ambiguous class name")
        else:
            if table is Classes:
                return class_info

            search['class_id'] = class_info.id

    info: SrgNamed

    try:
        info = table.query.filter_by(srg_id=int(name), **search).all()
    except ValueError:
        # search by srg
        info = table.query.filter_by(srg_name=name, **search).all()
        if not info:
            # search by obf
            info = table.query.filter_by(obf_name=name, **search).all()
        if not info:
            # search by mcp
            info = table.query.filter_by(**search).join(NameHistory).filter(NameHistory.mcp_name == name).all()

    if not info:
        raise abort(404, "Mapping not found")

    return info


valid_member_chars = string.ascii_letters + string.digits + "_$"


@auth.login_required
def set_srg_name(table: McpNamedTable, name: str):
    version = get_version(request.values.get('version', 'latest'))
    if version is None:
        raise abort(404, "No such version")
    version = version.version

    try:
        mcp = request.json['mcpname']
        force = request.json.get('force', False)
    except KeyError:
        raise abort(400)

    filtered = ''.join(c for c in mcp if c in valid_member_chars)
    if mcp != filtered or mcp[0] in string.digits:
        raise abort(400, "Illegal member name")

    user: Users = g.user

    if force and not user.admin:
        raise abort(403)

    info = table.query.filter_by(version=version, srg_name=name).one_or_none()
    if info is None:
        raise abort(404)

    if info.locked and not force:
        raise abort(403)

    if info.last_change is not None:
        old_mcp = info.last_change.mcp_name
    else:
        old_mcp = None

    if old_mcp == mcp:
        return dict(
            changed=False,
            old_name=old_mcp
        )

    info.last_change = NameHistory(
        member_type=table.member_type,
        srg_name=name,
        mcp_name=mcp,
        changed_by=user
    )

    db.session.commit()

    return dict(
        changed=True,
        old_name=old_mcp,
    )


version_model = api.model('Version', {
    'latest': fields.String,
    'versions': fields.List(fields.String)
})


@api.route('/versions')
class VersionResource(Resource):
    @api.marshal_with(version_model)
    def get(self):
        latest = get_latest()
        versions = Versions.query.all()
        return {
            'latest': latest.version,
            'versions': sorted([v.version for v in versions])
        }


@api.route('/class/<name>')
class ClassResource(Resource):
    srg_type: McpNamed

    @api.doc(params={'version': 'The Minecraft Version, defaults to latest.'},
             responses={404: "No name found or ambiguous class"})
    @api.marshal_with(base_model)
    def get(self, name):
        return get_srg_name(Classes, name)


def _init_resources():
    def init(endpoint_name, table, get_model):
        @api.route(f"/{endpoint_name}/<name>")
        class BaseResource(Resource):
            @api.marshal_with(get_model, as_list=True)
            def get(self, name):
                return get_srg_name(table, name)

            @api.marshal_with(srg_update)
            @api.doc(responses={
                400: "When bad parameters are passed",
                403: "When a non-admin tries to force a name"
            })
            @api.expect(srg_input_model)
            def put(self, name):
                return set_srg_name(table, name)

        @api.route(f"/{endpoint_name}/<name>/history")
        class HistoryResource(Resource):
            @api.marshal_with(history_model, as_list=True)
            def get(self, name):
                return NameHistory.query.filter_by(member_type=MemberType(endpoint_name), srg_name=name).all()

    for n, t, m in [("field", Fields, field_model),
                    ("method", Methods, method_model),
                    ("param", Parameters, param_model)]:
        init(n, t, m)


_init_resources()
del _init_resources
