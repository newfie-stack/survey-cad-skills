"""Compare actual, source-bound CAD/GIS point-export CSV with a plan table.

This is an exact point-register comparison, not a DWG/DXF/shapefile reader,
reconstruction, coordinate transformation, or independent control acceptance.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import csv
from decimal import Decimal, localcontext
from hashlib import sha256
import io
from pathlib import Path
import re


MAX_EXPORT_BYTES = 5 * 1024 * 1024
MAX_POINT_ROWS = 10_000
MAX_FIELD_CHARS = 1024
_FIELDS = ("point_id", "easting", "northing", "type")
_FLAGS = ("crs_verified", "provenance_verified", "coordinate_roles_resolved", "complete")
_HASH = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_POINT_ID = re.compile(r"[1-9][0-9]{0,17}\Z", re.ASCII)
_NUMBER = re.compile(r"[+-]?[0-9]{1,18}(?:\.[0-9]{1,12})?\Z", re.ASCII)
_TYPES = frozenset(("EC", "XC", "RC", "OC"))


def _metadata(value: dict, label: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    digest = value.get("source_sha256")
    if not isinstance(digest, str) or not _HASH.fullmatch(digest):
        raise ValueError(f"{label} requires a lowercase SHA-256 digest")
    for flag in _FLAGS:
        if type(value.get(flag)) is not bool:
            raise ValueError(f"{label}.{flag} requires an explicit boolean")
    for field in ("crs_identifier", "coordinate_frame_id"):
        item = value.get(field)
        if item is not None and (not isinstance(item, str) or not item.strip()
                                 or len(item) > MAX_FIELD_CHARS):
            raise ValueError(f"{label}.{field} must be a nonempty string or null")
    if value.get("coordinate_units") not in ("m", None):
        raise ValueError(f"{label}.coordinate_units must be m or null")


def validate_point_export_spec(spec: dict) -> dict:
    """Validate a CSV export declaration without opening any source file."""
    _metadata(spec, "Export specification")
    allowed = {"schema_version", "format", "origin_kind", "source_sha256",
               "crs_identifier", "coordinate_units", "coordinate_frame_id", *_FLAGS}
    if set(spec) != allowed:
        raise ValueError("Point-export specification requires exactly its declared schema fields")
    if type(spec["schema_version"]) is not int or spec["schema_version"] != 1:
        raise ValueError("Point-export specification requires schema_version 1")
    if spec["format"] != "CSV_POINT_EXPORT" or spec["origin_kind"] not in ("CAD", "GIS"):
        raise ValueError("Point-export specification requires CSV_POINT_EXPORT and CAD/GIS origin")
    return deepcopy(spec)


def _table_rows(table: dict) -> list[dict]:
    rows = table.get("rows")
    if not isinstance(rows, list) or len(rows) > MAX_POINT_ROWS:
        raise ValueError("Table rows must be a bounded list")
    for row in rows:
        if not isinstance(row, dict) or any(field not in row for field in _FIELDS):
            raise ValueError("Table rows require point_id, easting, northing and type")
        for field in _FIELDS:
            item = row[field]
            if item is not None and (not isinstance(item, str) or len(item) > MAX_FIELD_CHARS):
                raise ValueError("Table cells must preserve bounded original strings or null")
        if not isinstance(row.get("source_locator"), dict):
            raise ValueError("Table rows require their source locator object")
    return rows


def _read_export(path: Path, expected_hash: str) -> tuple[list[dict], str]:
    source = Path(path)
    if source.suffix.lower() != ".csv" or not source.is_file():
        raise ValueError("An existing point-export CSV is required")
    if source.stat().st_size > MAX_EXPORT_BYTES:
        raise ValueError("Point-export file size limit exceeded")
    with source.open("rb") as stream:
        snapshot = stream.read(MAX_EXPORT_BYTES + 1)
    if len(snapshot) > MAX_EXPORT_BYTES:
        raise ValueError("Point-export file size limit exceeded")
    digest = sha256(snapshot).hexdigest()
    if digest != expected_hash:
        raise ValueError("Point-export source SHA-256 does not match actual bytes")
    try:
        content = snapshot.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError("Point-export CSV must be UTF-8") from error
    if "\x00" in content:
        raise ValueError("NUL bytes are unsupported in point-export CSV")
    rows = []
    try:
        reader = csv.reader(io.StringIO(content, newline=""), strict=True)
        if next(reader, None) != list(_FIELDS):
            raise ValueError("Point-export CSV requires exact point_id,easting,northing,type header")
        for values in reader:
            if len(rows) >= MAX_POINT_ROWS:
                raise ValueError("Point-export row limit exceeded")
            if len(values) != len(_FIELDS) or any(len(v) > MAX_FIELD_CHARS for v in values):
                raise ValueError("Point-export CSV requires four bounded fields on every row")
            rows.append({**dict(zip(_FIELDS, values)), "export_line": reader.line_num})
    except csv.Error as error:
        raise ValueError("Malformed point-export CSV") from error
    return rows, digest


def _finding(reason_code: str, *, status: str = "REVIEW_REQUIRED", **evidence) -> dict:
    return {"reason_code": reason_code, "status": status, **evidence}


def _gates(spec: dict, table: dict, rows: list[dict], expected: list[dict]) -> list[dict]:
    findings = []
    for label, envelope in (("export", spec), ("table", table)):
        for flag in _FLAGS:
            if envelope[flag] is not True:
                findings.append(_finding("EVIDENCE_GATE_UNRESOLVED", side=label, gate=flag))
        if not envelope.get("crs_identifier"):
            findings.append(_finding("CRS_UNRESOLVED", side=label))
        if envelope.get("coordinate_units") != "m":
            findings.append(_finding("METRIC_UNITS_UNRESOLVED", side=label))
    if spec.get("crs_identifier") != table.get("crs_identifier"):
        findings.append(_finding("CRS_MISMATCH", export_crs=spec.get("crs_identifier"),
                                 table_crs=table.get("crs_identifier")))
    if (not spec.get("coordinate_frame_id") or not table.get("coordinate_frame_id")
            or spec["coordinate_frame_id"] != table["coordinate_frame_id"]):
        findings.append(_finding("COORDINATE_FRAME_UNRESOLVED",
                                 export_frame=spec.get("coordinate_frame_id"),
                                 table_frame=table.get("coordinate_frame_id")))
    if not rows or not expected:
        findings.append(_finding("POINT_SET_EMPTY"))
    for label, points in (("export", rows), ("table", expected)):
        counts = Counter(row["point_id"] for row in points)
        for identifier, count in counts.items():
            if count > 1:
                findings.append(_finding(f"DUPLICATE_{label.upper()}_POINT_ID",
                                         point_id=identifier, count=count))
        for index, row in enumerate(points, 1):
            identifier = row["point_id"]
            if not isinstance(identifier, str) or not _POINT_ID.fullmatch(identifier):
                findings.append(_finding("POINT_ID_UNRESOLVED", side=label, row=index,
                                         point_id=identifier))
            for field in ("easting", "northing"):
                value = row[field]
                if not isinstance(value, str) or not _NUMBER.fullmatch(value):
                    findings.append(_finding("COORDINATE_VALUE_UNRESOLVED", side=label,
                                             row=index, field=field, raw_value=value))
            if row["type"] not in _TYPES:
                findings.append(_finding("POINT_TYPE_UNRESOLVED", side=label, row=index,
                                         point_id=identifier, raw_value=row["type"]))
    return findings


def compare_point_export(path: str | Path, spec: dict, table: dict) -> dict:
    """Read/hash one actual CSV snapshot and compare fully resolved point sets.

    `spec` identifies CSV_POINT_EXPORT, CAD/GIS origin, schema_version 1, the
    expected source SHA-256, completeness and verified CRS/provenance/role
    declarations. Both envelopes require matching reviewed coordinate_frame_id
    values (including applicable datum/epoch/basis), coordinate_units "m", and
    crs_identifier. Null frame/units/CRS and unresolved table cells block the
    comparison. Boolean declarations are input gates, not independent proof.

    Table rows preserve source-bound original strings and source_locator dicts.
    Point IDs must be unambiguous positive ASCII integers without padding; no
    ID normalization, coordinate rounding, axis swapping or transform occurs.
    """
    spec = validate_point_export_spec(spec)
    _metadata(table, "Plan table")
    expected = _table_rows(table)
    rows, digest = _read_export(Path(path), spec["source_sha256"])
    findings = _gates(spec, table, rows, expected)
    result = {
        "kind": "CAD_GIS_POINT_EXPORT_COMPARISON", "execution_status": "EXECUTED",
        "comparison_execution_status": "NOT_EXECUTED", "origin_kind": spec["origin_kind"],
        "source_filename": Path(path).name, "source_sha256": digest,
        "plan_source_sha256": table["source_sha256"],
        "crs_identifier": table.get("crs_identifier"),
        "coordinate_frame_id": table.get("coordinate_frame_id"),
        "coordinate_units": table.get("coordinate_units"),
        "mechanical_status": "REVIEW_REQUIRED", "regulatory_status": "REVIEW_REQUIRED",
        "counts": {"export_rows": len(rows), "table_rows": len(expected),
                   "matched_ids": 0, "compared_points": 0},
        "findings": findings, "comparisons": [],
        "limitations": [
            "Only the actual CSV point export was read; native CAD/GIS files were not reopened or validated.",
            "Matching values do not independently verify control, CRS, datum, epoch, point roles or survey accuracy.",
            "Verification and whole-point-set completeness rely on source-bound reviewer declarations.",
            "No reconstruction, coordinate transformation, geometry/topology or regulatory acceptance is established.",
        ],
    }
    if findings:
        return result
    exported = {row["point_id"]: row for row in rows}
    tabulated = {row["point_id"]: row for row in expected}
    for identifier in tabulated:
        if identifier not in exported:
            findings.append(_finding("MISSING_EXPORT_POINT", status="FAIL", point_id=identifier,
                                     table=deepcopy(tabulated[identifier])))
    for identifier in exported:
        if identifier not in tabulated:
            findings.append(_finding("EXTRA_EXPORT_POINT", status="FAIL", point_id=identifier,
                                     export=deepcopy(exported[identifier])))
    common = exported.keys() & tabulated.keys()
    result["counts"]["matched_ids"] = len(common)
    for identifier in tabulated:
        if identifier not in common:
            continue
        actual, target = exported[identifier], tabulated[identifier]
        # Eighteen integer and twelve fractional digits fit exactly, including
        # a carry, in this local decimal context. The global context is untouched.
        with localcontext() as context:
            context.prec = 40
            dx = Decimal(actual["easting"]) - Decimal(target["easting"])
            dy = Decimal(actual["northing"]) - Decimal(target["northing"])
        comparison = {"point_id": identifier, "export": deepcopy(actual),
                      "table": deepcopy(target), "delta_easting": str(dx),
                      "delta_northing": str(dy), "status": "PASS"}
        if dx != 0 or dy != 0:
            comparison["status"] = "FAIL"
            findings.append(_finding("COORDINATES_DIFFER", status="FAIL", point_id=identifier,
                                     delta_easting=str(dx), delta_northing=str(dy)))
        if actual["type"] != target["type"]:
            comparison["status"] = "FAIL"
            findings.append(_finding("POINT_TYPE_DIFFERS", status="FAIL", point_id=identifier,
                                     export_type=actual["type"], table_type=target["type"]))
        result["comparisons"].append(comparison)
    result["counts"]["compared_points"] = len(common)
    result["comparison_execution_status"] = "EXECUTED"
    result["mechanical_status"] = "FAIL" if findings else "PASS"
    return result
