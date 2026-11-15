"""Evidence signals for candidate PDF annotations, never legal identification.

Classifies text phrases into *review hints* and ranks same-page line candidates
by geometry. Ambiguity is preserved; no normative compliance status is produced.
"""
from __future__ import annotations

import re
from associations import associate_labels

# Deliberately generic phrases, not client data or regulatory clauses.
PATTERNS = {
    "RIGHT_OF_WAY_LABEL": re.compile(r"\b(?:R/W|RIGHT\s+OF\s+WAY)\b", re.I),
    "CENTRELINE_LABEL": re.compile(r"\b(?:C/L|CENTRELINE|CENTERLINE)\b", re.I),
    "TIE_LINE_LABEL": re.compile(r"\bTIE\s+LINE\b", re.I),
    "ROAD_LABEL": re.compile(r"\b(?:ROAD|ACCESS)\b", re.I),
}


def review_candidates(inventory: dict, *, radius_points: float = 18.0,
                      ambiguity_margin_points: float = 3.0) -> list[dict]:
    if ambiguity_margin_points < 0:
        raise ValueError("ambiguity margin must be nonnegative")
    proximity = associate_labels(inventory, max_distance_points=radius_points, max_candidates=10)
    output = []
    for record in proximity:
        hints = sorted(name for name, pattern in PATTERNS.items() if pattern.search(record["text"] or ""))
        candidates = record["candidate_lines"]
        ambiguous = len(candidates) > 1 and (
            candidates[1]["distance_points"] - candidates[0]["distance_points"] <= ambiguity_margin_points
        )
        output.append({
            "page": record["page"],
            "span_index": record["span_index"],
            "text": record["text"],
            "semantic_hints": hints,
            "candidate_lines": candidates,
            "ambiguity": "MULTIPLE_NEARBY_LINES" if ambiguous else (
                "NO_NEARBY_LINE" if not candidates else "UNVERIFIED_ASSOCIATION"
            ),
            "status": "REVIEW_REQUIRED",
            "interpretation": "TEXT_HINT_AND_PAGE_PROXIMITY_ONLY",
        })
    return output
