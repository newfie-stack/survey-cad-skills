"""Candidate regulatory requirement catalogue with fail-closed applicability.

Catalogue entries are review prompts, not legal determinations. A future
independent official-source verification workflow must establish current
authority and precise clause applicability before any compliance assessment.
"""
from __future__ import annotations

import json
from pathlib import Path

from requirements import application_context
from source_review import review_source_record


def load_candidate_catalog(path: str | Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_candidate_catalog(data)


def validate_candidate_catalog(data: object) -> list[dict]:
    """Validate already parsed catalogue data without reopening its source."""
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Unsupported catalogue schema")
    entries = data.get("requirements")
    if not isinstance(entries, list):
        raise ValueError("Requirements must be a list")
    ids = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Requirement must be an object")
        ident = entry.get("requirement_id")
        if not isinstance(ident, str) or not ident.strip() or ident in ids:
            raise ValueError("Requirement IDs must be unique and nonempty")
        ids.add(ident)
        for key in ("evidence_key", "summary"):
            if not isinstance(entry.get(key), str) or not entry[key].strip():
                raise ValueError("Missing requirement " + key)
        if entry.get("check_method", "text") not in (
                "text", "numerical_scale", "visual", "plan_heading", "scenario_text",
                "total_area"):
            raise ValueError("Unsupported requirement check method")
        for key in ("plan_types", "activities", "stages"):
            if not isinstance(entry.get(key), list) or not entry[key] or not all(
                isinstance(x, str) and x.strip() for x in entry[key]
            ):
                raise ValueError("Explicit applicability dimensions required: " + key)
        if entry.get("source_status") != "UNVERIFIED_CURRENT":
            raise ValueError("Catalogue may not claim source verification")
        citation = review_source_record(entry.get("citation", {}))
        if citation["source_status"] != "REVIEW_REQUIRED":
            raise ValueError("Unexpected source verification")
    return entries


def candidate_applicability(entries: list[dict], scenario: dict) -> list[dict]:
    """Return possible matches; unknown dimensions never become applicable."""
    context = application_context(scenario)
    missing = context["missing_dimensions"]
    invalid = context["invalid_dimensions"]
    selected = []
    for entry in entries:
        dimensions = (("plan_types", "plan_type"), ("activities", "disposition"), ("stages", "stage"))
        if context["scope_status"] == "OUT_OF_SCOPE":
            status = "OUT_OF_SCOPE"
        elif missing or invalid:
            status = "UNRESOLVED_APPLICABILITY"
        elif any(context[field] not in entry[allowed] and "*" not in entry[allowed]
                 for allowed, field in dimensions):
            status = "NOT_SELECTED_FOR_REVIEW"
        else:
            status = "CANDIDATE_REVIEW"
        selected.append({"requirement_id": entry["requirement_id"],
                         "applicability_status": status,
                         "scope_status": context["scope_status"],
                         "land_class": context["land_class"],
                         "review_scope": context["review_scope"],
                         "missing_dimensions": missing,
                         "invalid_dimensions": invalid,
                         "source_status": "UNVERIFIED_CURRENT",
                         "status": "REVIEW_REQUIRED"})
    return selected
