"""
Structured logging for Zenix AI.
Replaces print() with proper logging levels, structured output, and file rotation.
Includes PII detection and redaction for privacy compliance.
"""

import os
import sys
import json
import logging
import logging.handlers
import re
from datetime import datetime
from typing import Any, Dict, Optional, List, Set


# ── PII Detection & Redaction ───────────────────────────────────────────────────

class PIIRedactor:
    """
    Detects and redacts Personally Identifiable Information (PII) from log messages.
    
    Detects:
    - Aadhaar numbers (12 digits, Verhoeff checksum validated)
    - PAN numbers (10 chars: 5 letters, 4 digits, 1 letter)
    - Phone numbers (Indian: 10 digits, with/without +91)
    - Email addresses
    - Credit/Debit card numbers (Luhn algorithm)
    - UPI IDs (user@bank)
    - Bank account numbers (9-18 digits)
    - IFSC codes (11 chars)
    - Passport numbers (Indian format)
    - Driving license numbers
    - Vehicle registration numbers
    - IP addresses
    """

    PATTERNS = {
        "aadhaar": re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),
        "pan": re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b'),
        "phone": re.compile(r'\b(?:\+91[\s-]?)?[6-9]\d{9}\b'),
        "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        "upi": re.compile(r'\b[A-Za-z0-9._-]+@[A-Za-z]{3,}\b'),
        "ifsc": re.compile(r'\b[A-Z]{4}0[A-Z0-9]{6}\b'),
        "passport": re.compile(r'\b[A-PR-WYa-pr-wy][1-9]\d{6}\b'),
        "dl": re.compile(r'\b[A-Z]{2}\d{2}[\s-]?\d{11}\b'),
        "vehicle": re.compile(r'\b[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}\b'),
        "ipv4": re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
        "ipv6": re.compile(r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'),
        "credit_card": re.compile(r'\b(?:\d{4}[\s-]?){3}\d{4}\b'),
        "bank_account": re.compile(r'\b\d{9,18}\b'),
    }

    WHITELIST = {
        "aadhaar": set(),
        "pan": set(),
        "phone": set(),
    }

    MASK_CHAR = "█"
    PARTIAL_MASK = True

    @classmethod
    def _verhoeff_check(cls, number: str) -> bool:
        """Validate Aadhaar using Verhoeff algorithm."""
        d = [
            [0,1,2,3,4,5,6,7,8,9],
            [1,2,3,4,0,6,7,8,9,5],
            [2,3,4,0,1,7,8,9,5,6],
            [3,4,0,1,2,8,9,5,6,7],
            [4,0,1,2,3,9,5,6,7,8],
            [5,9,8,7,6,0,4,3,2,1],
            [6,5,9,8,7,1,0,4,3,2],
            [7,6,5,9,8,2,1,0,4,3],
            [8,7,6,5,9,3,2,1,0,4],
            [9,8,7,6,5,4,3,2,1,0]
        ]
        p = [
            [0,1,2,3,4,5,6,7,8,9],
            [1,5,7,6,2,8,3,0,9,4],
            [5,8,0,3,7,9,6,1,4,2],
            [8,9,1,6,0,4,3,5,2,7],
            [9,4,5,3,1,2,6,8,7,0],
            [4,2,8,6,5,7,3,9,0,1],
            [2,7,9,3,8,0,6,4,1,5],
            [7,0,4,6,9,1,3,2,5,8]
        ]
        c = 0
        for i, ch in enumerate(reversed(number)):
            c = d[c][p[i % 8][int(ch)]]
        return c == 0

    @classmethod
    def _luhn_check(cls, number: str) -> bool:
        """Validate credit card using Luhn algorithm."""
        digits = [int(d) for d in number if d.isdigit()]
        if len(digits) < 13:
            return False
        checksum = 0
        for i, d in enumerate(reversed(digits)):
            if i % 2 == 1:
                d *= 2
                if d > 9:
                    d -= 9
            checksum += d
        return checksum % 10 == 0

    @classmethod
    def _mask_value(cls, value: str, pii_type: str) -> str:
        """Mask a detected PII value."""
        if cls.PARTIAL_MASK and len(value) > 4:
            return value[:2] + cls.MASK_CHAR * (len(value) - 4) + value[-2:]
        else:
            return cls.MASK_CHAR * len(value)

    @classmethod
    def redact(cls, text: str, pii_types: List[str] = None) -> str:
        """Redact PII from text."""
        if not text:
            return text

        if pii_types is None:
            pii_types = list(cls.PATTERNS.keys())

        result = text
        for pii_type in pii_types:
            if pii_type not in cls.PATTERNS:
                continue

            pattern = cls.PATTERNS[pii_type]
            matches = list(pattern.finditer(result))

            for match in reversed(matches):
                value = match.group()
                start, end = match.span()

                if value in cls.WHITELIST.get(pii_type, set()):
                    continue

                if pii_type == "aadhaar":
                    clean = value.replace(" ", "").replace("-", "")
                    if len(clean) == 12 and clean.isdigit():
                        if not cls._verhoeff_check(clean):
                            continue
                elif pii_type == "credit_card":
                    clean = value.replace(" ", "").replace("-", "")
                    if not cls._luhn_check(clean):
                        continue

                masked = cls._mask_value(value, pii_type)
                result = result[:start] + masked + result[end:]

        return result

    @classmethod
    def detect(cls, text: str) -> Dict[str, List[str]]:
        """Detect PII in text without redacting."""
        detected = {}
        for pii_type, pattern in cls.PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                validated = []
                for value in matches:
                    if pii_type == "aadhaar":
                        clean = value.replace(" ", "").replace("-", "")
                        if len(clean) == 12 and clean.isdigit() and cls._verhoeff_check(clean):
                            validated.append(value)
                    elif pii_type == "credit_card":
                        clean = value.replace(" ", "").replace("-", "")
                        if cls._luhn_check(clean):
                            validated.append(value)
                    elif pii_type == "pan" and re.match(r'^[A-Z]{5}\d{4}[A-Z]$', value):
                        validated.append(value)
                    elif pii_type == "phone":
                        clean = value.replace("+91", "").replace(" ", "").replace("-", "")
                        if len(clean) == 10 and clean.isdigit() and clean[0] in "6789":
                            validated.append(value)
                    else:
                        validated.append(value)

                if validated:
                    detected[pii_type] = validated

        return detected


