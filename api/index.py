from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, send_file
import sys
import os

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as application

# For Vercel serverless deployment
app = application 