import os
import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import yaml
from pathlib import Path

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
def load_agents_config():
    """Load agents configuration from agents.yaml"""
    try:
        config_path = Path("agents.yaml")
        if config_path.exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            # Return default configuration if file doesn't exist
            return {
                'agents': {
                    'Evidence Extractor': {
                        'description': 'Extracts key evidence from FDA submissions',
                        'default_prompt': 'Extract all clinical evidence, safety data, and comparative information from the submission.',
                        'temperature': 0.3,
                        'max_tokens': 4096
                    },
                    'Compliance Checker': {
                        'description': 'Checks FDA regulatory compliance',
                        'default_prompt': 'Review the submission for FDA 510(k) compliance requirements and identify any gaps.',
                        'temperature': 0.2,
                        'max_tokens': 4096
                    },
                    'Comparator Analyzer': {
                        'description': 'Compares device with predicate devices',
                        'default_prompt': 'Compare the subject device with predicate devices, identifying similarities and differences.',
                        'temperature': 0.4,
                        'max_tokens': 4096
                    },
                    'Risk Assessor': {
                        'description': 'Assesses risks and safety concerns',
                        'default_prompt': 'Identify and assess potential risks, safety concerns, and mitigation strategies.',
                        'temperature': 0.3,
                        'max_tokens': 4096
                    }
                }
            }
    except Exception as e:
        st.error(f"Error loading agents.yaml: {str(e)}")
        return {'agents': {}}

# -------------------- GEMINI CONFIG --------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    GEMINI_API_KEY = st.text_input("🔑 Enter your Gemini API Key:", type="password")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    st.warning("Please enter your Gemini API Key to continue.")

# -------------------- MAIN UI --------------------
st.title("🏎️ Ferrari FDA Evidence Extractor + Comparator")

# Load agent configurations
agents_config = load_agents_config()
agents = agents_config.get('agents', {})

# -------------------- INPUT METHOD SELECTION --------------------
st.subheader("📥 Input Method")
input_method = st.radio("Choose input method:", 
                        ["Upload Files", "Paste Text/Markdown"],
                        horizontal=True)

summary_text = ""
selected_pages = None

if input_method == "Upload Files":
    # -------------------- FILE UPLOAD --------------------
    uploaded_files = st.file_uploader(
        "📂 Upload 510(k) submission materials (PDF/TXT/MD)", 
        type=["pdf", "txt", "md", "markdown"], 
        accept_multiple_files=True
    )
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            st.write(f"**Processing:** {uploaded_file.name}")
            
            if uploaded_file.type == "application/pdf":
                reader = PdfReader(uploaded_file)
                total_pages = len(reader.pages)
                
                # PDF Page Selection
                st.write(f"📄 PDF has {total_pages} pages")
                use_page_selection = st.checkbox(f"Select specific pages for {uploaded_file.name}?", key=f"select_{uploaded_file.name}")
                
                if use_page_selection:
                    page_range = st.text_input(
                        f"Enter pages (e.g., '1,3,5-10' or 'all'):", 
                        value="all",
                        key=f"pages_{uploaded_file.name}"
                    )
                    
                    # Parse page selection
                    if page_range.lower() == "all":
                        selected_pages = list(range(total_pages))
                    else:
                        selected_pages = []
                        for part in page_range.split(','):
                            part = part.strip()
                            if '-' in part:
                                start, end = map(int, part.split('-'))
                                selected_pages.extend(range(start-1, min(end, total_pages)))
                            else:
                                page_num = int(part) - 1
                                if 0 <= page_num < total_pages:
                                    selected_pages.append(page_num)
                else:
                    selected_pages = list(range(total_pages))
                
                # Extract text from selected pages
                for page_num in selected_pages:
                    summary_text += f"\n--- Page {page_num + 1} ---\n"
                    summary_text += reader.pages[page_num].extract_text() + "\n"
                
                st.success(f"✅ Extracted {len(selected_pages)} pages from {uploaded_file.name}")
            
            else:  # TXT or Markdown
                content = uploaded_file.read().decode("utf-8")
                summary_text += f"\n--- {uploaded_file.name} ---\n{content}\n"
                st.success(f"✅ Loaded {uploaded_file.name}")

