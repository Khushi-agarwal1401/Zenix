"""
Entity Extraction for Zenix AI.

Two-stage extraction:
  1. Fast regex-based extraction for Indian-specific entities
  2. LLM fallback for general named entities

Indian entities detected:
  - PIN codes (6 digits)
  - Aadhaar numbers (12 digits, Verhoeff checksum)
  - PAN cards (AAAAA9999A format)
  - Indian phone numbers (+91 or 10-digit starting with 6-9)
  - Indian states and UTs
  - Indian districts (common ones)
  - Currency amounts (₹, Rs, INR, $, etc.)
  - Dates (DD/MM/YYYY, DD-MM-YYYY, month names)
  - Stock symbols (NSE/BSE tickers)
  - IFSC codes (11 chars)
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from .interface import PipelineModule
from .llm_client import LLMClient


# ═══════════════════════════════════════════════════════════════════════════════
# Indian States and Union Territories
# ═══════════════════════════════════════════════════════════════════════════════

INDIAN_STATES = {
    # States
    "andhra pradesh": "AP", "arunachal pradesh": "AR", "assam": "AS",
    "bihar": "BR", "chhattisgarh": "CG", "goa": "GA", "gujarat": "GJ",
    "haryana": "HR", "himachal pradesh": "HP", "jharkhand": "JH",
    "karnataka": "KA", "kerala": "KL", "madhya pradesh": "MP",
    "maharashtra": "MH", "manipur": "MN", "meghalaya": "ML",
    "mizoram": "MZ", "nagaland": "NL", "odisha": "OD", "punjab": "PB",
    "rajasthan": "RJ", "sikkim": "SK", "tamil nadu": "TN",
    "telangana": "TS", "tripura": "TR", "uttar pradesh": "UP",
    "uttarakhand": "UK", "west bengal": "WB",
    # Union Territories
    "andaman and nicobar": "AN", "chandigarh": "CH",
    "dadra and nagar haveli": "DD", "delhi": "DL",
    "jammu and kashmir": "JK", "ladakh": "LA",
    "lakshadweep": "LD", "puducherry": "PY",
    "delhi nct": "DL", "new delhi": "DL",
}

# Build a sorted pattern for state matching (longest first to avoid partial matches)
_STATES_SORTED = sorted(INDIAN_STATES.keys(), key=len, reverse=True)
_STATE_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(s) for s in _STATES_SORTED) + r')\b',
    re.IGNORECASE
)

# ═══════════════════════════════════════════════════════════════════════════════
# Indian Districts (top 100+ major districts)
# ═══════════════════════════════════════════════════════════════════════════════

INDIAN_DISTRICTS = {
    # Maharashtra
    "mumbai", "pune", "nagpur", "nashik", "aurangabad", "solapur", "thane",
    "nanded", "kolhapur", "sangli", "amravati", "jalgaon", "akola",
    "ahmednagar", "satara", "ratnagiri", " Wardha",
    # Delhi
    "new delhi", "central delhi", "south delhi", "north delhi", "east delhi",
    "west delhi",
    # Karnataka
    "bangalore", "bengaluru", "mysore", "mysuru", "hubli", "dharwad",
    "mangalore", "mangaluru", "belgaum", "belagavi", "gulbarga", "kalaburagi",
    # Tamil Nadu
    "chennai", "coimbatore", "madurai", "tiruchirappalli", "tirunelveli",
    "salem", "erode", "vellore", "thoothukudi", "dindigul",
    # Uttar Pradesh
    "lucknow", "kanpur", "agra", "varanasi", "allahabad", "prayagraj",
    "meerut", "bareilly", "aligarh", "gorakhpur", "noida", "ghaziabad",
    # Gujarat
    "ahmedabad", "surat", "vadodara", "rajkot", "bhavnagar", "jamnagar",
    "gandhinagar",
    # Rajasthan
    "jaipur", "jodhpur", "udaipur", "kota", "ajmer", "bikaner",
    "pushkar", "mount abu",
    # West Bengal
    "kolkata", "howrah", "darjeeling", "siliguri", "asansol",
    # Bihar
    "patna", "gaya", "muzaffarpur", "bhagalpur",
    # Madhya Pradesh
    "bhopal", "indore", "gwalior", "jabalpur", "ujjain",
    # Punjab
    "amritsar", "ludhiana", "jalandhar", "patiala", "chandigarh",
    # Haryana
    "gurgaon", "gurugram", "faridabad", "panipat", " Karnal",
    # Kerala
    "thiruvananthapuram", "kochi", "cochin", "kozhikode", "calicut",
    "thrissur",
    # Telangana
    "hyderabad", "warangal", "karimnagar",
    # Andhra Pradesh
    "visakhapatnam", "vijayawada", "guntur", "tirupati",
    # Odisha
    "bhubaneswar", "cuttack", "puri",
    # Assam
    "guwahati", "dispur",
    # Jharkhand
    "ranchi", "jamshedpur", "dhanbad",
    # Chhattisgarh
    "raipur", "bilaspur",
    # Goa
    "panaji", "mapusa", "margoa", "madgaon",
    # Uttarakhand
    "dehradun", "haridwar", "rishikesh",
    # Himachal Pradesh
    "shimla", "manali", "dharamshala",
    # Jammu & Kashmir
    "srinagar", "jammu", "leh", "ladakh",
    # North East
    "imphal", "shillong", "aizawl", "kohima", "itanagar",
}

# Build district pattern
_DISTRICTS_SORTED = sorted(INDIAN_DISTRICTS, key=len, reverse=True)
_DISTRICT_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(d) for d in _DISTRICTS_SORTED) + r')\b',
    re.IGNORECASE
)

# ═══════════════════════════════════════════════════════════════════════════════
# Indian-specific regex patterns
# ═══════════════════════════════════════════════════════════════════════════════

# PIN code: 6 digits (first digit 1-9)
PIN_PATTERN = re.compile(r'\b([1-9]\d{5})\b')

# Aadhaar: 12 digits, optionally spaced/dashed
AADHAAR_PATTERN = re.compile(r'\b(\d{4}\s?\d{4}\s?\d{4})\b')

# PAN: AAAAA9999A format
PAN_PATTERN = re.compile(r'\b([A-Z]{5}\d{4}[A-Z])\b', re.IGNORECASE)

# Indian phone: +91 XXXXX XXXXX or 10-digit starting with 6-9
PHONE_PATTERN = re.compile(r'(?:\+91[\s-]?)?([6-9]\d{9})\b')

# IFSC code: 4 letters + 0 + 6 alphanumeric
IFSC_PATTERN = re.compile(r'\b([A-Z]{4}0[A-Z0-9]{6})\b', re.IGNORECASE)

# Currency amounts: ₹1,234 / Rs. 5000 / INR 10000 / $100 / 500 rupees
AMOUNT_PATTERN = re.compile(
    r'(?:₹|Rs\.?|INR|USD|\$|€|£|¥)\s*([\d,]+(?:\.\d{1,2})?)'
    r'|([\d,]+(?:\.\d{1,2})?)\s*(?:rupees|lakh|lakhs|crore|crores| dollars?)',
    re.IGNORECASE
)

# Stock symbols: RELIANCE, TCS, INFY, etc. (3-5 uppercase letters on NSE/BSE)
STOCK_PATTERN = re.compile(
    r'\b(?:stock|share|price|nse|bse)\s+(?:of\s+)?([A-Z]{3,10})\b'
    r'|([A-Z]{3,10})\s+(?:stock|share|price)',
    re.IGNORECASE
)

# Date patterns: DD/MM/YYYY, DD-MM-YYYY, "15 January 2026", etc.
DATE_PATTERNS = [
    re.compile(r'\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b'),  # DD/MM/YYYY
    re.compile(
        r'\b(\d{1,2})\s+(january|february|march|april|may|june|'
        r'july|august|september|october|november|december)\s+(\d{4})\b',
        re.IGNORECASE
    ),
    re.compile(
        r'\b(january|february|march|april|may|june|'
        r'july|august|september|october|november|december)\s+(\d{1,2}),?\s*(\d{4})\b',
        re.IGNORECASE
    ),
]

# ═══════════════════════════════════════════════════════════════════════════════
# Verhoeff Algorithm for Aadhaar Validation
# ═══════════════════════════════════════════════════════════════════════════════

_VERHOEFF_D = [
    [0,1,2,3,4,5,6,7,8,9],
    [1,2,3,4,0,6,7,8,9,5],
    [2,3,4,0,1,7,8,9,5,6],
    [3,4,0,1,2,8,9,5,6,7],
    [4,0,1,2,3,9,5,6,7,8],
    [5,9,8,7,6,0,4,3,2,1],
    [6,5,9,8,7,1,0,4,3,2],
    [7,6,5,9,8,2,1,0,4,3],
    [8,7,6,5,9,3,2,1,0,4],
    [9,8,7,6,5,4,3,2,1,0],
]
_VERHOEFF_P = [
    [0,1,2,3,4,5,6,7,8,9],
    [1,5,7,6,2,8,3,0,9,4],
    [5,8,0,3,7,9,6,1,4,2],
    [8,9,1,6,0,4,3,5,2,7],
    [9,4,5,3,1,2,6,8,7,0],
    [4,2,8,6,5,7,3,9,0,1],
    [2,7,9,3,8,0,6,4,1,5],
    [7,0,4,6,9,1,3,2,5,8],
]


def _verhoeff_check(number: str) -> bool:
    """Verify Aadhaar number using Verhoeff checksum."""
    checksum = 0
    for i, digit in enumerate(reversed(number)):
        checksum = _VERHOEFF_D[checksum][_VERHOEFF_P[i % 8][int(digit)]]
    return checksum == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Regex-based Entity Extraction
# ═══════════════════════════════════════════════════════════════════════════════

def extract_indian_entities(text: str) -> List[Dict[str, Any]]:
    """
    Fast regex-based extraction of Indian-specific entities.
    Returns a list of {type, value, ...} dicts.
    """
    entities = []

    # Aadhaar (check first since it's 12 digits and could match PIN pattern)
    for match in AADHAAR_PATTERN.finditer(text):
        raw = match.group(1).replace(" ", "").replace("-", "")
        if len(raw) == 12 and _verhoeff_check(raw):
            entities.append({
                "type": "AADHAAR",
                "value": raw,
                "masked": f"XXXX XXXX {raw[-4:]}",
                "valid": True,
            })
        elif len(raw) == 12:
            entities.append({
                "type": "AADHAAR",
                "value": raw,
                "masked": f"XXXX XXXX {raw[-4:]}",
                "valid": False,
                "note": "Checksum mismatch — may be invalid",
            })

    # PAN
    for match in PAN_PATTERN.finditer(text):
        pan = match.group(1).upper()
        issuer_map = {
            "P": "Individual", "C": "Company", "H": "HUF",
            "F": "Firm", "A": "AOP", "T": "Trust",
            "L": "Local Authority", "J": "AJP", "G": "Government",
        }
        entities.append({
            "type": "PAN",
            "value": pan,
            "issuer_type": issuer_map.get(pan[3], "Unknown"),
            "masked": f"XXXXX{pan[5:9]}{pan[9]}",
        })

    # IFSC Code
    for match in IFSC_PATTERN.finditer(text):
        ifsc = match.group(1).upper()
        # Exclude false positives (e.g., Aadhaar digits that happen to match)
        if not any(e["type"] == "AADHAAR" and ifsc in e["value"] for e in entities):
            entities.append({
                "type": "IFSC",
                "value": ifsc,
                "bank_prefix": ifsc[:4],
            })

    # PIN Code (only if not already extracted as Aadhaar)
    aadhaar_values = {e["value"].replace(" ", "") for e in entities if e["type"] == "AADHAAR"}
    for match in PIN_PATTERN.finditer(text):
        pin = match.group(1)
        if pin not in aadhaar_values and pin not in {e["value"] for e in entities if e["type"] == "PIN"}:
            entities.append({
                "type": "PIN",
                "value": pin,
            })

    # Phone Number
    for match in PHONE_PATTERN.finditer(text):
        phone = match.group(1)
        if phone not in {e["value"] for e in entities if e["type"] == "PHONE"}:
            entities.append({
                "type": "PHONE",
                "value": phone,
                "formatted": f"+91 {phone[:5]} {phone[5:]}",
            })

    # Indian States
    for match in _STATE_PATTERN.finditer(text):
        state_name = match.group(1)
        code = INDIAN_STATES.get(state_name.lower(), "")
        entities.append({
            "type": "STATE",
            "value": state_name.title(),
            "code": code,
        })

    # Districts
    for match in _DISTRICT_PATTERN.finditer(text):
        district = match.group(1)
        # Avoid duplicates
        if not any(e["type"] == "DISTRICT" and e["value"].lower() == district.lower() for e in entities):
            entities.append({
                "type": "DISTRICT",
                "value": district.title(),
            })

    # Currency Amounts
    for match in AMOUNT_PATTERN.finditer(text):
        amount_str = match.group(1) or match.group(2)
        if amount_str:
            amount_str = amount_str.replace(",", "")
            try:
                amount = float(amount_str)
                # Detect currency symbol from match
                raw = match.group(0)
                if "₹" in raw or "Rs" in raw or "INR" in raw or "rupees" in raw.lower():
                    currency = "INR"
                elif "$" in raw or "USD" in raw or "dollar" in raw.lower():
                    currency = "USD"
                elif "€" in raw or "EUR" in raw:
                    currency = "EUR"
                elif "£" in raw or "GBP" in raw:
                    currency = "GBP"
                else:
                    currency = "INR"

                # Detect lakhs/crores
                raw_lower = raw.lower()
                if "crore" in raw_lower:
                    amount *= 10_000_000
                elif "lakh" in raw_lower:
                    amount *= 100_000

                entities.append({
                    "type": "AMOUNT",
                    "value": amount,
                    "currency": currency,
                    "raw": match.group(0).strip(),
                })
            except ValueError:
                pass

    # Stock Symbols
    for match in STOCK_PATTERN.finditer(text):
        symbol = (match.group(1) or match.group(2) or "").upper()
        if symbol and len(symbol) >= 3 and symbol not in {e["value"] for e in entities if e["type"] == "STOCK"}:
            entities.append({
                "type": "STOCK",
                "value": symbol,
            })

    # Dates
    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            groups = match.groups()
            raw = match.group(0)
            if not any(e["type"] == "DATE" and e["raw"] == raw for e in entities):
                entities.append({
                    "type": "DATE",
                    "value": raw.strip(),
                    "raw": raw,
                })

    return entities


# ═══════════════════════════════════════════════════════════════════════════════
# LLM-based Entity Extraction (General)
# ═══════════════════════════════════════════════════════════════════════════════

async def extract_entities_llm(text: str) -> List[Dict[str, Any]]:
    """LLM-based extraction for general named entities (Person, Organization, etc.)."""
    try:
        llm = LLMClient()
        system_prompt = (
            "You are an entity extraction assistant for an Indian AI assistant. "
            "Extract named entities from the text. "
            "Return entities as a comma-separated list of 'TYPE: VALUE' pairs. "
            "Types: Person, Organization, Product, Event, Landmark, University. "
            "Do NOT extract: dates, amounts, PIN codes, Aadhaar, PAN, phone numbers, "
            "states, or districts — these are handled by regex. "
            "Return 'None' if no relevant entities found."
        )
        prompt = f"Extract entities from this text:\n{text}\nEntities:"
        extracted = await llm.async_generate(prompt=prompt, system_prompt=system_prompt)

        if extracted and "none" not in extracted.lower().strip():
            entities = []
            for part in extracted.split(","):
                part = part.strip()
                if ":" in part:
                    etype, evalue = part.split(":", 1)
                    entities.append({
                        "type": etype.strip().upper(),
                        "value": evalue.strip(),
                    })
            return entities
    except Exception as e:
        print(f"LLM Entity Extraction failed: {e}")

    return []


# ═══════════════════════════════════════════════════════════════════════════════
# Combined Entity Extractor Module
# ═══════════════════════════════════════════════════════════════════════════════

class EntityExtractor(PipelineModule):
    """
    Two-stage entity extraction:
      1. Fast regex-based extraction for Indian-specific entities
      2. LLM fallback for general named entities

    This is much more reliable than pure LLM extraction for Indian entities
    like PIN codes, Aadhaar numbers, PAN cards, phone numbers, states, and districts.
    """

    async def process(self, input_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
        message = input_data

        # Stage 1: Fast regex extraction (Indian entities)
        regex_entities = extract_indian_entities(message)

        # Stage 2: LLM extraction (general entities) — only if message is long enough
        llm_entities = []
        if len(message.split()) > 3:
            llm_entities = await extract_entities_llm(message)

        # Merge, avoiding duplicates
        all_entities = list(regex_entities)
        existing_values = {
            (e["type"], e.get("value", "").lower()) for e in regex_entities
        }
        for entity in llm_entities:
            key = (entity["type"], entity.get("value", "").lower())
            if key not in existing_values:
                all_entities.append(entity)
                existing_values.add(key)

        # Build helpful context for downstream modules
        context_hints = {}
        for e in all_entities:
            if e["type"] == "PIN":
                context_hints["pincode"] = e["value"]
            elif e["type"] == "STATE":
                context_hints.setdefault("states", []).append(e["value"])
            elif e["type"] == "DISTRICT":
                context_hints.setdefault("districts", []).append(e["value"])
            elif e["type"] == "AADHAAR":
                context_hints["aadhaar_detected"] = True
            elif e["type"] == "PAN":
                context_hints["pan_detected"] = True
            elif e["type"] == "PHONE":
                context_hints.setdefault("phones", []).append(e["value"])
            elif e["type"] == "AMOUNT":
                context_hints.setdefault("amounts", []).append(e["value"])
            elif e["type"] == "IFSC":
                context_hints["ifsc"] = e["value"]
            elif e["type"] == "STOCK":
                context_hints.setdefault("stocks", []).append(e["value"])

        return {
            "entities": all_entities,
            "regex_count": len(regex_entities),
            "llm_count": len(llm_entities),
            "context_hints": context_hints,
        }
