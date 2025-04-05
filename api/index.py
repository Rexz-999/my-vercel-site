import sys
import os
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import tempfile
from pathlib import Path

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import app

from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, send_file, jsonify

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

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Use temporary directory for file operations
temp_dir = tempfile.gettempdir()

# Prompts
PROMPT = """
You are a YouTube video summarizer designed for Mumbai University engineering students. 
Your task is to summarize the video transcript following the proper answer-writing format for 8-10 mark questions.

### **Instructions for Summarization:**  
1. **Definition:** Start with a definition of the main topic and any closely related concepts.  
2. **Classification:** If the topic is broad, provide a **classification in a tree format** (use text-based representation like code blocks if needed).  
3. **Explanation:** Explain the topic in a structured, **stepwise or pointwise manner** to ensure clarity.  
4. **Diagrams:** If a diagram is necessary, Mention **"Draw a ____ Type of Diagram"**    
5. **Merits & Demerits:** List advantages and disadvantages **if applicable**.  
6. **Applications:** Mention real-world applications **if applicable**.    
7. **Conclusion:** End with a brief 2-3 line conclusion summarizing the key points.  
"""

CONCISE_PROMPT = """
You are a YouTube video summarizer. Create a concise summary of the video in 5-10 key points.
"""

PDF_PPT_PROMPT = """
You are an educational content summarizer designed for engineering students.
"""

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/process_video')
def process_video():
    youtube_link = session.get('youtube_link')
    if not youtube_link:
        return jsonify({"error": "No YouTube link provided"}), 400

    video_id = youtube_link.split("v=")[-1].split("&")[0]
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/0.jpg"
    
    try:
        transcript = extract_transcript(video_id)
        if isinstance(transcript, str) and transcript.startswith("Error"):
            return jsonify({"error": transcript}), 400

        prompt_option = session.get('prompt_option', 'default')
        custom_prompt = session.get('custom_prompt', '')
        
        summary = generate_summary(transcript, 
                                 CONCISE_PROMPT if prompt_option == "concise" else 
                                 custom_prompt if prompt_option == "custom" else 
                                 PDF_PPT_PROMPT if prompt_option == "pdf_ppt" else 
                                 PROMPT)
        
        if isinstance(summary, str) and summary.startswith("Error"):
            return jsonify({"error": summary}), 400

        return render_template('result.html',
                            thumbnail_url=thumbnail_url,
                            summary=summary,
                            youtube_link=youtube_link)
                            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/process_youtube', methods=['POST'])
def process_youtube():
    youtube_link = request.form.get('youtube_link')
    prompt_option = request.form.get('prompt_option')
    custom_prompt = request.form.get('custom_prompt', '')

    if youtube_link:
        session['youtube_link'] = youtube_link
        session['prompt_option'] = prompt_option
        session['custom_prompt'] = custom_prompt
        return redirect(url_for('process_video'))
    return redirect(url_for('home'))

# Helper functions
def extract_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        return ' '.join([entry['text'] for entry in transcript])
    except Exception as e:
        return f"Error extracting transcript: {str(e)}"

def generate_summary(transcript, prompt):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt + transcript)
        return response.text if hasattr(response, "text") else "Error: Unexpected response format"
    except Exception as e:
        return f"Error generating summary: {str(e)}"

# Error handling
@app.errorhandler(500)
def internal_error(error):
    return "500 Internal Server Error: The server encountered an unexpected condition.", 500

@app.errorhandler(404)
def not_found_error(error):
    return "404 Not Found: The requested URL was not found on the server.", 404 