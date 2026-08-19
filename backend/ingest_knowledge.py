#!/usr/bin/env python3
"""
Ingest Knowledge Base into ChromaDB for Zenix AI.
Loads government schemes, banking, legal, and health knowledge.
"""

import os
import sys
import re
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag_engine import RAGEngine
from pipeline.text_chunker import chunk_document, ChunkConfig


def clean_text(text: str) -> str:
    """Clean and normalize text for ingestion."""
    # Remove excessive whitespace but preserve paragraph structure
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    text = text.strip()
    return text


def read_knowledge_file(file_path: str) -> str:
    """Read a knowledge base file and return cleaned text."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return clean_text(content)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""


def ingest_knowledge_base():
    """Ingest all knowledge base files into ChromaDB."""
    
    knowledge_dir = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge")
    
    if not os.path.exists(knowledge_dir):
        print(f"Knowledge directory not found: {knowledge_dir}")
        return
    
    # Knowledge base files to ingest
    knowledge_files = [
        "government_schemes.md",
        "banking_finance.md",
        "legal_knowledge.md",
        "health_wellness.md",
        "india_stack_dpi.md",
        "education.md",
        "agriculture.md",
        "transport.md",
        "employment.md",
        "regional.md",
        "states_india.md",
        "legal_expanded.md",
        "financial_literacy.md",
        "recipes_food.md",
        "entertainment.md",
        "education_expanded.md",
        "shopping.md",
        "banking_comparison.md",
        "travel_india.md",
        "healthcare_india.md",
        "property_rental.md",
        "job_preparation.md",
        "parenting_family.md",
        "legal_templates.md",
        "festival_shopping.md",
    ]
    
    # Chunking configuration
    config = ChunkConfig(
        max_chunk_size=500,  # Smaller chunks for better retrieval
        min_chunk_size=100,
        overlap=75,  # More overlap for context preservation
        respect_sentences=True,
        respect_paragraphs=True,
    )
    
    print("=" * 60)
    print("ZENIX AI - Knowledge Base Ingestion")
    print("=" * 60)
    
    # Initialize RAG engine
    print("\nInitializing RAG Engine...")
    engine = RAGEngine()
    
    total_chunks = 0
    files_processed = 0
    
    for filename in knowledge_files:
        file_path = os.path.join(knowledge_dir, filename)
        
        if not os.path.exists(file_path):
            print(f"\n[SKIP] File not found: {filename}")
            continue
        
        print(f"\n{'─' * 60}")
        print(f"Processing: {filename}")
        print(f"{'─' * 60}")
        
        # Read and clean content
        content = read_knowledge_file(file_path)
        if not content:
            print(f"[SKIP] No content in {filename}")
            continue
        
        print(f"  Content length: {len(content)} characters")
        
        # Chunk the content
        doc_chunks = chunk_document(
            content,
            source=filename,
            config=config,
        )
        
        # Filter out very small chunks
        doc_chunks = [c for c in doc_chunks if len(c["content"]) > 80]
        
        if not doc_chunks:
            print(f"[SKIP] No chunks generated from {filename}")
            continue
        
        print(f"  Generated chunks: {len(doc_chunks)}")
        
        # Add metadata for better retrieval
        for i, chunk in enumerate(doc_chunks):
            chunk["metadata"]["domain"] = _get_domain(filename)
            chunk["metadata"]["chunk_size"] = len(chunk["content"])
        
        # Ingest into ChromaDB
        try:
            engine.ingest_documents(doc_chunks)
            total_chunks += len(doc_chunks)
            files_processed += 1
            print(f"  [OK] Ingested {len(doc_chunks)} chunks")
        except Exception as e:
            print(f"  [ERROR] Failed to ingest {filename}: {e}")
    
    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    print(f"  Files processed: {files_processed}/{len(knowledge_files)}")
    print(f"  Total chunks ingested: {total_chunks}")
    print("=" * 60)
    
    # Verify ingestion
    _verify_ingestion(engine)


def _get_domain(filename: str) -> str:
    """Extract domain from filename."""
    if "government" in filename.lower() or "india_stack" in filename.lower():
        return "government_schemes"
    elif "banking" in filename.lower() or "finance" in filename.lower():
        return "banking_finance"
    elif "legal" in filename.lower():
        return "legal"
    elif "health" in filename.lower():
        return "health"
    elif "education" in filename.lower():
        return "education"
    elif "agriculture" in filename.lower():
        return "agriculture"
    elif "transport" in filename.lower():
        return "transport"
    elif "employment" in filename.lower():
        return "employment"
    elif "regional" in filename.lower():
        return "regional"
    elif "states" in filename.lower():
        return "states_specific"
    elif "financial_literacy" in filename.lower():
        return "financial_literacy"
    elif "legal_expanded" in filename.lower():
        return "legal_expanded"
    elif "recipe" in filename.lower() or "food" in filename.lower():
        return "food_recipes"
    elif "entertainment" in filename.lower():
        return "entertainment"
    elif "education_expanded" in filename.lower():
        return "education_expanded"
    elif "shopping" in filename.lower():
        return "shopping"
    elif "banking" in filename.lower():
        return "banking_comparison"
    elif "travel" in filename.lower():
        return "travel"
    elif "healthcare" in filename.lower():
        return "healthcare"
    elif "property" in filename.lower() or "rental" in filename.lower():
        return "property"
    elif "job" in filename.lower() or "preparation" in filename.lower():
        return "job_preparation"
    elif "parenting" in filename.lower() or "family" in filename.lower():
        return "parenting"
    elif "legal_templates" in filename.lower():
        return "legal_templates"
    elif "festival_shopping" in filename.lower():
        return "festival_shopping"
    return "general"


def _verify_ingestion(engine: RAGEngine):
    """Verify the ingestion by running test queries."""
    print("\n" + "=" * 60)
    print("VERIFICATION - Running Test Queries")
    print("=" * 60)
    
    test_queries = [
        "What is PM-KISAN scheme?",
        "How to link Aadhaar to bank account?",
        "What are the grounds for divorce in India?",
        "What is Ayushman Bharat health insurance?",
        "How to file RTI application?",
        "What is UPI and how does it work?",
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        results = engine.search(query, k=2)
        
        if results:
            print(f"  Found {len(results)} results:")
            for i, r in enumerate(results):
                score = r.get('cross_score', 0)
                content_preview = r['content'][:100].replace('\n', ' ')
                print(f"    {i+1}. [Score: {score:.2f}] {content_preview}...")
        else:
            print("  No results found")
    
    print("\n" + "=" * 60)
    print("Verification complete!")
    print("=" * 60)


if __name__ == "__main__":
    ingest_knowledge_base()
