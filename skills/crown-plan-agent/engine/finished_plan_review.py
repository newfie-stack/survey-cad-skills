"""Read-only, scoped PDF drawing checks; never regulatory certification.

Region identities and completeness declarations come from a source-bound review
specification. Observations come from the actual PDF through the existing reader.
No COGO reconstruction, OCR, symbol recognition, external calls or source edits.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from decimal import Decimal, localcontext
from pathlib import Path

from finished_plan_spec import decimal_value, validate_spec
from pdf_inspector import extract_pdf
from pdf_source import read_pdf_snapshot
from native_text_reading import reading_lines
from revision_markdown import _literal
from runtime_security import load_pdf_runtime

SCALE = re.compile(r"(?<![\w:])1\s*:\s*((?:[0-9]{1,3}(?:[ ,][0-9]{3})+)|[0-9]+)(?![\w.])")


def _normal(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).split()).upper()


def _intersects(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _contains(a, b):
    return a[0] <= b[0] and a[1] <= b[1] and a[2] >= b[2] and a[3] >= b[3]


def _region_view(region: dict, spans: list[dict], images: list) -> dict:
    box = region["bbox_points"]
    selected = [s for s in spans if _intersects(box, s["bbox_points"])]
    blockers = []
    if len(selected) > 5000:
        raise ValueError("Selected region exceeds 5000 text spans; narrow the review scope")
    if any(_intersects(box, image) for image in images):
        blockers.append("Raster image overlaps the selected region; native text alone is insufficient")
    if any(not _contains(box, s["bbox_points"]) or "original_bbox_points" in s for s in selected):
        blockers.append("Clipped or partially selected text; revise the region and inspect the source")
    lines, orientation_blockers = reading_lines(selected)
    blockers.extend(orientation_blockers)
    values = []
    matched_lines = []
    for line in lines:
        text = _normal(line["text"])
        if "label" in region:
            prefix = _normal(region["label"])
            if not text.startswith(prefix):
                continue
            if prefix[-1].isalnum() and len(text) > len(prefix) and text[len(prefix)].isalnum():
                continue
            text = text[len(prefix):].strip()
        if text:
            values.append(text)
            matched_lines.append({**line, "text": text})
    return {"region": region, "lines": matched_lines, "values": values, "blockers": blockers,
            "evidence": {"page": region["page"], "bbox_points": list(box), "role": region["role"],
                         "text": "\n".join(line["text"] for line in lines),
                         "spans": [{key: s[key] for key in (
                             "text", "bbox_points", "text_angle_degrees", "text_direction",
                             "quad_points", "text_origin_points", "font_ascender", "font_descender",
                             "page_rotation_degrees", "display_angle_degrees")
                                    if key in s} for s in selected],
                         "coverage_review": region.get("coverage_review"),
                         "evidence_type": "EXTRACTED_TEXT" if selected else "SEARCH_REGION"}}


def _phrase_present(phrase: str, lines: list[dict]) -> bool:
    wanted = _normal(phrase)
    candidates = [_normal(line["text"]) for line in lines]
    # Allow genuinely wrapped notes, never join across large vertical/column gaps.
    for start, line in enumerate(lines):
        combined = _normal(line["text"])
        previous = line
        for following in lines[start + 1:start + 8]:
            if following["direction_group"] != line["direction_group"]:
                break
            a, b = previous["reading_box"], following["reading_box"]
            height = max(a[3] - a[1], b[3] - b[1])
            # Font boxes include ascender/descender space and can overlap at
            # ordinary line leading. Require a real forward line advance.
            if not (-height * 0.3 <= b[1] - a[3] <= height * 0.7
                    and abs(b[0] - line["reading_box"][0]) <= height):
                break
            combined += " " + _normal(following["text"])
            candidates.append(combined)
            previous = following
    return any(re.search(r"(?<!\w)" + re.escape(wanted) + r"(?!\w)", value) for value in candidates)


def _evaluate(check: dict, views: list[dict]) -> dict:
    result = {"check_id": check["id"], "kind": check["kind"], "description": check["description"],
              "basis": check["basis"], "assessment_scope": "DRAWING_QC_ONLY", "status": "REVIEW_REQUIRED",
              "observed": [view["values"] for view in views],
              "evidence": [view["evidence"] for view in views],
              "reason": "", "correction": "Inspect the selected source regions and resolve the evidence."}
    blockers = [b for v in views for b in v["blockers"]]
    if check["kind"] == "visual":
        result["reason"] = "Graphical/symbol interpretation is not implemented by this deterministic pass."
        result["correction"] = "Independently inspect this graphic; do not infer absence from missing text."
        return result
    if blockers:
        result["reason"] = "; ".join(dict.fromkeys(blockers))
        return result
    kind = check["kind"]
    if kind in {"same_text", "decimal_sum"}:
        seen = set()
        for view in views:
            observations = {(view["region"]["page"], tuple(s["bbox_points"]), s["text"])
                            for s in view["evidence"]["spans"]}
            if seen.intersection(observations):
                result["reason"] = "Selected regions reuse the same underlying observation; independent fields are unresolved."
                return result
            seen.update(observations)
    if kind == "same_text":
        if any(len(v["values"]) != 1 for v in views):
            result["reason"] = "Each selected subject field must contain exactly one unambiguous value."
            return result
        values = [v["values"][0] for v in views]
        result["observed"] = values
        result["status"] = "PASS" if len(set(values)) == 1 else "FAIL"
        result["reason"] = "Selected subject text agrees." if result["status"] == "PASS" else "Conflicting text in the selected subject fields."
        result["correction"] = "Confirm the authoritative subject identity and correct the conflicting field(s)."
    elif kind == "required_text":
        view = views[0]
        result["expected"] = check["expected"]
        result["observed"] = view["values"]
        found = _phrase_present(check["expected"], view["lines"])
        complete = "coverage_review" in view["region"]
        result["status"] = "PASS" if found else ("FAIL" if complete else "REVIEW_REQUIRED")
        result["reason"] = ("Expected text observed in the selected region." if found else
                            "Expected text not observed" + (" in a reviewer-declared complete region." if complete else "; extraction completeness is unverified."))
        result["correction"] = "Verify the stated basis, then restore or correct the expected text in its intended context."
    elif kind == "scale":
        denominators = [match[1].replace(" ", "").replace(",", "")
                        for value in views[0]["values"] for match in SCALE.finditer(value)]
        values = [int(value) if len(value) <= 10 else value for value in denominators]
        result["observed"] = values
        result["expected"] = check.get("expected_denominator", "One numeric scale ratio in the selected main-plan region")
        if not values:
            result["status"] = "FAIL" if "coverage_review" in views[0]["region"] else "REVIEW_REQUIRED"
            result["reason"] = "No numerical scale found in the selected main-plan region; inset scales are not substituted."
        elif len(values) != 1 or not isinstance(values[0], int) or not 1 <= values[0] <= 1_000_000_000:
            result["reason"] = "Multiple or unsupported scale ratios in the selected region."
        else:
            result["status"] = "PASS" if "expected_denominator" not in check or values[0] == check["expected_denominator"] else "FAIL"
            result["reason"] = "Scale ratio compared with the declared expectation; plotted scale is not measured."
        result["correction"] = "Verify the main-plan scale and its label separately from inset/detail scales."
    elif kind == "decimal_sum":
        numbers = []
        pattern = re.compile(r"((?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,12})?)\s*" + re.escape(check["unit"]), re.IGNORECASE)
        for view in views:
            match = pattern.fullmatch(view["values"][0]) if len(view["values"]) == 1 else None
            if match is None:
                result["reason"] = "Each selected amount must contain one plain decimal value with the declared unit; missing, competing or differently formatted cells remain unresolved."
                return result
            numbers.append(decimal_value(match[1]))
        with localcontext() as context:
            context.prec = 60
            expected = sum(numbers[:-1], Decimal(0))
            difference = abs(expected - numbers[-1])
            status = "PASS" if difference <= decimal_value(check["tolerance"]) else "FAIL"
        result.update(status=status, observed=[str(v) for v in numbers], expected=str(expected),
                      difference=str(difference), tolerance=check["tolerance"], unit=check["unit"],
                      reason="Sum of selected parts compared with selected total; not a legal boundary area calculation.",
                      correction="Check the selected rows and correct the displayed total or erroneous part; do not alter survey geometry to force agreement.")
    if result["status"] == "PASS":
        result["correction"] = "No discrepancy in this bounded comparison; other checks and professional review remain separate."
    return result


def _escaped(value) -> str:
    return _literal(str(value).replace("\n", " / "))


def render_finished_plan(report: dict) -> str:
    lines = ["\n## Finished-plan drawing QC", "", "Overall status: REVIEW_REQUIRED",
             "Regulatory compliance: NOT_ASSESSED. PASS/FAIL below describes only the stated drawing-QC comparison.",
             "", f"Source SHA-256: {report['source_sha256']}", f"Specification SHA-256: {report['spec_sha256']}",
             f"Scope prepared by: {_escaped(report['prepared_by'])}",
             "Context selections and completeness declarations are supplied evidence, not independent professional acceptance.",
             "", "Summary: " + "; ".join(f"{k}={v}" for k, v in report["summary"].items()), ""]
    for item in report["findings"]:
        lines.extend([f"### {_escaped(item['check_id'])}: {_escaped(item['description'])}",
                      f"Status: **{item['status']}**", f"Basis: {_escaped(item['basis'])}",
                      f"Observed: {_escaped(item['observed'])}", f"Finding: {_escaped(item['reason'])}"])
        for field in ("expected", "difference", "unit", "tolerance"):
            if field in item:
                lines.append(f"{field.title()}: {_escaped(item[field])}")
        for evidence in item["evidence"]:
            lines.append(f"Evidence: page {evidence['page']}, box {_escaped(evidence['bbox_points'])}; {_escaped(evidence['role'])}; text: {_escaped(evidence['text']) or '(none extracted)'}")
            angles = sorted({s["text_angle_degrees"] for s in evidence["spans"]
                             if "text_angle_degrees" in s})
            if any(angle != 0 for angle in angles):
                lines.append(f"Native text angle(s), unrotated page: {_escaped(angles)} degrees.")
            coverage = evidence.get("coverage_review")
            if coverage:
                lines.append(f"Coverage declaration: {_escaped(coverage['reviewer'])}; {_escaped(coverage['statement'])}")
        lines.extend([f"Action: {_escaped(item['correction'])}", ""])
    lines.extend(["Limits: selected text regions only; no automatic discovery of every omission, graphical recognition, field-truth verification, COGO reconstruction or regulatory certification.", ""])
    return "\n".join(lines)


def review_finished_plan(pdf: str | Path, spec: dict) -> dict:
    """Execute selected checks against current PDF bytes and return a traceable ledger."""
    validate_spec(spec)
    source = Path(pdf)
    source_bytes, digest = read_pdf_snapshot(source)
    if digest != spec["source_sha256"]:
        raise ValueError("Source SHA-256 digest does not match the finished-plan specification")
    inventory = extract_pdf(source, include_vectors=False)
    if inventory["source_sha256"] != digest:
        raise ValueError("Source PDF changed during review")
    by_page = defaultdict(list)
    for span in inventory["spans"]:
        by_page[span["page"]].append(span)
    fitz = load_pdf_runtime()
    page_info = {}
    with fitz.open(stream=source_bytes, filetype="pdf") as document:
        for check in spec["checks"]:
            for region in check["regions"]:
                index = region["page"]
                if index > len(document):
                    raise ValueError("Region references a nonexistent PDF page")
                if index not in page_info:
                    page = document[index - 1]
                    bounds = page.rect * page.derotation_matrix
                    images = page.get_image_info()
                    if len(images) > 20000:
                        raise ValueError("Page image count limit exceeded")
                    page_info[index] = ([0, 0, bounds.width, bounds.height], [list(i["bbox"]) for i in images])
                bounds, images = page_info[index]
                if not _contains(bounds, region["bbox_points"]):
                    raise ValueError("Region lies outside the visible unrotated PDF page")
    findings = []
    for check in spec["checks"]:
        views = [_region_view(region, by_page[region["page"]], page_info[region["page"]][1])
                 for region in check["regions"]]
        findings.append(_evaluate(check, views))
    if read_pdf_snapshot(source)[1] != digest:
        raise ValueError("Source PDF changed during review")
    counts = Counter(item["status"] for item in findings)
    report = {"schema_version": 1, "source_filename": source.name, "source_sha256": digest,
              "spec_sha256": hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest(),
              "prepared_by": spec["prepared_by"], "assessment_scope": "DRAWING_QC_ONLY",
              "overall_status": "REVIEW_REQUIRED", "regulatory_status": "NOT_ASSESSED", "findings": findings,
              "summary": {k: counts[k] for k in ("PASS", "FAIL", "REVIEW_REQUIRED")}}
    report["report_markdown"] = render_finished_plan(report)
    return report
