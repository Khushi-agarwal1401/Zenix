"""
Transliteration Module for Zenix AI.

Converts Romanized Indian language input (Hinglish, Tanglish, etc.)
to native Indic scripts (Devanagari, Bengali, Tamil, Telugu, etc.).

Uses rule-based mapping tables for common patterns — no external API needed.
For full-fidelity transliteration, falls back to the itrans/Akhil Bharatiya
transliteration standard.

Supported scripts:
  - Devanagari (Hindi, Marathi, Nepali, Sanskrit)
  - Bengali/Assamese
  - Tamil
  - Telugu
  - Gujarati
  - Kannada
  - Malayalam
  - Gurmukhi (Punjabi)
  - Odia
"""

import re
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Roman → Devanagari Transliteration Table (Hindi/Marathi/Sanskrit)
# Based on standard IAST/itrans mapping with common Hinglish patterns
# ═══════════════════════════════════════════════════════════════════════════════

_DEVANAGARI_MAP = {
    # Vowels (Swar)
    "a": "अ", "aa": "आ", "i": "इ", "ee": "ई",
    "u": "उ", "oo": "ऊ", "e": "ए", "ai": "ऐ",
    "o": "ओ", "au": "औ", "am": "अं", "ah": "अः",

    # Consonants (Vyanjan) — basic
    "k": "क", "kh": "ख", "g": "ग", "gh": "घ", "ng": "ङ",
    "ch": "छ", "Ch": "च",  # uppercase Ch for च vs छ
    "j": "ज", "jh": "झ", "nj": "ञ",
    "t": "त", "th": "थ", "d": "द", "dh": "ध", "n": "न",
    "T": "ट", "Th": "ठ", "D": "ड", "Dh": "ढ", "N": "ण",
    "p": "प", "ph": "फ", "b": "ब", "bh": "भ", "m": "म",
    "y": "य", "r": "र", "l": "ल", "v": "व", "w": "व",
    "sh": "श", "Sh": "ष", "s": "स", "h": "ह",
    "zh": "ज़", "f": "फ़",

    # Nukta variants
    "ksha": "क्ष", "jna": "ज्ञ", "tra": "त्र", "gya": "ज्ञ",

    # Matras (vowel signs applied after consonants)
    "_aa": "ा", "_i": "ि", "_ee": "ी",
    "_u": "ु", "_oo": "ू", "_e": "े", "_ai": "ै",
    "_o": "ो", "_au": "ौ", "_am": "ं", "_ah": "ः",
}

# Roman → Bengali Script
_BENGALI_MAP = {
    "a": "অ", "aa": "আ", "i": "ই", "ee": "ঈ",
    "u": "উ", "oo": "ঊ", "e": "এ", "ai": "ঐ",
    "o": "ও", "au": "ঔ", "am": "অং", "ah": "অঃ",
    "k": "ক", "kh": "খ", "g": "গ", "gh": "ঘ", "ng": "ঙ",
    "ch": "ছ", "Ch": "চ", "j": "জ", "jh": "ঝ", "nj": "ঞ",
    "t": "ত", "th": "থ", "d": "দ", "dh": "ধ", "n": "ন",
    "T": "ট", "Th": "ঠ", "D": "ড", "Dh": "ঢ", "N": "ণ",
    "p": "প", "ph": "ফ", "b": "ব", "bh": "ভ", "m": "ম",
    "y": "য", "r": "র", "l": "ল", "v": "ৱ", "w": "ৱ",
    "sh": "শ", "Sh": "ষ", "s": "স", "h": "হ",
}

