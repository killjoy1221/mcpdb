from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__, instance_relative_config=True)

app.config.from_object('config')
app.config.from_pyfile('config.py')

db = SQLAlchemy(app)

from .models import *

# Import later to prevent import errors
from .cli import *
from .api import bp

app.register_blueprint(bp)
