"""Conservative review ranking for possible annotation leaders.

Suppresses likely table ruling and dimension extension patterns by assigning
review flags, not by deleting underlying PDF evidence or certifying identities.
"""
from __future__ import annotations
from math import atan2, degrees, hypot, isfinite
from leaders import leader_candidates


def rank_leader_candidates(inventory: dict, *, endpoint_radius_points: float = 12.0) -> list[dict]:
    candidates = leader_candidates(inventory, endpoint_radius_points=endpoint_radius_points)
    vectors = inventory.get("vectors", [])
    spans = inventory.get("spans", [])
    output = []
    for candidate in candidates:
        vector = vectors[candidate["vector_index"]]
        coords = vector["endpoints_points"]
        dx, dy = coords[2]-coords[0], coords[3]-coords[1]
        angle = abs(degrees(atan2(dy, dx))) % 180
        span = spans[candidate["span_index"]]
        text = str(span.get("text", ""))
        signals = []
        if 15 <= angle <= 75 or 105 <= angle <= 165:
            signals.append("OBLIQUE_SEGMENT")
        if angle <= 5 or abs(angle-90) <= 5 or angle >= 175:
            signals.append("ORTHOGONAL_SEGMENT_POSSIBLE_RULE_OR_DIMENSION")
        if any(token in text.upper() for token in ("R/W", "C/L", "CAUTION", "DETAIL", "NOTE")):
            signals.append("CALLOUT_LIKE_TEXT")
        if any(token in text.upper() for token in ("SCALE", "LEGEND", "TABLE")):
            signals.append("LAYOUT_TEXT_POSSIBLE")
        output.append({**candidate, "evidence_signals": signals,
                       "review_priority": "LOW" if "LAYOUT_TEXT_POSSIBLE" in signals else (
                           "ELEVATED" if "OBLIQUE_SEGMENT" in signals and "CALLOUT_LIKE_TEXT" in signals else "NORMAL"),
                       "status": "REVIEW_REQUIRED",
                       "interpretation": "LEADER_HEURISTIC_ONLY"})
    return output
