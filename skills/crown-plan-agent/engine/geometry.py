"""Deterministic planar geometry checks for survey QA.

Coordinates must already be in a verified projected metric CRS. This module
never transforms coordinates or declares regulatory compliance.
"""
from __future__ import annotations
from decimal import Decimal, localcontext
from math import hypot, isfinite


def _point(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("Each point must have two coordinates")
    x, y = (float(v) for v in value)
    if not isfinite(x) or not isfinite(y):
        raise ValueError("Coordinates must be finite")
    return (x, y)


def _orientation(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def _on_segment(a, b, p, epsilon=1e-9):
    """Whether p lies on the closed segment a-b."""
    return (abs(_orientation(a, b, p)) <= epsilon
            and min(a[0], b[0])-epsilon <= p[0] <= max(a[0], b[0])+epsilon
            and min(a[1], b[1])-epsilon <= p[1] <= max(a[1], b[1])+epsilon)


def _intersects(a, b, c, d, epsilon=1e-9):
    """Includes proper intersections, touching, and collinear overlaps."""
    o1, o2 = _orientation(a,b,c), _orientation(a,b,d)
    o3, o4 = _orientation(c,d,a), _orientation(c,d,b)
    if ((o1 > epsilon and o2 < -epsilon or o1 < -epsilon and o2 > epsilon)
            and (o3 > epsilon and o4 < -epsilon or o3 < -epsilon and o4 > epsilon)):
        return True
    return any((abs(o) <= epsilon and _on_segment(u,v,p,epsilon))
               for o,u,v,p in ((o1,a,b,c),(o2,a,b,d),(o3,c,d,a),(o4,c,d,b)))


def check_polygon(vertices, *, crs_verified=False):
    """Return planar measurements, gated on verified CRS.

    Closed rings required; nonadjacent intersections and overlaps rejected.
    Does not validate holes, multipart geometry or curved boundaries.
    """
    vertices = list(vertices)
    points = [_point(p) for p in vertices]
    if len(points) < 4 or points[0] != points[-1]:
        raise ValueError("Polygon must be a closed ring of at least three vertices")
    edges = list(zip(points, points[1:]))
    if any(a == b for a,b in edges):
        raise ValueError("Zero-length edge")
    # Adjacent edges may share their endpoint, but may not backtrack
    # over the same segment (a degenerate ring boundary).
    for i in range(len(edges)):
        a, b = edges[i]
        _, c = edges[(i+1) % len(edges)]
        ux, uy = b[0]-a[0], b[1]-a[1]
        vx, vy = c[0]-b[0], c[1]-b[1]
        if abs(ux*vy-uy*vx) <= 1e-9 and ux*vx+uy*vy < 0:
            raise ValueError("Overlapping adjacent edges")
    for i, (a,b) in enumerate(edges):
        for j, (c,d) in enumerate(edges):
            if j <= i+1 or (i == 0 and j == len(edges)-1):
                continue
            if _intersects(a,b,c,d):
                raise ValueError("Self-intersecting polygon")
    # Preserve the supplied base-10 coordinate precision through subtraction
    # and shoelace products. Translating floats alone still introduces error
    # at projected offsets, which can flip an inclusive tolerance comparison.
    decimals = [tuple(Decimal(str(int(v) if isinstance(v, bool) else v)) for v in p)
                for p in vertices]
    coordinates = [v for point in decimals for v in point]
    places = max(0, -min(v.as_tuple().exponent for v in coordinates))
    digits = max(0, max(v.adjusted() for v in coordinates)) + places + 2
    with localcontext() as context:
        # Enough digits for exact differences/products, summation and /20000.
        context.prec = max(28, 2 * digits + len(str(len(points))) + 8)
        origin_x, origin_y = decimals[0]
        twice_area = sum((a[0]-origin_x)*(b[1]-origin_y)
                         - (b[0]-origin_x)*(a[1]-origin_y)
                         for a, b in zip(decimals, decimals[1:]))
        area_m2 = abs(twice_area) / 2
        area_ha = area_m2 / 10000
    if abs(twice_area) < 1e-12:
        raise ValueError("Degenerate polygon")
    perimeter = sum(hypot(b[0]-a[0], b[1]-a[1]) for a,b in edges)
    return {"area_m2": float(area_m2), "area_ha": float(area_ha),
            "area_ha_decimal": str(area_ha),
            "perimeter_m": perimeter,
            "crs_status": "VERIFIED" if crs_verified else "REVIEW_REQUIRED",
            "compliance_status": "REVIEW_REQUIRED"}