class PIIFilter(logging.Filter):
    """Logging filter that redacts PII from log records."""

    def __init__(self, pii_types: List[str] = None):
        super().__init__()
        self.pii_types = pii_types

    def filter(self, record: logging.LogRecord) -> bool:
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = PIIRedactor.redact(record.msg, self.pii_types)

        if record.args:
            new_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    new_args.append(PIIRedactor.redact(arg, self.pii_types))
                else:
                    new_args.append(arg)
            record.args = tuple(new_args)

        if hasattr(record, 'extra_data') and isinstance(record.extra_data, dict):
            for key, value in record.extra_data.items():
                if isinstance(value, str):
                    record.extra_data[key] = PIIRedactor.redact(value, self.pii_types)

        return True


# ── Structured Formatter (Updated with PII Redaction) ───────────────────────────

class StructuredFormatter(logging.Formatter):
    """JSON-structured log formatter for production use with PII redaction."""

    def __init__(self, pii_types: List[str] = None):
        super().__init__()
        self.pii_types = pii_types

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if self.pii_types is not None:
            message = PIIRedactor.redact(message, self.pii_types)

        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": message,
        }

        if hasattr(record, "extra_data"):
            extra = record.extra_data
            if isinstance(extra, dict):
                redacted_extra = {}
                for k, v in extra.items():
                    if isinstance(v, str) and self.pii_types:
                        redacted_extra[k] = PIIRedactor.redact(v, self.pii_types)
                    else:
                        redacted_extra[k] = v
                log_entry["data"] = redacted_extra

        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


class ReadableFormatter(logging.Formatter):
    """Human-readable formatter for development use with PII redaction."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def __init__(self, pii_types: List[str] = None):
        super().__init__()
        self.pii_types = pii_types

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if self.pii_types is not None:
            message = PIIRedactor.redact(message, self.pii_types)

        color = self.COLORS.get(record.levelname, "")
        timestamp = datetime.now().strftime("%H:%M:%S")
        name = record.name.split(".")[-1]

        formatted = f"{color}{timestamp} [{record.levelname:>7}] {name}: {message}{self.RESET}"

        if record.exc_info and record.exc_info[0]:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


# Default PII types to redact (all by default)
DEFAULT_PII_TYPES = [
    "aadhaar", "pan", "phone", "email", "upi", "ifsc",
    "passport", "dl", "vehicle", "ipv4", "ipv6",
    "credit_card", "bank_account"
]


def setup_logging(
    level: str = "INFO",
    log_dir: str = None,
    json_output: bool = False,
    pii_types: List[str] = None,
    redact_pii: bool = True,
) -> logging.Logger:
    """
    Set up structured logging for the Zenix backend.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_dir: Directory for log files. None = console only.
        json_output: If True, use JSON format. If False, use colored readable format.
        pii_types: List of PII types to redact. None = all default types.
        redact_pii: Whether to enable PII redaction (default: True).

    Returns:
        The root logger for the application.
    """
    if pii_types is None:
        pii_types = DEFAULT_PII_TYPES

    root_logger = logging.getLogger("zenix")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Add PII filter if redaction enabled
    if redact_pii:
        pii_filter = PIIFilter(pii_types)
        root_logger.addFilter(pii_filter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if json_output:
        console_handler.setFormatter(StructuredFormatter(pii_types if redact_pii else None))
    else:
        console_handler.setFormatter(ReadableFormatter(pii_types if redact_pii else None))
    root_logger.addHandler(console_handler)

    # File handler (if log_dir specified)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, "zenix.log"),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setFormatter(StructuredFormatter(pii_types if redact_pii else None))
        root_logger.addHandler(file_handler)

        # Error-only file
        error_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, "zenix_error.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=3,
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter(pii_types if redact_pii else None))
        root_logger.addHandler(error_handler)

    return root_logger


# ── Convenience Logger Instances ──────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """Get a child logger for a specific module."""
    return logging.getLogger(f"zenix.{name}")


# Pre-configured loggers for common modules
pipeline_log = get_logger("pipeline")
llm_log = get_logger("llm")
rag_log = get_logger("rag")
agent_log = get_logger("agent")
cache_log = get_logger("cache")
rate_log = get_logger("rate_limiter")
api_log = get_logger("api")