else:  # Paste Text/Markdown
    st.subheader("📝 Paste Your Content")
    pasted_text = st.text_area(
        "Paste your text, markdown, or document content here:",
        height=300,
        placeholder="Paste your 510(k) submission content, clinical data, or any relevant text here..."
    )
    
    if pasted_text:
        summary_text = pasted_text
        st.success(f"✅ Text loaded ({len(pasted_text)} characters)")

# -------------------- AGENT SELECTION & CONFIG --------------------
if summary_text:
    st.subheader("🤖 Agent Configuration")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if agents:
            agent_names = list(agents.keys())
            selected_agent = st.selectbox("Select Agent:", agent_names)
            
            agent_config = agents[selected_agent]
            st.info(f"**Description:** {agent_config.get('description', 'No description')}")
        else:
            st.warning("No agents found. Using default configuration.")
            selected_agent = "Default Agent"
            agent_config = {
                'default_prompt': 'Analyze the submission and extract key information.',
                'temperature': 0.3,
                'max_tokens': 4096
            }
    
    with col2:
        # Display and allow modification of agent parameters
        st.write("**Agent Parameters:**")
        
        temperature = st.slider(
            "Temperature (creativity):",
            min_value=0.0,
            max_value=1.0,
            value=float(agent_config.get('temperature', 0.3)),
            step=0.1
        )
        
        max_tokens = st.number_input(
            "Max Tokens:",
            min_value=512,
            max_value=8192,
            value=int(agent_config.get('max_tokens', 4096)),
            step=512
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
        with st.spinner(f"🏁 {selected_agent} processing... Ferrari engines at full throttle!"):
            try:
                # Configure model with selected parameters
                generation_config = genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens
                )
                
                model = genai.GenerativeModel(
                    "gemini-1.5-flash",
                    generation_config=generation_config
                )
                
                # Build full prompt
                full_prompt = f"""Agent: {selected_agent}

Submission Content:
{summary_text}

Task:
{user_prompt}

Please provide a detailed analysis."""
                
                # Generate response
                response = model.generate_content(full_prompt)
                
                # Process and highlight results
                result = response.text
                result = result.replace("[YES]", "<span class='highlight-positive'>✔ YES</span>")
                result = result.replace("[NO]", "<span class='highlight-negative'>✘ NO</span>")
                result = result.replace("PASS", "<span class='highlight-positive'>✔ PASS</span>")
                result = result.replace("FAIL", "<span class='highlight-negative'>✘ FAIL</span>")
                
                # Display results
                st.subheader("📊 Analysis Results")
                st.markdown(f"<div class='ai-msg chat-bubble'>{result}</div>", unsafe_allow_html=True)
                
                # Export options
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        "📥 Download Report (Markdown)",
                        result,
                        file_name=f"FDA_Agent_Report_{selected_agent.replace(' ', '_')}.md",
                        mime="text/markdown"
                    )
                with col2:
                    # Create a formatted report
                    formatted_report = f"""# FDA Agent Analysis Report
## Agent: {selected_agent}
## Date: {st.session_state.get('timestamp', 'N/A')}

### Configuration
- Temperature: {temperature}
- Max Tokens: {max_tokens}

### Prompt
{user_prompt}

### Analysis Results
{response.text}
"""
                    st.download_button(
                        "📥 Download Full Report",
                        formatted_report,
                        file_name=f"FDA_Full_Report_{selected_agent.replace(' ', '_')}.md",
                        mime="text/markdown"
                    )
                
            except Exception as e:
                st.error(f"❌ Error during processing: {str(e)}")

# -------------------- FOOTER --------------------
st.markdown("""---
### 🏎️ Powered by Ferrari-Style AI Agents
Built with **Streamlit + Gemini API** | Multi-Agent System with YAML Configuration
**Features:** PDF Page Selection • Text Pasting • Agent Configuration • Parameter Tuning
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
  
  Comparator Analyzer:
    description: Compares device with predicate devices
    default_prompt: Compare the subject device with predicate devices, identifying similarities and differences.
    temperature: 0.4
    max_tokens: 4096
  
  Risk Assessor:
    description: Assesses risks and safety concerns
    default_prompt: Identify and assess potential risks, safety concerns, and mitigation strategies.
    temperature: 0.3
    max_tokens: 4096
""", language="yaml")
