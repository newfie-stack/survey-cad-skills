"""Bounded literal extracted-span differences, without edit or sheet pairing.

Whitespace is the only normalized content. Span splitting/merging can therefore
produce inventory differences requiring review; no graphical or semantic change
is inferred. Invalid source provenance leaves the raw occurrence unlocated.
"""
from __future__ import annotations

from math import isfinite

MAX_PAGES = 100
MAX_SPANS = 200000
MAX_TEXT_GROUPS = 20000
MAX_CHANGED_GROUPS = 10000
MAX_TEXT_LENGTH = 8192
FRAME = "UNROTATED_CROP_RELATIVE_PDF_POINTS"


def _numbers(value: object, length: int) -> list[float] | None:
    if (not isinstance(value, (list, tuple)) or len(value) != length
            or any(type(number) not in (int, float) for number in value)):
        return None
    try:
        numbers = [float(number) for number in value]
    except (ValueError, OverflowError):
        return None
    return numbers if all(isfinite(number) for number in numbers) else None


def _occurrence(span: dict, pages: int, frame: object) -> dict:
    page = span.get("page")
    page = page if type(page) is int and 1 <= page <= pages else None
    result = {"raw_text": span["text"], "page": page,
              "bbox_points": None, "page_size_points": None,
              "text_angle_degrees": None, "location_reason": "INVALID_SOURCE_BOUNDS"}
    if page is None:
        result["location_reason"] = "INVALID_SOURCE_PAGE"
        return result
    if frame != FRAME or span.get("coordinate_frame", FRAME) != FRAME:
        result["location_reason"] = "UNKNOWN_COORDINATE_FRAME"
        return result
    box = _numbers(span.get("bbox_points"), 4)
    size = _numbers(span.get("page_size_points"), 2)
    if (box is None or size is None or min(size) <= 0
            or not 0 <= box[0] < box[2] <= size[0]
            or not 0 <= box[1] < box[3] <= size[1]):
        return result
    angle = span.get("text_angle_degrees")
    if angle is not None:
        angles = _numbers([angle], 1)
        if angles is None:
            result["location_reason"] = "INVALID_SOURCE_ORIENTATION"
            return result
        angle = angles[0]
    result.update(bbox_points=box, page_size_points=size, text_angle_degrees=angle,
                  location_reason="VALID_SOURCE_LOCATION" if angle is not None
                  else "SOURCE_ORIENTATION_UNKNOWN")
    return result


def _groups(inventory: dict) -> dict[str, list[dict]]:
    if not isinstance(inventory, dict):
        raise TypeError("Source inventory must be an object")
    pages, spans = inventory.get("pages"), inventory.get("spans")
    if type(pages) is not int or not 1 <= pages <= MAX_PAGES:
        raise ValueError("Source page count must be from 1 through 100")
    if not isinstance(spans, list):
        raise ValueError("Source spans must be a list")
    if len(spans) > MAX_SPANS:
        raise ValueError("Span count limit exceeded")
    groups = {}
    frame = inventory.get("coordinate_frame", FRAME)
    for span in spans:
        if not isinstance(span, dict) or not isinstance(span.get("text"), str):
            raise ValueError("Source span must contain literal text")
        raw_text = span["text"]
        # Bound the raw input before split/join allocate normalized copies.
        if len(raw_text) > MAX_TEXT_LENGTH:
            raise ValueError("Text field length limit exceeded")
        normalized = " ".join(raw_text.split())
        if not normalized:
            raise ValueError("Source span text must be nonempty")
        if normalized not in groups:
            # Check before allocating the next group or occurrence collection.
            if len(groups) >= MAX_TEXT_GROUPS:
                raise ValueError("Group count limit exceeded")
            groups[normalized] = []
        groups[normalized].append(_occurrence(span, pages, frame))
    return groups


def _occurrence_order(item: dict) -> tuple:
    """Order actual occurrences without pairing them across source documents."""
    box, size, angle, page = (item["bbox_points"], item["page_size_points"],
                             item["text_angle_degrees"], item["page"])
    return (page is None, page or 0, box is None, tuple(box or ()),
            tuple(size or ()), angle is None, angle or 0,
            item["raw_text"], item["location_reason"])


def compare_text_inventories(baseline: dict, revised: dict) -> list[dict]:
    """Return deterministic changed literal groups with every raw occurrence.

    Counts are multisets over normalized extractor spans across the entire PDF;
    movement, extraction order and sheet order alone do not create text changes.
    Limits reject explicitly, rather than returning a partial comparison.
    Location fields are copied validated PDF points or null with a reason.
    """
    before, after = _groups(baseline), _groups(revised)
    changed = []

    def retain(text: str) -> None:
        if len(changed) >= MAX_CHANGED_GROUPS:
            raise ValueError("Changed group count limit exceeded")
        changed.append(text)

    # Do not first allocate an unbounded union or a complete list of changes.
    for text, occurrences in before.items():
        if len(occurrences) != len(after.get(text, ())):
            retain(text)
    for text in after:
        if text not in before:
            retain(text)

    result = []
    for index, text in enumerate(sorted(changed), 1):
        baseline_occurrences = sorted(before.get(text, ()), key=_occurrence_order)
        revised_occurrences = sorted(after.get(text, ()), key=_occurrence_order)
        before_count, after_count = len(baseline_occurrences), len(revised_occurrences)
        status = "ADDED" if not before_count else "REMOVED" if not after_count else "COUNT_CHANGED"
        result.append({"change_id": f"T{index:05d}", "normalized_text": text,
                       "change_status": status, "before_count": before_count,
                       "after_count": after_count,
                       "baseline_occurrences": baseline_occurrences,
                       "revised_occurrences": revised_occurrences})
    return result
