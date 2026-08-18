from rag_engine import RAGEngine
from pipeline.text_chunker import chunk_document, ChunkConfig
from pipeline.document_parser import parse_document
import os
import re


def clean_text(text: str) -> str:
    """
    Cleans and normalizes text.
    1. Removes excessive whitespace.
    2. Normalizes line breaks.
    """
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text


def ingest_file(file_path: str, source_name: str = None, chunk_config: ChunkConfig = None):
    """
    Generic ingestion: parse any supported file, chunk it, and ingest into RAG engine.

    Args:
        file_path: Path to the file to ingest.
        source_name: Optional label for the source (defaults to filename).
        chunk_config: Optional chunking configuration.
    """
    if not os.path.exists(file_path):
        if os.path.exists(f"../{file_path}"):
            file_path = f"../{file_path}"
        else:
            raise FileNotFoundError(f"Could not find {file_path}")

    source_name = source_name or os.path.basename(file_path)
    config = chunk_config or ChunkConfig(max_chunk_size=500, overlap=50)

    print(f"Parsing {file_path}...")
    content = parse_document(file_path)

    if not content:
        print(f"Warning: No content extracted from {file_path}")
        return

    content = clean_text(content)

    print(f"Chunking {source_name} ({len(content)} chars)...")
    doc_chunks = chunk_document(content, source=source_name, config=config)

    if not doc_chunks:
        print(f"Warning: No chunks generated from {file_path}")
        return

    # Filter out very small chunks
    doc_chunks = [c for c in doc_chunks if len(c["content"]) > 50]

    print(f"Ingesting {len(doc_chunks)} chunks from {source_name}...")
    engine = RAGEngine()
    engine.ingest_documents(doc_chunks)
    print(f"Done: {source_name}")


def ingest_blueprint():
    """Ingest the BLUEPRINT.md file with default settings."""
    print("Initializing RAG Engine...")
    config = ChunkConfig(max_chunk_size=500, overlap=50)

    file_path = "docs/BLUEPRINT.md"
    ingest_file(file_path, source_name="BLUEPRINT.md", chunk_config=config)

    print("\nIngestion complete.")


def ingest_directory(dir_path: str, extensions: list = None):
    """
    Ingest all supported files in a directory.

    Args:
        dir_path: Path to the directory.
        extensions: List of file extensions to include (default: .pdf, .docx, .txt, .md)
    """
    if extensions is None:
        extensions = [".pdf", ".docx", ".doc", ".txt", ".md"]

    if not os.path.exists(dir_path):
        raise FileNotFoundError(f"Directory not found: {dir_path}")

    files_ingested = 0
    for root, dirs, files in os.walk(dir_path):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in extensions:
                fpath = os.path.join(root, fname)
                try:
                    ingest_file(fpath, source_name=fname)
                    files_ingested += 1
                except Exception as e:
                    print(f"Error ingesting {fpath}: {e}")

    print(f"\nTotal files ingested: {files_ingested}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        target = sys.argv[1]
        if os.path.isdir(target):
            ingest_directory(target)
        else:
            ingest_file(target)
    else:
        ingest_blueprint()
