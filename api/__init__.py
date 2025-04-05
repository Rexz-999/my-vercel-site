from flask import Flask
import os

app = Flask(__name__,
           static_folder='../static',
           template_folder='../templates')

app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

from . import routes  # Import routes after app creation 