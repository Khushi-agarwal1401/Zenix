"""
Verification Layer for Zenix AI responses.
Checks for toxicity, PII exposure, harmful content, and ensures response quality.
"""

import re
from typing import Any, Dict, List, Tuple
from .interface import PipelineModule


# ── Toxicity / Harmful Content Patterns ───────────────────────────────────────

# Common harmful patterns (English + Hindi/mixed)
TOXIC_PATTERNS: List[re.Pattern] = [
    # Slurs and hate speech (partial list — extend as needed)
    re.compile(r'\b(nigg[ae]r|fagg?ot|retard|chink|spic|kike)\b', re.IGNORECASE),
    # Communal / caste hate
    re.compile(r'\b(kafir|infidel|untouchable caste|lower caste|upper caste)\b', re.IGNORECASE),
    # Violence incitement
    re.compile(r'\b(kill\s+him|kill\s+her|murder|homicide|bomb\s+making|how\s+to\s+make\s+a\s+bomb)\b', re.IGNORECASE),
    # Self-harm
    re.compile(r'\b(suicide\s+method|how\s+to\s+suicide|kill\s+myself|end\s+my\s+life)\b', re.IGNORECASE),
    # Sexual exploitation
    re.compile(r'\b(child\s+porn|cp\s+link|underage\s+sex|loli)\b', re.IGNORECASE),
    # Drug manufacturing
    re.compile(r'\b(make\s+ meth|synthesize\s+cocaine|cook\s+crack|drug\s+recipe)\b', re.IGNORECASE),
    # Political hate (India-specific)
    re.compile(r'\b(all\s+\w+\s+are\s+terrorist|destroy\s+mosque|burn\s+temple|genocide)\b', re.IGNORECASE),
]

# ── PII Patterns ──────────────────────────────────────────────────────────────

PII_PATTERNS: Dict[str, re.Pattern] = {
    "aadhaar": re.compile(r'\b\d{4}\s?\d{4}\s?\d{4}\b'),  # 12 digits
    "pan": re.compile(r'\b[A-Z]{5}\d{4}[A-Z]\b'),
    "phone": re.compile(r'\b(?:\+91[\s-]?)?[6-9]\d{9}\b'),
    "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    "upi_pin": re.compile(r'\b\d{4,6}\b'),  # Could be a UPI PIN in context
}


class VerificationLayer(PipelineModule):
    """
    Verifies the output before sending it to the user.
    Performs safety checks, PII detection, and quality validation.
    """

    async def process(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        response = input_data.get("response", "")

        if not response:
            return {"response": "I'm sorry, I couldn't generate a response. Please try again.", "verified": False}

        output = input_data.copy()

        # 1. Toxicity check
        is_toxic, toxic_reason = self._check_toxicity(response)
        if is_toxic:
            output["response"] = self._get_toxicity_fallback(context)
            output["verified"] = False
            output["toxicity_flag"] = toxic_reason
            return output

        # 2. PII detection & redaction
        has_pii, pii_types = self._check_pii(response)
        if has_pii:
            output["response"] = self._redact_pii(response, context)
            output["verified"] = True  # Still verified, just redacted
            output["pii_redacted"] = pii_types
            return output

        # 3. Quality checks
        quality_issues = self._check_quality(response)
        if quality_issues:
            output["quality_warnings"] = quality_issues

        output["verified"] = True
        return output

    def _check_toxicity(self, text: str) -> Tuple[bool, str]:
        """Check if the response contains toxic or harmful content."""
        for pattern in TOXIC_PATTERNS:
            match = pattern.search(text)
            if match:
                return True, f"Detected harmful pattern: {match.group()[:50]}"
        return False, ""

    def _get_toxicity_fallback(self, context: Dict[str, Any]) -> str:
        """Generate a safe fallback when toxicity is detected."""
        persona = context.get("persona", "desi")
        if persona == "desi":
            return ("Arre yaar, main aisi baatein nahi kar sakta. "
                    "Kuch aur baat karte hain jo helpful ho! 😊")
        return ("I'm unable to provide responses on that topic. "
                "Let's discuss something constructive instead.")

    def _check_pii(self, text: str) -> Tuple[bool, List[str]]:
        """Check if the response exposes PII."""
        found_types = []
        for pii_type, pattern in PII_PATTERNS.items():
            if pattern.search(text):
                found_types.append(pii_type)
        return len(found_types) > 0, found_types

    def _redact_pii(self, text: str, context: Dict[str, Any]) -> str:
        """Redact PII from the response."""
        # Add a disclaimer
        disclaimer = ""
        persona = context.get("persona", "desi")
        if persona == "desi":
            disclaimer = "\n\n⚠️ Note: I've hidden some personal details (phone/aadhaar/pan) for your safety."
        else:
            disclaimer = "\n\nNote: Personal identification details have been redacted for privacy."

        # Redact Aadhaar
        text = re.sub(
            r'\b(\d{4})\s?(\d{4})\s?(\d{4})\b',
            r'XXXX-XXXX-\3',
            text,
        )
        # Redact PAN
        text = re.sub(
            r'\b([A-Z]{5})\d{4}([A-Z])\b',
            r'\1XXXX\2',
            text,
        )
        # Redact phone numbers
        text = re.sub(
            r'\b(?:\+91[\s-]?)?[6-9]\d{9}\b',
            '[PHONE REDACTED]',
            text,
        )
        # Redact emails
        text = re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '[EMAIL REDACTED]',
            text,
        )

        return text + disclaimer

    def _check_quality(self, text: str) -> List[str]:
        """Check response quality and return any warnings."""
        warnings = []
        text_stripped = text.strip()

        # Too short
        if len(text_stripped) < 10:
            warnings.append("Response is very short")

        # Ends with error-like text
        error_patterns = ["error", "failed", "exception", "traceback"]
        for ep in error_patterns:
            if text_stripped.lower().endswith(ep) or text_stripped.lower().startswith(ep):
                warnings.append(f"Response may contain error output: '{ep}'")
                break

        # Contains raw code-like output that shouldn't be there
        if text_stripped.startswith("```") and text_stripped.endswith("```"):
            warnings.append("Response is a raw code block — consider formatting")

        return warnings
