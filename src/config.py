"""
Configuration file for Resume Roaster Pro
Update your API keys here or use environment variables
"""

import os

# ============================================
# GOOGLE GEMINI API KEY
# ============================================
# Get your free API key from: https://makersuite.google.com/app/apikey

# Option 1: Set environment variable (recommended)
# export GEMINI_API_KEY='your-api-key-here'

# Option 2: Hardcode it here (NOT recommended for production)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_API_KEY_HERE")

# ============================================
# MODEL SETTINGS
# ============================================

# Gemini model to use
GEMINI_MODEL = "gimini-2.5-pro"

# Generation parameters
GENERATION_CONFIG = {
    "roast_mode": {
        "temperature": 0.95,  # High creativity for roasting
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 2048,
    },
    "constructive_mode": {
        "temperature": 0.7,  # Balanced
        "top_p": 0.9,
        "top_k": 40,
        "max_output_tokens": 2048,
    },
    "normal_mode": {
        "temperature": 0.7,  # Balanced
        "top_p": 0.9,
        "top_k": 40,
        "max_output_tokens": 1536,
    }
}

# ============================================
# EMBEDDING SETTINGS
# ============================================

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 200
CHUNK_OVERLAP = 50

# ============================================
# VOICE SETTINGS
# ============================================

VOICE_ENABLED_BY_DEFAULT = False

VOICE_CONFIGS = {
    "🔥 Roast Mode": {
        "voice_name": "en-US-GuyNeural",  # Male, assertive
        "rate": "+10%",
        "pitch": "+0Hz"
    },
    "💡 Constructive Mode": {
        "voice_name": "en-US-JennyNeural",  # Female, professional
        "rate": "+0%",
        "pitch": "+0Hz"
    },
    "Normal": {
        "voice_name": "en-US-AriaNeural",  # Neutral, friendly
        "rate": "+5%",
        "pitch": "+0Hz"
    }
}

# ============================================
# VALIDATION
# ============================================

def validate_config():
    """Check if configuration is valid."""
    issues = []
    
    if GEMINI_API_KEY == "YOUR_API_KEY_HERE":
        issues.append("⚠️  Gemini API key not configured")
        issues.append("   Get your key: https://makersuite.google.com/app/apikey")
    
    return issues

def print_config_status():
    """Print configuration status."""
    print("=" * 60)
    print("Resume Roaster Pro - Configuration")
    print("=" * 60)
    
    issues = validate_config()
    
    if not issues:
        print("✅ All configurations valid")
        print(f"✅ Gemini Model: {GEMINI_MODEL}")
        print(f"✅ Embedding Model: {EMBEDDING_MODEL}")
    else:
        print("❌ Configuration Issues:")
        for issue in issues:
            print(issue)
    
    print("=" * 60)

if __name__ == "__main__":
    print_config_status()
