"""Source-bound mechanical observations for selected dated hybrid-table clauses.

This reads actual native PDF fields. It performs no reconstruction, coordinate
transformation, signature verification or legal-role acceptance. A complete-table
declaration and CRS/provenance/role flags are supplied review assertions, not
facts established by this module. Regulatory authority remains separate.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal, localcontext
import hashlib
import json
from math import hypot, isfinite
from pathlib import Path
import re

from clause_schema import _bounded_data
from finished_plan_review import _contains, _intersects, _region_view
from finished_plan_spec import _fields, _text
from native_text_reading import reading_lines
from pdf_inspector import extract_pdf
from pdf_source import read_pdf_snapshot
from runtime_security import load_pdf_runtime

FIELDS = ("point_id", "northing", "easting", "type")
CHECKS = (
    ("C_3_5_2_1_01", "Coordinate table numbering starts at one"),
    ("C_3_5_2_1_02", "Coordinate table numbering is consecutive without suffixes"),
    ("C_3_5_2_2_01", "Printed coordinates have two ASCII decimal places"),
    ("C_3_5_2_2_02", "Printed coordinates have no grouping spaces or commas"),
    ("C_3_5_2_3_01", "Each coordinate declares EC, XC, RC or OC"),
    ("C_3_5_6_2_01", "At least two distinct reviewed observed coordinates"),
    ("C_3_5_6_3_01", "Every EC, XC and RC is within inclusive ten kilometres of an OC"),
)
INTEGER = re.compile(r"[0-9]{1,9}\Z")
NUMBER = re.compile(r"[0-9]{1,18}(?:\.[0-9]{1,12})?\Z")
TWO_PLACES = re.compile(r"[0-9][0-9, \u00a0]{0,29}\.[0-9]{2}\Z")
TYPES = frozenset({"EC", "XC", "RC", "OC"})


def _region(value: object) -> None:
    _fields(value, {"page", "bbox_points", "role", "label"},
            {"page", "bbox_points", "role"}, "hybrid field region")
    if type(value["page"]) is not int or value["page"] < 1:
        raise ValueError("Hybrid field page must be a positive one-based integer")
    box = value["bbox_points"]
    if not isinstance(box, list) or len(box) != 4:
        raise ValueError("Hybrid field requires four bbox_points")
    for number in box:
        try:
            valid = type(number) in (int, float) and isfinite(number) and 0 <= number <= 1_000_000
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError("Hybrid field coordinates must be bounded finite numbers")
    if box[0] >= box[2] or box[1] >= box[3]:
        raise ValueError("Hybrid field region must have positive width and height")
    _text(value["role"], "Hybrid field role", 200)
    if "label" in value:
        _text(value["label"], "Hybrid field label", 200)


def validate_hybrid_spec(spec: object) -> dict:
    """Validate bounded review intent; never accept asserted field values."""
    _bounded_data(spec)
    keys = {"schema_version", "source_sha256", "prepared_by", "table_complete",
            "crs_identifier", "crs_verified", "provenance_verified", "coordinate_roles_resolved",
            "coordinate_frame_id", "coordinate_units", "rows"}
    _fields(spec, keys, keys, "hybrid table specification")
    if type(spec["schema_version"]) is not int or spec["schema_version"] != 1:
        raise ValueError("Unsupported hybrid table schema_version")
    if not isinstance(spec["source_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", spec["source_sha256"]):
        raise ValueError("Hybrid table requires lowercase source SHA-256")
    _text(spec["prepared_by"], "Hybrid table prepared_by", 200)
    for key in ("crs_verified", "provenance_verified", "coordinate_roles_resolved"):
        if type(spec[key]) is not bool:
            raise ValueError(key + " must be an explicit boolean")
    for key in ("crs_identifier", "coordinate_frame_id"):
        if spec[key] is not None:
            _text(spec[key], key, 300)
    if spec["coordinate_units"] not in (None, "m"):
        raise ValueError("Hybrid coordinate_units must be m or null")
    complete = spec["table_complete"]
    if complete is not None:
        keys = {"status", "method", "reviewer", "statement"}
        _fields(complete, keys, keys, "table_complete")
        if complete["status"] != "TEXT_COMPLETE" or complete["method"] != "VISUAL_TO_TEXT_COMPARISON":
            raise ValueError("Hybrid table completeness requires explicit visual-to-text review")
        _text(complete["reviewer"], "Table completeness reviewer", 200)
        _text(complete["statement"], "Table completeness statement")
    if not isinstance(spec["rows"], list) or not 1 <= len(spec["rows"]) <= 500:
        raise ValueError("Hybrid table requires 1..500 row selections")
    for row in spec["rows"]:
        _fields(row, set(FIELDS), set(FIELDS), "hybrid table row")
        for field in FIELDS:
            _region(row[field])
    return spec


def _raw_value(region: dict, spans: list[dict]) -> str | None:
    """Retain printed formatting, avoiding NFKC conversion of numeric glyphs."""
    selected = [span for span in spans if _intersects(region["bbox_points"], span["bbox_points"])]
    lines, blockers = reading_lines(selected)
    if blockers:
        return None
    # The directional reader inserts separators when joining separate spans.
    # Such separators cannot prove that printed coordinates contain grouping
    # spaces. Accept one literal span, or an exact separate label/value pair.
    if len(selected) != 1:
        if (len(selected) != 2 or "label" not in region
                or sum(span["text"].strip().casefold() == region["label"].strip().casefold()
                       for span in selected) != 1):
            return None
    values = []
    for line in lines:
        value = line["text"].strip()
        if "label" in region:
            label = region["label"].strip()
            match = re.match(re.escape(label), value, re.IGNORECASE)
            if match is None:
                continue
            if label[-1].isalnum() and len(value) > match.end() and value[match.end()].isalnum():
                continue
            value = value[match.end():].strip()
        values.append(value)
    if len(values) != 1 or not values[0] or len(values[0]) > 1000:
        return None
    return values[0]


def _row_geometry(row: dict, by_page: dict) -> tuple[dict | None, str | None]:
    """Bind four fields to one physical native row before making any table."""
    pages = {region["page"] for region in row.values()}
    if len(pages) != 1:
        return None, "Fields in a row must share one source page"
    page = next(iter(pages))
    direction = None
    baselines, heights, columns = [], [], {}
    for field in FIELDS:
        region = row[field]
        selected = [span for span in by_page[page]
                    if _intersects(region["bbox_points"], span["bbox_points"])]
        if not selected:
            return None, "Every row field needs native baseline evidence"
        positions = []
        for span in selected:
            dx, dy = span["text_direction"]
            length = hypot(dx, dy)
            dx, dy = dx / length, dy / length
            if direction is None:
                direction = (dx, dy)
            gx, gy = direction
            if gx * dx + gy * dy <= 0 or abs(gx * dy - gy * dx) > 1e-4:
                return None, "All fields in a table row must have one coherent native reading direction"
            origin = span.get("text_origin_points")
            if (not isinstance(origin, list) or len(origin) != 2
                    or not all(type(value) in (int, float) and isfinite(value) for value in origin)):
                return None, "Native field origins are needed to establish row membership"
            baselines.append(-origin[0] * gy + origin[1] * gx)
            box = span["bbox_points"]
            corners = span.get("quad_points") or [(box[0], box[1]), (box[2], box[1]), (box[0], box[3]), (box[2], box[3])]
            heights.append(max(-x * gy + y * gx for x, y in corners)
                           - min(-x * gy + y * gx for x, y in corners))
            positions.extend(x * gx + y * gy for x, y in corners)
        columns[field] = (min(positions), max(positions))
    tolerance = max(0.25, min(heights) * 0.15)
    if max(baselines) - min(baselines) > tolerance:
        return None, "Selected fields do not occupy the same physical native table row"
    return {"page": page, "direction": direction, "baseline": sum(baselines) / len(baselines),
            "tolerance": tolerance, "columns": columns}, None


def _physical_order(geometries: list[dict]) -> tuple[list[int] | None, str | None]:
    """Derive source order; unsupported multiple side-by-side tables abstain."""
    pages = defaultdict(list)
    for index, geometry in enumerate(geometries):
        pages[geometry["page"]].append((index, geometry))
    order = []
    for page in sorted(pages):
        rows = pages[page]
        gx, gy = rows[0][1]["direction"]
        for _, geometry in rows:
            dx, dy = geometry["direction"]
            if gx * dx + gy * dy <= 0 or abs(gx * dy - gy * dx) > 1e-4:
                return None, "Rows on one page need one native table reading frame"
        rows.sort(key=lambda item: item[1]["baseline"])
        for (_, previous), (_, following) in zip(rows, rows[1:]):
            if following["baseline"] - previous["baseline"] <= max(previous["tolerance"], following["tolerance"]):
                return None, "Source row ordering is ambiguous; side-by-side or overlapping tables need separate review"
        for field in FIELDS:
            intervals = [geometry["columns"][field] for _, geometry in rows]
            if max(value[0] for value in intervals) >= min(value[1] for value in intervals):
                return None, "Fields do not retain consistent source table columns"
        order.extend(index for index, _ in rows)
    return order, None


def _number(value: str) -> Decimal | None:
    return Decimal(value) if NUMBER.fullmatch(value) else None


def review_hybrid_table(pdf: str | Path, spec: dict) -> dict:
    """Read selected fields and execute seven explicitly bounded predicates."""
    validate_hybrid_spec(spec)
    source = Path(pdf)
    source_bytes, digest = read_pdf_snapshot(source)
    if digest != spec["source_sha256"]:
        raise ValueError("Source SHA-256 digest does not match hybrid table specification")
    inventory = extract_pdf(source, include_vectors=False)
    if inventory["source_sha256"] != digest:
        raise ValueError("Source PDF changed during hybrid table review")
    by_page = defaultdict(list)
    for span in inventory["spans"]:
        by_page[span["page"]].append(span)
    runtime = load_pdf_runtime()
    page_info = {}
    with runtime.open(stream=source_bytes, filetype="pdf") as document:
        for row in spec["rows"]:
            for region in row.values():
                number = region["page"]
                if number > len(document):
                    raise ValueError("Hybrid field references a nonexistent PDF page")
                if number not in page_info:
                    page = document[number - 1]
                    bounds = page.rect * page.derotation_matrix
                    images = page.get_image_info()
                    if len(images) > 20000:
                        raise ValueError("Page image count limit exceeded")
                    page_info[number] = ([0, 0, bounds.width, bounds.height], [list(i["bbox"]) for i in images])
                if not _contains(page_info[number][0], region["bbox_points"]):
                    raise ValueError("Hybrid field lies outside the visible unrotated PDF page")
    decoded, all_evidence, blockers, seen, geometries = [], [], [], set(), []
    for index, row in enumerate(spec["rows"], 1):
        values, fields = {}, {}
        for field in FIELDS:
            region = row[field]
            spans = by_page[region["page"]]
            view = _region_view(region, spans, page_info[region["page"]][1])
            fields[field] = view["evidence"]
            values[field] = _raw_value(region, spans)
            blockers.extend(f"Row {index} {field}: {reason}" for reason in view["blockers"])
            if values[field] is None or len(view["values"]) != 1 or view["has_empty_label_value"]:
                blockers.append(f"Row {index} {field}: exactly one complete native field value is required")
            observations = {(region["page"], tuple(span["bbox_points"]), span["text"])
                            for span in view["evidence"]["spans"]}
            if seen.intersection(observations):
                blockers.append(f"Row {index} {field}: a native observation is reused by another field")
            seen.update(observations)
        locator = {"source_sha256": digest, "fields": fields}
        all_evidence.append({"row_index": index, "selection_index": index, "source_locator": locator})
        decoded.append({**values, "source_locator": locator})
        geometry, issue = _row_geometry(row, by_page)
        geometries.append(geometry)
        if issue:
            blockers.append(f"Row {index}: {issue}")
    if all(geometry is not None for geometry in geometries):
        order, issue = _physical_order(geometries)
        if issue:
            blockers.append(issue)
        else:
            decoded = [decoded[index] for index in order]
            all_evidence = [{**all_evidence[index], "row_index": physical_index}
                            for physical_index, index in enumerate(order, 1)]
    blockers = list(dict.fromkeys(blockers))
    complete = spec["table_complete"] is not None and not blockers
    findings = []
    def finding(check_id, description, passed=None, reason=""):
        status = "REVIEW_REQUIRED" if passed is None else "PASS" if passed else "FAIL"
        findings.append({"check_id": check_id, "workbook_check_id": check_id, "description": description,
                         "mechanical_status": status,
                         "execution_status": "BLOCKED" if passed is None else "EXECUTED",
                         "assessment_scope": "DATED_CLAUSE_MECHANICAL_EVIDENCE",
                         "reason": reason, "source_status": "UNVERIFIED_CURRENT",
                         "evidence": all_evidence})
    if not complete:
        reason = ("; ".join(blockers) if blockers else
                  "Complete-table visual-to-text coverage has not been explicitly reviewed.")
        for check_id, description in CHECKS:
            finding(check_id, description, reason=reason)
    else:
        ids = [int(row["point_id"]) if INTEGER.fullmatch(row["point_id"]) else None for row in decoded]
        coords = [value for row in decoded for value in (row["northing"], row["easting"])]
        categories = [row["type"].upper() for row in decoded]
        xy = [(_number(row["easting"]), _number(row["northing"])) for row in decoded]
        statuses = [ids[0] == 1,
                    all(value is not None for value in ids) and ids == list(range(1, len(ids) + 1)),
                    all(TWO_PLACES.fullmatch(value) is not None for value in coords),
                    all(not any(char == "," or char.isspace() for char in value) for value in coords),
                    all(value in TYPES for value in categories)]
        reasons = ["Compared the first printed point number with 1.",
                   "Compared every printed point number with the consecutive 1..N sequence without suffixes.",
                   "Inspected original coordinate strings for exactly two ASCII decimal digits; no float serialization is used.",
                   "Inspected original coordinate strings for grouping commas or whitespace.",
                   "Compared printed categories with EC/XC/RC/OC; legal or accepted evidence roles remain separate."]
        for (check_id, description), passed, reason in zip(CHECKS, statuses, reasons):
            finding(check_id, description, passed, reason)
        gates = (spec["crs_verified"] and spec["crs_identifier"] is not None
                 and spec["coordinate_frame_id"] is not None and spec["coordinate_units"] == "m"
                 and spec["provenance_verified"] and spec["coordinate_roles_resolved"])
        numeric = all(e is not None and n is not None for e, n in xy)
        identities = all(value is not None for value in ids) and len(set(ids)) == len(ids)
        if not gates or not numeric or not identities or not statuses[4]:
            reason = ("Count/distance acceptance requires distinct numeric point identities, bounded ungrouped nonnegative coordinates, "
                      "recognized roles, and explicit reviewed provenance/role/common metric CRS and coordinate-frame evidence. "
                      "These declarations are not independently verified by this reader.")
            for check_id, description in CHECKS[5:]:
                finding(check_id, description, reason=reason)
        else:
            observed = {point for point, category in zip(xy, categories) if category == "OC"}
            governing = [(row["point_id"], point) for row, point, category in zip(decoded, xy, categories)
                         if category in {"EC", "XC", "RC"}]
            finding(*CHECKS[5], len(observed) >= 2,
                    f"Counted {len(observed)} distinct XY locations in reviewed OC rows; duplicate coordinates count once.")
            if not observed or not governing:
                finding(*CHECKS[6], reason="Both an OC set and EC/XC/RC subjects are needed; an empty set is not a distance pass.")
            else:
                # 18 integer plus 12 fractional digits need at most 62 digits
                # for a squared difference. 70 preserves exact endpoint cases.
                with localcontext() as context:
                    context.prec = 70
                    failures = [identity for identity, (e, n) in governing
                                if not any((e-oe)**2 + (n-on)**2 <= Decimal("100000000") for oe, on in observed)]
                finding(*CHECKS[6], not failures,
                        "Compared exact squared distances with 100000000 m² in the declared common frame; "
                        + ("outside-limit point IDs: " + ", ".join(failures) if failures else "all selected subjects are within the inclusive limit.")
                        + " No transformation or survey reconstruction was performed.")
    if read_pdf_snapshot(source)[1] != digest:
        raise ValueError("Source PDF changed during hybrid table review")
    table = {"source_sha256": digest, "crs_identifier": spec["crs_identifier"],
             "crs_verified": spec["crs_verified"], "provenance_verified": spec["provenance_verified"],
             "coordinate_roles_resolved": spec["coordinate_roles_resolved"],
             "coordinate_frame_id": spec["coordinate_frame_id"], "coordinate_units": spec["coordinate_units"],
             "complete": complete, "rows": decoded if not blockers else []}
    counts = Counter(item["mechanical_status"] for item in findings)
    return {"schema_version": 1, "source_filename": source.name, "source_sha256": digest,
            "spec_sha256": hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest(),
            "prepared_by": spec["prepared_by"], "assessment_scope": "DATED_CLAUSE_MECHANICAL_EVIDENCE",
            "overall_status": "REVIEW_REQUIRED", "source_status": "UNVERIFIED_CURRENT",
            "table_complete_review": spec["table_complete"], "table": table,
            "field_evidence": all_evidence, "blockers": blockers, "findings": findings,
            "summary": {key: counts[key] for key in ("PASS", "FAIL", "REVIEW_REQUIRED")},
            "residual_manual_review": ["Verify current applicable source edition and exact clauses/overrides.",
                                       "Verify coordinate roles, source provenance, control, datum/epoch and grid/ground/axis frame.",
                                       "A table match does not accept the survey, control network, CAD geometry or regulator submission."]}
