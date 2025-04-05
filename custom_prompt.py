import streamlit as st
from dotenv import load_dotenv
import os
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi
import requests
import shutil
from pathlib import Path
from bs4 import BeautifulSoup  # For extracting image URLs
import random

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Bing Search API (Replace 'YOUR_BING_KEY' with actual key)
BING_SEARCH_API_KEY = os.getenv("BING_API_KEY")
BING_SEARCH_URL = "https://www.bing.com/images/search"

# Directory to store images
temp_dir = Path("temp_images")

# Remove old images safely
try:
    shutil.rmtree(temp_dir)  # Deletes folder and contents
except FileNotFoundError:
    pass  # Folder doesn't exist, nothing to remove
except Exception as e:
    print(f"Warning: Could not delete temp_images - {e}")

# Recreate directory
temp_dir.mkdir(exist_ok=True)

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

### **Important Notes:**  
- **Maintain proper formatting** to avoid clustering of information. Use **clear headings** and proper spacing.  
- If the transcript has **errors due to accent-based misinterpretations**, **correct them** based on the context.  
- Avoid unnecessary repetition or overly casual language. Keep the summary **precise, structured, and professional**.  
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
        # Use custom prompt if provided, otherwise use the default prompt
        if custom_prompt:
            response = model.generate_content(custom_prompt + transcript_text)
        else:
            response = model.generate_content(PROMPT + transcript_text)

        if hasattr(response, "text"):
            return response.text
        else:
            return "Error: Unexpected response format from API."
    except Exception as e:
        return f"Error generating summary: {str(e)}"

# --- FUNCTION TO SEARCH AND DOWNLOAD IMAGE FROM BING ---
def fetch_image(search_query):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        params = {"q": search_query, "form": "HDRSC2"}

        response = requests.get(BING_SEARCH_URL, headers=headers, params=params)
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract image URLs
        image_elements = soup.find_all("img")
        image_urls = [img["src"] for img in image_elements if img.get("src") and img["src"].startswith("http")]

        if image_urls:
            # Select a random image from the first 5 results
            image_url = random.choice(image_urls[:5])

            # Download the image
            image_response = requests.get(image_url, stream=True)
            image_path = temp_dir / "diagram.jpg"

            with open(image_path, "wb") as f:
                for chunk in image_response.iter_content(1024):
                    f.write(chunk)

            return str(image_path)
        else:
            return None

    except Exception as e:
        return f"Error fetching image: {str(e)}"

# --- STREAMLIT UI ---
st.title("📜 YouTube Video Summarizer (Engineering Notes)")

# Input YouTube URL
youtube_link = st.text_input("🎥 Enter YouTube Video Link:")

# Display video thumbnail if URL is entered
if youtube_link:
    video_id = youtube_link.split("v=")[-1].split("&")[0]
    st.image(f"http://img.youtube.com/vi/{video_id}/0.jpg", use_container_width=True)

# Option to choose default or custom prompt
prompt_option = st.radio(
    "Choose a prompt option:",
    ("Default: Get Detailed Notes", "Custom: Provide Your Own Prompt")
)

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
            # Use custom prompt if provided
            summary = generate_gemini_summary(transcript_text, custom_prompt)

        st.markdown("## 📝 Detailed Notes:")
        st.write(summary)

        # Extract possible diagram keyword
        keywords = summary.split()[:5]  # Use first few words to find a diagram
        diagram_query = " ".join(keywords) + " diagram"

        with st.spinner("Searching for relevant diagrams..."):
            image_path = fetch_image(diagram_query)

        if image_path and not image_path.startswith("Error"):
            st.image(image_path, caption="Relevant Diagram", use_container_width=True, width=700)
        else:
            st.error("No relevant diagram image found. Please 'Draw a ____ Type of Diagram' as indicated in the summary.")

    else:
        st.error(transcript_text)
