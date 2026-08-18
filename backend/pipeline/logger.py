"""
Structured logging for Zenix AI.
Replaces print() with proper logging levels, structured output, and file rotation.
"""

import os
import sys
import json
import logging
import logging.handlers
from datetime import datetime
from typing import Any, Dict, Optional


class StructuredFormatter(logging.Formatter):
    """JSON-structured log formatter for production use."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data

        # Add exception info if present
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


class ReadableFormatter(logging.Formatter):
    """Human-readable formatter for development use."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        timestamp = datetime.now().strftime("%H:%M:%S")
        name = record.name.split(".")[-1]  # Short logger name
        msg = record.getMessage()

        formatted = f"{color}{timestamp} [{record.levelname:>7}] {name}: {msg}{self.RESET}"

        if record.exc_info and record.exc_info[0]:
            formatted += f"\n{self.formatException(record.exc_info)}"

        return formatted


def setup_logging(
    level: str = "INFO",
    log_dir: str = None,
    json_output: bool = False,
) -> logging.Logger:
    """
    Set up structured logging for the Zenix backend.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_dir: Directory for log files. None = console only.
        json_output: If True, use JSON format. If False, use colored readable format.

    Returns:
        The root logger for the application.
    """
    root_logger = logging.getLogger("zenix")
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if json_output:
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_handler.setFormatter(ReadableFormatter())
    root_logger.addHandler(console_handler)

    # File handler (if log_dir specified)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, "zenix.log"),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)

        # Error-only file
        error_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, "zenix_error.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=3,
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter())
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
