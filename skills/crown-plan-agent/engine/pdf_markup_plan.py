"""Plan review-only notes with source-bound text locations, never guessed points."""
from __future__ import annotations

from math import isfinite
import re

FRAME = "UNROTATED_CROP_RELATIVE_PDF_POINTS"
MAX_NOTES = 200
MAX_BODY = 4096
MAX_TITLE = 512
MAX_PAGES = 100
MAX_SPANS = 200000
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _text(value: object, label: str, *, limit: int = MAX_BODY,
          default: str | None = None) -> str:
    if value is None and default is not None:
        return default
    if not isinstance(value, str) or len(value) > limit or not value.strip():
        raise ValueError(label + " must be bounded nonempty text")
    if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
        raise ValueError(label + " contains unsupported control characters")
    return value


def _box(value: object) -> tuple[float, float, float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    if any(type(v) not in (int, float) for v in value):
        return None
    try:
        coords = tuple(float(v) for v in value)
    except (ValueError, OverflowError):
        return None
    if (not all(isfinite(v) for v in coords) or coords[0] < 0 or coords[1] < 0
            or coords[0] >= coords[2] or coords[1] >= coords[3]):
        return None
    return coords


def _page(value: object, pages: int) -> int | None:
    return value if type(value) is int and 1 <= value <= pages else None


def _citation(entry: dict) -> dict:
    result = {}
    for key, original in (("title", "publication_title"), ("version", "source_version"),
                          ("section", "section"), ("url", "source_url")):
        value = entry.get(original)
        if key == "version" and value is None:
            value = entry.get("version_date")
        result[key] = None if value is None else _text(value, "Citation " + key)
    page = entry.get("source_page")
    if page is not None and (type(page) is not int or page < 1):
        raise ValueError("Citation page must be a positive reference-publication page")
    result["page"] = page
    if sum(len(v) for v in result.values() if isinstance(v, str)) > MAX_BODY:
        raise ValueError("Combined citation text exceeds its limit")
    return result


def _span_index(spans: list) -> dict:
    result = {}
    for span in spans:
        if not isinstance(span, dict):
            continue
        page, text, box = span.get("page"), span.get("text"), _box(span.get("bbox_points"))
        if type(page) is not int or not isinstance(text, str) or not text.strip() or box is None:
            continue
        result.setdefault((page, box, text), []).append(span)
    return result


def _locate(entry: dict, pages: int, spans: dict) -> tuple[dict | None, str, int | None, bool]:
    page = _page(entry.get("page"), pages)
    status = entry.get("evidence_status")
    if status == "VISUAL_CHECK_REQUIRED":
        return None, "VISUAL_REVIEW_LOCATION_UNKNOWN", page, False
    if status != "OBSERVED_CANDIDATE":
        return None, "NO_SOURCE_LOCATION", page, False
    count = entry.get("candidate_count")
    if type(count) is not int or count != 1:
        reason = "MULTIPLE_CANDIDATES" if type(count) is int and count > 1 else "NO_UNIQUE_CANDIDATE"
        return None, reason, page, False
    box = _box(entry.get("bbox_points"))
    evidence = entry.get("input_evidence")
    if page is None or box is None:
        return None, "INVALID_SOURCE_BOUNDS", page, False
    if not isinstance(evidence, dict):
        return None, "NO_SOURCE_LOCATION", page, False
    if _page(evidence.get("page"), pages) != page or _box(evidence.get("bbox_points")) != box:
        return None, "INCONSISTENT_EVIDENCE_REFERENCE", page, False
    raw_text = evidence.get("source_text", entry.get("observation"))
    if not isinstance(raw_text, str) or not raw_text.strip():
        return None, "NO_SOURCE_TEXT", page, False
    matches = spans.get((page, box, raw_text), [])
    if len(matches) != 1:
        return None, "SOURCE_SPAN_NOT_UNIQUE_OR_NOT_FOUND", page, False
    span = matches[0]
    size = span.get("page_size_points")
    if (not isinstance(size, (list, tuple)) or len(size) != 2
            or any(type(v) not in (int, float) for v in size)):
        return None, "INVALID_SOURCE_BOUNDS", page, False
    try:
        width, height = (float(v) for v in size)
    except (ValueError, OverflowError):
        return None, "INVALID_SOURCE_BOUNDS", page, False
    if not all(isfinite(v) and v > 0 for v in (width, height)) or box[2] > width or box[3] > height:
        return None, "INVALID_SOURCE_BOUNDS", page, False
    clipped = "original_bbox_points" in span
    return {"page": page, "bbox_points": list(box)}, "UNIQUE_SOURCE_SPAN", page, clipped


def build_markup_plan(report: dict, inventory: dict, *, source_sha256: str,
                      max_notes: int = MAX_NOTES) -> dict:
    """Return bounded notes for an independently inspected immutable PDF snapshot.

    The renderer must obtain this inventory from the actual bound source bytes.
    Hash equality binds bytes; it does not authenticate a reviewer or establish
    legal feature identity, source currency, geometry or compliance.
    """
    if type(max_notes) is not int or not 1 <= max_notes <= MAX_NOTES:
        raise ValueError("max_notes must be an integer from 1 through 200")
    if not isinstance(report, dict) or not isinstance(inventory, dict):
        raise TypeError("Report and source inventory must be objects")
    for digest in (source_sha256, report.get("source_sha256"), inventory.get("source_sha256")):
        if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None or digest != source_sha256:
            raise ValueError("Markup requires matching source SHA-256 bindings")
    if (report.get("overall_status") != "REVIEW_REQUIRED"
            or report.get("assessment_type") != "CANDIDATE_EVIDENCE_REVIEW_NOT_COMPLIANCE"):
        raise ValueError("Only review-only evidence reports support markup")
    entries, pages, raw_spans = report.get("requirements"), inventory.get("pages"), inventory.get("spans")
    if (not isinstance(entries, list) or type(pages) is not int or not 1 <= pages <= MAX_PAGES
            or not isinstance(raw_spans, list) or len(raw_spans) > MAX_SPANS):
        raise ValueError("Invalid requirement list or source inventory")
    if len(entries) > max_notes:
        raise ValueError("Markup note limit exceeded")
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("status") != "REVIEW_REQUIRED":
            raise ValueError("Only review-required findings support markup")
        identifier = _text(entry.get("requirement_id"), "Finding ID", limit=256)
        if identifier in seen:
            raise ValueError("Duplicate finding ID")
        seen.add(identifier)
    spans, notes = _span_index(raw_spans), []
    for entry in sorted(entries, key=lambda item: item["requirement_id"]):
        identifier = entry["requirement_id"]
        anchor, reason, page, clipped = _locate(entry, pages, spans)
        observation = entry.get("observation")
        observation = (_text(observation, "Observation") if isinstance(observation, str) and observation.strip()
                       else "No unambiguous literal text observation was recorded.")
        instruction = _text(entry.get("review_instruction") or entry.get("correction"),
                            "Review instruction", default="Independently inspect the drawing evidence.")
        body = "Observation: " + observation + "\nReview: " + instruction
        if clipped:
            body += "\nThe source text box is clipped to the visible page; confirm the original evidence."
        notes.append({"finding_id": identifier, "kind": "REQUIREMENT",
                      "title": _text(entry.get("requirement_summary") or identifier, "Note title", limit=MAX_TITLE),
                      "body": _text(body, "Combined note body"), "citation": _citation(entry),
                      "status": "REVIEW_REQUIRED",
                      "source_status": _text(entry.get("source_status"), "Source status", limit=256,
                                             default="UNVERIFIED_CURRENT"),
                      "anchor": anchor, "evidence_page": page, "location_reason": reason})
    from pdf_markup_findings import expanded_markup_notes
    expanded = expanded_markup_notes(report, digest=source_sha256, pages=pages,
                                     spans=spans, remaining=max_notes-len(notes))
    for note in expanded:
        if note["finding_id"] in seen:
            raise ValueError("Duplicate expanded finding ID")
        seen.add(note["finding_id"])
        notes.append(note)
    summary = report.get("review_summary")
    if summary is not None and not isinstance(summary, dict):
        raise ValueError("Review summary must be an object")
    summary = summary or {}
    global_texts = set()

    def global_note(body: str, title: str) -> None:
        body = _text(body, "Global review note")
        if body in global_texts:
            return
        if len(notes) >= max_notes:
            raise ValueError("Markup note limit exceeded")
        global_texts.add(body)
        suffix = len(global_texts)
        identifier = f"GLOBAL-{suffix:03}"
        while identifier in seen:
            suffix += 1
            identifier = f"GLOBAL-{suffix:03}"
        seen.add(identifier)
        notes.append({"finding_id": identifier, "kind": "GLOBAL_REVIEW", "title": title,
                      "body": body, "citation": {"title": None, "version": None, "section": None,
                                                 "page": None, "url": None},
                      "status": "REVIEW_REQUIRED", "source_status": "UNVERIFIED_CURRENT",
                      "anchor": None, "evidence_page": None, "location_reason": "GLOBAL_REVIEW_ITEM"})

    for key in ("needs_attention", "not_checked"):
        values = summary.get(key, [])
        if not isinstance(values, list):
            raise ValueError("Summary review items must be lists")
        if len(values) > MAX_NOTES:
            raise ValueError("Summary review item limit exceeded")
        for value in values:
            global_note(value, "General review note")
    actions = summary.get("next_steps", [])
    if not isinstance(actions, list):
        raise ValueError("Summary next steps must be a list")
    if len(actions) > MAX_NOTES:
        raise ValueError("Summary next-step item limit exceeded")
    question = summary.get("context_question")
    parts = []
    parts_seen = set()
    combined_length = 0

    def action_part(value: str, label: str) -> None:
        nonlocal combined_length
        value = _text(value, label)
        if value in parts_seen:
            return
        added = len(value) + (1 if parts else 0)
        if combined_length + added > MAX_BODY:
            raise ValueError("Combined action note exceeds its text limit")
        parts_seen.add(value)
        parts.append(value)
        combined_length += added

    if question is not None:
        action_part(question, "Grouped context question")
    for action in actions:
        action_part(action, "Next-step action")
    if parts:
        global_note("\n".join(parts), "Next steps and missing information")
    if len(notes) > max_notes:
        raise ValueError("Markup note limit exceeded")
    for index, note in enumerate(notes, 1):
        note["note_id"] = f"R{index:03}"
    return {"status": "REVIEW_REQUIRED", "source_sha256": source_sha256,
            "coordinate_frame": FRAME, "notes": notes}
