"""
Text Chunker for RAG ingestion.
Provides semantic-aware chunking with sentence boundaries, paragraph awareness,
and recursive splitting for oversized chunks.
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ChunkConfig:
    """Configuration for text chunking."""
    max_chunk_size: int = 500       # Max characters per chunk
    min_chunk_size: int = 100       # Min characters (avoid tiny chunks)
    overlap: int = 50               # Overlap between adjacent chunks
    respect_sentences: bool = True  # Try to split at sentence boundaries
    respect_paragraphs: bool = True # Prefer splitting at paragraph boundaries


# Sentence-ending patterns (handles periods, exclamation, question marks, and Indic dandas)
SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?।])\s+')

# Paragraph split pattern (double newline)
PARAGRAPH_SPLIT_RE = re.compile(r'\n\s*\n')


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences, respecting common sentence boundaries."""
    sentences = SENTENCE_SPLIT_RE.split(text.strip())
    return [s.strip() for s in sentences if s.strip()]


def split_into_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs."""
    paragraphs = PARAGRAPH_SPLIT_RE.split(text.strip())
    return [p.strip() for p in paragraphs if p.strip()]


def chunk_text(text: str, config: Optional[ChunkConfig] = None) -> List[str]:
    """
    Split text into chunks with semantic awareness.

    Strategy:
    1. Split by paragraphs first (if configured)
    2. For each paragraph, if it exceeds max_chunk_size:
       a. Split by sentences
       b. Group sentences into chunks respecting max_chunk_size
       c. Add overlap between chunks
    3. If a single sentence exceeds max_chunk_size, split by words (recursive)

    Returns a list of chunk strings.
    """
    if config is None:
        config = ChunkConfig()

    if not text or not text.strip():
        return []

    text = text.strip()

    # If the entire text fits in one chunk, return it
    if len(text) <= config.max_chunk_size:
        return [text]

    chunks: List[str] = []

    if config.respect_paragraphs:
        # Strategy: Paragraph → Sentence → Word (recursive)
        paragraphs = split_into_paragraphs(text)
        for para in paragraphs:
            if len(para) <= config.max_chunk_size:
                if len(para) >= config.min_chunk_size:
                    chunks.append(para)
            else:
                para_chunks = _chunk_paragraph(para, config)
                chunks.extend(para_chunks)
    else:
        # Strategy: Sentence → Word (recursive)
        chunks = _chunk_paragraph(text, config)

    # Apply overlap
    if config.overlap > 0 and len(chunks) > 1:
        chunks = _apply_overlap(chunks, config.overlap)

    return chunks


def _chunk_paragraph(text: str, config: ChunkConfig) -> List[str]:
    """Chunk a single paragraph using sentence boundaries."""
    if len(text) <= config.max_chunk_size:
        return [text] if len(text) >= config.min_chunk_size else []

    sentences = split_into_sentences(text)
    chunks: List[str] = []
    current_chunk: List[str] = []
    current_size = 0

    for sentence in sentences:
        sentence_size = len(sentence)

        # If a single sentence is too large, recursively split by words
        if sentence_size > config.max_chunk_size:
            # Flush current chunk
            if current_chunk:
                chunk_text = " ".join(current_chunk)
                if len(chunk_text) >= config.min_chunk_size:
                    chunks.append(chunk_text)
                current_chunk = []
                current_size = 0

            # Recursively split the oversized sentence
            word_chunks = _chunk_by_words(sentence, config)
            chunks.extend(word_chunks)
            continue

        # Check if adding this sentence would exceed the limit
        added_size = sentence_size + (1 if current_chunk else 0)  # +1 for space
        if current_size + added_size > config.max_chunk_size:
            # Flush current chunk
            if current_chunk:
                chunk_text = " ".join(current_chunk)
                if len(chunk_text) >= config.min_chunk_size:
                    chunks.append(chunk_text)
                current_chunk = []
                current_size = 0

        current_chunk.append(sentence)
        current_size += added_size

    # Flush remaining
    if current_chunk:
        chunk_text = " ".join(current_chunk)
        if len(chunk_text) >= config.min_chunk_size:
            chunks.append(chunk_text)

    return chunks


def _chunk_by_words(text: str, config: ChunkConfig) -> List[str]:
    """Last resort: split by words when a sentence is too large."""
    words = text.split()
    chunks: List[str] = []
    current_chunk: List[str] = []
    current_size = 0

    for word in words:
        word_size = len(word)
        added_size = word_size + (1 if current_chunk else 0)

        if current_size + added_size > config.max_chunk_size:
            if current_chunk:
                chunk_text = " ".join(current_chunk)
                if len(chunk_text) >= config.min_chunk_size:
                    chunks.append(chunk_text)
                current_chunk = []
                current_size = 0

        current_chunk.append(word)
        current_size += added_size

    if current_chunk:
        chunk_text = " ".join(current_chunk)
        if len(chunk_text) >= config.min_chunk_size:
            chunks.append(chunk_text)

    return chunks


def _apply_overlap(chunks: List[str], overlap: int) -> List[str]:
    """Add overlap between adjacent chunks by appending tail of previous to head of next."""
    if len(chunks) <= 1 or overlap <= 0:
        return chunks

    result = [chunks[0]]
    for i in range(1, len(chunks)):
        prev = chunks[i - 1]
        current = chunks[i]

        # Take last 'overlap' characters from previous chunk
        overlap_text = prev[-overlap:].strip()
        # Find a clean break point (word boundary)
        space_idx = overlap_text.find(" ")
        if space_idx > 0:
            overlap_text = overlap_text[space_idx + 1:]

        if overlap_text and not current.startswith(overlap_text):
            result.append(f"{overlap_text} {current}")
        else:
            result.append(current)

    return result


def chunk_document(content: str, source: str = "unknown", config: Optional[ChunkConfig] = None) -> List[Dict]:
    """
    Chunk a document and return structured metadata for each chunk.

    Returns:
        [{"content": "...", "metadata": {"source": "...", "chunk_index": 0, "chunk_total": N}}]
    """
    chunks = chunk_text(content, config)
    total = len(chunks)

    return [
        {
            "content": chunk,
            "metadata": {
                "source": source,
                "chunk_index": i,
                "chunk_total": total,
                "char_count": len(chunk),
            },
        }
        for i, chunk in enumerate(chunks)
    ]
