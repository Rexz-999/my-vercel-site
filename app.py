from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, send_file, jsonify
import requests
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import os
import re
from pytube import YouTube
import tempfile
from pathlib import Path
from duckduckgo_search import DDGS
from werkzeug.utils import secure_filename
import PyPDF2
from pptx import Presentation
import time

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Use memory storage for session
class MemoryStorage:
    def __init__(self):
        self._storage = {}

    def get(self, key):
        return self._storage.get(key)

    def set(self, key, value):
        self._storage[key] = value

memory_storage = MemoryStorage()

# Routes
def home():
    return render_template('index.html')

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

# Keep your existing PROMPT, CONCISE_PROMPT, and PDF_PPT_PROMPT constants
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

# Add this new prompt constant
CONCISE_PROMPT = """
You are a YouTube video summarizer. Create a concise summary of the video in 5-10 key points.

Guidelines:
1. Each point should be clear and concise (1-2 lines max)
2. Use bullet points (•)
3. Focus on the most important concepts/ideas
4. Use keywords and technical terms where relevant
5. Keep the total summary within 200 words
6. Make points easy to remember and understand

Please provide a concise summary of this transcript:
"""

# Add this new prompt
PDF_PPT_PROMPT = """
You are an educational content summarizer designed for engineering students. Analyze the provided content and create a comprehensive yet concise summary following this structure:

1. **Chapter Overview:**
   - Main topic and its significance
   - Key concepts covered
   - Prerequisites needed

2. **Topics Breakdown:**
   - List main topics and subtopics
   - Show relationships between concepts
   - Highlight important terms/definitions

3. **Simplified Explanations:**
   - Break down complex concepts
   - Use simple language
   - Provide examples where possible

4. **Key Points Summary:**
   - Bullet points of crucial information
   - Important formulas/equations (if any)
   - Common applications

5. **Study Focus:**
   - What to concentrate on
   - Potential exam topics
   - Common misconceptions to avoid

6. **Quick Revision Notes:**
   - 5-6 most important takeaways
   - Critical formulas/concepts to remember
   - Practice suggestion areas

Please analyze and summarize the following content:
"""

@app.route('/static/temp_images/<path:filename>')
def serve_image(filename):
    return send_from_directory('temp_images', filename)

@app.route('/download_media/<video_id>/<media_type>')
def download_media(video_id, media_type):
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        yt = YouTube(url, use_oauth=True, allow_oauth_cache=True)
        
        # Create downloads directory if it doesn't exist
        downloads_dir = Path('downloads')
        downloads_dir.mkdir(exist_ok=True)
        
        if media_type == 'mp4':
            # Get the highest resolution stream
            video = yt.streams.get_highest_resolution()
            if not video:
                return "No video stream available"
                
            file_path = video.download(output_path='downloads')
            if os.path.exists(file_path):
                return send_file(
                    file_path,
                    as_attachment=True,
                    download_name=f"{yt.title}.mp4"
                )
            return "Failed to download video"

        elif media_type == 'mp3':
            # Get audio stream
            audio = yt.streams.filter(only_audio=True).first()
            if not audio:
                return "No audio stream available"
                
            # Download audio
            file_path = audio.download(output_path='downloads')
            if not os.path.exists(file_path):
                return "Failed to download audio"
                
            # Convert to MP3
            base, _ = os.path.splitext(file_path)
            new_file = base + '.mp3'
            os.rename(file_path, new_file)
            
            return send_file(
                new_file,
                as_attachment=True,
                download_name=f"{yt.title}.mp3"
            )

        elif media_type == 'thumbnail':
            # Get thumbnail
            thumbnail_url = yt.thumbnail_url
            if not thumbnail_url:
                return "No thumbnail available"
                
            response = requests.get(thumbnail_url)
            if response.status_code != 200:
                return "Failed to download thumbnail"
                
            thumbnail_path = os.path.join('downloads', f"{video_id}_thumbnail.jpg")
            with open(thumbnail_path, 'wb') as f:
                f.write(response.content)
                
            return send_file(
                thumbnail_path,
                as_attachment=True,
                download_name=f"{yt.title}_thumbnail.jpg"
            )

        else:
            return "Invalid media type specified"

    except Exception as e:
        print(f"Download error: {str(e)}")
        return f"Download failed: {str(e)}"

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

@app.route('/process_document', methods=['POST'])
def process_document():
    if 'document' not in request.files:
        return "No file uploaded"
    
    file = request.files['document']
    if file.filename == '':
        return "No file selected"
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join('uploads', filename)
        
        # Create uploads directory if it doesn't exist
        os.makedirs('uploads', exist_ok=True)
        
        file.save(file_path)
        
        # Extract text based on file type
        if filename.endswith('.pdf'):
            text = extract_pdf_text(file_path)
        elif filename.endswith(('.ppt', '.pptx')):
            text = extract_ppt_text(file_path)
        else:
            return "Unsupported file format"
        
        # Generate summary
        summary = generate_summary(text, PDF_PPT_PROMPT)
        
        # Clean up
        os.remove(file_path)
        
        return render_template('document_result.html', summary=summary)

def extract_pdf_text(file_path):
    text = ""
    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def extract_ppt_text(file_path):
    text = ""
    prs = Presentation(file_path)
    for slide in prs.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text += shape.text + "\n"
    return text

if __name__ == '__main__':
    app.run(debug=True)
