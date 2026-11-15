"""Survey traverse closure diagnostics for explicitly supplied projected coordinates.

Inputs are ordered vertices in a verified projected metric CRS. This module
does not infer CRS, survey accuracy class, or regulatory acceptance.
"""
from __future__ import annotations
from decimal import Decimal, localcontext
from math import atan2, degrees, hypot, isfinite


def traverse_closure(vertices, *, crs_verified=False, tolerance_m=None):
    if type(crs_verified) is not bool:
        raise ValueError("crs_verified must be boolean")
    if not isinstance(vertices, (list, tuple)) or len(vertices) < 3:
        raise ValueError("At least three ordered vertices required")
    points = []
    for value in vertices:
        if not isinstance(value, (tuple, list)) or len(value) != 2:
            raise ValueError("Each vertex must contain x and y")
        x, y = (float(v) for v in value)
        if not isfinite(x) or not isfinite(y):
            raise ValueError("Coordinates must be finite")
        points.append((x, y))
    if tolerance_m is not None:
        if type(tolerance_m) not in (float, int) or not isfinite(tolerance_m) or tolerance_m < 0:
            raise ValueError("Tolerance must be finite and nonnegative")
    segment_lengths = [hypot(b[0]-a[0], b[1]-a[1])
                       for a, b in zip(points, points[1:])]
    if any(length == 0 for length in segment_lengths):
        raise ValueError("Zero-length traverse leg")
    # Preserve supplied decimal coordinates through subtraction, including
    # displayed closure measurements at large projected coordinate offsets.
    endpoints = [tuple(Decimal(str(int(v) if isinstance(v, bool) else v))
                       for v in point)
                 for point in (vertices[0], vertices[-1])]
    tolerance = Decimal(str(tolerance_m)) if tolerance_m is not None else None
    values = [v for point in endpoints for v in point]
    if tolerance is not None:
        values.append(tolerance)
    places = max(0, -min(v.as_tuple().exponent for v in values))
    digits = max(0, max(v.adjusted() for v in values)) + places + 2
    within_tolerance = None
    with localcontext() as context:
        context.prec = max(28, 2 * digits + 8)
        exact_dx = endpoints[-1][0] - endpoints[0][0]
        exact_dy = endpoints[-1][1] - endpoints[0][1]
        if tolerance is not None:
            # Exact squares avoid sqrt rounding at the inclusive boundary.
            within_tolerance = (exact_dx * exact_dx + exact_dy * exact_dy
                                <= tolerance * tolerance)
    dx, dy = float(exact_dx), float(exact_dy)
    misclosure = hypot(dx, dy)
    travelled = sum(segment_lengths)
    # Closure ratio is only meaningful for nonzero misclosure.
    ratio = travelled / misclosure if misclosure else None
    return {
        "misclosure_m": misclosure,
        "delta_easting_m": dx,
        "delta_northing_m": dy,
        "travelled_distance_m": travelled,
        "closure_ratio_denominator": ratio,
        "closure_direction_degrees_from_east": degrees(atan2(dy, dx)) if misclosure else None,
        "within_supplied_tolerance": within_tolerance,
        "crs_status": "VERIFIED" if crs_verified else "REVIEW_REQUIRED",
        "status": "REVIEW_REQUIRED",
        "limitations": ["Not a survey adjustment", "No regulatory tolerance inferred",
                        "Coordinates must be in a verified projected metric CRS"],
    }
