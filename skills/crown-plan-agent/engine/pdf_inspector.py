"""Read-only PDF text/position inventory for Crown plan review.

This adapter inventories text spans and pages; it does not infer missing graphical
symbols, certify survey geometry, or decide regulatory compliance.
Requires the reviewed PDF runtime from requirements.txt; runtime policy is
checked before native parsing.
"""
from __future__ import annotations

import json
from math import atan2, degrees, hypot, isfinite
from pathlib import Path
from typing import Any
from curves import curve_candidates
from pdf_source import read_pdf_snapshot
from runtime_security import load_pdf_runtime


def normalize_span(span: dict, page_index: int, page_width: float, page_height: float, direction=(1, 0)) -> dict:
    """Bound a visible text box; retain the extracted box if an edge is clipped."""
    text = str(span.get("text", "")).strip()
    bbox = span.get("bbox")
    if not text or not isinstance(bbox, (tuple, list)) or len(bbox) != 4:
        raise ValueError("Nonempty span text and four bbox coordinates required")
    box = [float(v) for v in bbox]
    if not all(isfinite(v) and v > 0 for v in (page_width, page_height)):
        raise ValueError("Invalid page dimensions")
    if not all(isfinite(v) for v in box) or box[0] > box[2] or box[1] > box[3]:
        raise ValueError("Invalid bounding box")
    visible_box = [max(0.0, box[0]), max(0.0, box[1]),
                   min(page_width, box[2]), min(page_height, box[3])]
    if visible_box[0] >= visible_box[2] or visible_box[1] >= visible_box[3]:
        raise ValueError("Invalid or out-of-page bounding box")
    if not isinstance(direction, (tuple, list)) or len(direction) != 2:
        raise ValueError("Invalid text direction")
    dx, dy = (float(v) for v in direction)
    if not all(isfinite(v) for v in (dx, dy)) or hypot(dx, dy) < 1e-12:
        raise ValueError("Invalid text direction")
    angle = degrees(atan2(dy, dx))
    result = {"page": page_index + 1, "text": text, "bbox_points": visible_box,
              "page_size_points": [float(page_width), float(page_height)],
              "text_angle_degrees": round(angle, 4),
              "text_direction": [dx, dy]}
    if visible_box != box:
        result["original_bbox_points"] = box
    return result


def extract_pdf(path: str | Path, max_pages: int = 100, max_spans: int = 200000,
                max_file_bytes: int = 100_000_000, *,
                include_vectors: bool = True) -> dict[str, Any]:
    if any(type(v) is not int or v < 1 for v in (max_pages, max_spans, max_file_bytes)):
        raise ValueError("Limits must be positive integers")
    source = Path(path)
    source_bytes, source_sha256 = read_pdf_snapshot(source, max_file_bytes=max_file_bytes)
    fitz = load_pdf_runtime()
    spans = []
    vectors = []
    curves = []
    with fitz.open(stream=source_bytes, filetype="pdf") as doc:
        if doc.needs_pass:
            raise ValueError("Encrypted PDF not supported")
        if doc.page_count > max_pages:
            raise ValueError("Page limit exceeded")
        for index, page in enumerate(doc):
            # Text, drawings and directions use unrotated CropBox-relative points.
            # Derotate page.rect's size so rotation and PDF UserUnit stay consistent.
            bounds = page.rect * page.derotation_matrix
            page_width, page_height = bounds.width, bounds.height
            raw = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES)
            for block in raw.get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if not str(span.get("text", "")).strip():
                            continue
                        item = normalize_span(span, index, page_width, page_height,
                                              line.get('dir', (1, 0)))
                        item["text_writing_mode"] = line.get("wmode", 0)
                        item["page_rotation_degrees"] = page.rotation
                        item["display_angle_degrees"] = round(
                            (item["text_angle_degrees"] + page.rotation + 180) % 360 - 180, 4)
                        origin = span.get("origin")
                        if (isinstance(origin, (tuple, list)) and len(origin) == 2
                                and all(isinstance(v, (int, float)) and isfinite(v) for v in origin)):
                            item["text_origin_points"] = list(origin)
                        for source_key, target_key in (("ascender", "font_ascender"),
                                                       ("descender", "font_descender")):
                            value = span.get(source_key)
                            if isinstance(value, (int, float)) and isfinite(value):
                                item[target_key] = value
                        try:
                            quad = fitz.recover_quad(line.get("dir", (1, 0)), span)
                            points = [[float(p.x), float(p.y)] for p in quad]
                            if all(isfinite(v) for p in points for v in p):
                                item["quad_points"] = points
                        except (ValueError, TypeError, ZeroDivisionError):
                            # Retain the native words/evidence when geometry is
                            # unsupported; the directional reader will abstain.
                            pass
                        spans.append(item)
                        if len(spans) > max_spans:
                            raise ValueError("Text span limit exceeded")
            if not include_vectors:
                continue
            page_curves = curve_candidates(page, index + 1, max_curves=max_spans)
            if len(page_curves) > max_spans - len(curves):
                raise ValueError("Curve limit exceeded")
            curves.extend(page_curves)
            if len(curves) > max_spans:
                raise ValueError('Curve limit exceeded')
            for drawing in page.get_drawings():
                for item in drawing.get("items", []):
                    kind = item[0]
                    if kind != "l":
                        continue  # curves and rectangles are not converted to legal segments
                    start, end = item[1], item[2]
                    coords = [float(start.x), float(start.y), float(end.x), float(end.y)]
                    if not all(isfinite(v) for v in coords):
                        continue
                    vectors.append({"page": index + 1, "type": "PDF_LINE",
                                    "endpoints_points": coords,
                                    "stroke_width_points": float(drawing.get("width") or 0),
                                    "role": "UNCLASSIFIED_GRAPHIC"})
                    if len(vectors) > max_spans:
                        raise ValueError("Vector line limit exceeded")
        return {"source_filename": source.name, "source_sha256": source_sha256, "pages": doc.page_count,
                "spans": spans, "vectors": vectors, "curves": curves,
                "status": "TEXT_AND_VECTOR_INVENTORY_ONLY" if include_vectors else "TEXT_INVENTORY_ONLY",
                "limitations": ["PDF coordinates are page points, not survey coordinates",
                                "No line-to-label association", "Bezier curves are not cadastral arcs", "No graphical symbol recognition",
                                "No legal geometry verification", "No regulatory compliance determination"]}


def write_inventory(inventory: dict, output: str | Path) -> None:
    destination = Path(output)
    with destination.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(inventory, indent=2, ensure_ascii=False) + "\n")
