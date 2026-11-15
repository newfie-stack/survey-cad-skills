"""Conservative PDF leader-like geometry candidates.

A leader-like segment is a short PDF line with one endpoint near text.
This is a visual review heuristic, not a CAD leader entity classifier.
"""
from __future__ import annotations
from math import hypot, isfinite


def leader_candidates(inventory: dict, *, endpoint_radius_points: float = 12.0,
                      min_length_points: float = 5.0,
                      max_length_points: float = 150.0) -> list[dict]:
    limits = (endpoint_radius_points, min_length_points, max_length_points)
    if not all(isfinite(x) and x > 0 for x in limits) or min_length_points > max_length_points:
        raise ValueError("Invalid leader candidate limits")
    results = []
    for span_index, span in enumerate(inventory.get("spans", [])):
        bbox = span.get("bbox_points")
        if not isinstance(bbox, list) or len(bbox) != 4:
            continue
        if not all(isinstance(v, (int, float)) and isfinite(v) for v in bbox):
            continue
        cx, cy = (bbox[0] + bbox[2])/2, (bbox[1] + bbox[3])/2
        for vector_index, vector in enumerate(inventory.get("vectors", [])):
            if vector.get("page") != span.get("page") or vector.get("type") != "PDF_LINE":
                continue
            coords = vector.get("endpoints_points")
            if not isinstance(coords, list) or len(coords) != 4:
                continue
            if not all(isinstance(v, (int, float)) and isfinite(v) for v in coords):
                continue
            a, b = coords[:2], coords[2:]
            length = hypot(b[0]-a[0], b[1]-a[1])
            if not min_length_points <= length <= max_length_points:
                continue
            d_a, d_b = hypot(a[0]-cx, a[1]-cy), hypot(b[0]-cx, b[1]-cy)
            if min(d_a, d_b) > endpoint_radius_points:
                continue
            results.append({
                "page": span["page"], "span_index": span_index,
                "vector_index": vector_index,
                "text_near_endpoint": "START" if d_a <= d_b else "END",
                "distance_points": round(min(d_a, d_b), 4),
                "length_points": round(length, 4),
                "status": "REVIEW_REQUIRED",
                "interpretation": "POSSIBLE_LEADER_NOT_VERIFIED",
            })
    return results
