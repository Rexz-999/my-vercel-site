#streamlit run B:/NHITM/SEM-IV/Mini/Hive/stu_ft_add.py
import streamlit as st
from dotenv import load_dotenv
import os
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Improved prompt with structured format
PROMPT = """
You are a YouTube video summarizer designed for Mumbai University engineering students. 
Your task is to summarize the video transcript following the proper answer-writing format for 8-10 mark questions.

### **Instructions for Summarization:**  
1. **Definition:** Start with a definition of the main topic and any closely related concepts.  
2. **Classification:** If the topic is broad, provide a **classification in a tree format** (use text-based representation like code blocks if needed).  
3. **Explanation:** Explain the topic in a structured, **stepwise or pointwise manner** to ensure clarity.  
4. **Diagrams:** If a diagram is necessary, either:  ```1  
   - Provide a **relevant image link** from online sources, OR  
   - Mention **"Draw a ____ Type of Diagram"** if an image isn’t available.(use text-based representation like code blocks)    
5. **Merits & Demerits:** List advantages and disadvantages **if applicable**.  
6. **Applications:** Mention real-world applications **if applicable**.    
7. **Conclusion:** End with a brief 2-3 line conclusion summarizing the key points.  

### **Important Notes:**  
- **Maintain proper formatting** to avoid clustering of information. Use **clear headings** and proper spacing.  
- If the transcript has **errors due to accent-based misinterpretations**, **correct them** based on the context.  
- Avoid unnecessary repetition or overly casual language. Keep the summary **precise, structured, and professional**.  
"""

# Function to extract transcript from YouTube video
def extract_transcript(youtube_video_url):
    try:
        video_id = youtube_video_url.split("v=")[-1]  # Extract video ID
        transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'hi'])

        transcript = " ".join([entry["text"] for entry in transcript_data])
        return transcript

    except Exception as e:
        return f"Error retrieving transcript: {str(e)}"

# Function to generate summary using Google Gemini API
def generate_gemini_summary(transcript_text):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(PROMPT + transcript_text)

        if hasattr(response, "text"):
            return response.text
        else:
            return "Error: Unexpected response format from API."

    except Exception as e:
        return f"Error generating summary: {str(e)}"

# Streamlit UI
st.title("📜 YouTube Video Summarizer (Engineering Notes)")

# Input YouTube URL
youtube_link = st.text_input("🎥 Enter YouTube Video Link:")

# Display video thumbnail if URL is entered
if youtube_link:
    video_id = youtube_link.split("v=")[-1]
    st.image(f"http://img.youtube.com/vi/{video_id}/0.jpg", use_container_width=True)

# Generate summary when button is clicked
if st.button("📝 Get Detailed Notes"):
    with st.spinner("Fetching transcript..."):
        transcript_text = extract_transcript(youtube_link)

    if "Error" not in transcript_text:
        with st.spinner("Generating summary..."):
            summary = generate_gemini_summary(transcript_text)

        st.markdown("## 📝 Detailed Notes:")
        st.write(summary)
    else:
        st.error(transcript_text)
