"""Order native text in its own direction, retaining original page evidence.

Reading frames are temporary PDF-page geometry, never survey coordinates.
They neither recognize outlined/raster lettering nor establish text completeness.
"""
from __future__ import annotations

from math import hypot, isfinite


def _union(a, b):
    return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]


def _coherent_quad(span, quad, direction):
    """Reject recovered oblique quads inconsistent with the native baseline.

    PyMuPDF derives the quad from font metrics. Nonuniform affine fonts can
    invalidate that derivation, even when the edges look parallel at 45 degrees.
    The independently extracted native origin anchors the baseline.
    """
    dx, dy = direction
    upper = [quad[1][i] - quad[0][i] for i in (0, 1)]
    side = [quad[2][i] - quad[0][i] for i in (0, 1)]
    width, height = hypot(*upper), hypot(*side)
    if width < 1e-12 or height < 1e-12:
        return False
    ux, uy = (v / width for v in upper)
    sx, sy = (v / height for v in side)
    if (ux * dx + uy * dy <= 0 or abs(ux * dy - uy * dx) > 1e-4
            or -sx * dy + sy * dx <= 0 or abs(sx * dx + sy * dy) > 1e-4):
        return False
    origin = span.get("text_origin_points")
    ascender, descender = span.get("font_ascender"), span.get("font_descender")
    if (not isinstance(origin, (list, tuple)) or len(origin) != 2
            or not all(isinstance(v, (int, float)) and isfinite(v)
                       for v in (*origin, ascender, descender))
            or ascender <= descender):
        return False
    fraction = ascender / (ascender - descender)
    if not 0 <= fraction <= 1:
        return False
    rounding = max(1e-5, max(abs(v) for p in quad for v in p) * 2e-7)
    tolerance = max(rounding * 4, height * 0.001)
    if tolerance > height * 0.02:
        return False  # Coordinates too coarse to establish this text height.
    predicted = [quad[0][i] + side[i] * fraction for i in (0, 1)]
    closure = [quad[1][i] + side[i] for i in (0, 1)]
    return (hypot(*(predicted[i] - origin[i] for i in (0, 1))) <= tolerance
            and hypot(*(closure[i] - quad[3][i] for i in (0, 1))) <= tolerance)


def _geometry(span):
    direction = span.get("text_direction", (1, 0))
    if (not isinstance(direction, (list, tuple)) or len(direction) != 2
            or not all(isinstance(v, (int, float)) and isfinite(v) for v in direction)):
        return None
    length = hypot(*direction)
    if length < 1e-12 or span.get("text_writing_mode", 0) != 0:
        return None
    dx, dy = (v / length for v in direction)
    if min(abs(dx), abs(dy)) <= 1e-7:
        # Cardinal AABBs retain true height, including nonuniform font scaling.
        x0, y0, x1, y1 = span["bbox_points"]
        quad = [[x0, y0], [x1, y0], [x0, y1], [x1, y1]]
        return (dx, dy), quad
    quad = span.get("quad_points")
    if (not isinstance(quad, (list, tuple)) or len(quad) != 4
            or any(not isinstance(p, (list, tuple)) or len(p) != 2
                   or not all(isinstance(v, (int, float)) and isfinite(v) for v in p)
                   for p in quad)):
        return None
    if not _coherent_quad(span, quad, (dx, dy)):
        return None
    return (dx, dy), quad


def _reading_box(points, direction):
    dx, dy = direction
    projected = [(x * dx + y * dy, -x * dy + y * dx) for x, y in points]
    return [min(p[0] for p in projected), min(p[1] for p in projected),
            max(p[0] for p in projected), max(p[1] for p in projected)]


def reading_lines(spans: list[dict]) -> tuple[list[dict], list[str]]:
    """Return directional lines plus explicit blockers for unreadable geometry.

    A line has its original page ``box`` and a temporary ``reading_box``.
    Independent/opposite directions have separate ``direction_group`` values.
    """
    groups = []
    blockers = []
    for span in spans:
        geometry = _geometry(span)
        if geometry is None:
            blockers.append("Native text direction/geometry needs a separate visual reading")
            continue
        direction, points = geometry
        dx, dy = direction
        for group in groups:
            gx, gy = group["direction"]
            # Full directed baselines: opposite text is never the same flow.
            if gx * dx + gy * dy > 0 and abs(gx * dy - gy * dx) <= 1e-4:
                break
        else:
            group = {"direction": direction, "spans": []}
            groups.append(group)
        if direction == (1.0, 0.0) and group["direction"] == direction:
            # Preserve established horizontal-font bounding behavior exactly.
            box = list(span["bbox_points"])
        else:
            box = _reading_box(points, group["direction"])
        if box[0] >= box[2] or box[1] >= box[3]:
            blockers.append("Native text direction/geometry needs a separate visual reading")
            continue
        group["spans"].append({"source": span, "box": box})

    lines = []
    for group_index, group in enumerate(groups):
        rows = []
        for item in sorted(group["spans"], key=lambda s: (s["box"][1], s["box"][0])):
            box = item["box"]
            centre = (box[1] + box[3]) / 2
            height = box[3] - box[1]
            if rows and abs(rows[-1]["centre"] - centre) <= max(height, rows[-1]["height"]) * 0.3:
                rows[-1]["spans"].append(item)
            else:
                rows.append({"centre": centre, "height": height, "spans": [item]})
        for row in rows:
            current = None
            for item in sorted(row["spans"], key=lambda s: s["box"][0]):
                source, box = item["source"], item["box"]
                gap = box[0] - current["reading_box"][2] if current else float("inf")
                if current and -0.5 <= gap <= row["height"] * 2.5:
                    current["text"] += " " + source["text"]
                    current["reading_box"] = _union(current["reading_box"], box)
                    current["box"] = _union(current["box"], source["bbox_points"])
                else:
                    current = {"text": source["text"], "reading_box": list(box),
                               "box": list(source["bbox_points"]),
                               "direction_group": group_index}
                    lines.append(current)
    return lines, list(dict.fromkeys(blockers))
