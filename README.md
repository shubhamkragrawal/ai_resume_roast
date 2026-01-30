# Resume Roaster Pro

An AI-powered resume analysis tool that provides intelligent feedback on resumes. Upload your resume, optionally add a job description, and receive targeted feedback in multiple modes including honest criticism or detailed constructive guidance.

## What is this project?

Resume Roaster Pro is a web application that uses advanced AI to analyze resumes and provide actionable feedback. It features:

- **Multiple Feedback Modes**: Choose between normal, roast (brutally honest), or constructive (detailed guidance) feedback
- **Job Description Matching**: Upload a job description to get targeted feedback on how well your resume matches
- **Voice Responses**: Enable text-to-speech for audio feedback
- **Smart Parsing**: Automatically extracts and organizes resume sections
- **RAG-Powered**: Uses retrieval-augmented generation for contextual responses

The application parses your resume, creates vector embeddings for semantic search, and uses Google's Gemini AI to provide intelligent, context-aware feedback.

## Technologies Used

### Core Technologies
- **Python 3.10+**: Programming language
- **Streamlit**: Web interface framework
- **Google Gemini Pro**: Large language model for generating responses

### AI/ML Components
- **sentence-transformers**: Text embeddings (all-MiniLM-L6-v2 model)
- **FAISS**: Vector similarity search
- **Transformers**: AI model utilities

### Document Processing
- **pdfplumber**: PDF text extraction
- **Custom parsers**: Resume section detection

### Text-to-Speech
- **ElevenLabs API**: High-quality voice synthesis (primary)
- **gTTS**: Google Text-to-Speech (fallback)

## How to Run

### Prerequisites

- Python 3.10 or higher
- pip package manager
- Google Gemini API key (free)

### Installation

1. **Clone or download this repository**
```bash
cd resume-roaster-pro
```

2. **Create a virtual environment**
```bash
python -m venv venv
source venv/bin/activate  
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Get API keys**

**Google Gemini API (required)**
   - Visit: https://makersuite.google.com/app/apikey
   - Sign in with your Google account
   - Click "Create API Key"
   - Copy your API key (starts with AIza)

**ElevenLabs API (optional, for voice)**
   - Visit: https://elevenlabs.io/
   - Sign up for an account
   - Get your API key from the profile section
   - Copy your API key

5. **Set your API keys**

Choose one method:

**Option A: Environment Variable (recommended)**
```bash
export GEMINI_API_KEY='your-gemini-api-key-here'
export ELEVENLABS_API_KEY='your-elevenlabs-api-key-here'  
```

**Option B: .env file**
```bash
cat > .env << EOF
GEMINI_API_KEY=your-gemini-api-key-here
ELEVENLABS_API_KEY=your-elevenlabs-api-key-here
EOF
pip install python-dotenv
```

**Option C: Hardcode (testing only)**
- Edit `rag_chat.py` for Gemini key
- Edit `audio_handler.py` for ElevenLabs key
- Replace placeholder values with your actual keys

### Running the Application

```bash
streamlit run app.py
```

The application will open in your browser at http://localhost:8501

### Using the Application

1. **Upload Resume**: Choose PDF, TXT, or paste text directly
2. **Parse Resume**: Click to extract sections automatically
3. **Add Job Description** (optional): Paste a job description for targeted feedback
4. **Select Feedback Mode**: Normal, Roast, or Constructive
5. **Enable Voice** (optional): Toggle for audio responses
6. **Ask Questions**: Chat with your resume or use quick actions

### Example Questions

- "Analyze my resume"
- "How can I improve my experience section?"
- "What keywords am I missing for this job description?"
- "Rate my resume from 1 to 10"
- "Roast my resume"
