"""Locate a total area in a split PDF measurement header."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
import re


NUMBER = re.compile(r"[0-9]+(?:\.[0-9]+)?")
AREA_HECTARES = r"([0-9]+(?:\.[0-9]+)?)\s*ha"
TOTAL_AREA_PREFIX = r"total\s+(?:activity\s+)?area\s*[:=]?\s*"
TOTAL_AREA = re.compile(TOTAL_AREA_PREFIX + AREA_HECTARES, re.IGNORECASE)


def center(span: dict) -> tuple[float, float]:
    left, top, right, bottom = span["bbox_points"]
    return (left + right) / 2, (top + bottom) / 2


def total_area_cells(spans: list[dict]) -> list[tuple[Decimal, dict]]:
    """Use a Total header over adjacent hectare and acre columns on one page."""
    pages = defaultdict(list)
    for span in spans:
        if span.get("bbox_points") and isinstance(span.get("text"), str):
            pages[span.get("page")].append(span)
    candidates = []
    for page_spans in pages.values():
        units = {"ha": [], "ac": []}
        headings = []
        values = []
        for span in page_spans:
            label = span["text"].strip().casefold().rstrip(".:")
            if label in units:
                units[label].append(span)
            elif label in ("total", "total area"):
                headings.append(span)
            elif NUMBER.fullmatch(span["text"].strip()):
                values.append(span)
        for hectare in units["ha"]:
            hx, hy = center(hectare)
            box = hectare["bbox_points"]
            height = box[3] - box[1]
            for acre in units["ac"]:
                ax, ay = center(acre)
                width = ax - hx
                if not (height <= width <= 7 * height and abs(ay - hy) <= height / 2):
                    continue
                if not any(hy - 2.5 * height <= ty <= hy - height / 2
                           and abs(tx - (hx + ax) / 2) <= width / 4
                           for tx, ty in map(center, headings)):
                    continue
                hectare_values = []
                acre_rows = []
                for value in values:
                    x, y = center(value)
                    if not hy + height / 2 <= y <= hy + 4 * height:
                        continue
                    if abs(x - hx) <= width / 4:
                        hectare_values.append((value, y))
                    if abs(x - ax) <= width / 4:
                        acre_rows.append(y)
                # Require a paired first row. Additional aligned values make
                # the table ambiguous even when an acre cell is missing.
                if not any(y <= hy + 2.5 * height
                           and any(abs(y - other) <= height / 2 for other in acre_rows)
                           for _, y in hectare_values):
                    continue
                for value, _ in hectare_values:
                    number = value["text"].strip()
                    candidates.append((Decimal(number),
                                       {**value, "cell_text": number,
                                        "text": f"{number} ha (Total column)"}))
    return candidates


def total_area_evidence(spans: list[dict]) -> tuple[list[dict], str | None]:
    """Share document-wide total-area ambiguity between review sections."""
    candidates = []
    for span in spans:
        text = span.get("text")
        match = TOTAL_AREA.fullmatch(text.strip()) if isinstance(text, str) else None
        if match:
            candidates.append((Decimal(match[1]), span))
    cells = total_area_cells(spans)
    candidates.extend(cells)
    ambiguity = None
    if len({value for value, _ in candidates}) > 1:
        ambiguity = "Conflicting total area values found. Confirm the activity total."
    elif len(cells) > 1:
        ambiguity = "Multiple table cells match the total area. Confirm the activity total."
    return [span for _, span in candidates], ambiguity