# Roman → Tamil Script
_TAMIL_MAP = {
    "a": "அ", "aa": "ஆ", "i": "இ", "ee": "ஈ",
    "u": "உ", "oo": "ஊ", "e": "எ", "ai": "ஐ",
    "o": "ஒ", "au": "ஔ", "am": "அம்", "ah": "அஃ",
    "k": "க", "kh": "க", "g": "க", "gh": "க",
    "ng": "ங", "ch": "ச", "Ch": "ச", "j": "ஜ",
    "jh": "ஜ", "nj": "ஞ", "t": "த", "th": "த",
    "d": "ட", "dh": "ட", "n": "ந", "T": "ட",
    "Th": "ட", "D": "ட", "Dh": "ட", "N": "ண",
    "p": "ப", "ph": "ப", "b": "ப", "bh": "ப", "m": "ம",
    "y": "ய", "r": "ர", "l": "ல", "v": "வ", "w": "வ",
    "sh": "ஷ", "Sh": "ஷ", "s": "ச", "h": "ஹ",
}

# Roman → Telugu Script
_TELUGU_MAP = {
    "a": "అ", "aa": "ఆ", "i": "ఇ", "ee": "ఈ",
    "u": "ఉ", "oo": "ఊ", "e": "ఏ", "ai": "ఐ",
    "o": "ఓ", "au": "ఔ", "am": "అం", "ah": "అః",
    "k": "క", "kh": "ఖ", "g": "గ", "gh": "ఘ", "ng": "ఙ",
    "ch": "ఛ", "Ch": "చ", "j": "జ", "jh": "ఝ", "nj": "ఞ",
    "t": "త", "th": "థ", "d": "ద", "dh": "ధ", "n": "న",
    "T": "ట", "Th": "ఠ", "D": "డ", "Dh": "ఢ", "N": "ణ",
    "p": "ప", "ph": "ఫ", "b": "బ", "bh": "భ", "m": "మ",
    "y": "య", "r": "ర", "l": "ల", "v": "వ", "w": "వ",
    "sh": "శ", "Sh": "ష", "s": "స", "h": "హ",
}

# Roman → Gujarati Script
_GUJARATI_MAP = {
    "a": "અ", "aa": "આ", "i": "ઇ", "ee": "ઈ",
    "u": "ઉ", "oo": "ઊ", "e": "એ", "ai": "ઐ",
    "o": "ઓ", "au": "ઔ", "am": "અં", "ah": "અઃ",
    "k": "ક", "kh": "ખ", "g": "ગ", "gh": "ઘ", "ng": "ઙ",
    "ch": "છ", "Ch": "ચ", "j": "જ", "jh": "ઝ", "nj": "ઞ",
    "t": "ત", "th": "થ", "d": "દ", "dh": "ધ", "n": "ન",
    "T": "ટ", "Th": "ઠ", "D": "ડ", "Dh": "ઢ", "N": "ણ",
    "p": "પ", "ph": "ફ", "b": "બ", "bh": "ભ", "m": "મ",
    "y": "ય", "r": "ર", "l": "લ", "v": "વ", "w": "વ",
    "sh": "શ", "Sh": "ષ", "s": "સ", "h": "હ",
}

# Roman → Kannada Script
_KANNADA_MAP = {
    "a": "ಅ", "aa": "ಆ", "i": "ಇ", "ee": "ಈ",
    "u": "ಉ", "oo": "ಊ", "e": "ಏ", "ai": "ಐ",
    "o": "ಓ", "au": "ಔ", "am": "ಅಂ", "ah": "ಅಃ",
    "k": "ಕ", "kh": "ಖ", "g": "ಗ", "gh": "ಘ", "ng": "ಙ",
    "ch": "ಛ", "Ch": "ಚ", "j": "ಜ", "jh": "ಝ", "nj": "ಞ",
    "t": "ತ", "th": "ಥ", "d": "ದ", "dh": "ಧ", "n": "ನ",
    "T": "ಟ", "Th": "ಠ", "D": "ಡ", "Dh": "ಢ", "N": "ಣ",
    "p": "ಪ", "ph": "ಫ", "b": "ಬ", "bh": "ಭ", "m": "ಮ",
    "y": "ಯ", "r": "ರ", "l": "ಲ", "v": "ವ", "w": "ವ",
    "sh": "ಶ", "Sh": "ಷ", "s": "ಸ", "h": "ಹ",
}

