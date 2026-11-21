"""Discover source-bound native text and prepare checks in reviewed contexts.

Candidate labels and native reading directions are observations, not verified
plan roles, drafting conventions, completeness claims or survey coordinates.
Preparation never chooses a field by its expected value or crosses a supplied
semantic context. The existing geometric checker remains the final reader.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import re

from finished_plan_review import _contains, _intersects, _normal, _region_view
from finished_plan_spec import validate_spec
from native_text_reading import reading_lines
from pdf_inspector import extract_pdf
from pdf_source import read_pdf_snapshot
from runtime_security import load_pdf_runtime

MAX_IMAGES = 20_000
MAX_CONTEXT_SPANS = 5_000
MAX_CLOSURE_ROUNDS = 32


def _union(boxes):
    return [min(box[0] for box in boxes), min(box[1] for box in boxes),
            max(box[2] for box in boxes), max(box[3] for box in boxes)]


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def _labels(text):
    """Suggest only observed prefixes; never assign an authoritative field role."""
    match = re.match(r"^([^\d:\n][^:\n]{0,99}):", text)
    return [match[0].rstrip()] if match else []


def _task(page, box, kind, reason, **extra):
    return {"page": page, "bbox_points": list(box), "kind": kind,
            "status": "REVIEW_REQUIRED", "reason": reason, **extra}


def _inspect(pdf):
    source = Path(pdf)
    source_bytes, digest = read_pdf_snapshot(source)
    inventory = extract_pdf(source, include_vectors=False)
    if inventory["source_sha256"] != digest:
        raise ValueError("Source PDF changed during intake")
    fitz = load_pdf_runtime()
    spans = inventory["spans"]
    by_page = defaultdict(list)
    candidates_by_page = defaultdict(list)
    span_lookup = {}
    candidates = []
    pages = []
    visual_tasks = []
    cursor = 0
    image_count = 0
    with fitz.open(stream=source_bytes, filetype="pdf") as document:
        for index, page in enumerate(document):
            number = index + 1
            bounds = page.rect * page.derotation_matrix
            page_box = [0.0, 0.0, float(bounds.width), float(bounds.height)]
            image_info = page.get_image_info()
            image_count += len(image_info)
            if image_count > MAX_IMAGES:
                raise ValueError("Intake image count limit exceeded")
            images = []
            for item in image_info:
                box = [float(v) for v in item["bbox"]]
                if len(box) != 4 or not all(isfinite(v) for v in box) or box[0] >= box[2] or box[1] >= box[3]:
                    raise ValueError("Unsupported raster image rectangle")
                images.append(box)
                visual_tasks.append(_task(number, box, "RASTER_CONTENT",
                    "Inspect raster content visually; native text cannot establish its content or completeness."))
            metadata = {"page": number, "size_points": page_box[2:],
                        "rotation_degrees": page.rotation, "image_rectangles": images,
                        "native_span_count": 0, "line_candidate_ids": []}
            pages.append(metadata)
            # Retain native block/line boundaries. Reconstructing the whole page
            # first would merge independent same-baseline titleblock columns.
            raw = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES)
            for block_index, block in enumerate(raw.get("blocks", [])):
                if block.get("type") != 0:
                    continue
                for line_index, native_line in enumerate(block.get("lines", [])):
                    members = []
                    member_ids = []
                    for native_span in native_line.get("spans", []):
                        text = str(native_span.get("text", "")).strip()
                        if not text:
                            continue
                        if cursor >= len(spans) or spans[cursor]["page"] != number or spans[cursor]["text"] != text:
                            raise ValueError("Native text observations changed during intake")
                        span = spans[cursor]
                        span_id = f"{digest[:16]}:p{number}:s{cursor}"
                        cursor += 1
                        members.append(span)
                        member_ids.append(span_id)
                        span_lookup[span_id] = span
                        by_page[number].append(span)
                        metadata["native_span_count"] += 1
                    if not members:
                        continue
                    lines, blockers = reading_lines(members)
                    if len(lines) != 1:
                        blockers.append("Native line contains separated or unsupported fields; visual association is required")
                    text = " ".join(line["text"] for line in lines) if lines else " ".join(s["text"] for s in members)
                    box = _union([s["bbox_points"] for s in members])
                    if any("original_bbox_points" in span for span in members):
                        blockers.append("Clipped native text at the visible page boundary")
                    if any(_intersects(box, image) for image in images):
                        blockers.append("Raster image overlaps native text support")
                    cid = f"{digest[:16]}:p{number}:b{block_index}:l{line_index}"
                    first = members[0]
                    labels = _labels(text)
                    hints = []
                    if labels:
                        hints.append("label")
                    if re.search(r"(?<!\w)1\s*:", text):
                        hints.append("scale")
                    if re.search(r"\d.*(?:\bha\b|\bm2\b|\bm\^2\b|m²|\bm\b)", text, re.IGNORECASE):
                        hints.append("amount")
                    if text.upper() == text and any(c.isalpha() for c in text):
                        hints.append("heading")
                    candidate = {"id": cid, "page": number, "text": text,
                        "bbox_points": box, "span_ids": member_ids,
                        "native_locator": {"block_index": block_index, "line_index": line_index},
                        "text_direction": list(first["text_direction"]),
                        "text_angle_degrees": first["text_angle_degrees"],
                        "display_angle_degrees": first["display_angle_degrees"],
                        "label_candidates": labels, "kind_hints": hints,
                        "blockers": list(dict.fromkeys(blockers))}
                    if len(lines) == 1:
                        candidate["reading_box"] = lines[0]["reading_box"]
                    originals = [s["original_bbox_points"] for s in members if "original_bbox_points" in s]
                    if originals:
                        candidate["original_span_bbox_points"] = originals
                    candidates.append(candidate)
                    candidates_by_page[number].append(candidate)
                    metadata["line_candidate_ids"].append(cid)
                    if blockers:
                        visual_tasks.append(_task(number, box, "UNRESOLVED_NATIVE_TEXT",
                            "; ".join(dict.fromkeys(blockers)), candidate_ids=[cid]))
            visual_tasks.append(_task(number, page_box,
                "WHOLE_SHEET_CONTEXT_REVIEW" if metadata["native_span_count"] else "NO_NATIVE_TEXT",
                "Read the whole sheet to identify current titleblocks, notes, schedules, insets and history. "
                "Native text does not establish completeness or recognize scanned/outlined lettering."
                if metadata["native_span_count"] else
                "No native text was extracted. Visually inspect scanned, outlined or empty content; do not infer omissions."))
            if any(c["text_angle_degrees"] != 0 for c in candidates_by_page[number]):
                visual_tasks.append(_task(number, page_box, "NATIVE_DIRECTION_CONTEXT",
                    "Read each label in its native direction and inspect readability in context. "
                    "PDF baselines are separate from survey azimuths; no office rotation cutoff is assumed."))
    if cursor != len(spans) or read_pdf_snapshot(source)[1] != digest:
        raise ValueError("Source PDF changed during intake")
    result = {"schema_version": 1, "source_filename": source.name, "source_sha256": digest,
              "assessment_scope": "INTAKE_CANDIDATES_ONLY", "overall_status": "REVIEW_REQUIRED",
              "regulatory_status": "NOT_ASSESSED", "coordinate_space": "UNROTATED_CROPBOX_POINTS",
              "pages": pages, "line_candidates": candidates, "visual_tasks": visual_tasks,
              "limitations": ["Candidate labels/headings are not verified plan roles",
                  "No OCR, outlined lettering recognition, text completeness or regulatory acceptance",
                  "Native baseline directions are not survey azimuths or drafting-rule thresholds"]}
    return result, by_page, candidates_by_page, span_lookup


def discover_plan(pdf: str | Path) -> dict:
    """Inventory actual local PDF evidence and source-located visual followups."""
    return _inspect(pdf)[0]


def _label_value(text, label):
    text = _normal(text)
    prefix = _normal(label)
    if not text.startswith(prefix):
        return None
    if prefix[-1].isalnum() and len(text) > len(prefix) and text[len(prefix)].isalnum():
        return None
    return text[len(prefix):].strip()


def _possible_continuation(selected, candidates, declared_labels=()):
    """Abstain on a nearby unlabelled continuation rather than invent an association."""
    if "reading_box" not in selected:
        return False
    a = selected["reading_box"]
    dx, dy = selected["text_direction"]
    for candidate in candidates:
        if (candidate["id"] == selected["id"] or candidate["label_candidates"]
                or "scale" in candidate["kind_hints"] or "reading_box" not in candidate):
            continue
        if any(_label_value(candidate["text"], label) is not None for label in declared_labels):
            continue  # Another observed anchor explicitly supplied for this same panel.
        gx, gy = candidate["text_direction"]
        if dx * gx + dy * gy <= 0 or abs(dx * gy - dy * gx) > 1e-4:
            continue
        b = candidate["reading_box"]
        height = max(a[3] - a[1], b[3] - b[1])
        # Hanging values commonly align beneath the value after a label,
        # farther than one font height from the line's left edge. Treat every
        # start within the selected line's full reading support as a possible
        # continuation; explicitly observed independent anchors were excluded
        # above. This detects uncertainty without joining or completing text.
        if (-height * 0.3 <= b[1] - a[3] <= height * 0.7
                and b[1] > a[1] + height * 0.3
                and a[0] - height <= b[0] <= a[2] + height):
            return True
    return False


def _support_closure(selected, context, spans):
    """Bounded O(rounds*n) closure; an unfinished chain never becomes evidence."""
    support = list(selected)
    for _ in range(MAX_CLOSURE_ROUNDS):
        touching = [s for s in spans if _intersects(support, s["bbox_points"])]
        boxes = [support] + [s["bbox_points"] for s in touching]
        expanded = _union(boxes)
        if not _contains(context, expanded):
            return support, "Complete native-text support would cross the supplied context boundary"
        if expanded == support:
            return support, ""
        support = expanded
    return support, "Native-text overlap closure exceeded the bounded iteration limit; inspect the context visually"


def _resolve_region(region, candidates, spans, images, *, visual=False, declared_labels=()):
    context = region["bbox_points"]
    context_spans = [s for s in spans if _intersects(context, s["bbox_points"])]
    over_limit = len(context_spans) > MAX_CONTEXT_SPANS
    available = [c for c in candidates if _intersects(context, c["bbox_points"])]
    if "label" in region:
        matching = [c for c in available if _label_value(c["text"], region["label"]) is not None]
    else:
        matching = available
    record = {"page": region["page"], "role": region["role"],
              "context_bbox_points": list(context),
              "context_candidate_count": len(available), "matching_candidate_count": len(matching),
              "candidate_listing": "REFER_TO_INTAKE_CONTEXT_LIMIT" if over_limit else "COMPLETE",
              "context_candidate_ids": [] if over_limit else [c["id"] for c in available],
              "matching_candidate_ids": [] if over_limit else [c["id"] for c in matching],
              "matching_candidates": [] if over_limit else deepcopy(matching),
              "selected_bbox_points": _union([c["bbox_points"] for c in matching]) if matching else None,
              "support_bbox_points": None, "status": "REVIEW_REQUIRED", "reason": "",
              "coverage_review_handling": "NOT_TRANSFERRED_TO_DERIVED_REGION" if "coverage_review" in region else "NOT_SUPPLIED"}
    if "label" in region:
        record["label"] = region["label"]
    if over_limit:
        record["reason"] = f"Context exceeds the bounded {MAX_CONTEXT_SPANS}-span selection limit; consult the intake map and narrow the context"
    elif visual:
        record["reason"] = "Graphical interpretation requires independent visual review"
    elif not matching:
        record["reason"] = "No matching native line in the supplied context; inspect scanned, outlined or missing content visually"
    elif len(matching) != 1:
        record["reason"] = "Multiple native line candidates in the supplied context; select a more specific reviewed context or literal label"
    else:
        selected = matching[0]
        record["selected_bbox_points"] = list(selected["bbox_points"])
        if selected["blockers"]:
            record["reason"] = "; ".join(selected["blockers"])
        elif not _contains(context, selected["bbox_points"]):
            record["reason"] = "Matching native text crosses the supplied context boundary"
        elif "label" in region and not _label_value(selected["text"], region["label"]):
            record["reason"] = "The matching label has no same-line value; stacked/blank fields require visual association"
        elif "label" in region and _possible_continuation(selected, available, declared_labels):
            record["reason"] = "A possible wrapped value needs explicit visual association; native lines were not joined"
        else:
            support, error = _support_closure(selected["bbox_points"], context, context_spans)
            record["support_bbox_points"] = support
            if error:
                record["reason"] = error
            else:
                derived = {key: deepcopy(value) for key, value in region.items() if key != "coverage_review"}
                derived["bbox_points"] = support
                view = _region_view(derived, context_spans, images)
                intended = _label_value(selected["text"], region["label"]) if "label" in region else _normal(selected["text"])
                if view["blockers"]:
                    record["reason"] = "; ".join(view["blockers"])
                elif Counter(view["values"]) != Counter([intended]):
                    record["reason"] = "The existing reader cannot isolate this native field without merging or competing values"
                else:
                    record.update(status="READY", reason="One whole native field resolved inside the supplied context")
                    return derived, record, view
    return None, record, None


def prepare_finished_plan(pdf: str | Path, context_spec: dict) -> dict:
    """Build strict v1 ready checks; retain every unresolved source-bound request.

