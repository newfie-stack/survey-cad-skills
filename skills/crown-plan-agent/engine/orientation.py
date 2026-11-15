"""Text orientation as an additional PDF association review signal.

Orientation cannot establish legal feature identity; it only ranks candidates.
"""
from __future__ import annotations
from math import atan2, degrees, hypot, isfinite
from associations import associate_labels


def _parallel_difference_degrees(angle_a: float, angle_b: float) -> float:
    return abs((angle_a - angle_b + 90.0) % 180.0 - 90.0)


def orientation_candidates(inventory: dict, *, radius_points: float = 18.0,
                           parallel_tolerance_degrees: float = 12.0) -> list[dict]:
    if not isfinite(parallel_tolerance_degrees) or not 0 <= parallel_tolerance_degrees <= 90:
        raise ValueError("Invalid parallel tolerance")
    proximity = associate_labels(inventory, max_distance_points=radius_points, max_candidates=10)
    spans = inventory.get("spans", [])
    vectors = inventory.get("vectors", [])
    results = []
    for match in proximity:
        span = spans[match["span_index"]]
        angle = span.get("text_angle_degrees")
        valid_angle = isinstance(angle, (int, float)) and not isinstance(angle, bool) and isfinite(angle)
        candidates = []
        for item in match["candidate_lines"]:
            vector = vectors[item["vector_index"]]
            x1, y1, x2, y2 = vector["endpoints_points"]
            if hypot(x2-x1, y2-y1) < 1e-9:
                continue
            line_angle = degrees(atan2(y2-y1, x2-x1))
            delta = _parallel_difference_degrees(float(angle), line_angle) if valid_angle else None
            candidates.append({**item,
                               "angle_difference_degrees": round(delta, 3) if delta is not None else None,
                               "orientation_signal": "PARALLEL_LIKE" if delta is not None and delta <= parallel_tolerance_degrees
                               else ("UNKNOWN_TEXT_DIRECTION" if delta is None else "NONPARALLEL")})
        candidates.sort(key=lambda item: (
            0 if item["orientation_signal"] == "PARALLEL_LIKE" else 1,
            item["distance_points"], item["vector_index"]))
        results.append({"span_index": match["span_index"], "page": match["page"],
                        "text": match["text"], "candidates": candidates,
                        "status": "REVIEW_REQUIRED", "basis": "PROXIMITY_PLUS_ORIENTATION_HEURISTIC"})
    return results