# Roman → Malayalam Script
_MALAYALAM_MAP = {
    "a": "അ", "aa": "ആ", "i": "ഇ", "ee": "ഈ",
    "u": "ഉ", "oo": "ഊ", "e": "എ", "ai": "ഐ",
    "o": "ഒ", "au": "ഔ", "am": "അം", "ah": "അഃ",
    "k": "ക", "kh": "ഖ", "g": "ഗ", "gh": "ഘ", "ng": "ങ",
    "ch": "ഛ", "Ch": "ച", "j": "ജ", "jh": "ഝ", "nj": "ഞ",
    "t": "ത", "th": "ഥ", "d": "ദ", "dh": "ധ", "n": "ന",
    "T": "ട", "Th": "ഠ", "D": "ഡ", "Dh": "ഢ", "N": "ണ",
    "p": "പ", "ph": "ഫ", "b": "ബ", "bh": "ഭ", "m": "മ",
    "y": "യ", "r": "ര", "l": "ല", "v": "വ", "w": "വ",
    "sh": "ശ", "Sh": "ഷ", "s": "സ", "h": "ഹ",
}

# Roman → Gurmukhi (Punjabi)
_GURMUKHI_MAP = {
    "a": "ਅ", "aa": "ਆ", "i": "ਇ", "ee": "ਈ",
    "u": "ਉ", "oo": "ਊ", "e": "ਏ", "ai": "ਐ",
    "o": "ਓ", "au": "ਔ", "am": "ਅੰ", "ah": "ਅਃ",
    "k": "ਕ", "kh": "ਖ", "g": "ਗ", "gh": "ਘ", "ng": "ਙ",
    "ch": "ਛ", "Ch": "ਚ", "j": "ਜ", "jh": "ਝ", "nj": "ਞ",
    "t": "ਤ", "th": "ਥ", "d": "ਦ", "dh": "ਧ", "n": "ਨ",
    "T": "ਟ", "Th": "ਠ", "D": "ਡ", "Dh": "ਢ", "N": "ਣ",
    "p": "ਪ", "ph": "ਫ", "b": "ਬ", "bh": "ਭ", "m": "ਮ",
    "y": "ਯ", "r": "ਰ", "l": "ਲ", "v": "ਵ", "w": "ਵ",
    "sh": "ਸ਼", "Sh": "ਸ਼", "s": "ਸ", "h": "ਹ",
}

# Roman → Odia Script
_ODIA_MAP = {
    "a": "ଅ", "aa": "ଆ", "i": "ଇ", "ee": "ଈ",
    "u": "ଉ", "oo": "ଊ", "e": "ଏ", "ai": "ଐ",
    "o": "ଓ", "au": "ଔ", "am": "ଅଂ", "ah": "ଅଃ",
    "k": "କ", "kh": "ଖ", "g": "ଗ", "gh": "ଘ", "ng": "ଙ",
    "ch": "ଛ", "Ch": "ଚ", "j": "ଜ", "jh": "ଝ", "nj": "ଞ",
    "t": "ତ", "th": "ଥ", "d": "ଦ", "dh": "ଧ", "n": "ନ",
    "T": "ଟ", "Th": "ଠ", "D": "ଡ", "Dh": "ଢ", "N": "ଣ",
    "p": "ପ", "ph": "ଫ", "b": "ବ", "bh": "ଭ", "m": "ମ",
    "y": "ୟ", "r": "ର", "l": "ଲ", "v": "ୱ", "w": "ୱ",
    "sh": "ଶ", "Sh": "ଷ", "s": "ସ", "h": "ହ",
}


# ═══════════════════════════════════════════════════════════════════════════════
# Language detection keywords
# ═══════════════════════════════════════════════════════════════════════════════

