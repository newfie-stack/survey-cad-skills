"""Strict, bounded, local specifications for evidence-bound drawing QC.

A specification records review intent and selected contexts. It is not a verified
regulatory requirement, a source of drawing observations, or professional acceptance.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal
from math import isfinite
from pathlib import Path

MAX_SPEC_BYTES = 1_000_000
MAX_CHECKS = 100
MAX_REGIONS = 200
KINDS = {"required_text", "same_text", "scale", "decimal_sum", "visual"}
DECIMAL = re.compile(r"(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,12})?\Z")


def _fields(value: object, allowed: set[str], required: set[str], location: str) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{location} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise ValueError(f"{location} keys must be strings")
    if set(value) - allowed:
        raise ValueError(f"Unknown fields in {location}: {sorted(set(value) - allowed)}")
    if required - set(value):
        raise ValueError(f"Missing fields in {location}: {sorted(required - set(value))}")
    return value


def _text(value: object, location: str, limit: int = 1000) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{location} requires nonempty text of at most {limit} characters")
    if any(ord(char) < 32 and char not in "\n\t\r" for char in value):
        raise ValueError(f"Control characters in {location}")


def decimal_value(value: object) -> Decimal:
    if not isinstance(value, str) or not DECIMAL.fullmatch(value):
        raise ValueError("Decimal values must be bounded nonnegative plain decimal strings")
    return Decimal(value)


def validate_spec(spec: object) -> dict:
    spec = _fields(spec, {"schema_version", "source_sha256", "prepared_by", "checks"},
                   {"schema_version", "source_sha256", "prepared_by", "checks"}, "spec")
    if type(spec["schema_version"]) is not int or spec["schema_version"] != 1:
        raise ValueError("Unsupported finished-plan schema_version")
    if not isinstance(spec["source_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", spec["source_sha256"]):
        raise ValueError("source_sha256 must be a lowercase SHA-256 digest")
    _text(spec["prepared_by"], "prepared_by", 200)
    checks = spec["checks"]
    if not isinstance(checks, list) or not 1 <= len(checks) <= MAX_CHECKS:
        raise ValueError(f"checks must contain 1..{MAX_CHECKS} checks")
    ids = set()
    region_count = 0
    for check in checks:
        common = {"id", "kind", "description", "basis", "regions"}
        check = _fields(check, common | {"expected", "expected_denominator", "unit", "tolerance"}, common, "check")
        cid = check["id"]
        if not isinstance(cid, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,63}", cid) or cid in ids:
            raise ValueError("Check IDs must be unique, bounded identifiers")
        ids.add(cid)
        _text(check["description"], "description")
        _text(check["basis"], "basis")
        kind = check["kind"]
        if not isinstance(kind, str) or kind not in KINDS:
            raise ValueError("Unsupported check kind")
        extras = {"required_text": {"expected"}, "scale": {"expected_denominator"},
                  "decimal_sum": {"unit", "tolerance"}}.get(kind, set())
        _fields(check, common | extras, common | (extras if kind in {"required_text", "decimal_sum"} else set()), "check")
        regions = check["regions"]
        minimum = 3 if kind == "decimal_sum" else (2 if kind == "same_text" else 1)
        maximum = 1 if kind in {"required_text", "scale"} else 20
        if not isinstance(regions, list) or not minimum <= len(regions) <= maximum:
            raise ValueError(f"{kind} requires {minimum}..{maximum} regions")
        region_count += len(regions)
        selectors = set()
        for region in regions:
            _fields(region, {"page", "bbox_points", "role", "label", "coverage_review"},
                    {"page", "bbox_points", "role"}, "region")
            if type(region["page"]) is not int or region["page"] < 1:
                raise ValueError("Region page must be a positive one-based integer")
            box = region["bbox_points"]
            if not isinstance(box, list) or len(box) != 4:
                raise ValueError("Region bbox_points requires four finite coordinates")
            for v in box:
                if type(v) not in (int, float):
                    raise ValueError("Region coordinates must be finite numbers, not booleans")
                try:
                    valid = isfinite(v) and 0 <= v <= 1_000_000
                except OverflowError:
                    valid = False
                if not valid:
                    raise ValueError("Invalid region coordinate")
            if box[0] >= box[2] or box[1] >= box[3]:
                raise ValueError("Region must have positive width and height")
            _text(region["role"], "region role", 200)
            if "label" in region:
                _text(region["label"], "region label", 200)
            selector = (region["page"], tuple(box), region.get("label"))
            if selector in selectors:
                raise ValueError("Repeated region selection cannot count as independent evidence")
            selectors.add(selector)
            if "coverage_review" in region:
                coverage = _fields(region["coverage_review"], {"status", "reviewer", "method", "statement"},
                                   {"status", "reviewer", "method", "statement"}, "coverage_review")
                if coverage["status"] != "TEXT_COMPLETE" or coverage["method"] != "VISUAL_TO_TEXT_COMPARISON":
                    raise ValueError("Coverage requires explicit visual-to-text completeness review")
                _text(coverage["reviewer"], "coverage reviewer", 200)
                _text(coverage["statement"], "coverage statement")
        if kind == "required_text":
            _text(check["expected"], "expected phrase")
        if kind == "scale" and "expected_denominator" in check:
            n = check["expected_denominator"]
            if type(n) is not int or not 1 <= n <= 1_000_000_000:
                raise ValueError("Expected scale denominator must be a bounded positive integer")
        if kind == "decimal_sum":
            if check["unit"] not in ("ha", "m2", "m"):
                raise ValueError("Use an explicit supported unit: ha, m2, or m")
            decimal_value(check["tolerance"])
    if region_count > MAX_REGIONS:
        raise ValueError(f"At most {MAX_REGIONS} total regions may be reviewed")
    return spec


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f"Non-finite JSON constant: {value}")


def load_spec(path: str | Path) -> dict:
    source = Path(path)
    with source.open("rb") as handle:
        raw = handle.read(MAX_SPEC_BYTES + 1)
    if len(raw) > MAX_SPEC_BYTES:
        raise ValueError("Finished-plan specification size limit exceeded")
    return validate_spec(json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique_object,
                                    parse_constant=_reject_constant))
