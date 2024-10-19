import streamlit as st
from transformers import pipeline
import pyttsx3
import threading
import requests
from bs4 import BeautifulSoup

# Set up the Streamlit app
st.set_page_config(page_title="Summarization App", page_icon="📝", layout="wide")

# Add custom CSS for animations and styling
st.markdown("""
    <style>
    @keyframes fadeIn {
        0% { opacity: 0; }
        100% { opacity: 1; }
    }
    .fade-in {
        animation: fadeIn 2s;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        transition: background-color 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .stSidebar .element-container {
        animation: fadeIn 1.5s;
    }
    .about-section {
        animation: fadeIn 2s;
        border: 2px solid #4CAF50;
        padding: 10px;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# Add starting animation
st.markdown("""
    <div class="fade-in">
        <h1>Welcome to the Summarization App</h1>
        <p>This app uses NLP to summarize text and URLs. Choose an option from the sidebar.</p>
    </div>
    """, unsafe_allow_html=True)

# Sidebar with page selection
st.sidebar.markdown("""
    <div class="fade-in">
        <img src="https://media.giphy.com/media/26tn33aiTi1jkl6H6/giphy.gif" alt="Summarization Logo" style="width:100%;">
    </div>
    """, unsafe_allow_html=True)
page = st.sidebar.selectbox("Choose a page", ["Text Summarization", "URL/Link Summarization", "About"])

# Load summarization pipeline
@st.cache_resource
def load_summarizer(model_name="allenai/led-base-16384"):
    return pipeline("summarization", model=model_name)

# Initialize the summarizer
summarizer = load_summarizer()

# Function to handle text-to-speech
def speak_summary(summary, speed):
    engine = pyttsx3.init()
    engine.setProperty('rate', 200 * speed)  # Adjust the speed of the speech
    engine.setProperty('volume', 1.0)  # Set volume to maximum
    # Select a more pleasant voice
    voices = engine.getProperty('voices')
    for voice in voices:
        if 'female' in voice.name.lower():
            engine.setProperty('voice', voice.id)
            break
    engine.say(summary)
    engine.runAndWait()

# Function to stop text-to-speech
def stop_speech():
    engine = pyttsx3.init()
    engine.stop()

# Function to post-process the summary to remove repetition
def post_process_summary(summary):
    sentences = summary.split('. ')
    seen = set()
    processed_summary = []
    for sentence in sentences:
        if sentence not in seen:
            processed_summary.append(sentence)
            seen.add(sentence)
    return '. '.join(processed_summary)

# Function to summarize text with retries and post-processing
def summarize_text_with_retries(text, min_length, max_length, retries=3):
    for _ in range(retries):
        summary = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)[0]['summary_text']
        summary_word_count = len(summary.split())
        if summary_word_count >= min_length:
            summary = post_process_summary(summary)
            return summary, summary_word_count
    summary = post_process_summary(summary)
    return summary, summary_word_count

# Text Summarization Page
if page == "Text Summarization":
    st.header("Text Summarization")
    
    # Input text box
    input_text = st.text_area("Enter text to summarize:", height=200)
    
    # Display word count for input text
    input_word_count = len(input_text.split())
    st.write(f"Word count of input text: {input_word_count}")
    
    # Sliders for minimum and maximum length of summary
    min_summary_length = st.sidebar.slider("Minimum length of summary:", min_value=40, max_value=100, value=40)
    summary_length = st.sidebar.slider("Maximum length of summary:", min_value=40, max_value=400, value=150)
    tts_speed = st.sidebar.slider("Text-to-Speech Speed:", min_value=0.25, max_value=2.0, value=1.0, step=0.05)
    
    # Summarize button
    if st.button("Summarize"):
        if input_text:
            # Ensure max_length is not less than min_length
            min_length = min_summary_length
            max_length = max(summary_length, min_length)
            
            # Debug information
            st.write(f"Summarizing with min_length={min_length} and max_length={max_length}")
            
            summary, summary_word_count = summarize_text_with_retries(input_text, min_length, max_length)
            
            # Ensure the summary meets the minimum word count requirement
            if summary_word_count < min_length:
                st.warning(f"The generated summary is shorter than the minimum length of {min_length} words. Please try again with a longer input text.")
            else:
                # Store the summary in session state
                st.session_state.summary = summary
                st.session_state.summary_word_count = summary_word_count
        else:
            st.warning("Please enter some text to summarize.")
    
    # Display summarized text and word count if available
    if "summary" in st.session_state:
        st.subheader("Summarized Text")
        st.text_area("Summary:", st.session_state.summary, height=200, key="summary_text_area")
        st.write(f"Word count of summarized text: {st.session_state.summary_word_count}")
    
    # Speak button
    if "summary" in st.session_state and st.button("Speak Summary"):
        threading.Thread(target=speak_summary, args=(st.session_state.summary, tts_speed)).start()
    
    # Stop button
    if "summary" in st.session_state and st.button("Stop Speaking"):
        stop_speech()

# URL/Link Summarization Page
elif page == "URL/Link Summarization":
    st.header("URL/Link Summarization")
    
    # Input URL box
    input_url = st.text_input("Enter URL to summarize:")
    
    # Sliders for minimum and maximum length of summary
    min_summary_length = st.sidebar.slider("Minimum length of summary:", min_value=40, max_value=100, value=40)
    summary_length = st.sidebar.slider("Maximum length of summary:", min_value=40, max_value=400, value=150)
    tts_speed = st.sidebar.slider("Text-to-Speech Speed:", min_value=0.25, max_value=2.0, value=1.0, step=0.05)
    
    # Summarize button
    if st.button("Summarize URL"):
        if input_url:
            try:
                # Fetch the content from the URL
                response = requests.get(input_url)
                soup = BeautifulSoup(response.content, 'html.parser')
                paragraphs = soup.find_all('p')
                text = ' '.join([para.get_text() for para in paragraphs])
                
                # Ensure max_length is not less than min_length
                min_length = min_summary_length
                max_length = max(summary_length, min_length)
                
                # Debug information
                st.write(f"Summarizing with min_length={min_length} and max_length={max_length}")
                
                summary, summary_word_count = summarize_text_with_retries(text, min_length, max_length)
                
                # Ensure the summary meets the minimum word count requirement
                if summary_word_count < min_length:
                    st.warning(f"The generated summary is shorter than the minimum length of {min_length} words. Please try again with a longer input text.")
                else:
                    # Store the summary in session state
                    st.session_state.url_summary = summary
                    st.session_state.url_summary_word_count = summary_word_count
            except Exception as e:
                st.error(f"Error fetching URL: {e}")
        else:
            st.warning("Please enter a URL to summarize.")
    
    # Display summarized text and word count if available
    if "url_summary" in st.session_state:
        st.subheader("Summarized Text")
        st.text_area("Summary:", st.session_state.url_summary, height=200, key="url_summary_text_area")
        st.write(f"Word count of summarized text: {st.session_state.url_summary_word_count}")
    
    # Speak button
    if "url_summary" in st.session_state and st.button("Speak URL Summary"):
        threading.Thread(target=speak_summary, args=(st.session_state.url_summary, tts_speed)).start()
    
    # Stop button
    if "url_summary" in st.session_state and st.button("Stop Speaking URL Summary"):
        stop_speech()

# About Page
elif page == "About":
    st.header("About This Project")
    
    # Add some text about the project and its features
    st.markdown("""
    <div class="about-section fade-in">
        <h2>Text Summarization Project</h2>
        <p>This project is designed to provide text summarization capabilities using state-of-the-art NLP models.</p>
        <h3>Features:</h3>
        <ul>
            <li>Summarize text input directly</li>
            <li>Summarize content from URLs</li>
            <li>Text-to-Speech functionality for summarized text</li>
            <li>Customizable summary length</li>
        </ul>
        <p>Choose an option from the sidebar to get started.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Add some animations to make it attractive
    st.markdown("""
    <div class="fade-in">
        <img src="https://media.giphy.com/media/3o7aD2saalBwwftBIY/giphy.gif" alt="Summarization Animation" style="width:100%;">
    </div>
    """, unsafe_allow_html=True)