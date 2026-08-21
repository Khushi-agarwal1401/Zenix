"""
Input Guard for Zenix AI.
Sanitizes user input and detects prompt injection attempts.
"""

import re
from typing import Tuple


# ── Prompt Injection Patterns ─────────────────────────────────────────────────

INJECTION_PATTERNS = [
    # Direct instruction override
    re.compile(r'ignore\s+(all\s+)?(previous|prior|above|earlier|preceding)\s+(instructions?|prompts?|rules?|guidelines?)', re.IGNORECASE),
    re.compile(r'disregard\s+(all\s+)?(previous|your)\s+(instructions?|programming|rules?)', re.IGNORECASE),
    re.compile(r'forget\s+(everything|all|your)\s+(you|instructions?|rules?|training)', re.IGNORECASE),

    # Role hijacking
    re.compile(r'you\s+are\s+now\s+(a|an|the)\s+', re.IGNORECASE),
    re.compile(r'act\s+as\s+(if\s+)?(you\s+are|a|an|there\s+are\s+no)', re.IGNORECASE),
    re.compile(r'pretend\s+(you\s+are|to\s+be|there\s+are\s+no)', re.IGNORECASE),
    re.compile(r'switch\s+to\s+(developer|debug|admin|root|god)\s+mode', re.IGNORECASE),
    re.compile(r'enter\s+(developer|debug|admin|DAN|jailbreak)\s+mode', re.IGNORECASE),

    # System prompt extraction
    re.compile(r'(show|reveal|print|output|display|repeat)\s+(me\s+)?(your|the)\s+(system\s+prompt|instructions?|rules?|programming)', re.IGNORECASE),
    re.compile(r'what\s+(are|is)\s+your\s+(system\s+prompt|initial\s+instructions?|rules?)', re.IGNORECASE),
    re.compile(r'tell\s+me\s+your\s+(system|original)\s+(prompt|instructions?)', re.IGNORECASE),

    # Data exfiltration
    re.compile(r'(send|forward|email|transmit)\s+(all|your|the)\s+(data|info|information)\s+to', re.IGNORECASE),
    re.compile(r'copy\s+(everything|all)\s+to', re.IGNORECASE),

    # SQL injection in natural language
    re.compile(r'(drop|delete|truncate|insert|update)\s+(table|database|all|everything)', re.IGNORECASE),
]

# ── Potentially Harmful Content ───────────────────────────────────────────────

HARMFUL_PATTERNS = [
    re.compile(r'how\s+to\s+(make|build|create)\s+(a\s+)?(bomb|explosive|weapon|gun|knife)', re.IGNORECASE),
    re.compile(r'(bypass|crack|hack)\s+(security|firewall|password|authentication)', re.IGNORECASE),
    re.compile(r'(steal|phish|scam|fraud)\s+(money|data|credentials|information)', re.IGNORECASE),
]


def sanitize_input(text: str) -> str:
    """
    Basic input sanitization:
    - Strip leading/trailing whitespace
    - Remove null bytes
    - Collapse excessive whitespace
    - Truncate extremely long inputs
    """
    if not text:
        return ""

    # Remove null bytes
    text = text.replace("\x00", "")

    # Strip whitespace
    text = text.strip()

    # Collapse multiple spaces
    text = re.sub(r'\s+', ' ', text)

    # Truncate at 2000 chars (LLM context limit safety)
    if len(text) > 2000:
        text = text[:2000] + "..."

    return text


def detect_injection(text: str) -> Tuple[bool, str]:
    """
    Detect prompt injection attempts in user input.

    Returns:
        (is_suspicious, reason) — True if injection detected with explanation.
    """
    for pattern in INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            return True, f"Possible prompt injection: '{match.group()[:80]}'"

    return False, ""


def detect_harmful(text: str) -> Tuple[bool, str]:
    """
    Detect requests for harmful content.

    Returns:
        (is_harmful, reason) — True if harmful content detected.
    """
    for pattern in HARMFUL_PATTERNS:
        match = pattern.search(text)
        if match:
            return True, f"Harmful request detected: '{match.group()[:80]}'"

    return False, ""


def detect_roman_indic(text: str) -> bool:
    """
    Detect if input contains Romanized Indic text (Hinglish/Tanglish/etc.).
    Checks for common patterns like 'namaste', 'shukriya', 'dhanyavaad', etc.
    """
    roman_indic_words = [
        'namaste', 'namaskar', 'namaskaram', 'vanakkam', 'namaskara',
        'shukriya', 'dhanyavaad', 'dhanyavad', 'bohot', 'bahut', 'acha',
        'theek', 'kaise', 'kya', 'haan', 'nahi', 'nahin', 'ji', 'jihaan',
        'aap', 'tum', 'mai', 'hum', 'unka', 'uska', 'yeh', 'woh', 'karo',
        'karo', 'bolo', 'suno', 'dekho', 'jao', 'aao', 'khaana', 'paani',
        'ghar', 'bahar', 'andar', 'upar', 'neeche', 'saath', 'alag',
        'dost', 'bhai', 'behen', 'maa', 'papa', 'beta', 'beti',
        'accha', 'bura', 'sundar', 'chhota', 'bada', 'tez', 'dheere',
        'subah', 'shaam', 'raat', 'din', 'mahina', 'saal', 'aaj', 'kal',
        'parson', 'abhi', 'phir', 'magar', 'lekin', 'aur', 'ya', 'ki',
        'ka', 'ke', 'ko', 'se', 'mein', 'pe', 'par', 'ko', 'ne',
    ]
    text_lower = text.lower()
    words = set(text_lower.split())
    matches = words.intersection(set(roman_indic_words))
    return len(matches) >= 2


def guard_input(text: str) -> Tuple[str, bool, str]:
    """
    Full input guard pipeline:
    1. Sanitize
    2. Detect crisis (return crisis response, don't block)
    3. Detect injection
    4. Detect harmful content
    5. Detect Romanized Indic text for transliteration hints

    Returns:
        (sanitized_text, is_blocked, block_reason)
    """
    sanitized = sanitize_input(text)

    # Check for crisis — these should NOT be blocked, they need empathetic response
    try:
        from .crisis import detect_crisis
        crisis = detect_crisis(sanitized)
        if crisis:
            # Crisis detected — don't block, but flag for special handling
            return sanitized, False, f"CRISIS:{crisis['type']}:{crisis['severity']}"
    except ImportError:
        pass

    # Check for injection
    is_injection, reason = detect_injection(sanitized)
    if is_injection:
        return sanitized, True, reason

    # Check for harmful content
    is_harmful, reason = detect_harmful(sanitized)
    if is_harmful:
        return sanitized, True, reason

    return sanitized, False, ""