Input boxes are reviewed semantic contexts, never search hints inferred from an
expected phrase. Completeness declarations do not transfer to derived boxes.
"""
    validate_spec(context_spec)
    _, digest = read_pdf_snapshot(pdf)
    if digest != context_spec["source_sha256"]:
        raise ValueError("Source SHA-256 digest does not match the context specification")
    intake, spans_by_page, candidates_by_page, _ = _inspect(pdf)
    if intake["source_sha256"] != digest:
        raise ValueError("Source PDF changed during check preparation")
    page_info = {p["page"]: p for p in intake["pages"]}
    # Reject every invalid page/bound before preparing any check.
    for check in context_spec["checks"]:
        for region in check["regions"]:
            info = page_info.get(region["page"])
            if info is None:
                raise ValueError("Context references a nonexistent PDF page")
            if not _contains([0, 0, *info["size_points"]], region["bbox_points"]):
                raise ValueError("Context lies outside the visible unrotated PDF page")
    ready = []
    resolutions = []
    followups = list(intake["visual_tasks"])
    declared_labels = defaultdict(set)
    for check in context_spec["checks"]:
        for region in check["regions"]:
            if "label" in region:
                declared_labels[(region["page"], tuple(region["bbox_points"]))].add(region["label"])
    for check in context_spec["checks"]:
        regions = []
        records = []
        views = []
        for index, region in enumerate(check["regions"]):
            number = region["page"]
            derived, record, view = _resolve_region(region, candidates_by_page[number], spans_by_page[number],
                page_info[number]["image_rectangles"], visual=check["kind"] == "visual",
                declared_labels=declared_labels[(number, tuple(region["bbox_points"]))])
            record["region_index"] = index
            records.append(record)
            if derived is not None:
                regions.append(derived)
                views.append(view)
        resolution = {"check_id": check["id"], "description": check["description"],
                      "status": "REVIEW_REQUIRED", "reason": "", "request": deepcopy(check), "regions": records}
        if all(record["status"] == "READY" for record in records):
            seen = set()
            reused = False
            if check["kind"] in {"same_text", "decimal_sum"}:
                for view in views:
                    observed = {(view["region"]["page"], tuple(s["bbox_points"]), s["text"])
                                for s in view["evidence"]["spans"]}
                    reused = reused or bool(observed.intersection(seen))
                    seen.update(observed)
            if reused:
                resolution["reason"] = "Derived regions reuse the same underlying observation; independent fields remain unresolved"
            else:
                derived_check = deepcopy(check)
                derived_check["regions"] = regions
                ready.append(derived_check)
                resolution.update(status="READY", reason="All requested fields resolved from whole native observations")
        else:
            resolution["reason"] = "; ".join(dict.fromkeys(r["reason"] for r in records if r["status"] != "READY"))
        if resolution["status"] != "READY":
            for record in records:
                if record["status"] != "READY" or not resolution["reason"]:
                    followups.append(_task(record["page"], record["context_bbox_points"], "CHECK_CONTEXT_FOLLOWUP",
                        record["reason"] or resolution["reason"], check_id=check["id"], region_index=record["region_index"],
                        candidate_ids=record["matching_candidate_ids"]))
            if all(r["status"] == "READY" for r in records):
                for record in records:
                    followups.append(_task(record["page"], record["context_bbox_points"], "CHECK_CONTEXT_FOLLOWUP",
                        resolution["reason"], check_id=check["id"], region_index=record["region_index"],
                        candidate_ids=record["matching_candidate_ids"]))
        resolutions.append(resolution)
    spec = {key: deepcopy(context_spec[key]) for key in ("schema_version", "source_sha256", "prepared_by")}
    spec["checks"] = ready
    if ready:
        validate_spec(spec)
    if read_pdf_snapshot(pdf)[1] != digest:
        raise ValueError("Source PDF changed during check preparation")
    return {"schema_version": 1, "source_filename": Path(pdf).name, "source_sha256": digest,
            "context_spec_sha256": _digest(context_spec), "assessment_scope": "SOURCE_BOUND_CHECK_PREPARATION",
            "overall_status": "REVIEW_REQUIRED", "regulatory_status": "NOT_ASSESSED",
            "spec": spec if ready else None, "resolutions": resolutions, "visual_tasks": followups,
            "intake": intake}
