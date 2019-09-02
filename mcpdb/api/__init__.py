import traceback

from flask import Blueprint
from flask_restplus import Api, Resource, abort
from werkzeug.exceptions import HTTPException, InternalServerError

bp = Blueprint('api', __name__, url_prefix="/api")
api = Api(bp)

from .login import *
from .srg import *

__all__ = (
    "api",
    "auth",
    "bp"
)


# Attach to blueprint because api doesn't catch it
@bp.errorhandler(Exception)
def on_error(e):
    if isinstance(e, HTTPException):
        raise
    traceback.print_exc()
    return {
               "message": InternalServerError.description,
               "error": traceback.format_exception_only(type(e), e)[0].strip()
           }, 500


@api.route('/<path:path>')
class DefaultResource(Resource):
    """Handles the default 404 errors.
    This should be the last route defined in the Blueprint.
    """

    def dispatch_request(self, *args, **kwargs):
        abort(404)
