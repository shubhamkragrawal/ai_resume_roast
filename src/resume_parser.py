import re
from collections import OrderedDict
from pathlib import Path
import json

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("Warning: pdfplumber not installed. PDF parsing disabled.")

try:
    from transformers import pipeline
    AI_PARSER_AVAILABLE = True
except ImportError:
    AI_PARSER_AVAILABLE = False
    print("Warning: transformers not available. Using rule-based parsing.")

# Enhanced section headers with more variations
SECTION_HEADERS = [
    # Summary/Objective variations
    "summary", "professional summary", "profile", "objective", "career objective",
    "about me", "overview", "executive summary", "professional profile",
    
    # Experience variations
    "experience", "work experience", "employment", "professional experience",
    "work history", "career history", "employment history", "relevant experience",
    
    # Education variations
    "education", "academic background", "academic qualifications", "educational background",
    "qualifications", "degrees",
    
    # Skills variations
    "skills", "technical skills", "core competencies", "expertise", "proficiencies",
    "technical proficiencies", "key skills", "areas of expertise", "skill set",
    
    # Projects variations
    "projects", "notable projects", "key projects", "personal projects", "portfolio",
    
    # Certifications
    "certifications", "certificates", "professional certifications", "licenses",
    "credentials",
    
    # Additional sections
    "awards", "honors", "achievements", "accomplishments", "recognition",
    "publications", "research", "papers",
    "volunteer", "volunteering", "volunteer experience", "community service",
    "languages", "language proficiency",
    "interests", "hobbies", "activities"
]

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file using pdfplumber with enhanced settings."""
    if not PDF_AVAILABLE:
        raise ImportError("pdfplumber is required. Install: pip install pdfplumber")
    
    text_parts = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Extract text with layout preservation
                page_text = page.extract_text(layout=True)
                if page_text:
                    text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        # Fallback to simple extraction
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    
    return "\n\n".join(text_parts)

def clean_text(text):
    """Clean and normalize text with better handling."""
    # Remove excessive whitespace but preserve some structure
    text = re.sub(r' +', ' ', text)
    # Normalize line breaks
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    # Remove page markers
    text = re.sub(r'--- Page \d+ ---\n', '', text)
    return text.strip()

def ai_based_section_detection(text):
    """
    Use AI model to detect and classify resume sections.
    Falls back to rule-based if AI unavailable.
    """
    if not AI_PARSER_AVAILABLE:
        return None
    
    try:
        # Use zero-shot classification to identify sections
        classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
        
        # Split text into potential sections (by double newlines or headers)
        potential_sections = re.split(r'\n\n+', text)
        
        section_labels = [
            "contact information",
            "professional summary",
            "work experience", 
            "education",
            "skills",
            "projects",
            "certifications",
            "awards"
        ]
        
        classified_sections = OrderedDict()
        
        for chunk in potential_sections:
            if len(chunk.strip()) < 20:  # Skip very short chunks
                continue
                
            # Classify the chunk
            result = classifier(chunk[:500], section_labels, multi_label=False)
            best_label = result['labels'][0]
            confidence = result['scores'][0]
            
            if confidence > 0.3:  # Only include if reasonably confident
                if best_label not in classified_sections:
                    classified_sections[best_label] = []
                classified_sections[best_label].append(chunk)
        
        # Combine chunks for same sections
        final_sections = OrderedDict()
        for label, chunks in classified_sections.items():
            final_sections[label.title()] = "\n\n".join(chunks)
        
        return final_sections if final_sections else None
        
    except Exception as e:
        print(f"AI parsing failed: {e}")
        return None

def rule_based_section_detection(text):
    """
    Enhanced rule-based section detection with better header matching.
    """
    sections = OrderedDict()
    
    # Create regex pattern with word boundaries
    header_pattern = r'(?:^|\n)\s*(' + '|'.join([re.escape(h) for h in SECTION_HEADERS]) + r')[\s:]*\n'
    
    # Find all section header matches
    matches = list(re.finditer(header_pattern, text, re.IGNORECASE))
    
    if not matches:
        # Try alternative: look for all-caps headers
        caps_pattern = r'\n([A-Z\s]{3,30})\n'
        matches = list(re.finditer(caps_pattern, text))
        
        if not matches:
            # No clear sections found
            sections["Full Resume"] = text
            return sections
    
    # Extract sections
    for i, match in enumerate(matches):
        section_name = match.group(1).strip().title()
        start_pos = match.end()
        
        # Find end position (start of next section or end of text)
        if i < len(matches) - 1:
            end_pos = matches[i + 1].start()
        else:
            end_pos = len(text)
        
        section_content = text[start_pos:end_pos].strip()
        
        if section_content:
            # Normalize section names
            normalized_name = normalize_section_name(section_name)
            sections[normalized_name] = section_content
    
    # Extract contact info from top if exists
    if matches and matches[0].start() > 50:
        header_content = text[:matches[0].start()].strip()
        if header_content:
            sections_copy = OrderedDict()
            sections_copy["Contact Information"] = header_content
            sections_copy.update(sections)
            sections = sections_copy
    
    return sections

def normalize_section_name(name):
    """Normalize section names to standard categories."""
    name_lower = name.lower()
    
    if any(x in name_lower for x in ["summary", "profile", "objective", "about"]):
        return "Professional Summary"
    elif any(x in name_lower for x in ["experience", "employment", "work history"]):
        return "Experience"
    elif any(x in name_lower for x in ["education", "academic"]):
        return "Education"
    elif any(x in name_lower for x in ["skill", "competenc", "expertise", "proficien"]):
        return "Skills"
    elif any(x in name_lower for x in ["project", "portfolio"]):
        return "Projects"
    elif any(x in name_lower for x in ["certif", "license", "credential"]):
        return "Certifications"
    elif any(x in name_lower for x in ["award", "honor", "achievement", "recognition"]):
        return "Awards"
    elif any(x in name_lower for x in ["publication", "research", "paper"]):
        return "Publications"
    elif any(x in name_lower for x in ["volunteer", "community"]):
        return "Volunteer Experience"
    else:
        return name.title()

def extract_key_metrics(sections):
    """Extract key metrics from resume for quick analysis."""
    metrics = {
        "total_sections": len(sections),
        "has_summary": any("summary" in s.lower() for s in sections.keys()),
        "has_experience": any("experience" in s.lower() for s in sections.keys()),
        "has_education": any("education" in s.lower() for s in sections.keys()),
        "has_skills": any("skill" in s.lower() for s in sections.keys()),
        "has_quantifiable_achievements": False,
        "word_count": sum(len(content.split()) for content in sections.values())
    }
    
    # Check for numbers (potential quantifiable achievements)
    full_text = " ".join(sections.values())
    if re.search(r'\d+%|\$\d+|\d+\+|increased by \d+|reduced by \d+', full_text, re.IGNORECASE):
        metrics["has_quantifiable_achievements"] = True
    
    return metrics

def parse_resume(input_data):
    """
    Parse resume using AI-based detection first, fallback to rule-based.
    
    Args:
        input_data: PDF path, TXT path, or raw text string
        
    Returns:
        tuple: (sections_dict, combined_text)
    """
    # Determine input type and extract text
    if isinstance(input_data, (str, Path)):
        path = Path(input_data)
        if path.exists():
            if path.suffix.lower() == '.pdf':
                text = extract_text_from_pdf(path)
            elif path.suffix.lower() == '.txt':
                with open(path, 'r', encoding='utf-8') as f:
                    text = f.read()
            else:
                text = str(input_data)
        else:
            text = str(input_data)
    else:
        text = str(input_data)
    
    # Clean the text
    cleaned_text = clean_text(text)
    
    # Try AI-based detection first
    sections = None
    if AI_PARSER_AVAILABLE:
        print("Attempting AI-based section detection...")
        sections = ai_based_section_detection(cleaned_text)
    
    # Fallback to rule-based
    if sections is None or len(sections) < 2:
        print("Using enhanced rule-based section detection...")
        sections = rule_based_section_detection(cleaned_text)
    
    # Extract metrics
    metrics = extract_key_metrics(sections)
    print(f"Parsed {metrics['total_sections']} sections, {metrics['word_count']} words")
    
    return sections, cleaned_text

def get_section_summary(sections):
    """Generate a detailed summary of parsed sections."""
    summary_parts = ["📊 Resume Analysis:"]
    
    for section_name, content in sections.items():
        word_count = len(content.split())
        char_count = len(content)
        summary_parts.append(f"  • {section_name}: {word_count} words, {char_count} characters")
    
    return "\n".join(summary_parts)

# Test function
if __name__ == "__main__":
    sample_text = """
    John Doe
    john.doe@email.com | (555) 123-4567 | LinkedIn: linkedin.com/in/johndoe
    
    PROFESSIONAL SUMMARY
    Experienced software engineer with 5+ years in full-stack development.
    Increased team productivity by 40% through automation initiatives.
    
    EXPERIENCE
    Senior Developer at Tech Corp (2020-Present)
    - Led team of 5 developers on microservices architecture
    - Improved system performance by 40% through optimization
    - Reduced deployment time from 2 hours to 15 minutes
    
    Software Engineer at StartupXYZ (2018-2020)
    - Built RESTful APIs serving 1M+ requests daily
    - Implemented CI/CD pipeline reducing bugs by 60%
    
    EDUCATION
    BS Computer Science, State University, 2018
    GPA: 3.8/4.0
    
    SKILLS
    Languages: Python, JavaScript, Java, Go
    Frameworks: React, Node.js, Django, Spring Boot
    Cloud: AWS, Docker, Kubernetes, Terraform
    
    PROJECTS
    Open Source Contributor - Contributed to 10+ popular repositories
    Personal Portfolio - Built with React and deployed on AWS
    """
    
    print("Testing resume parser...")
    sections, combined = parse_resume(sample_text)
    print("\n" + get_section_summary(sections))
    print("\n✅ Parser test complete!")