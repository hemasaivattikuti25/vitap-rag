"""
Template-based answer engine — minimal version.
ONLY bypasses LLM for queries that can be answered with certainty from clean data.
Everything else goes to Groq for a proper, coherent answer.
"""

import re
from typing import List, Optional


# Patterns that strongly suggest noisy/footer content
_NOISE_PATTERNS = [
    r"beside ap secretariat",
    r"how to reach vit-?ap",
    r"copyright.*all rights reserved",
    r"quick links.*careers.*hostels",
    r"public self disclosure",
    r"academic bank of credit",
    r"website credits",
    r"viteee-20\d\d",
    r"apply now.*maps",
]


def _is_clean(content: str) -> bool:
    """Return True only if content looks genuinely informative."""
    lower = content.lower()
    # Reject if any noise pattern found
    for pat in _NOISE_PATTERNS:
        if re.search(pat, lower):
            return False
    # Reject if same phrase repeated (footer duplication)
    lines = [l.strip() for l in content.split("\n") if l.strip()]
    if len(lines) >= 3:
        unique = set(lines)
        if len(unique) / len(lines) < 0.6:  # >40% duplicates = noisy
            return False
    return True


def try_template_answer(query: str, docs: List[dict]) -> Optional[str]:
    """
    Bypass Groq LLM only for very specific, verifiable queries.
    Returns None in all other cases — forces Groq to answer.
    """
    # Always pass to Groq — templates caused bad answers with footer noise.
    # The Groq LLM is fast and free enough (14,400/day) to handle all queries.
    return None
