from flask import Blueprint
from flask_restplus import Api

api_bp = Blueprint('api', __name__, url_prefix="/api")
api = Api(api_bp)

from . import token
from . import srg
