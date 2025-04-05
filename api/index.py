import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import app

from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, send_file

# Create Flask app
app = Flask(__name__, 
            static_folder='../static',
            template_folder='../templates')

# Import routes after app creation to avoid circular imports
from app import (
    home, process_video, serve_image, download_media,
    process_youtube, process_document
)

# Register routes
app.route('/')(home)
app.route('/process_video')(process_video)
app.route('/static/temp_images/<path:filename>')(serve_image)
app.route('/download_media/<video_id>/<media_type>')(download_media)
app.route('/process_youtube', methods=['POST'])(process_youtube)
app.route('/process_document', methods=['POST'])(process_document)

# Configure app
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# Error handling
@app.errorhandler(500)
def internal_error(error):
    return "500 Internal Server Error: The server encountered an unexpected condition.", 500

@app.errorhandler(404)
def not_found_error(error):
    return "404 Not Found: The requested URL was not found on the server.", 404 