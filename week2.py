import os
import yt_dlp
import requests
from pytube import YouTube
import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi

# Load environment variables
load_dotenv()

# Google Gemini API setup
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

prompt = """
You are YouTube video summarizer. You will be taking the transcript text and summarizing the entire video and
provide the summary in specific format (Topic of the video, then give Concepts or Subtopics then give its sub points make sure to  the whole summary is under 350 words and in the end i want a Conclusion in which wrap up things discussed in the whole video/transcript).
Please provide the summary of the text given here:.
"""

# YouTube video downloader
def download_youtube_content(url, download_choice):
    try:
        yt = YouTube(url)
    except Exception as e:
        st.error(f"Error: {e}")
        return

    if download_choice == 'Download Video (MP4)':
        st.write("Downloading video in MP4 format...")
        ydl_opts = {
            'format': 'best',
            'outtmpl': '%(title)s.%(ext)s',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        st.success("Video downloaded successfully!")

    elif download_choice == 'Download Audio (MP3)':
        st.write("Downloading audio in MP3 format...")
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',  # Prefer M4A
            'extractaudio': True,
            'audioformat': 'mp3',
            'outtmpl': '%(title)s.mp3',  # Enforce .mp3 extension
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        st.success("Audio downloaded and converted to MP3 successfully!")

    elif download_choice == 'Download Thumbnail':
        st.write("Downloading thumbnail...")
        thumbnail_url = yt.thumbnail_url
        thumbnail_file = "thumbnail.jpg"  # Generic name to avoid dependency on title
        response = requests.get(thumbnail_url)
        with open(thumbnail_file, 'wb') as file:
            file.write(response.content)
        st.success(f"Thumbnail downloaded successfully as {thumbnail_file}!")

# Extract YouTube video transcript
def extract_transcript_details(youtube_video_url):
    try:
        video_id = youtube_video_url.split("=")[1]
        transcript_text = YouTubeTranscriptApi.get_transcript(video_id)

        transcript = ""
        for i in transcript_text:
            transcript += " " + i["text"]

        return transcript

    except Exception as e:
        st.error(f"Error fetching transcript: {e}")
        return None

# Generate summary from Google Gemini
def generate_gemini_content(transcript_text, prompt):
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(prompt + transcript_text)
    return response.text

# Streamlit interface
st.title("YouTube Video Downloader and Summarizer")

# Input field for YouTube video URL
youtube_link = st.text_input("Enter YouTube Video Link:")

if youtube_link:
    video_id = youtube_link.split("=")[1]
    st.image(f"http://img.youtube.com/vi/{video_id}/0.jpg", use_container_width=True)

    # Video download options
    st.subheader("Download Options")
    download_choice = st.radio(
        "What would you like to download?",
        ("Download Video (MP4)", "Download Audio (MP3)", "Download Thumbnail")
    )

    if st.button("Download Content"):
        download_youtube_content(youtube_link, download_choice)

    # Get and summarize transcript
    if st.button("Get Detailed Notes"):
        transcript_text = extract_transcript_details(youtube_link)

        if transcript_text:
            summary = generate_gemini_content(transcript_text, prompt)
            st.markdown("## Detailed Notes:")
            st.write(summary)
