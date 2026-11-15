"""Conservative PDF text-to-vector candidate association.

Page-point proximity produces review candidates, never legal feature identity.
Does not mutate source inventory or assign survey coordinates.
"""
from __future__ import annotations
from math import hypot, isfinite


def _distance_point_to_segment(point, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    if length2 <= 0:
        return hypot(point[0] - a[0], point[1] - a[1])
    t = max(0.0, min(1.0, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / length2))
    return hypot(point[0] - (a[0] + t * dx), point[1] - (a[1] + t * dy))


def associate_labels(inventory: dict, max_distance_points: float = 18.0, max_candidates: int = 3) -> list[dict]:
    """Return nearest same-page PDF line candidates for each text span.

    Each candidate is explicitly REVIEW_REQUIRED. A close label may refer to
    another line, detail, table, dimension, or feature.
    """
    if not isfinite(max_distance_points) or max_distance_points <= 0:
        raise ValueError("max_distance_points must be positive and finite")
    if not isinstance(max_candidates, int) or isinstance(max_candidates, bool) or max_candidates < 1:
        raise ValueError("max_candidates must be a positive integer")
    vectors_by_page: dict[int, list] = {}
    for index, vector in enumerate(inventory.get("vectors", [])):
        if vector.get("type") != "PDF_LINE" or vector.get("role") != "UNCLASSIFIED_GRAPHIC":
            continue
        coords = vector.get("endpoints_points")
        if not isinstance(coords, list) or len(coords) != 4 or not all(isinstance(v, (int, float)) and isfinite(v) for v in coords):
            continue
        vectors_by_page.setdefault(vector.get("page"), []).append((index, coords))
    results = []
    for index, span in enumerate(inventory.get("spans", [])):
        bbox = span.get("bbox_points")
        if not isinstance(bbox, list) or len(bbox) != 4 or not all(isinstance(v, (int, float)) and isfinite(v) for v in bbox):
            continue
        point = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
        ranked = []
        for vector_index, coords in vectors_by_page.get(span.get("page"), []):
            distance = _distance_point_to_segment(point, coords[:2], coords[2:])
            if distance <= max_distance_points:
                ranked.append((distance, vector_index))
        ranked.sort(key=lambda item: (item[0], item[1]))
        results.append({"span_index": index, "page": span.get("page"),
                        "text": span.get("text"), "status": "REVIEW_REQUIRED",
                        "candidate_lines": [{"vector_index": i, "distance_points": round(d, 4)}
                                            for d, i in ranked[:max_candidates]],
                        "basis": "NEAREST_PDF_PAGE_GEOMETRY_ONLY"})
    return results
