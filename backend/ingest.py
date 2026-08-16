from rag_engine import RAGEngine
import os
import re

def clean_text(text: str) -> str:
    """
    Cleans and normalizes text.
    1. Removes excessive whitespace.
    2. Normalizes line breaks.
    """
    # Create simple cleaning pipeline
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces/newlines with single space
    text = text.strip()
    return text

def recursive_chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Splits text into chunks with overlap, respecting sentence boundaries where possible.
    For now, we implement a simple sliding window approach since we don't have LangChain.
    """
    words = text.split(' ')
    chunks = []
    
    current_chunk = []
    current_length = 0
    
    i = 0
    while i < len(words):
        word = words[i]
        word_len = len(word) + 1 # +1 for space
        
        if current_length + word_len > chunk_size and current_chunk:
            # Chunk is full, finalize it
            chunks.append(" ".join(current_chunk))
            
            # Create overlap for next chunk
            overlap_words = []
            overlap_len = 0
            # Backtrack to find overlap
            back_idx = len(current_chunk) - 1
            while back_idx >= 0 and overlap_len < overlap:
                 w = current_chunk[back_idx]
                 overlap_words.insert(0, w)
                 overlap_len += len(w) + 1
                 back_idx -= 1
            
            current_chunk = overlap_words[:]
            current_length = overlap_len
            
        current_chunk.append(word)
        current_length += word_len
        i += 1
        
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks

def ingest_blueprint():
    print("Initializing RAG Engine...")
    engine = RAGEngine()
    
    file_path = "docs/BLUEPRINT.md"
    if not os.path.exists(file_path):
        if os.path.exists(f"../{file_path}"):
            file_path = f"../{file_path}"
        else:
            raise FileNotFoundError(f"Could not find {file_path}")
            
    print(f"Reading {file_path}...")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Process by sections first (double newline) to respect document structure better
    sections = content.split("\n\n")
    all_chunks = []
    
    for section in sections:
        cleaned_section = clean_text(section)
        if not cleaned_section:
            continue
            
        # If section is small, keep as is. If large, chunk it.
        if len(cleaned_section) > 600:
            section_chunks = recursive_chunk_text(cleaned_section, chunk_size=500, overlap=50)
            all_chunks.extend(section_chunks)
        else:
            all_chunks.append(cleaned_section)
    
    documents = []
    for chunk in all_chunks:
        # Deduplication check (simple)
        if len(chunk) > 50:
            # Add basic metadata extraction potential here
            meta = {"source": "BLUEPRINT.md", "type": "documentation"}
            documents.append({
                "content": chunk,
                "metadata": meta
            })
            
    print(f"Ingesting {len(documents)} cleaned chunks...")
    # Clean existing collection before re-ingesting to avoid duplicates
    # Note: In a real system we'd check for existing IDs or use a delete logic
    # For now, we are appending, which might create dupes if run multiple times without clearing
    # But RAGEngine generates random UUIDs.
    # ideally we should have engine.clear()
    
    engine.ingest_documents(documents)
    print("Ingestion complete.")

if __name__ == "__main__":
    ingest_blueprint()
