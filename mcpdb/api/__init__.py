from flask import Blueprint
from flask_restplus import Api

bp = Blueprint('api', __name__, url_prefix="/api")
api = Api(bp)

from .login import *
from .srg import *
from .cli import *

__all__ = (
    "api",
    "auth",
    "bp"
)
