"""Audit candidate rule citations and applicability coverage without legal approval."""
from __future__ import annotations

from source_review import review_source_record


def audit_catalogue(entries: list[dict]) -> dict:
    if not isinstance(entries, list):
        raise TypeError("Catalogue entries must be a list")
    findings = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("requirement_id"), str):
            raise ValueError("Each entry needs a requirement ID")
        citation = review_source_record(entry.get("citation", {}))
        wildcards = [field for field in ("plan_types", "activities", "stages")
                     if "*" in entry.get(field, [])]
        findings.append({
            "requirement_id": entry["requirement_id"],
            "citation_complete": citation["citation_complete"],
            "citation_gaps": citation["missing_or_invalid"],
            "broad_applicability_fields": wildcards,
            "source_status": "UNVERIFIED_CURRENT",
            "status": "REVIEW_REQUIRED",
        })
    return {
        "status": "REVIEW_REQUIRED",
        "total": len(findings),
        "incomplete_citations": sum(not item["citation_complete"] for item in findings),
        "broad_applicability": sum(bool(item["broad_applicability_fields"]) for item in findings),
        "findings": findings,
        "next_action": "Verify exact current clause and replace wildcard applicability only with source-backed criteria",
    }
