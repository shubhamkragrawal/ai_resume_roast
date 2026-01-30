from embeddings import get_relevant_context, compare_resume_to_jd, get_jd_keywords
import os
import time
import hashlib
import json
from pathlib import Path
import requests
# from dotenv import load_dotenv

# Load environment variables
# load_dotenv()

# Global conversation history
conversation_history = []

# Cache for API responses (prevents duplicate calls)
response_cache = {}
CACHE_DIR = Path("response_cache")
CACHE_DIR.mkdir(exist_ok=True)

# Rate limiting tracker
api_call_times = []
MAX_CALLS_PER_MINUTE = 10  # OpenRouter has higher limits

# OpenRouter API configuration
OPENROUTER_API_KEY = None
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
GEMINI_MODEL = "google/gemini-2.5-pro"  # OpenRouter model identifier

def get_cache_key(user_query, context, feedback_mode):
    """Generate a unique cache key for a query."""
    cache_string = f"{user_query}|{context[:500]}|{feedback_mode}"
    return hashlib.md5(cache_string.encode()).hexdigest()

def check_cache(cache_key):
    """Check if response exists in cache."""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                cached_data = json.load(f)
            # Check if cache is less than 1 hour old
            if time.time() - cached_data['timestamp'] < 3600:
                print("Using cached response")
                return cached_data['response']
        except:
            pass
    return None

def save_to_cache(cache_key, response):
    """Save response to cache."""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    try:
        with open(cache_file, 'w') as f:
            json.dump({
                'response': response,
                'timestamp': time.time()
            }, f)
    except Exception as e:
        print(f"Cache save failed: {e}")

def check_rate_limit():
    """Check if we're within rate limits."""
    global api_call_times
    
    current_time = time.time()
    # Remove calls older than 1 minute
    api_call_times = [t for t in api_call_times if current_time - t < 60]
    
    calls_in_last_minute = len(api_call_times)
    
    if calls_in_last_minute >= MAX_CALLS_PER_MINUTE:
        wait_time = 60 - (current_time - api_call_times[0])
        print(f"RATE LIMIT: {calls_in_last_minute} calls in last minute")
        print(f"   Waiting {wait_time:.1f} seconds...")
        return False, wait_time
    
    return True, 0

def record_api_call():
    """Record that an API call was made."""
    global api_call_times
    api_call_times.append(time.time())
    print(f"API calls in last minute: {len(api_call_times)}/{MAX_CALLS_PER_MINUTE}")

def build_prompt(user_query, context, feedback_mode, jd_comparison=None):
    """Build the prompt based on feedback mode."""
    
    if feedback_mode == "🔥 Roast Mode":
        system_message = """You are a brutally honest resume critic with a sharp tongue. Your job is to ROAST this resume mercilessly.

                    BE BLUNT AND DIRECT. No questions, no hand-holding - just pure, unfiltered criticism. Point out:
                    - Vague, meaningless statements like "responsible for" or "worked on"
                    - Missing metrics and numbers (if you didn't quantify it, it didn't happen)
                    - Weak action verbs that make you sound passive
                    - Buzzword soup and corporate jargon
                    - Formatting disasters and readability issues
                    - Anything that screams "I have no idea what I actually accomplished"

                    Use sarcasm. Be harsh. Mock the bad parts relentlessly. Examples:
                    - "Responsible for managing projects" - Congratulations, you showed up to work and breathed air.
                    - No numbers anywhere? What did you actually DO? Exist in the office space?
                    - "Team player" - Thanks for that groundbreaking insight. Next you'll tell me you have "strong communication skills."

                    End with a harsh numerical rating out of 10 and a one-line brutal summary.

                    DO NOT ASK QUESTIONS. DO NOT BE ENCOURAGING. Just roast it."""

    elif feedback_mode == "💡 Constructive Mode":
        system_message = """You are an expert resume coach providing detailed, actionable feedback.

                    For each issue you identify, provide:
                    1. WHAT'S WRONG: Be specific about the problem
                    2. WHY IT MATTERS: Explain the impact on recruiters/ATS
                    3. HOW TO FIX IT: Give concrete examples and templates
                    4. BEFORE/AFTER: Show the transformation

                    Focus on:
                    - Quantifiable achievements (numbers, percentages, scale, impact)
                    - Strong action verbs (achieved, spearheaded, architected vs. managed, helped, worked on)
                    - ATS keyword optimization
                    - Clear impact statements (Action + Result + Benefit)
                    - Proper structure and formatting

                    Be thorough but practical. Provide real examples the person can immediately use."""

    else:  # Normal mode
        system_message = """You are a professional resume consultant providing balanced feedback.

                    Be honest but encouraging. Point out both strengths and weaknesses. Give specific, actionable suggestions for improvement.
                      Keep responses focused and practical."""

    # Add JD comparison context if available
    jd_context = ""
    if jd_comparison:
        match_score = jd_comparison.get('overall_match', 0)
        weak_sections = jd_comparison.get('weak_sections', [])
        jd_context = f"""
                JOB DESCRIPTION ALIGNMENT:
                - Match Score: {match_score:.1f}%
                - Sections needing improvement: {', '.join(weak_sections) if weak_sections else 'None'}

                Address gaps between the resume and JD requirements in your feedback.
                """

    user_message = f"""{jd_context}

                RESUME CONTENT:
                {context}

                USER REQUEST: {user_query}"""
    
    return system_message, user_message

