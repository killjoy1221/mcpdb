from flask import request
from flask_restplus import Resource, fields

from . import api
from ..models import *
from ..util import get_version

dump_model = api.model("Dump", {
    'srg_name': fields.String,
    'mcp_name': fields.String(attribute='last_change.mcp_name')
})
dump_doc_model = api.inherit("Dump+Docs", dump_model, {
    'comment': fields.String
})


@api.route('/summary')
class SummaryResource(Resource):
    def get(self):
        version = get_version(request.values.get('version', 'latest')).version

        def compute(table):
            result = table.query.filter_by(version=version)

            if table is not Parameters:
                result = result.filter(table.srg_id != None)

            total = result.count()
            unmapped = result.filter_by(last_change=None).count()
            mapped = total - unmapped
            return dict(
                total=total,
                mapped=mapped,
                unmapped=unmapped
            )

        return dict(
            fields=compute(Fields),
            methods=compute(Methods),
            params=compute(Parameters)
        )


@api.route('/dump')
class SummaryDetailResource(Resource):
    def get(self):
        version = get_version(request.values.get('version', 'latest')).version
        nodoc = 'nodoc' in request.values

        m = dump_model if nodoc else dump_doc_model

        def compute(table):
            return table.query.filter_by(version=version).filter(table.last_change != None).all()

        return dict(
            fields=api.marshal(compute(Fields), m),
            methods=api.marshal(compute(Methods), m),
            params=api.marshal(compute(Parameters), m)
        )