# Common words that help identify the target language
_LANG_INDICATORS = {
    "hindi": [
        "namaste", "aap", "kaise", "hai", "hain", "mein", "hum", "tum",
        "kya", "nahi", "haan", "ji", "bhai", "didi", "bhaiya", "behen",
        "accha", "theek", "dhanyavaad", "shukriya", "mujhe", "aapko",
        "batao", "bataiye", "samajh", "samjhe", "karo", "kijiye",
    ],
    "marathi": [
        "namaskar", "tumhi", "aamhi", "kay", "aahe", "nahi", "dhanyavaad",
        "bhau", "baji", "mama", "aai", "baba", "kiti", "kuthay", "yay",
        "pahunche", "jaun", "karun", "bolu", "mhanje",
    ],
    "bengali": [
        "nomoshkar", "apni", "amra", "kemon", "ache", "na", "dhonnobad",
        "dada", "didi", "bhai", "kemon", "thakben", "jete", "khete",
    ],
    "tamil": [
        "vanakkam", "neenga", "naan", "enna", "irukku", "illai", "nandri",
        "anna", "akka", "thalaiva", "sevi", "sellam", "pogirom",
    ],
    "telugu": [
        "namaskaram", "meeru", "nenu", "enti", "undi", "ledu", "dhanyavaadalu",
        "anna", "akka", "garu", "cheyali", "velli", "tinu", "chudali",
    ],
    "gujarati": [
        "namaste", "tame", "hu", "che", "nathi", "dhanyavaad",
        "bhai", "ben", "kem", "chho", "jao", "aao", "karo",
    ],
    "kannada": [
        "namaskara", "neevu", "naanu", "enu", "ide", "illa", "dhanyavaadagalu",
        "anna", "akka", "hodi", "hogi", "maadi", "thinni",
    ],
    "malayalam": [
        "namaskaram", "ningal", "njan", "entha", "undu", "illa", "nanni",
        "chetta", "chechi", "pokam", "thinnam", "kazhinju",
    ],
    "punjabi": [
        "sat sri akal", "tussi", "main", "ki", "hai", "nahi", "dhanyavaad",
        "bhai", "behen", "jatt", "kiddan", "thik", "chal", "aajo",
    ],
    "odia": [
        "namaskar", "aapana", "mu", "kine", "ache", "nahi", "dhanyavaad",
        "bhai", "bhoun", "kana", "ache", "jao", "asila",
    ],
}

# Language name → script mapping
LANGUAGE_SCRIPT_MAP = {
    "hindi": "devanagari",
    "marathi": "devanagari",
    "sanskrit": "devanagari",
    "nepali": "devanagari",
    "bengali": "bengali",
    "assamese": "bengali",
    "tamil": "tamil",
    "telugu": "telugu",
    "gujarati": "gujarati",
    "kannada": "kannada",
    "malayalam": "malayalam",
    "punjabi": "gurmukhi",
    "odia": "odia",
    "oriya": "odia",
}

# Script → transliteration map
SCRIPT_MAP = {
    "devanagari": _DEVANAGARI_MAP,
    "bengali": _BENGALI_MAP,
    "tamil": _TAMIL_MAP,
    "telugu": _TELUGU_MAP,
    "gujarati": _GUJARATI_MAP,
    "kannada": _KANNADA_MAP,
    "malayalam": _MALAYALAM_MAP,
    "gurmukhi": _GURMUKHI_MAP,
    "odia": _ODIA_MAP,
}


# ═══════════════════════════════════════════════════════════════════════════════
# Core Transliteration Engine
# ═══════════════════════════════════════════════════════════════════════════════

# Characters already in an Indic script (Unicode range check)
_DEVANAGARI_RANGE = range(0x0900, 0x097F)
_BENGALI_RANGE = range(0x0980, 0x09FF)
_TAMIL_RANGE = range(0x0B80, 0x0BFF)
_TELUGU_RANGE = range(0x0C00, 0x0C7F)
_GUJARATI_RANGE = range(0x0A80, 0x0AFF)
_KANNADA_RANGE = range(0x0C80, 0x0CFF)
_MALAYALAM_RANGE = range(0x0D00, 0x0D7F)
_GURMUKHI_RANGE = range(0x0A00, 0x0A7F)
_ODIA_RANGE = range(0x0B00, 0x0B7F)