def apply_minimal_filter(response):
    """Minimal filtering - only removes truly discriminatory content."""
    blocked_patterns = []
    
    response_lower = response.lower()
    for pattern in blocked_patterns:
        if pattern in response_lower:
            return "Response contained inappropriate content. Rephrasing to focus on resume quality..."
    
    return response

def enhance_roast_response(response):
    """Add roast mode formatting without exposing system instructions."""
    roast_header = "🔥 **ROAST MODE** 🔥\n\n"
    footer = "\n\n---\n💀 *Now go fix this mess.* 💀"
    return roast_header + response + footer

def enhance_constructive_response(response):
    """Add structure to constructive feedback without exposing system instructions."""
    header = "💡 **CONSTRUCTIVE ANALYSIS** 💡\n\n"
    footer = "\n\n---\n*You've got this! Every improvement matters.*"
    return header + response + footer

def call_openrouter_api(system_message, user_message, feedback_mode):
    """
    Call OpenRouter API with Gemini 2.5 Pro model.
    
    Args:
        system_message: System prompt
        user_message: User's question with context
        feedback_mode: Feedback mode for temperature adjustment
        
    Returns:
        str: Model's response
    """
    
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not found in environment variables")
    
    # Temperature settings based on mode
    temp_config = {
        "🔥 Roast Mode": 0.95,
        "💡 Constructive Mode": 0.7,
        "Normal": 0.7
    }
    
    temperature = temp_config.get(feedback_mode, 0.7)
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://github.com/yourusername/resume-roaster",  # Optional: your site URL
        "X-Title": "Resume Roaster Pro",  # Optional: shows in rankings
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": GEMINI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_message
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        "temperature": temperature,
        "max_tokens": 2048,
        "top_p": 0.95
    }
    
    print(f"🤖 Calling OpenRouter API (Model: {GEMINI_MODEL})...")
    print(f"   Temperature: {temperature}")
    
    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        response.raise_for_status()
        
        result = response.json()
        
        # Extract response text
        if 'choices' in result and len(result['choices']) > 0:
            return result['choices'][0]['message']['content']
        else:
            raise ValueError(f"Unexpected API response format: {result}")
            
    except requests.exceptions.RequestException as e:
        raise Exception(f"OpenRouter API request failed: {str(e)}")

