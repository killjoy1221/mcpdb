import sqlalchemy.orm.exc
from flask import abort, request, g, jsonify
from flask_restplus import Resource, fields

from . import api
from ..models import Tokens, Classes
from ..util import *

base_model = api.model('BaseSrg', dict(
    version=fields.String,
    obf_name=fields.String,
    srg_name=fields.String
))

class_model = api.inherit('Class', base_model, dict(

))

field_model = api.inherit('Field', base_model, dict(
    mcp_name=fields.String(attribute='last_change.mcp_name'),
    owner=fields.String(attribute='owner.srg_name'),
    locked=fields.Boolean
))

method_model = api.inherit('Method', field_model, dict(
    signature=fields.String
))

srg_update = api.model('Srg Update', dict(
    changed=fields.Boolean,
    old_name=fields.String,
))


class BaseResource(Resource):
    srg_type: SrgType

    def get(self, version, name):
        table = self.srg_type.table
        class_name = None
        if self.srg_type is ClassType:
            class_name = name
        elif '.' in name:
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
                if self.srg_type is ClassType:
                    return class_info

                search['class_id'] = class_info.id

        try:
            info = table.query.filter_by(srg_id=int(name), **search).all()
        except ValueError:
            print(search)
            info = table.query.filter_by(srg_name=name, **search).all()
            if not info:
                info = table.query.filter_by(obf_name=name, **search).all()
            if not info:
                info = table.query.filter_by(**search).filter(table.last_change.mcp_name == name).all()

        if not info:
            raise abort(404, "Mapping not found")

        return info


class MutableResource(BaseResource):
    @api.marshal_with(srg_update)
    def put(self, version, srg):
        try:
            mcp = request.json['name']
            force = request.json.get('force', False)
        except KeyError:
            raise abort(400)

        token: Tokens = g.token

        if force and not token.user.admin:
            raise abort(403)

        info = self.srg_type.table.query.filter_by(version=version, srg_name=srg).one_or_none()
        if info is None:
            raise abort(404)

        if info.locked and not force:
            raise abort(403)

        old_mcp = info.mcp

        if info.mcp == mcp:
            return jsonify(
                changed=False,
                old_name=old_mcp
            )

        info.last_changed = self.srg_type.history(
            version=version,
            srg=srg,
            mcp=mcp,
            changed_by=token.user
        )

        return jsonify(
            changed=True,
            old_name=old_mcp,
        )


@api.route('/class/<version:version>/<name>')
class ClassResource(BaseResource):
    srg_type = ClassType

    @api.marshal_with(class_model)
    def get(self, version, name):
        return super().get(version, name)


@api.route('/field/<version:version>/<name>')
class FieldResource(MutableResource):
    srg_type = FieldType

    @api.marshal_with(field_model)
    def get(self, version, name):
        return super().get(version, name)


@api.route('/method/<version:version>/<name>')
class MethodResource(MutableResource):
    srg_type = MethodType

    @api.marshal_with(method_model, as_list=True)
    def get(self, version, name):
        return super().get(version, name)


@api.route('/param/<version:version>/<name>')
class ParamResource(MutableResource):
    srg_type = ParamType

    @api.marshal_with(base_model)
    def get(self, version, name):
        return super().get(version, name)


history_model = api.model('History', dict(
    version=fields.String,
    srg_name=fields.String(attribute='srg'),
    mcp_name=fields.String(attribute='name'),
    changed_by=fields.String(attribute='changed_by.name'),
    created=fields.DateTime
))


@api.route("/<srgtype:srg_type>/<version:version>/<name>/history")
class SrgHistory(Resource):
    @api.marshal_with(history_model)
    def get(self, srg_type: SrgType, version, name):
        if srg_type is ClassType:
            raise abort(404)

        return srg_type.history.query.filter_by(version=version, name=name).all()
