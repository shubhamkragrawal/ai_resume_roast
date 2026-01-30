import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss
import re

# Global variables
model = None
index = None
metadata = []
job_description_embedding = None

INDEX_PATH = "resume_index.faiss"
METADATA_PATH = "resume_metadata.json"
JD_EMBEDDING_PATH = "jd_embedding.npy"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

def get_model():
    """Get or initialize the sentence transformer model."""
    global model
    if model is None:
        print("Loading embedding model...")
        model = SentenceTransformer(EMBEDDING_MODEL)
        print("Embedding model loaded")
    return model

def chunk_text(text, max_tokens=200, overlap=50):
    """
    Split text into overlapping chunks for better context preservation.
    """
    words = text.split()
    chunks = []
    
    i = 0
    while i < len(words):
        chunk = ' '.join(words[i:i + max_tokens])
        if chunk.strip():
            chunks.append(chunk)
        i += max_tokens - overlap  # Overlap for context
    
    return chunks

def build_embeddings(sections, combined_text, job_description=None):
    """
    Build embeddings for resume sections with optional JD comparison.
    
    Args:
        sections: OrderedDict of section_name -> content
        combined_text: Full resume text
        job_description: Optional JD text for comparison
    """
    global index, metadata, job_description_embedding
    
    model = get_model()
    
    # Prepare chunks with metadata
    chunks = []
    metadata = []
    
    # Add full resume overview as first chunk
    resume_overview = combined_text[:1500]
    chunks.append(resume_overview)
    metadata.append({
        "section": "Resume Overview",
        "chunk_id": 0,
        "text": resume_overview,
        "type": "overview"
    })
    
    chunk_id = 1
    
    # Process each section with overlapping chunks
    for section_name, content in sections.items():
        section_chunks = chunk_text(content, max_tokens=200, overlap=50)
        
        for chunk in section_chunks:
            chunks.append(chunk)
            metadata.append({
                "section": section_name,
                "chunk_id": chunk_id,
                "text": chunk,
                "type": "section",
                "word_count": len(chunk.split())
            })
            chunk_id += 1
    
    if job_description and job_description.strip():
        print("Adding job description to index...")
        jd_chunks = chunk_text(job_description, max_tokens=250)
        
        for jd_chunk in jd_chunks:
            chunks.append(jd_chunk)
            metadata.append({
                "section": "Job Description",
                "chunk_id": chunk_id,
                "text": jd_chunk,
                "type": "job_description"
            })
            chunk_id += 1
        
        jd_embedding = model.encode([job_description], convert_to_numpy=True)
        job_description_embedding = jd_embedding[0]
        np.save(JD_EMBEDDING_PATH, job_description_embedding)
    else:
        job_description_embedding = None
        if Path(JD_EMBEDDING_PATH).exists():
            Path(JD_EMBEDDING_PATH).unlink()
    
    print(f"Generating embeddings for {len(chunks)} chunks...")
    
    embeddings = model.encode(
        chunks, 
        show_progress_bar=True, 
        convert_to_numpy=True,
        batch_size=32
    )
    
    # Create FAISS index with better settings
    dimension = embeddings.shape[1]
    
    # Use IndexFlatIP (inner product) for cosine similarity
    index = faiss.IndexFlatIP(dimension)
    
    # Normalize embeddings for cosine similarity
    faiss.normalize_L2(embeddings.astype('float32'))
    index.add(embeddings.astype('float32'))
    
    faiss.write_index(index, INDEX_PATH)
    with open(METADATA_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Created embeddings for {len(chunks)} chunks")
    print(f"   Resume chunks: {len([m for m in metadata if m['type'] != 'job_description'])}")
    if job_description:
        print(f"   JD chunks: {len([m for m in metadata if m['type'] == 'job_description'])}")

def load_or_create_index():
    """Load existing index or return None if not found."""
    global index, metadata, job_description_embedding
    
    if Path(INDEX_PATH).exists() and Path(METADATA_PATH).exists():
        index = faiss.read_index(INDEX_PATH)
        with open(METADATA_PATH, 'r') as f:
            metadata = json.load(f)
        
        # Load JD embedding if exists
        if Path(JD_EMBEDDING_PATH).exists():
            job_description_embedding = np.load(JD_EMBEDDING_PATH)
        
        print(f"Loaded index with {len(metadata)} chunks")
        return True
    return False

def search_similar(query, k=5, filter_type=None):
    """
    Search for k most similar chunks to the query.
    
    Args:
        query: Search query string
        k: Number of results to return
        filter_type: Filter by type ('section', 'job_description', 'overview')
        
    Returns:
        List of dicts with section, text, and similarity score
    """
    global index, metadata
    
    if index is None:
        if not load_or_create_index():
            raise ValueError("No index found. Please build embeddings first.")
    
    model = get_model()
    
    # Encode query
    query_embedding = model.encode([query], convert_to_numpy=True)
    faiss.normalize_L2(query_embedding.astype('float32'))
    
    # Search more results to filter
    search_k = k * 3 if filter_type else k
    distances, indices = index.search(query_embedding.astype('float32'), search_k)
    
    # Prepare results
    results = []
    for i, idx in enumerate(indices[0]):
        if idx < len(metadata):
            result = metadata[idx].copy()
            # Convert distance to similarity score (cosine similarity)
            result['similarity'] = float(distances[0][i])
            
            # Filter by type if specified
            if filter_type is None or result.get('type') == filter_type:
                results.append(result)
            
            if len(results) >= k:
                break
    
    return results[:k]

def get_relevant_context(query, k=5, include_jd=False):
    """
    Get relevant context for a query as formatted string.
    
    Args:
        query: Search query
        k: Number of chunks to retrieve
        include_jd: Whether to include JD chunks in results
    """
    # Get resume chunks
    filter_type = None if include_jd else 'section'
    results = search_similar(query, k=k, filter_type=filter_type)
    
    context_parts = []
    seen_sections = set()
    
    for result in results:
        section = result['section']
        text = result['text']
        similarity = result.get('similarity', 0)
        
        # Add section header only once
        if section not in seen_sections:
            context_parts.append(f"\n--- {section} (relevance: {similarity:.2f}) ---")
            seen_sections.add(section)
        
        context_parts.append(text)
    
    return "\n\n".join(context_parts)

def compare_resume_to_jd():
    """
    Compare resume embeddings to job description.
    Returns similarity score and missing keywords.
    """
    global job_description_embedding, metadata, index
    
    if job_description_embedding is None:
        return None
    
    model = get_model()
    
    # Get all resume sections (not JD)
    resume_chunks = [m for m in metadata if m['type'] in ['section', 'overview']]
    
    if not resume_chunks:
        return None
    
    # Calculate similarity scores
    resume_texts = [chunk['text'] for chunk in resume_chunks]
    resume_embeddings = model.encode(resume_texts, convert_to_numpy=True)
    faiss.normalize_L2(resume_embeddings.astype('float32'))
    
    # Calculate cosine similarity with JD
    jd_emb_normalized = job_description_embedding.copy()
    jd_emb_normalized = jd_emb_normalized.reshape(1, -1)
    faiss.normalize_L2(jd_emb_normalized.astype('float32'))
    
    similarities = np.dot(resume_embeddings, jd_emb_normalized.T).flatten()
    
    # Overall match score
    overall_score = float(np.mean(similarities))
    
    # Find sections with low similarity (potential gaps)
    section_scores = {}
    for chunk, sim in zip(resume_chunks, similarities):
        section = chunk['section']
        if section not in section_scores:
            section_scores[section] = []
        section_scores[section].append(float(sim))
    
    # Average scores by section
    section_avg_scores = {
        section: np.mean(scores) 
        for section, scores in section_scores.items()
    }
    
    return {
        "overall_match": overall_score * 100,  # Convert to percentage
        "section_scores": section_avg_scores,
        "weak_sections": [s for s, score in section_avg_scores.items() if score < 0.5]
    }

def get_jd_keywords():
    """Extract potential keywords from job description."""
    jd_chunks = [m for m in metadata if m.get('type') == 'job_description']
    if not jd_chunks:
        return []
    
    jd_text = " ".join([chunk['text'] for chunk in jd_chunks])
    
    # Simple keyword extraction
    # Extract capitalized words and acronyms (likely important terms)
    words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b|\b[A-Z]{2,}\b', jd_text)
    
    # Also extract common technical terms
    tech_pattern = r'\b(?:Python|Java|JavaScript|React|AWS|Docker|Kubernetes|SQL|Node\.js|TypeScript|Go|Ruby|C\+\+|C#|Swift|Kotlin|Scala|MongoDB|PostgreSQL|Redis|Git|CI/CD|Agile|Scrum|REST|API|Machine Learning|AI|DevOps|Cloud|Linux|Azure|GCP)\b'
    tech_terms = re.findall(tech_pattern, jd_text, re.IGNORECASE)
    
    # Combine and deduplicate
    all_keywords = list(set(words + tech_terms))
    
    # Filter out common words
    stopwords = {'the', 'and', 'for', 'with', 'this', 'that', 'from', 'will', 'can', 'are', 'our', 'your'}
    keywords = [w for w in all_keywords if len(w) > 2 and w.lower() not in stopwords]
    
    return list(set(keywords))[:20]  # Top 20 unique keywords

# Test function
if __name__ == "__main__":
    sample_sections = {
        "Experience": "Senior Developer at Tech Corp. Led team of 5. Improved performance by 40%.",
        "Skills": "Python, JavaScript, React, AWS, Docker"
    }
    
    sample_combined = "Senior Developer with Python, JavaScript, React experience."
    sample_jd = "Looking for Senior Developer with Python, AWS, Kubernetes experience. Must have 5+ years."
    
    print("Building embeddings...")
    build_embeddings(sample_sections, sample_combined, sample_jd)
    
    print("\nTesting search...")
    results = search_similar("What programming languages?", k=3)
    for r in results:
        print(f"Section: {r['section']}, Similarity: {r['similarity']:.4f}")
    
    print("\nComparing to JD...")
    comparison = compare_resume_to_jd()
    if comparison:
        print(f"Overall match: {comparison['overall_match']:.1f}%")
        print(f"Weak sections: {comparison['weak_sections']}")
    
    print("\nExtracting JD keywords...")
    keywords = get_jd_keywords()
    print(f"Keywords: {keywords}")