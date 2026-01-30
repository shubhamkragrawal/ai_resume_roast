"""
Audio handler for text-to-speech using ElevenLabs API.
Provides high-quality, realistic voice output for resume feedback.
"""

import os
import re
from pathlib import Path
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
import io

# Load environment variables
load_dotenv()

# HARDCODE YOUR API KEY HERE (temporary for testing)
ELEVENLABS_API_KEY_HARDCODED = None  # Replace with "sk_your_api_key_here"

# Initialize ElevenLabs client
client = None
ELEVENLABS_AVAILABLE = False
ELEVEN_API_KEY = None

try:
    # Get API key from hardcoded value or environment
    ELEVEN_API_KEY = ELEVENLABS_API_KEY_HARDCODED or os.getenv("ELEVENLABS_API_KEY")
    
    if not ELEVEN_API_KEY:
        raise ValueError("ELEVENLABS_API_KEY not found. Set it in .env or hardcode in audio_handler.py")
    
    # Try importing and initializing
    from elevenlabs import ElevenLabs
    
    # Try multiple initialization methods for compatibility
    try:
        # Method 1: New SDK style with api_key parameter
        client = ElevenLabs(api_key=ELEVEN_API_KEY)
    except TypeError:
        # Method 2: Set environment variable and init without params
        os.environ["ELEVEN_API_KEY"] = ELEVEN_API_KEY
        client = ElevenLabs()
    
    ELEVENLABS_AVAILABLE = True
    print("✅ ElevenLabs client initialized successfully")
    print(f"   API Key: {ELEVEN_API_KEY[:10]}..." if ELEVEN_API_KEY else "   API Key: Not set")
    
except ImportError as e:
    print(f"⚠️ ElevenLabs library not installed: {e}")
    print("   Install with: pip install elevenlabs")
except Exception as e:
    print(f"⚠️ ElevenLabs initialization failed: {e}")
    print(f"   Make sure your API key is correct: {ELEVEN_API_KEY[:10] if ELEVEN_API_KEY else 'None'}...")

# Custom voice settings - NOW ONLY FOR ROAST MODE
USE_CUSTOM_VOICE_FOR_ROAST = True  # Set to True to use custom voice for Roast Mode only
CUSTOM_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Will be set after cloning
CUSTOM_VOICE_PATH = "/Users/shubhamagrawal/Documents/MS fall 25/MS fall'25/matthew_sample.wav"  # Path to your .wav file
CUSTOM_VOICE_NAME = "my_custom_voice"  # Name for your cloned voice

# Voice configurations for different feedback modes
VOICE_CONFIGS = {
    "🔥 Roast Mode": {
        "voice_id":"pNInz6obpgDQGcFmaJgB",# "nPczCjzI2devNBz1zQrb",  # Brian - Male voice (will be replaced if custom voice enabled)
        "stability": 0.50,  # 50%
        "similarity_boost": 0.75,  # 75%
        "style": 0.0,
        "speed": 1.0,  # Normal speed (1.0 = 100%)
        "use_custom": True  # NEW: Flag to indicate this mode uses custom voice
    },
    "💡 Constructive Mode": {
        "voice_id": "21m00Tcm4TlvDq8ikWAM",  # Rachel - professional, warm
        "stability": 0.60,
        "similarity_boost": 0.80,
        "style": 0.4,
        "speed": 1.0,
        "use_custom": False  # NEW: This mode keeps default voice
    },
    "Normal": {
        "voice_id": "pNInz6obpgDQGcFmaJgB",  # Adam - neutral, clear
        "stability": 0.65,
        "similarity_boost": 0.75,
        "style": 0.5,
        "speed": 1.0,
        "use_custom": False  # NEW: This mode keeps default voice
    }
}

def clone_custom_voice(audio_file_path, voice_name, description="Custom cloned voice"):
    """
    Clone a custom voice from an audio file.
    
    Args:
        audio_file_path: Path to .wav file (min 1 minute recommended)
        voice_name: Name for the cloned voice
        description: Description of the voice
        
    Returns:
        str: Voice ID of the cloned voice, or None if failed
    """
    global CUSTOM_VOICE_ID, USE_CUSTOM_VOICE_FOR_ROAST
    
    if not ELEVENLABS_AVAILABLE or not client:
        print("⚠️ ElevenLabs not available")
        return None
    
    audio_path = Path(audio_file_path)
    if not audio_path.exists():
        print(f"❌ Audio file not found: {audio_file_path}")
        return None
    
    print(f"🎤 Cloning voice from: {audio_file_path}")
    print(f"   Voice name: {voice_name}")
    
    try:
        # Read audio file
        with open(audio_path, 'rb') as audio_file:
            audio_data = audio_file.read()
        
        # Clone the voice using ElevenLabs API
        voice = client.voices.clone(
            name=voice_name,
            description=description,
            files=[audio_data]  # Can provide multiple samples for better quality
        )
        
        CUSTOM_VOICE_ID = voice.voice_id
        USE_CUSTOM_VOICE_FOR_ROAST = True
        
        print(f"✅ Voice cloned successfully!")
        print(f"   Voice ID: {CUSTOM_VOICE_ID}")
        print(f"   Name: {voice_name}")
        print(f"   This voice will be used for Roast Mode only")
        
        # Update ONLY Roast Mode to use custom voice
        VOICE_CONFIGS["🔥 Roast Mode"]["voice_id"] = CUSTOM_VOICE_ID
        
        return CUSTOM_VOICE_ID
        
    except Exception as e:
        print(f"❌ Voice cloning failed: {e}")
        return None

