import streamlit as st
import os
from pathlib import Path
from resume_parser import parse_resume
from rag_chat import rag_query, clear_conversation_history
from embeddings import build_embeddings, load_or_create_index
from audio_handler import text_to_speech
import base64

# Page config
st.set_page_config(
    page_title="Resume Roaster 🔥",
    page_icon="🔥",
    layout="wide"
)

# Initialize session state
if 'resume_parsed' not in st.session_state:
    st.session_state.resume_parsed = False
if 'sections' not in st.session_state:
    st.session_state.sections = {}
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'feedback_mode' not in st.session_state:
    st.session_state.feedback_mode = "Normal"
if 'show_text' not in st.session_state:
    st.session_state.show_text = {}  # Track which messages show text
if 'embeddings_ready' not in st.session_state:
    st.session_state.embeddings_ready = False
if 'job_description' not in st.session_state:
    st.session_state.job_description = ""
if 'jd_provided' not in st.session_state:
    st.session_state.jd_provided = False

# Custom CSS
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
    }
    .roast-badge {
        background: linear-gradient(90deg, #ff6b6b, #ff8787);
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .constructive-badge {
        background: linear-gradient(90deg, #51cf66, #69db7c);
        color: white;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .voice-priority {
        background: linear-gradient(90deg, #5c7cfa, #748ffc);
        color: white;
        padding: 8px 12px;
        border-radius: 8px;
        font-size: 0.9em;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("🔥 Resume Roaster Pro (Voice-First)")
st.markdown("Upload your resume, optionally add a Job Description, and **hear** brutally honest feedback!")

# Sidebar
with st.sidebar:
    st.header("📤 Upload Resume")
    
    upload_method = st.radio("Choose input method:", ["Upload PDF", "Upload TXT", "Paste Text"])
    
    resume_input = None
    
    if upload_method == "Upload PDF":
        uploaded_file = st.file_uploader("Upload PDF Resume", type=['pdf'])
        if uploaded_file:
            temp_path = Path("temp_resume.pdf")
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.read())
            resume_input = str(temp_path)
    
    elif upload_method == "Upload TXT":
        uploaded_file = st.file_uploader("Upload TXT Resume", type=['txt'])
        if uploaded_file:
            resume_input = uploaded_file.read().decode('utf-8')
    
    else:
        resume_input = st.text_area("Paste your resume text here:", height=300)
    
    # Job Description Section
    st.divider()
    st.subheader("📋 Job Description (Optional)")
    st.caption("Compare your resume against a specific job posting")
    
    jd_input = st.text_area(
        "Paste Job Description:",
        height=200,
        placeholder="Paste the job description here to get targeted feedback..."
    )
    
    if jd_input and jd_input.strip():
        st.session_state.job_description = jd_input
        st.session_state.jd_provided = True
        st.success("✅ JD loaded! Feedback will be tailored to this role.")
    else:
        st.session_state.jd_provided = False
    
    st.divider()
    
    if st.button("🚀 Parse Resume", type="primary"):
        if resume_input:
            with st.spinner("Parsing resume with AI..."):
                try:
                    sections, combined_text = parse_resume(resume_input)
                    st.session_state.sections = sections
                    st.session_state.combined_text = combined_text
                    st.session_state.resume_parsed = True
                    
                    # Build embeddings
                    with st.spinner("Building embeddings..."):
                        build_embeddings(sections, combined_text, st.session_state.job_description)
                        st.session_state.embeddings_ready = True
                    
                    st.success("✅ Resume parsed successfully!")
                    
                    # Cleanup
                    if upload_method == "Upload PDF" and Path("temp_resume.pdf").exists():
                        os.remove("temp_resume.pdf")
                        
                except Exception as e:
                    st.error(f"Error parsing resume: {str(e)}")
        else:
            st.warning("Please upload or paste resume content first!")
    
    if st.session_state.resume_parsed:
        st.divider()
        st.subheader("⚙️ Feedback Settings")
        
        # Feedback mode selection
        feedback_mode = st.selectbox(
            "Feedback Mode:",
            ["Normal", "🔥 Roast Mode", "💡 Constructive Mode"],
            help="Normal: Balanced | Roast: Sarcastic & blunt | Constructive: Detailed improvements"
        )
        st.session_state.feedback_mode = feedback_mode
        
        st.divider()
        st.info("🎤 **Voice-First Mode Active**\nAll responses are read aloud automatically. Click 'Show Text' to see written version.")
        
        st.divider()
        
        # Action buttons
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.session_state.show_text = {}
            clear_conversation_history()
            st.rerun()
        
        if st.button("❌ Delete All Data"):
            st.session_state.resume_parsed = False
            st.session_state.sections = {}
            st.session_state.chat_history = []
            st.session_state.show_text = {}
            st.session_state.embeddings_ready = False
            st.session_state.job_description = ""
            st.session_state.jd_provided = False
            if Path("resume_index.faiss").exists():
                os.remove("resume_index.faiss")
            if Path("resume_metadata.json").exists():
                os.remove("resume_metadata.json")
            st.rerun()

# Main content
if st.session_state.resume_parsed:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📄 Parsed Resume Sections")
        
        # Show JD match status
        if st.session_state.jd_provided:
            st.info("🎯 Resume will be compared against provided Job Description")
        
        for section_name, content in st.session_state.sections.items():
            with st.expander(f"**{section_name.title()}**", expanded=False):
                st.text(content[:500] + "..." if len(content) > 500 else content)
    
    with col2:
        st.subheader("🎤 Voice Chat Interface")
        
        # Show current mode badge
        if st.session_state.feedback_mode == "🔥 Roast Mode":
            st.markdown('<div class="roast-badge">🔥 ROAST MODE ACTIVE - Brace yourself!</div>', unsafe_allow_html=True)
        elif st.session_state.feedback_mode == "💡 Constructive Mode":
            st.markdown('<div class="constructive-badge">💡 CONSTRUCTIVE MODE - Detailed guidance</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="voice-priority">🎧 Voice Priority Mode: Listen first, read optionally</div>', unsafe_allow_html=True)
        
        # Chat history display
        chat_container = st.container(height=400)
        with chat_container:
            for idx, message in enumerate(st.session_state.chat_history):
                with st.chat_message(message["role"]):
                    if message["role"] == "user":
                        st.write(message["content"])
                    else:
                        # Assistant message - show audio first
                        if "audio" in message:
                            st.audio(message["audio"], format="audio/mp3")
                            
                            # Toggle button for text
                            show_text_key = f"show_text_{idx}"
                            if show_text_key not in st.session_state.show_text:
                                st.session_state.show_text[show_text_key] = False
                            
                            col_a, col_b = st.columns([1, 4])
                            with col_a:
                                if st.button("📝 Show Text" if not st.session_state.show_text[show_text_key] else "🎤 Hide Text", 
                                           key=f"toggle_{idx}"):
                                    st.session_state.show_text[show_text_key] = not st.session_state.show_text[show_text_key]
                                    st.rerun()
                            
                            if st.session_state.show_text[show_text_key]:
                                with st.expander("📄 Full Text Response", expanded=True):
                                    st.write(message["content"])
                        else:
                            # No audio available, show text
                            st.write(message["content"])
                            st.caption("⚠️ Audio generation failed - showing text")
        
        # Quick action buttons
        st.caption("💡 Quick Actions:")
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            if st.button("📊 Analyze Resume"):
                st.session_state.quick_prompt = "Give me a comprehensive analysis of this resume"
        
        with col_b:
            if st.button("🎯 JD Match"):
                if st.session_state.jd_provided:
                    st.session_state.quick_prompt = "How well does my resume match the job description? What's missing?"
                else:
                    st.warning("Add a Job Description first!")
        
        with col_c:
            if st.button("⚡ Quick Roast"):
                old_mode = st.session_state.feedback_mode
                st.session_state.feedback_mode = "🔥 Roast Mode"
                st.session_state.quick_prompt = "Roast my resume - be brutally honest"
        
        # Chat input
        user_input = st.chat_input("Ask a question or request feedback...")
        
        # Handle quick prompts
        if 'quick_prompt' in st.session_state:
            user_input = st.session_state.quick_prompt
            del st.session_state.quick_prompt
        
        if user_input:
            # Add user message
            st.session_state.chat_history.append({
                "role": "user",
                "content": user_input
            })
            
            # Get AI response
            with st.spinner("🤔 Thinking and preparing voice response..."):
                try:
                    response = rag_query(
                        user_input,
                        feedback_mode=st.session_state.feedback_mode,
                        job_description=st.session_state.job_description if st.session_state.jd_provided else None
                    )
                    
                    message_data = {
                        "role": "assistant",
                        "content": response
                    }
                    
                    # Generate voice (PRIORITY)
                    with st.spinner("🎤 Generating voice response..."):
                        audio_bytes = text_to_speech(response, mode=st.session_state.feedback_mode)
                        if audio_bytes:
                            message_data["audio"] = audio_bytes
                        else:
                            st.warning("⚠️ Voice generation failed. Text will be shown instead.")
                    
                    st.session_state.chat_history.append(message_data)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error generating response: {str(e)}")

else:
    st.info("👈 Upload your resume using the sidebar to get started!")
    
    