"""
Multi-Modal Processing — Image understanding, OCR, document parsing.

Supports:
- Document photos (Aadhaar, PAN, receipts, bills)
- Handwritten text recognition
- Receipt/bill data extraction
- General image description via LLM vision
"""

import os
import json
import base64
import logging
import tempfile
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MultiModalProcessor:
    """Process images: OCR, document detection, receipt parsing."""

    # Document types we can recognize
    DOCUMENT_TYPES = {
        "aadhaar": {"fields": ["name", "dob", "gender", "aadhaar_number", "address"]},
        "pan": {"fields": ["name", "pan_number", "father_name", "dob"]},
        "passport": {"fields": ["name", "passport_number", "nationality", "dob", "expiry"]},
        "driving_license": {"fields": ["name", "dl_number", "validity", "vehicle_class"]},
        "voter_id": {"fields": ["name", "epic_number", "assembly_constituency"]},
        "electricity_bill": {"fields": ["consumer_number", "amount", "due_date", "units"]},
        "water_bill": {"fields": ["consumer_number", "amount", "due_date"]},
        "bank_passbook": {"fields": ["account_number", "ifsc", "name", "balance"]},
        "marksheet": {"fields": ["name", "board", "year", "percentage", "subjects"]},
        "receipt": {"fields": ["items", "total", "date", "vendor"]},
    }

    def __init__(self):
        self._tesseract_available = None

    def _check_tesseract(self) -> bool:
        """Check if Tesseract OCR is installed."""
        if self._tesseract_available is not None:
            return self._tesseract_available
        try:
            import subprocess
            result = subprocess.run(["tesseract", "--version"], capture_output=True, timeout=5)
            self._tesseract_available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._tesseract_available = False
        return self._tesseract_available

    def process_image(self, image_path: str, task: str = "auto") -> Dict[str, Any]:
        """
        Process an image file.

        Args:
            image_path: Path to the image file
            task: Processing task - 'auto', 'ocr', 'document', 'receipt', 'describe'

        Returns:
            Dict with extracted information
        """
        if not os.path.exists(image_path):
            return {"error": f"File not found: {image_path}"}

        file_size = os.path.getsize(image_path)
        if file_size > 20 * 1024 * 1024:  # 20MB limit
            return {"error": "Image too large. Maximum size is 20MB."}

        ext = os.path.splitext(image_path)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".gif"):
            return {"error": f"Unsupported image format: {ext}. Use JPG, PNG, or WebP."}

        # Try OCR first
        ocr_text = self._ocr_extract(image_path)

        if task == "ocr" or (task == "auto" and ocr_text):
            result = {
                "type": "ocr",
                "raw_text": ocr_text,
                "image_path": image_path,
                "file_size": file_size,
            }

            # Try to classify document type
            if task in ("auto", "document"):
                doc_info = self._classify_document(ocr_text)
                if doc_info:
                    result["document_type"] = doc_info["type"]
                    result["extracted_fields"] = doc_info["fields"]
                    result["type"] = "document"

            # Try receipt parsing
            if task in ("auto", "receipt"):
                receipt_info = self._parse_receipt(ocr_text)
                if receipt_info:
                    result["receipt_data"] = receipt_info
                    result["type"] = "receipt"

            return result

        # Fallback: describe image via base64
        return {
            "type": "image",
            "image_path": image_path,
            "file_size": file_size,
            "message": "Image received. OCR text extraction requires Tesseract. Install: brew install tesseract",
            "suggestion": "Use the 'describe' task with an LLM that supports vision for image understanding.",
        }

    def process_image_bytes(self, image_bytes: bytes, filename: str = "image.jpg", task: str = "auto") -> Dict[str, Any]:
        """Process image from bytes (e.g., from upload)."""
        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1] or ".jpg", delete=False) as f:
            f.write(image_bytes)
            temp_path = f.name

        try:
            return self.process_image(temp_path, task=task)
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    def process_base64(self, b64_data: str, task: str = "auto") -> Dict[str, Any]:
        """Process a base64-encoded image."""
        try:
            image_bytes = base64.b64decode(b64_data)
            return self.process_image_bytes(image_bytes, task=task)
        except Exception as e:
            return {"error": f"Invalid base64 data: {e}"}

    def _ocr_extract(self, image_path: str) -> str:
        """Extract text from image using Tesseract OCR."""
        if not self._check_tesseract():
            return ""

        try:
            import subprocess
            result = subprocess.run(
                ["tesseract", image_path, "stdout", "-l", "eng+hin"],
                capture_output=True, text=True, timeout=30
            )
            return result.stdout.strip()
        except Exception as e:
            logger.warning(f"OCR failed: {e}")
            return ""

    def _classify_document(self, text: str) -> Optional[Dict[str, Any]]:
        """Classify document type from OCR text."""
        text_lower = text.lower()

        # Aadhaar detection
        if any(kw in text_lower for kw in ["aadhaar", "unique identification", "uidai", "आधार"]):
            return {
                "type": "aadhaar",
                "fields": self._extract_fields(text, self.DOCUMENT_TYPES["aadhaar"]["fields"]),
            }

        # PAN detection
        if any(kw in text_lower for kw in ["permanent account", "income tax", "pan card"]):
            return {
                "type": "pan",
                "fields": self._extract_fields(text, self.DOCUMENT_TYPES["pan"]["fields"]),
            }

        # Passport detection
        if any(kw in text_lower for kw in ["passport", "republic of india", "passport number"]):
            return {
                "type": "passport",
                "fields": self._extract_fields(text, self.DOCUMENT_TYPES["passport"]["fields"]),
            }

        # Electricity bill
        if any(kw in text_lower for kw in ["electricity", "electric", "bill", "consumption", "units"]):
            return {
                "type": "electricity_bill",
                "fields": self._extract_fields(text, self.DOCUMENT_TYPES["electricity_bill"]["fields"]),
            }

        # Marksheet
        if any(kw in text_lower for kw in ["marksheet", "mark sheet", "percentage", "result", "examination"]):
            return {
                "type": "marksheet",
                "fields": self._extract_fields(text, self.DOCUMENT_TYPES["marksheet"]["fields"]),
            }

        # Generic receipt
        if any(kw in text_lower for kw in ["total", "amount", "receipt", "invoice", "bill"]):
            return {
                "type": "receipt",
                "fields": self._extract_fields(text, self.DOCUMENT_TYPES["receipt"]["fields"]),
            }

        return None

    def _extract_fields(self, text: str, field_names: list) -> Dict[str, str]:
        """Best-effort field extraction from OCR text."""
        import re
        fields = {}

        # Aadhaar number: 12 digits
        aadhaar_match = re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', text)
        if aadhaar_match and "aadhaar_number" in field_names:
            fields["aadhaar_number"] = aadhaar_match.group()

        # PAN: 5 letters + 4 digits + 1 letter
        pan_match = re.search(r'\b[A-Z]{5}\d{4}[A-Z]\b', text, re.IGNORECASE)
        if pan_match and "pan_number" in field_names:
            fields["pan_number"] = pan_match.group().upper()

        # Date patterns (DD/MM/YYYY or DD-MM-YYYY)
        dates = re.findall(r'\b(\d{2}[/\-]\d{2}[/\-]\d{4})\b', text)
        if dates and "dob" in field_names:
            fields["dob"] = dates[0]
        if dates and len(dates) > 1 and "expiry" in field_names:
            fields["expiry"] = dates[-1]

        # Amounts
        amounts = re.findall(r'(?:Rs\.?|INR|₹)\s*[\d,]+\.?\d*', text)
        if amounts and "amount" in field_names:
            fields["amount"] = amounts[0]

        # Email
        email_match = re.search(r'\b[\w.-]+@[\w.-]+\.\w+\b', text)
        if email_match:
            fields["email"] = email_match.group()

        # Phone
        phone_match = re.search(r'\b[6-9]\d{9}\b', text)
        if phone_match:
            fields["phone"] = phone_match.group()

        # Name (first line after document type indicators, heuristic)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        for i, line in enumerate(lines):
            if any(kw in line.lower() for kw in ["name", "naam", "नाम"]):
                if i + 1 < len(lines):
                    name_line = lines[i + 1]
                    if len(name_line.split()) <= 4 and name_line.isupper():
                        fields["name"] = name_line.title()
                break

        return fields

    def _parse_receipt(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse receipt/bill data from OCR text."""
        import re

        # Look for total amount
        total_match = re.search(
            r'(?:total|grand total|amount due|balance due|to pay)[\s:]*[₹Rs.]*\s*([\d,]+\.?\d*)',
            text, re.IGNORECASE
        )
        if not total_match:
            return None

        receipt = {
            "total": total_match.group(1),
            "currency": "INR",
        }

        # Extract date
        dates = re.findall(r'\b(\d{2}[/\-]\d{1,2}[/\-]\d{4})\b', text)
        if dates:
            receipt["date"] = dates[0]

        # Extract line items (lines with price patterns)
        items = []
        lines = text.split('\n')
        for line in lines:
            item_match = re.match(r'(.+?)\s+[₹Rs.]*\s*([\d,]+\.?\d*)$', line.strip())
            if item_match:
                item_name = item_match.group(1).strip()
                if len(item_name) > 2 and not any(kw in item_name.lower() for kw in ["total", "tax", "vat", "gst"]):
                    items.append({
                        "name": item_name,
                        "price": item_match.group(2),
                    })

        if items:
            receipt["items"] = items

        # GST
        gst_match = re.search(r'(?:gst|tax|vat)[\s:]*[₹Rs.]*\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
        if gst_match:
            receipt["tax"] = gst_match.group(1)

        return receipt


# Singleton
multimodal = MultiModalProcessor()