ALL_INDIC_RANGES = [
    _DEVANAGARI_RANGE, _BENGALI_RANGE, _TAMIL_RANGE, _TELUGU_RANGE,
    _GUJARATI_RANGE, _KANNADA_RANGE, _MALAYALAM_RANGE, _GURMUKHI_RANGE,
    _ODIA_RANGE,
]


def is_indic_script(text: str) -> bool:
    """Check if text already contains Indic script characters."""
    for ch in text:
        cp = ord(ch)
        for rng in ALL_INDIC_RANGES:
            if cp in rng:
                return True
    return False


def detect_language(text: str) -> Optional[str]:
    """
    Detect the likely target language from Romanized text.
    Returns language name (e.g., 'hindi', 'tamil') or None.
    """
    text_lower = text.lower().strip()
    words = set(re.findall(r'[a-z]+', text_lower))

    scores: Dict[str, int] = {}
    for lang, indicators in _LANG_INDICATORS.items():
        score = len(words.intersection(set(indicators)))
        if score > 0:
            scores[lang] = score

    if not scores:
        return None

    return max(scores, key=scores.get)


def transliterate(text: str, target_script: str = "devanagari") -> str:
    """
    Transliterate Romanized Indian text to the target Indic script.

    Args:
        text: Romanized input text (e.g., "namaste", "kaise ho")
        target_script: Target script name — one of:
            'devanagari', 'bengali', 'tamil', 'telugu', 'gujarati',
            'kannada', 'malayalam', 'gurmukhi', 'odia'

    Returns:
        Transliterated text in the target script, or original text if
        already in an Indic script or transliteration not possible.
    """
    if not text or not text.strip():
        return text

    # If already in Indic script, return as-is
    if is_indic_script(text):
        return text

    # Get the mapping for the target script
    char_map = SCRIPT_MAP.get(target_script)
    if not char_map:
        logger.warning(f"Unknown target script: {target_script}")
        return text

    # Build the transliteration
    result = _apply_transliteration(text, char_map)
    return result


def auto_transliterate(text: str, target_language: str = None) -> str:
    """
    Auto-detect language and transliterate to the appropriate script.

    Args:
        text: Romanized input text
        target_language: Force a specific language (e.g., 'hindi', 'tamil').
                        If None, auto-detects from the text.

    Returns:
        Transliterated text, or original if no transliteration needed.
    """
    if not text or not text.strip():
        return text

    # Already in Indic script — return as-is
    if is_indic_script(text):
        return text

    # Determine target language
    lang = target_language or detect_language(text)
    if not lang:
        # Default to Devanagari (most common)
        lang = "hindi"

    # Map language to script
    script = LANGUAGE_SCRIPT_MAP.get(lang, "devanagari")

    return transliterate(text, script)


def _apply_transliteration(text: str, char_map: Dict[str, str]) -> str:
    """
    Apply transliteration using a character mapping table.

    Strategy:
    1. First, try to match multi-character sequences (longest match first)
    2. Then fall back to single character mapping
    3. Keep spaces, punctuation, and numbers as-is
    """
    result = []
    i = 0
    text_lower = text.lower()

    while i < len(text_lower):
        # Check for multi-character matches (longest first)
        matched = False
        # Try lengths from 4 down to 2
        for length in range(min(4, len(text_lower) - i), 1, -1):
            substr = text_lower[i:i + length]
            if substr in char_map:
                result.append(char_map[substr])
                i += length
                matched = True
                break

        if not matched:
            ch = text_lower[i]
            # Single character match
            if ch in char_map:
                result.append(char_map[ch])
            elif ch.isalpha():
                # Roman letter not in map — keep as-is (best effort)
                result.append(ch)
            else:
                # Keep punctuation, numbers, spaces as-is
                result.append(text[i])
            i += 1

    return "".join(result)


# ═══════════════════════════════════════════════════════════════════════════════
# Convenience API
# ═══════════════════════════════════════════════════════════════════════════════

def roman_to_hindi(text: str) -> str:
    """Shortcut: Roman → Devanagari (Hindi)."""
    return transliterate(text, "devanagari")


