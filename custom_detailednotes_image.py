import streamlit as st
from dotenv import load_dotenv
import os
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import shutil
from pathlib import Path
import requests
import time
from duckduckgo_search import DDGS  # Using DDGS as per your original code

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Directory to store images
temp_dir = Path("temp_images")

# Remove old images safely
try:
    shutil.rmtree(temp_dir)  # Delete folder and its contents
except FileNotFoundError:
    pass  # Folder doesn't exist, nothing to remove
except Exception as e:
    print(f"Warning: Could not delete temp_images - {e}")

# Recreate directory
temp_dir.mkdir(exist_ok=True)

# --- SESSION STATE INITIALIZATION ---
if "summary" not in st.session_state:
    st.session_state.summary = None
if "image_paths" not in st.session_state:
    st.session_state.image_paths = []
if "image_index" not in st.session_state:
    st.session_state.image_index = 0

# --- PROMPT FOR SUMMARIZATION ---
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


# --- FUNCTION TO EXTRACT YOUTUBE TRANSCRIPT ---
def extract_transcript(youtube_video_url):
    try:
        video_id = youtube_video_url.split("v=")[-1].split("&")[0]  # Extract Video ID
        transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'hi'])
        transcript = " ".join([entry["text"] for entry in transcript_data])
        return transcript
    except Exception as e:
        return f"Error retrieving transcript: {str(e)}"


# --- FUNCTION TO GENERATE SUMMARY USING GEMINI ---
def generate_gemini_summary(transcript_text, custom_prompt=""):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt_to_use = (custom_prompt + transcript_text) if custom_prompt else (PROMPT + transcript_text)
        response = model.generate_content(prompt_to_use)
        return response.text if hasattr(response, "text") else "Error: Unexpected response format from API."
    except Exception as e:
        return f"Error generating summary: {str(e)}"


# --- FUNCTION TO DOWNLOAD 5 IMAGES USING DUCKDUCKGO ---
def download_relevant_images(search_query):
    try:
        with DDGS() as ddgs:
            image_results = ddgs.images(search_query, max_results=5)
        if not image_results:
            return None

        downloaded_images = []
        for index, result in enumerate(image_results[:5]):
            image_url = result["image"]
            print(f"Downloading image {index}: {image_url}")  # Debug print
            response = requests.get(image_url, stream=True, timeout=10)
            if response.status_code == 200:
                image_path = temp_dir / f"image_{index}.jpg"
                with open(image_path, "wb") as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                # Brief delay to ensure the file is flushed
                time.sleep(0.2)
                abs_path = str(image_path.resolve())
                if os.path.exists(abs_path):
                    print(f"Saved image {index} at: {abs_path}")  # Debug print
                    downloaded_images.append(abs_path)
                else:
                    print(f"Failed to save image {index} at: {abs_path}")
        return downloaded_images if downloaded_images else None
    except Exception as e:
        return f"Error downloading images: {str(e)}"


# --- STREAMLIT UI ---

st.title("📜 YouTube Video Summarizer (Engineering Notes)")

# Input YouTube URL
youtube_link = st.text_input("🎥 Enter YouTube Video Link:")

# Display video thumbnail if URL is entered
if youtube_link:
    video_id = youtube_link.split("v=")[-1].split("&")[0]
    st.image(f"http://img.youtube.com/vi/{video_id}/0.jpg", use_container_width=True)

# Option to choose default or custom prompt
prompt_option = st.radio("Choose a prompt option:",
                         ("Default: Get Detailed Notes", "Custom: Provide Your Own Prompt"))

# Show text box for custom prompt if selected
custom_prompt = ""
if prompt_option == "Custom: Provide Your Own Prompt":
    custom_prompt = st.text_area("Enter your custom prompt:")

# Generate summary when button is clicked
if st.button("📝 Get Summary"):
    with st.spinner("Fetching transcript..."):
        transcript_text = extract_transcript(youtube_link)
    if "Error" not in transcript_text:
        with st.spinner("Generating summary..."):
            st.session_state.summary = generate_gemini_summary(transcript_text, custom_prompt)
        # Print summary only once here
        st.markdown("## 📝 Detailed Notes:")
        st.write(st.session_state.summary)

        # Determine diagram query:
        # Use a fixed query if summary mentions "8086", otherwise use first few words.
        if "8086" in st.session_state.summary:
            diagram_query = "8086 microprocessor architecture block diagram"
        else:
            keywords = st.session_state.summary.split()[:5]
            diagram_query = " ".join(keywords) + " diagram"

        st.write(f"Using diagram query: **{diagram_query}**")  # Debug: show the query

        with st.spinner("Downloading relevant diagrams..."):
            st.session_state.image_paths = download_relevant_images(diagram_query)
            st.session_state.image_index = 0  # Reset index
    else:
        st.error(transcript_text)

# Display images if available (without reprinting the summary)
if st.session_state.image_paths and not isinstance(st.session_state.image_paths, str):
    current_image = st.session_state.image_paths[st.session_state.image_index]
    if os.path.exists(current_image):
        st.image(current_image, use_container_width=True)
    else:
        st.error(f"Error: The image file '{current_image}' was not found.")

    if st.button("Next ➡️"):
        st.session_state.image_index = (st.session_state.image_index + 1) % len(st.session_state.image_paths)
        # No explicit rerun needed; Streamlit re-runs on each interaction.
elif st.session_state.summary and not st.session_state.image_paths:
    st.error("No relevant diagram images found. Please 'Draw a ____ Type of Diagram' as indicated in the summary.")
