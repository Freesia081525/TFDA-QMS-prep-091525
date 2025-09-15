import os
import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import tempfile

# -------------------- CONFIG --------------------
st.set_page_config(page_title="Ferrari FDA Agent", page_icon="🏎️", layout="wide")

# Ferrari style CSS
st.markdown("""
    <style>
        .main {background-color: #0d0d0d; color: #ffffff;}
        h1, h2, h3 {color: #ff0000; text-align: center; font-family: 'Arial Black';}
        .stButton>button {background-color: #ff0000; color:white; border-radius:12px; font-size:18px;}
        .stTextInput>div>div>input {background-color: #1a1a1a; color: #fff;}
        .highlight-positive {color: lightgreen; font-weight: bold;}
        .highlight-negative {color: coral; font-weight: bold;}
        .chat-bubble {padding:10px; border-radius:15px; margin:5px;}
        .user-msg {background:#ff0000; color:white; text-align:right;}
        .ai-msg {background:#262626; color:white; text-align:left;}
    </style>
""", unsafe_allow_html=True)

# -------------------- GEMINI CONFIG --------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    GEMINI_API_KEY = st.text_input("🔑 Enter your Gemini API Key:", type="password")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    st.warning("Please enter your Gemini API Key to continue.")

# -------------------- FILE UPLOAD --------------------
st.title("🏎️ Ferrari FDA Evidence Extractor + Comparator")
uploaded_files = st.file_uploader("📂 Upload 510(k) submission materials (PDF/TXT)", type=["pdf", "txt"], accept_multiple_files=True)

summary_text = ""
if uploaded_files:
    for uploaded_file in uploaded_files:
        if uploaded_file.type == "application/pdf":
            reader = PdfReader(uploaded_file)
            for page in reader.pages:
                summary_text += page.extract_text() + "\n"
        else:
            summary_text += uploaded_file.read().decode("utf-8") + "\n"

# -------------------- PROMPT & GENERATION --------------------
user_prompt = st.text_area("✍️ Enter FDA Officer prompt:", placeholder="Extract evidence and compare...")

if st.button("🚀 Run Agents") and summary_text and user_prompt:
    with st.spinner("Engines revving... Ferrari Agents at work 🏁"):
        full_prompt = f"Submission Summary:\n{summary_text}\n\nTask:\n{user_prompt}"
        response = model.generate_content(full_prompt)

        # Highlight positive/negative answers
        result = response.text
        result = result.replace("[YES]", "<span class='highlight-positive'>✔ YES</span>")
        result = result.replace("[NO]", "<span class='highlight-negative'>✘ NO</span>")

        st.markdown(f"<div class='ai-msg chat-bubble'>{result}</div>", unsafe_allow_html=True)

        # Export option
        st.download_button("📥 Download Report (Markdown)", result, file_name="FDA_Agent_Report.md")

# -------------------- FOOTER --------------------
st.markdown("""---
### 🏎️ Powered by Ferrari-Style AI Agents
Built with **Streamlit + Gemini API** | Deployed on **Hugging Face Spaces**
""")
