"""
Hallucination Detector for Zenix AI.
Cross-references LLM responses against retrieved context to detect
unsupported claims and fabricated information.
"""

import re
from typing import Dict, List, Tuple, Optional


def extract_claims(text: str) -> List[str]:
    """
    Extract key claims/facts from a response text.
    Splits on sentence boundaries and filters out short/empty fragments.
    """
    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?।])\s+', text.strip())

    claims = []
    for sentence in sentences:
        sentence = sentence.strip()
        # Filter out very short or non-factual sentences
        if len(sentence) > 15 and not sentence.startswith(("```", "#", "---")):
            # Remove markdown formatting
            cleaned = re.sub(r'[*_`#]', '', sentence).strip()
            if cleaned:
                claims.append(cleaned)

    return claims


def check_claim_support(claim: str, context_docs: List[str], threshold: float = 0.3) -> Tuple[bool, float]:
    """
    Check if a claim is supported by the retrieved context documents.

    Uses a simple keyword overlap heuristic (no ML model required):
    - Tokenizes the claim and context
    - Checks what fraction of claim keywords appear in the context
    - Returns (is_supported, support_score)

    Args:
        claim: The claim to verify.
        context_docs: List of retrieved context document strings.
        threshold: Minimum support score to consider the claim supported.

    Returns:
        (is_supported, support_score) — True if score >= threshold.
    """
    if not claim or not context_docs:
        return False, 0.0

    # Tokenize claim into meaningful words (lowercase, alpha only)
    claim_words = set(
        w.lower() for w in re.findall(r'\b[a-zA-Z]{3,}\b', claim)
        if w.lower() not in _STOP_WORDS
    )

    if not claim_words:
        return True, 1.0  # Can't verify short/stopword-only claims

    # Combine all context documents
    full_context = " ".join(context_docs).lower()
    context_words = set(
        w for w in re.findall(r'\b[a-zA-Z]{3,}\b', full_context)
    )

    # Calculate support: what fraction of claim keywords appear in context
    supported = claim_words & context_words
    support_score = len(supported) / len(claim_words)

    return support_score >= threshold, support_score


def detect_hallucination(
    response: str,
    context_docs: List[str],
    strict_threshold: float = 0.3,
    lenient_threshold: float = 0.15,
) -> Dict:
    """
    Detect hallucination by cross-referencing response claims against context.

    Args:
        response: The LLM-generated response.
        context_docs: Retrieved context documents used for generation.
        strict_threshold: Minimum score for "fully supported" claims.
        lenient_threshold: Minimum score for "partially supported" claims.

    Returns:
        {
            "is_hallucinated": bool,     # True if significant hallucination detected
            "hallucination_score": float, # 0.0 (no hallucination) to 1.0 (all hallucinated)
            "unsupported_claims": [...],  # List of unsupported claim strings
            "support_scores": [...],      # Per-claim support scores
        }
    """
    if not context_docs:
        # No context to verify against — can't detect hallucination
        return {
            "is_hallucinated": False,
            "hallucination_score": 0.0,
            "unsupported_claims": [],
            "support_scores": [],
            "note": "No context available for verification",
        }

    claims = extract_claims(response)
    if not claims:
        return {
            "is_hallucinated": False,
            "hallucination_score": 0.0,
            "unsupported_claims": [],
            "support_scores": [],
        }

    unsupported = []
    scores = []

    for claim in claims:
        is_supported, score = check_claim_support(claim, context_docs, lenient_threshold)
        scores.append({"claim": claim[:100], "score": round(score, 2)})

        if not is_supported:
            unsupported.append(claim)

    # Calculate overall hallucination score
    total_claims = len(claims)
    unsupported_count = len(unsupported)
    hallucination_score = unsupported_count / total_claims if total_claims > 0 else 0.0

    # A response is "hallucinated" if >30% of claims are unsupported
    is_hallucinated = hallucination_score > 0.3 and unsupported_count >= 2

    return {
        "is_hallucinated": is_hallucinated,
        "hallucination_score": round(hallucination_score, 2),
        "total_claims": total_claims,
        "unsupported_count": unsupported_count,
        "unsupported_claims": [c[:150] for c in unsupported],
        "support_scores": scores,
    }


# ── Stop Words ────────────────────────────────────────────────────────────────

_STOP_WORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had",
    "her", "was", "one", "our", "out", "has", "his", "how", "its", "may",
    "new", "now", "old", "see", "way", "who", "did", "get", "let", "say",
    "she", "too", "use", "that", "with", "have", "this", "will", "your",
    "from", "they", "been", "said", "each", "make", "like", "than", "them",
    "then", "what", "when", "were", "there", "their", "which", "would",
    "about", "could", "other", "more", "very", "also", "just", "some",
    "into", "over", "such", "after", "well", "only", "most", "any",
}
