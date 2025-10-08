import os
import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import yaml
from pathlib import Path
from datetime import datetime
import google.api_core.exceptions

# -------------------- CONFIG --------------------
st.set_page_config(page_title="Ferrari FDA Agent", page_icon="🏎️", layout="wide")

# Ferrari style CSS
st.markdown("""
    <style>
        .main {background-color: #0d0d0d; color: #ffffff;}
        h1, h2, h3 {color: #ff0000; text-align: center; font-family: 'Arial Black';}
        .stButton>button {background-color: #ff0000; color:white; border-radius:12px; font-size:18px;}
        .stTextInput>div>div>input {background-color: #1a1a1a; color: #fff;}
        .stTextArea>div>div>textarea {background-color: #1a1a1a; color: #fff;}
        .highlight-positive {color: lightgreen; font-weight: bold;}
        .highlight-negative {color: coral; font-weight: bold;}
        .chat-bubble {padding:10px; border-radius:15px; margin:5px;}
        .user-msg {background:#ff0000; color:white; text-align:right;}
        .ai-msg {background:#262626; color:white; text-align:left;}
        .stSelectbox>div>div>select {background-color: #1a1a1a; color: #fff;}
    </style>
""", unsafe_allow_html=True)

# -------------------- AGENT CONFIG LOADER --------------------
@st.cache_data # Cache the config loading
def load_agents_config():
    """Load agents configuration from agents.yaml"""
    try:
        config_path = Path("agents.yaml")
        if config_path.exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            return {
                'agents': {
                    'Evidence Extractor': {'description': 'Extracts key evidence from FDA submissions', 'default_prompt': 'Extract all clinical evidence, safety data, and comparative information.', 'temperature': 0.3, 'max_tokens': 4096},
                    'Compliance Checker': {'description': 'Checks FDA regulatory compliance', 'default_prompt': 'Review the submission for FDA 510(k) compliance requirements and identify any gaps.', 'temperature': 0.2, 'max_tokens': 4096}
                }
            }
    except Exception as e:
        st.error(f"Error loading agents.yaml: {str(e)}")
        return {'agents': {}}

# -------------------- GEMINI CONFIG --------------------
if 'GEMINI_API_KEY' not in st.session_state:
    st.session_state['GEMINI_API_KEY'] = os.getenv("GEMINI_API_KEY")

if not st.session_state['GEMINI_API_KEY']:
    api_key_input = st.text_input("🔑 Enter your Gemini API Key:", type="password", key="api_key_input")
    if api_key_input:
        st.session_state['GEMINI_API_KEY'] = api_key_input

if st.session_state.get('GEMINI_API_KEY'):
    try:
        genai.configure(api_key=st.session_state['GEMINI_API_KEY'])
    except Exception as e:
        st.error(f"Failed to configure Gemini API: {e}")
else:
    st.warning("Please enter your Gemini API Key to continue.")

# -------------------- MAIN UI --------------------
st.title("🏎️ Ferrari FDA Evidence Extractor + Comparator")

st.subheader("📥 Input Method")
input_method = st.radio("Choose input method:", ["Upload Files", "Paste Text/Markdown"], horizontal=True)

summary_text = ""

if input_method == "Upload Files":
    uploaded_files = st.file_uploader(
        "📂 Upload 510(k) submission materials (PDF/TXT/MD)",
        type=["pdf", "txt", "md", "markdown"],
        accept_multiple_files=True
    )
    if uploaded_files:
        # Text extraction logic here
        pass # Placeholder for your text extraction logic

else:
    pasted_text = st.text_area(
        "📝 Paste your text, markdown, or document content here:",
        height=300,
        placeholder="Paste your 510(k) submission content, clinical data, or any relevant text here..."
    )
    if pasted_text:
        summary_text = pasted_text
        st.success(f"✅ Text loaded ({len(pasted_text)} characters)")

# -------------------- AGENT SELECTION & CONFIG --------------------
# Load agent configurations
agents_config = load_agents_config()
agents = agents_config.get('agents', {})

