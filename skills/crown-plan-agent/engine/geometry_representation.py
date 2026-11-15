"""Validate the declared representation supported by straight-coordinate QA."""
from __future__ import annotations

from math import isfinite


def requires_specialist_geometry(survey: dict) -> bool:
    """Inspect declarations only; absent metadata does not prove simple geometry."""
    for name in ("curves", "parts", "holes"):
        if name in survey and not isinstance(survey[name], list):
            raise ValueError(f"{name} must be a list")
    if "geometry_type" in survey and not isinstance(survey["geometry_type"], str):
        raise ValueError("geometry_type must be a string")
    return (any(survey.get(name) for name in ("curves", "parts", "holes"))
            or survey.get("geometry_type", "STRAIGHT_SINGLE_RING").upper()
            not in ("STRAIGHT_SINGLE_RING", "POLYGON", "LINESTRING"))


def validate_xy_pairs(vertices: object) -> None:
    """Require finite numeric XY pairs without testing closure or geometry."""
    if not isinstance(vertices, list):
        raise ValueError("vertices must be a list")
    for point in vertices:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError("vertices must contain finite numeric XY pairs")
        for value in point:
            if type(value) not in (int, float):
                raise ValueError("vertices must contain finite numeric XY pairs")
            try:
                finite = isfinite(value)
            except OverflowError:
                finite = False
            if not finite:
                raise ValueError("vertices must contain finite numeric XY pairs")