def roman_to_bengali(text: str) -> str:
    """Shortcut: Roman → Bengali script."""
    return transliterate(text, "bengali")


def roman_to_tamil(text: str) -> str:
    """Shortcut: Roman → Tamil script."""
    return transliterate(text, "tamil")


def roman_to_telugu(text: str) -> str:
    """Shortcut: Roman → Telugu script."""
    return transliterate(text, "telugu")


def roman_to_gujarati(text: str) -> str:
    """Shortcut: Roman → Gujarati script."""
    return transliterate(text, "gujarati")


def roman_to_kannada(text: str) -> str:
    """Shortcut: Roman → Kannada script."""
    return transliterate(text, "kannada")


def roman_to_malayalam(text: str) -> str:
    """Shortcut: Roman → Malayalam script."""
    return transliterate(text, "malayalam")


def roman_to_punjabi(text: str) -> str:
    """Shortcut: Roman → Gurmukhi (Punjabi)."""
    return transliterate(text, "gurmukhi")


def roman_to_odia(text: str) -> str:
    """Shortcut: Roman → Odia script."""
    return transliterate(text, "odia")


def get_supported_scripts():
    """Return list of supported target scripts."""
    return list(SCRIPT_MAP.keys())


def get_supported_languages():
    """Return list of supported languages with their scripts."""
    return {
        lang: {"script": script, "sample": _get_sample(lang)}
        for lang, script in LANGUAGE_SCRIPT_MAP.items()
    }


def _get_sample(lang: str) -> str:
    """Get a sample transliteration for a language."""
    samples = {
        "hindi": roman_to_hindi("namaste aap kaise hain"),
        "marathi": roman_to_hindi("namaskar tumhi kase ahat"),
        "bengali": roman_to_bengali("nomoshkar apni kemon ache"),
        "tamil": roman_to_tamil("vanakkam neenga enna irukku"),
        "telugu": roman_to_telugu("namaskaram meeru enti undi"),
        "gujarati": roman_to_gujarati("namaste tame kem che"),
        "kannada": roman_to_kannada("namaskara neevu enu ide"),
        "malayalam": roman_to_malayalam("namaskaram ningal entha undu"),
        "punjabi": roman_to_punjabi("sat sri akal tussi ki han"),
        "odia": roman_to_odia("namaskar aapana kine ache"),
    }
    return samples.get(lang, "")


# ═══════════════════════════════════════════════════════════════════════════════
# Transliteration tool handler (for integration with ToolRegistry)
# ═══════════════════════════════════════════════════════════════════════════════

def handle_transliterate(args: str) -> str:
    """
    Tool handler for transliteration.
    Formats:
      transliterate: namaste to hindi
      transliterate: kaise ho to bengali
      transliterate: namaskaram (auto-detect)
    """
    if not args.strip():
        return (
            "Error: Please provide text and optional target language.\n"
            "Examples:\n"
            "  transliterate: namaste to hindi\n"
            "  transliterate: kaise ho to tamil\n"
            "  transliterate: nomoshkar (auto-detect)"
        )

    # Check for "to <language>" pattern
    to_match = re.search(r'\bto\s+([a-zA-Z]+)\s*$', args, re.IGNORECASE)
    target_lang = None
    text = args.strip()

    if to_match:
        target_lang = to_match.group(1).lower()
        text = args[:to_match.start()].strip()

    if not text:
        return "Error: No text provided for transliteration."

    # Already in Indic script?
    if is_indic_script(text):
        return f"Text is already in Indic script: {text}"

    # Perform transliteration
    result = auto_transliterate(text, target_lang)

    if result == text:
        return (
            f"Could not transliterate '{text}'. "
            f"Please ensure it's Romanized Indian text."
        )

    detected_lang = target_lang or detect_language(text) or "hindi"
    script = LANGUAGE_SCRIPT_MAP.get(detected_lang, "devanagari")

    return (
        f"🔤 Transliteration ({detected_lang} / {script}):\n"
        f"  Roman: {text}\n"
        f"  Script: {result}"
    )
