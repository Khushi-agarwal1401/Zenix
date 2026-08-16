import fitz  # PyMuPDF
import docx
from pathlib import Path

def parse_pdf(file_path: str) -> str:
    """Extracts text from a PDF document using PyMuPDF."""
    text = ""
    try:
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        print(f"Error parsing PDF {file_path}: {e}")
        return ""

def parse_docx(file_path: str) -> str:
    """Extracts text from a Word document using python-docx."""
    text = ""
    try:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    except Exception as e:
        print(f"Error parsing DOCX {file_path}: {e}")
        return ""

def parse_document(file_path: str) -> str:
    """Route to correct parser based on file extension."""
    path = Path(file_path)
    if path.suffix.lower() == '.pdf':
        return parse_pdf(file_path)
    elif path.suffix.lower() in ['.docx', '.doc']:
        return parse_docx(file_path)
    else:
        # Fallback to plain text read
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ""
