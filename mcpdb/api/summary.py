from flask import request
from flask_restplus import Resource, fields

from . import api
from ..models import *
from ..util import get_version

summary_model = api.model("Summary", {
    'total': fields.Integer,
    'mapped': fields.Integer,
    'unmapped': fields.Integer
})
dump_model = api.model("Dump", {
    'srg_name': fields.String,
    'mcp_name': fields.String(attribute='last_change.mcp_name')
})


@api.route('/summary')
class SummaryResource(Resource):
    @api.marshal_with(api.model("Total Summary", {
        'fields': fields.Nested(summary_model),
        'methods': fields.Nested(summary_model),
        'params': fields.Nested(summary_model),
    }))
    def get(self):
        version = get_version(request.values.get('version', 'latest')).version

        def compute(table):
            result = table.query.filter_by(version=version)

            if table is not Parameters:
                result = result.filter(table.srg_id != None)

            total = result.count()
            unmapped = result.filter_by(last_change=None).count()
            mapped = total - unmapped
            return {
                'total': total,
                'mapped': mapped,
                'unmapped': unmapped
            }

        return {
            'fields': compute(Fields),
            'methods': compute(Methods),
            'params': compute(Parameters)
        }


@api.route('/dump')
class SummaryDetailResource(Resource):
    @api.marshal_with(api.model("Full Dump", {
        'fields': fields.List(fields.Nested(dump_model)),
        'methods': fields.List(fields.Nested(dump_model)),
        'params': fields.List(fields.Nested(dump_model)),
    }))
    def get(self):
        version = get_version(request.values.get('version', 'latest')).version

        def compute(table):
            return table.query.filter_by(version=version).filter(table.last_change != None)

        return {
            'fields': compute(Fields),
            'methods': compute(Methods),
            'params': compute(Parameters)
        }