def rag_query(user_query, feedback_mode="Normal", job_description=None, k=6):
    """
    Process a user query using RAG with OpenRouter's Gemini API.
    Includes caching and rate limiting to prevent RPM issues.
    
    Args:
        user_query: User's question
        feedback_mode: "Normal", "🔥 Roast Mode", or "💡 Constructive Mode"
        job_description: Optional JD text for comparison
        k: Number of context chunks
        
    Returns:
        str: Model's response (clean, without system prompts)
    """
    global conversation_history
    
    try:
        # Get JD comparison if available
        jd_comparison = None
        if job_description:
            jd_comparison = compare_resume_to_jd()
            
            if any(term in user_query.lower() for term in ['jd', 'job description', 'match', 'missing', 'gap']):
                k = 8
        
        # Retrieve relevant context
        include_jd = job_description is not None
        context = get_relevant_context(user_query, k=k, include_jd=include_jd)
        
        # Add JD keywords if relevant
        if job_description and any(term in user_query.lower() for term in ['keyword', 'missing', 'gap', 'ats']):
            jd_keywords = get_jd_keywords()
            context += f"\n\nKEY JD TERMS: {', '.join(jd_keywords[:15])}"
        
        # Check cache first
        cache_key = get_cache_key(user_query, context, feedback_mode)
        cached_response = check_cache(cache_key)
        
        if cached_response:
            return cached_response
        
        # Check rate limit
        can_proceed, wait_time = check_rate_limit()
        if not can_proceed:
            return f"⏳ Rate limit reached. Please wait {int(wait_time)} seconds before asking another question. (This prevents API quota issues)"
        
        # Build prompt
        system_message, user_message = build_prompt(user_query, context, feedback_mode, jd_comparison)
        
        # Record API call
        record_api_call()
        
        # Call OpenRouter API
        response_text = call_openrouter_api(system_message, user_message, feedback_mode)
        
        # Apply minimal filtering
        response_text = apply_minimal_filter(response_text)
        
        # Add minimal mode indicators
        if feedback_mode == "🔥 Roast Mode":
            response_text = enhance_roast_response(response_text)
        elif feedback_mode == "💡 Constructive Mode":
            response_text = enhance_constructive_response(response_text)
        
        # Add JD match summary if relevant
        if jd_comparison and any(term in user_query.lower() for term in ['match', 'compare', 'jd']):
            match_summary = f"\n\n📊 **JD Match Score: {jd_comparison['overall_match']:.1f}%**"
            if jd_comparison['weak_sections']:
                match_summary += f"\n⚠️ Weak sections: {', '.join(jd_comparison['weak_sections'])}"
            response_text += match_summary
        
        # Save to cache
        save_to_cache(cache_key, response_text)
        
        # Store in conversation history
        conversation_history.append({
            "query": user_query,
            "response": response_text,
            "mode": feedback_mode,
            "had_jd": job_description is not None
        })
        
        return response_text
        
    except Exception as e:
        error_msg = f"Error generating response: {str(e)}"
        print(error_msg)
        
        if "api" in str(e).lower() or "key" in str(e).lower() or "auth" in str(e).lower():
            return """❌ **OpenRouter API Error**

                Please check your OpenRouter API key:

                1. Get an API key from: https://openrouter.ai/keys
                2. Add to your .env file: OPENROUTER_API_KEY=your-key-here
                3. Make sure you have credits in your OpenRouter account

                Error details: """ + str(e)[:200]
        
        if feedback_mode == "🔥 Roast Mode":
            return "🔥 The system crashed trying to process this resume. That should tell you something. Fix your API key first though."
        else:
            return f"I encountered an error. Please check your OpenRouter API key. Error: {str(e)[:150]}"

def get_conversation_summary():
    """Get a summary of the conversation history."""
    if not conversation_history:
        return "No conversation history yet."
    
    roast_count = sum(1 for h in conversation_history if h['mode'] == "🔥 Roast Mode")
    constructive_count = sum(1 for h in conversation_history if h['mode'] == "💡 Constructive Mode")
    
    summary = f"""📊 Session Summary:
- Total exchanges: {len(conversation_history)}
- 🔥 Roast Mode: {roast_count}
- 💡 Constructive Mode: {constructive_count}
- With JD: {sum(1 for h in conversation_history if h.get('had_jd'))}
"""
    return summary

def clear_conversation_history():
    """Clear the conversation history."""
    global conversation_history
    conversation_history = []

def clear_cache():
    """Clear response cache."""
    import shutil
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
        CACHE_DIR.mkdir()
    print("✅ Cache cleared")

def check_api_key():
    """Check if API key is configured."""
    if not OPENROUTER_API_KEY:
        print("⚠️ WARNING: OPENROUTER_API_KEY not found in environment")
        print("   Get your key from: https://openrouter.ai/keys")
        return False
    return True

if __name__ == "__main__":
    print("RAG Chat Module - OpenRouter + Gemini 2.5 Pro")
    print("=" * 60)
    
    if check_api_key():
        print("✅ OpenRouter API key configured")
    else:
        print("❌ OpenRouter API key not configured - please update .env file")
    
    print("\nFeatures:")
    print("- 🔥 Roast Mode: Brutal, no-questions criticism")
    print("- 💡 Constructive Mode: Detailed improvement guidance")
    print("- Normal Mode: Balanced feedback")
    print("- 💾 Response Caching: Prevents duplicate API calls")
    print("- ⏱️ Rate Limiting: Protects against RPM quota")
    print(f"- Model: {GEMINI_MODEL} via OpenRouter")
    print(f"- Max calls per minute: {MAX_CALLS_PER_MINUTE}")