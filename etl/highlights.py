"""Generate skeptical, buyer-focused highlights from listing descriptions."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class HighlightResult:
    """Result of highlight extraction."""

    highlights: list[str]


_BOILERPLATE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(must\s*see|won['’]?t\s*last|priced\s*to\s*sell)\b", re.I),
    re.compile(
        r"\b(luxury|luxurious|stunning|gorgeous|breathtaking|impeccable)\b", re.I
    ),
    re.compile(r"\b(!!+|\*\*+|\bWOW\b)\b", re.I),
]


_FEATURE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(pool|screened\s+pool|salt\s*water\s+pool)\b", re.I), "Pool"),
    (re.compile(r"\b(new|recent)\s+(roof)\b", re.I), "Recent roof"),
    (
        re.compile(r"\b(HVAC|A/C|AC)\b|\bnew\s+air\s+condition", re.I),
        "HVAC / A/C mention",
    ),
    (
        re.compile(r"\b(updated\s+kitchen|remodeled\s+kitchen|quartz|granite)\b", re.I),
        "Kitchen updates mentioned",
    ),
    (re.compile(r"\b(stainless\s+steel)\b", re.I), "Stainless appliances mentioned"),
    (
        re.compile(r"\b(open\s+concept|open\s+floor\s+plan)\b", re.I),
        "Open layout (marketing term)",
    ),
    (re.compile(r"\b(walk[-\s]?in\s+closet)\b", re.I), "Walk-in closet"),
    (re.compile(r"\b(hoa)\b", re.I), "HOA mentioned (check rules/fees)"),
    (re.compile(r"\b(no\s+hoa)\b", re.I), "No HOA (verify)"),
    (re.compile(r"\b(gated)\b", re.I), "Gated community (verify fees)"),
    (re.compile(r"\b(solar)\b", re.I), "Solar mentioned (ask lease vs owned)"),
    (re.compile(r"\b(flood\s+zone|flooding)\b", re.I), "Flood risk mentioned"),
    (
        re.compile(r"\b(short\s*term\s*rental|airbnb)\b", re.I),
        "Short-term rental angle (verify zoning/HOA)",
    ),
]


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def distill_highlights(description: str, *, max_items: int = 6) -> HighlightResult:
    """Extract buyer-relevant highlights from marketing descriptions.

    Heuristics-based and intentionally skeptical:
    - Prefer concrete, checkable claims.
    - Label vague marketing terms as such.
    - Flag risk/unknowns (HOA, flood, solar lease, etc.).
    """

    cleaned = _normalize_whitespace(description)
    if not cleaned:
        return HighlightResult(highlights=[])

    highlights: list[str] = []

    for pattern in _BOILERPLATE_PATTERNS:
        if pattern.search(cleaned):
            highlights.append(
                "Heavy marketing language—verify condition with inspection"
            )
            break

    seen: set[str] = set()
    for pattern, label in _FEATURE_PATTERNS:
        if pattern.search(cleaned) and label not in seen:
            highlights.append(label)
            seen.add(label)
        if len(highlights) >= max_items:
            break

    if not highlights:
        # Fallback: extract first sentence fragment as a neutral summary.
        first = re.split(r"(?<=[.!?])\s+", cleaned, maxsplit=1)[0]
        if len(first) > 160:
            first = first[:157].rstrip() + "..."
        highlights.append(first)

    return HighlightResult(highlights=highlights[:max_items])