def list_available_voices():
    """List all available voices (including custom cloned voices)."""
    if not ELEVENLABS_AVAILABLE or not client:
        print("⚠️ ElevenLabs not available")
        return []
    
    try:
        voices = client.voices.get_all()
        
        print("\n📋 Available Voices:")
        print("=" * 60)
        
        voice_list = []
        for voice in voices.voices:
            voice_info = {
                "name": voice.name,
                "voice_id": voice.voice_id,
                "category": voice.category if hasattr(voice, 'category') else "Unknown"
            }
            voice_list.append(voice_info)
            print(f"  • {voice.name} ({voice.voice_id})")
        
        print("=" * 60)
        return voice_list
        
    except Exception as e:
        print(f"❌ Failed to list voices: {e}")
        return []

def delete_custom_voice(voice_id):
    """Delete a custom cloned voice."""
    if not ELEVENLABS_AVAILABLE or not client:
        print("⚠️ ElevenLabs not available")
        return False
    
    try:
        client.voices.delete(voice_id)
        print(f"✅ Voice {voice_id} deleted successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to delete voice: {e}")
        return False

def clean_text_for_speech(text):
    """
    Clean text to make it optimized for speech synthesis.
    Removes dates, formatting, and unnecessary symbols while keeping the core message.
    """
    
    # Remove markdown formatting
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Remove bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)  # Remove italic
    text = re.sub(r'#{1,6}\s+', '', text)  # Remove headers
    text = re.sub(r'`([^`]+)`', r'\1', text)  # Remove code formatting
    
    # Remove emojis (they don't read well)
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    text = emoji_pattern.sub('', text)
    
    # Remove special formatting markers
    text = re.sub(r'---+', '', text)  # Remove horizontal rules
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)  # Remove bullet points
    
    # Remove dates in common formats (e.g., "Jan 2023", "2023-01-15", "01/15/2023")
    text = re.sub(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b', '', text)
    text = re.sub(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b', '', text)
    text = re.sub(r'\b\d{4}\b', '', text)  # Remove standalone years
    
    # Remove percentages and specific metrics markers (keep the numbers but clean context)
    text = re.sub(r'\(relevance:\s*\d+\.?\d*\)', '', text)  # Remove relevance scores
    text = re.sub(r'Match Score:\s*\d+\.?\d*%', 'Overall match score', text)
    
    # Remove section markers like "--- Section Name ---"
    text = re.sub(r'---\s*[^-]+\s*---', '', text)
    
    # Clean up multiple newlines and spaces
    text = re.sub(r'\n\s*\n+', '. ', text)
    text = re.sub(r'\s+', ' ', text)
    
    # Remove parenthetical citations or notes
    text = re.sub(r'\([^)]*\)', '', text)
    
    # Limit length for TTS (max ~1000 words for quality)
    words = text.split()
    if len(words) > 1000:
        text = ' '.join(words[:1000]) + "... I have more to say, but check the full text for details."
    
    # Final cleanup
    text = text.strip()
    
    # Replace common abbreviations for better speech
    replacements = {
        'e.g.': 'for example',
        'i.e.': 'that is',
        'etc.': 'and so on',
        'vs.': 'versus',
        'Jr.': 'Junior',
        'Sr.': 'Senior',
    }
    
    for abbr, full in replacements.items():
        text = text.replace(abbr, full)
    
    return text

def text_to_speech(text, mode="Normal"):
    """
    Convert text to speech using ElevenLabs API.
    
    Args:
        text: Text to convert to speech
        mode: Feedback mode for voice customization ("Normal", "🔥 Roast Mode", "💡 Constructive Mode")
        
    Returns:
        bytes: Audio data in MP3 format, or None if failed
    """
    
    if not ELEVENLABS_AVAILABLE or not client:
        print("⚠️ ElevenLabs not available. Please check your API key.")
        return None
    
    # Clean text for speech
    cleaned_text = clean_text_for_speech(text)
    
    if len(cleaned_text) < 10:
        print("Text too short for TTS")
        return None
    
    # Get voice configuration
    config = VOICE_CONFIGS.get(mode, VOICE_CONFIGS["Normal"])
    
    # Use custom voice ONLY if this mode allows it AND custom voice is available
    voice_id = config["voice_id"]
    if config.get("use_custom", False) and USE_CUSTOM_VOICE_FOR_ROAST and CUSTOM_VOICE_ID:
        voice_id = CUSTOM_VOICE_ID
        print(f"   Using custom cloned voice for {mode}: {CUSTOM_VOICE_ID}")
    else:
        print(f"   Using default voice for {mode}: {voice_id}")
    
    print(f"🎤 Generating speech with ElevenLabs ({mode})...")
    print(f"   Voice ID: {voice_id}")
    print(f"   Text length: {len(cleaned_text)} characters")
    print(f"   Settings: Stability={config['stability']*100}%, Similarity={config['similarity_boost']*100}%, Speed={config['speed']}")
    
    try:
        # Build voice settings
        from elevenlabs import VoiceSettings
        
        voice_settings = VoiceSettings(
            stability=config["stability"],
            similarity_boost=config["similarity_boost"],
            style=config.get("style", 0.0),
            use_speaker_boost=True
        )
        
        # Generate audio with ElevenLabs
        audio_generator = client.text_to_speech.convert(
            text=cleaned_text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
            voice_settings=voice_settings
        )
        
        # Collect audio bytes from generator
        audio_bytes = b"".join(audio_generator)
        
        print(f"✅ Audio generated successfully ({len(audio_bytes)} bytes)")
        return audio_bytes
        
    except Exception as e:
        print(f"❌ ElevenLabs TTS failed: {e}")
        
        # Check for API key issues
        error_str = str(e).lower()
        if "auth" in error_str or "key" in error_str or "401" in error_str:
            print("⚠️ API Key issue detected!")
            print(f"   Current key starts with: {ELEVEN_API_KEY[:10] if ELEVEN_API_KEY else 'None'}...")
            print("   Get your key from: https://elevenlabs.io/app/settings/api-keys")
            print("   Set ELEVENLABS_API_KEY_HARDCODED in audio_handler.py or add to .env file")
        
        return None

def get_available_voices():
    """Get list of available voices from ElevenLabs."""
    if not ELEVENLABS_AVAILABLE:
        return []
    
    try:
        voices = client.voices.get_all()
        return [{"name": voice.name, "voice_id": voice.voice_id} for voice in voices.voices]
    except Exception as e:
        print(f"Error fetching voices: {e}")
        return []

# Test function
if __name__ == "__main__":
    print("Testing ElevenLabs TTS Audio Handler with Custom Voice for Roast Mode")
    print("=" * 60)
    
    if not ELEVENLABS_AVAILABLE:
        print("❌ ElevenLabs not initialized. Please check your API key.")
        print("   Set ELEVENLABS_API_KEY in your .env file")
        exit(1)
    
    # List available voices
    print("\n1. Listing available voices...")
    list_available_voices()
    
    # Clone custom voice if file exists
    if Path(CUSTOM_VOICE_PATH).exists():
        print(f"\n2. Custom voice file found: {CUSTOM_VOICE_PATH}")
        choice = input("Clone this voice for Roast Mode? (y/n): ").lower()
        
        if choice == 'y':
            voice_id = clone_custom_voice(
                CUSTOM_VOICE_PATH,
                CUSTOM_VOICE_NAME,
                "Custom voice for Resume Roaster - Roast Mode only"
            )
            
            if voice_id:
                print(f"\n✅ Custom voice ready for Roast Mode! Voice ID: {voice_id}")
                USE_CUSTOM_VOICE_FOR_ROAST = True
            else:
                print("\n❌ Voice cloning failed. Using default voice for Roast Mode.")
    else:
        print(f"\n2. No custom voice file found at: {CUSTOM_VOICE_PATH}")
        print("   Place your .wav file there to enable custom voice cloning for Roast Mode")
    
    # Test TTS with different modes
    print("\n3. Testing TTS generation...")
    test_texts = {
        "🔥 Roast Mode": "Your resume is terrible. Where are the metrics? Did you even do anything measurable?",
        "💡 Constructive Mode": "Let's improve your resume. Focus on quantifiable achievements and strong action verbs.",
        "Normal": "Your resume shows good experience. Consider adding more specific examples."
    }
    
    for mode, text in test_texts.items():
        print(f"\n{'='*60}")
        print(f"Testing {mode}...")
        print(f"{'='*60}")
        
        audio_bytes = text_to_speech(text, mode=mode)
        
        if audio_bytes:
            # Save test audio
            output_path = f"test_audio_{mode.replace(' ', '_').replace('🔥', 'roast').replace('💡', 'constructive')}.mp3"
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            print(f"✅ Saved: {output_path}")
        else:
            print(f"❌ Failed to generate audio for {mode}")
    
    print("\n" + "=" * 60)
    print("Testing complete!")
    print(f"\nCustom voice for Roast Mode enabled: {USE_CUSTOM_VOICE_FOR_ROAST}")
    if USE_CUSTOM_VOICE_FOR_ROAST and CUSTOM_VOICE_ID:
        print(f"Custom voice ID (Roast Mode only): {CUSTOM_VOICE_ID}")
        print(f"Constructive Mode voice: {VOICE_CONFIGS['💡 Constructive Mode']['voice_id']}")
        print(f"Normal Mode voice: {VOICE_CONFIGS['Normal']['voice_id']}")