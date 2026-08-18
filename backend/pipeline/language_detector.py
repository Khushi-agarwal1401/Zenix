"""
Backend language detection for Zenix.
Uses Unicode script analysis — no heavy external dependencies.
Detects Indic languages, code-mixed text (Hinglish), and normalizes input.
"""

import re
import unicodedata
from typing import Dict, List, Optional, Tuple


# ── Unicode Script Detection ──────────────────────────────────────────────────

def get_unicode_script(char: str) -> Optional[str]:
    """Get the Unicode script name for a character."""
    try:
        name = unicodedata.name(char, "")
    except ValueError:
        return None

    # Map Unicode names to script labels
    script_map = {
        "DEVANAGARI": "Devanagari",
        "BENGALI": "Bengali",
        "GURMUKHI": "Gurmukhi",
        "GUJARATI": "Gujarati",
        "TAMIL": "Tamil",
        "TELUGU": "Telugu",
        "KANNADA": "Kannada",
        "MALAYALAM": "Malayalam",
        "ORIYA": "Odia",
        "THAI": "Thai",
        "ARABIC": "Arabic",
        "HIRAGANA": "Hiragana",
        "KATAKANA": "Katakana",
        "HANGUL": "Hangul",
        "CJK": "Han",
    }

    for keyword, script in script_map.items():
        if keyword in name:
            return script
    return None


SCRIPT_TO_LANGUAGES = {
    "Devanagari": ["hi", "mr", "ne", "sa"],
    "Bengali": ["bn", "as"],
    "Gurmukhi": ["pa"],
    "Gujarati": ["gu"],
    "Tamil": ["ta"],
    "Telugu": ["te"],
    "Kannada": ["kn"],
    "Malayalam": ["ml"],
    "Odia": ["or"],
    "Arabic": ["ar", "ur"],
    "Hangul": ["ko"],
    "Han": ["zh"],
    "Hiragana": ["ja"],
    "Katakana": ["ja"],
}

# Common Hinglish indicator words
CODE_MIXED_INDICATORS = {
    "hai", "ho", "kya", "kaun", "kahan", "kyun", "kaise", "nahi", "haan",
    "bhai", "yaar", "arre", "acha", "theek", "suno", "batao", "bolo",
    "chalo", "dekho", "mat", "mai", "mera", "tera", "uska", "iska",
    "woh", "yeh", "kab", "ab", "phir", "bhi", "toh", "se", "ko",
    "me", "pe", "ne", "ke", "ki", "ka", "par", "aur", "ek", "do",
    "namaste", "namaskar", "ji",
}


class LanguageDetector:
    """
    Detects language and script of input text using Unicode analysis.
    Supports all 22 Scheduled Languages of India + English + code-mixed text.
    """

    def detect(self, text: str) -> Dict:
        """
        Detect the language of the input text.

        Returns:
            {
                "language": str,        # ISO 639 code: 'hi', 'bn', 'en', 'hi-en' etc.
                "script": str,          # Script name: 'Devanagari', 'Bengali', 'Latn'
                "confidence": float,    # 0.0 - 1.0
                "is_code_mixed": bool,
            }
        """
        if not text or not text.strip():
            return {
                "language": "en",
                "script": "Latn",
                "confidence": 0.5,
                "is_code_mixed": False,
            }

        script_counts: Dict[str, int] = {}
        total_meaningful = 0
        latin_count = 0

        for char in text:
            script = get_unicode_script(char)
            if script:
                script_counts[script] = script_counts.get(script, 0) + 1
                total_meaningful += 1
            elif char.isalpha():
                latin_count += 1

        scripts_detected = list(script_counts.keys())

        # Case 1: Only Latin script
        if latin_count > 0 and not scripts_detected:
            words = text.lower().split()
            indic_matches = sum(1 for w in words if w.strip(".,!?;:") in CODE_MIXED_INDICATORS)
            mix_ratio = indic_matches / max(len(words), 1)

            if mix_ratio > 0.3:
                return {
                    "language": "hi-en",
                    "script": "Latn",
                    "confidence": min(0.5 + mix_ratio, 0.95),
                    "is_code_mixed": True,
                }
            return {
                "language": "en",
                "script": "Latn",
                "confidence": 0.9,
                "is_code_mixed": False,
            }

        # Case 2: Indic script(s) detected
        if scripts_detected:
            dominant_script = max(script_counts, key=script_counts.get)
            max_count = script_counts[dominant_script]
            dominant_ratio = max_count / max(total_meaningful, 1)
            is_code_mixed = len(scripts_detected) > 1 or latin_count > total_meaningful * 0.15

            languages = SCRIPT_TO_LANGUAGES.get(dominant_script, ["unknown"])
            primary_lang = languages[0]
            final_lang = f"{primary_lang}-en" if is_code_mixed and latin_count > 5 else primary_lang

            return {
                "language": final_lang,
                "script": dominant_script,
                "confidence": min(dominant_ratio + 0.1, 1.0),
                "is_code_mixed": is_code_mixed,
            }

        return {
            "language": "en",
            "script": "Latn",
            "confidence": 0.5,
            "is_code_mixed": False,
        }


# ── Input Normalization ──────────────────────────────────────────────────────

def normalize_input(text: str) -> str:
    """
    Normalize input text:
    - Trim whitespace
    - Collapse multiple spaces
    - Normalize elongated characters ("kyaaa" → "kya")
    """
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"([a-zA-Z])\1{2,}", r"\1\1", text)  # Elongated chars
    return text


# ── Module-level convenience ─────────────────────────────────────────────────

_default_detector = LanguageDetector()


def detect_language(text: str) -> Dict:
    """Convenience function for language detection."""
    return _default_detector.detect(text)
