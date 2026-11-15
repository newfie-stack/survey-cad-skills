"""Inventory PDF Bezier curves as unclassified graphics.

No curve is interpreted as a cadastral arc or surveyed geometry. PDF page
coordinates are not ground coordinates.
"""
from __future__ import annotations
from math import isfinite


def curve_candidates(page, page_number: int, max_curves: int = 200000) -> list[dict]:
    """Extract cubic Bezier control points from a PyMuPDF page."""
    if max_curves < 1:
        raise ValueError("max_curves must be positive")
    results = []
    for drawing in page.get_drawings():
        for item in drawing.get("items", []):
            if not item or item[0] != "c":
                continue
            if len(item) != 5:
                continue
            coords = []
            for point in item[1:]:
                coords.extend((float(point.x), float(point.y)))
            if not all(isfinite(value) for value in coords):
                continue
            results.append({"page": page_number, "type": "PDF_CUBIC_BEZIER",
                            "control_points_points": coords,
                            "role": "UNCLASSIFIED_GRAPHIC",
                            "status": "REVIEW_REQUIRED"})
            if len(results) > max_curves:
                raise ValueError("Curve limit exceeded")
    return results
