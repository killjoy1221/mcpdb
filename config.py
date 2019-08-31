# Config file for the app. Don't edit this file.
# Create a new file at instance/config.py or using environment variables

DEBUG = False
SECRET_KEY = "secret123"  # Required


# https://flask-sqlalchemy.palletsprojects.com/en/2.x/config/#configuration-keys
SQLALCHEMY_DATABASE_URI = "sqlite:///mcpdb.sqlite"
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = False

GITHUB_CLIENT_ID = None
GITHUB_CLIENT_SECRET = None