if summary_text: # Check if there is text to analyze
    st.subheader("🤖 Agent Configuration")
    
    # --- THIS IS THE FIX ---
    # First, we check if 'agents' is a dictionary (our "toolbox").
    if not isinstance(agents, dict):
        # If it's not, we show a clear error message to the user.
        st.error(
            "Configuration Error: The `agents` key in your agents.yaml file seems to be a list, not a dictionary. "
            "Please ensure it is formatted correctly."
        )
        # We also show the user the correct format to help them fix their file.
        with st.expander("Click to see the required format for agents.yaml"):
            st.code("""
# CORRECT FORMAT:
agents:
  AgentNameOne:
    description: "A description..."
    default_prompt: "A default prompt..."
  AgentNameTwo:
    description: "Another description..."
    default_prompt: "Another prompt..."
""", language="yaml")
        # To prevent a crash, we reset 'agents' to an empty dictionary and continue.
        agents = {}
    # --- END OF THE FIX ---

    col1, col2 = st.columns([1, 2])
    
    with col1:
        # This line is now safe, because 'agents' is guaranteed to be a dictionary.
        agent_names = list(agents.keys()) if agents else ["Default Agent"]
        selected_agent = st.selectbox("Select Agent:", agent_names)
        
        # This logic is now protected from the wrong data type.
        agent_config = agents.get(selected_agent, {
            'description': 'Default agent for general analysis.',
            'default_prompt': 'Analyze the submission and extract key information.',
            'temperature': 0.3,
            'max_tokens': 4096
        })
        st.info(f"**Description:** {agent_config.get('description', 'No description')}")
    
    with col2:
        # Display and allow modification of agent parameters
        st.write("**Agent Parameters:**")
        
        temperature = st.slider(
            "Temperature (creativity):", 0.0, 1.0, float(agent_config.get('temperature', 0.3)), 0.1
        )
        
        max_tokens = st.number_input(
            "Max Tokens:", 512, 8192, int(agent_config.get('max_tokens', 4096)), 512
        )
    
    # -------------------- PROMPT MODIFICATION --------------------
    st.subheader("✍️ Prompt Configuration")
    
    default_prompt = agent_config.get('default_prompt', '')
    user_prompt = st.text_area(
        "Modify the agent prompt:",
        value=default_prompt,
        height=150,
        placeholder="Enter your custom prompt or use the default..."
    )
    
    # -------------------- EXECUTION --------------------
    if st.button("🚀 Run Agent") and user_prompt:
        st.session_state['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with st.spinner(f"🏁 {selected_agent} processing... Ferrari engines at full throttle!"):
            try:
                generation_config = genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens
                )
                
                model = genai.GenerativeModel(
                    "gemini-2.0-flash",
                    generation_config=generation_config
                )
                
                full_prompt = f"Agent: {selected_agent}\n\nSubmission Content:\n{summary_text}\n\nTask:\n{user_prompt}\n\nPlease provide a detailed analysis."
                
                response = model.generate_content(full_prompt)
                
                result = response.text
                result_html = result.replace("[YES]", "<span class='highlight-positive'>✔ YES</span>")
                result_html = result_html.replace("[NO]", "<span class='highlight-negative'>✘ NO</span>")
                result_html = result_html.replace("PASS", "<span class='highlight-positive'>✔ PASS</span>")
                result_html = result_html.replace("FAIL", "<span class='highlight-negative'>✘ FAIL</span>")
                
                st.subheader("📊 Analysis Results")
                st.markdown(f"<div class='ai-msg chat-bubble'>{result_html}</div>", unsafe_allow_html=True)
                
            except google.api_core.exceptions.GoogleAPICallError as e:
                st.error(f"❌ API Error: {e.message}")
            except Exception as e:
                st.error(f"❌ An unexpected error occurred: {str(e)}")
# -------------------- FOOTER --------------------
st.markdown("""---
### 🏎️ Powered by Ferrari-Style AI Agents
Built with **Streamlit + Gemini API** | Multi-Agent System with YAML Configuration
""")

# -------------------- SAMPLE AGENTS.YAML --------------------
with st.expander("📋 Sample agents.yaml Configuration"):
    st.code("""
agents:
  Evidence Extractor:
    description: Extracts key evidence from FDA submissions
    default_prompt: Extract all clinical evidence, safety data, and comparative information from the submission.
    temperature: 0.3
    max_tokens: 4096
  
  Compliance Checker:
    description: Checks FDA regulatory compliance
    default_prompt: Review the submission for FDA 510(k) compliance requirements and identify any gaps.
    temperature: 0.2
    max_tokens: 4096
""", language="yaml")
