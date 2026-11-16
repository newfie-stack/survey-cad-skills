"""Evidence-bound deficiency ledger for Crown plan review.

A candidate requirement is not an enforceable rule until exact current source,
applicability and reviewer confirmation are independently established.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from requirements import application_context


def build_ledger(scenario: dict[str, Any], rules: list[dict[str, Any]],
                 observations: dict[str, Any]) -> dict[str, Any]:
    """Build a review-only ledger without promoting observations to compliance."""
    if not isinstance(scenario, dict) or not isinstance(rules, list) or not isinstance(observations, dict):
        raise TypeError("Scenario, rules and observations have invalid types")
    context = application_context(scenario)
    entries = []
    seen = set()
    for rule in rules:
        if not isinstance(rule, dict):
            raise TypeError("Each rule must be a mapping")
        rule_id = rule.get("requirement_id")
        key = rule.get("evidence_key")
        if not isinstance(rule_id, str) or not rule_id.strip() or rule_id in seen:
            raise ValueError("Requirement IDs must be unique nonempty strings")
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Evidence key required")
        seen.add(rule_id)
        evidence = observations.get(key)
        if evidence is not None and not isinstance(evidence, dict):
            raise TypeError("Evidence must be a mapping with observation and provenance")
        evidence = evidence or {}
        page = evidence.get("page")
        if page is not None and (type(page) is not int or page < 1):
            raise ValueError("Evidence page must be a positive integer")
        present = evidence.get("present")
        if present is not None and type(present) is not bool:
            raise ValueError("Evidence present must be boolean or unknown")
        # Never infer source verification from a caller-supplied boolean.
        # A separate authenticated regulatory source-review process is required.
        if present is True:
            evidence_status = "OBSERVED_CANDIDATE"
        elif present is False:
            evidence_status = "NOT_OBSERVED_IN_SUPPLIED_EVIDENCE"
        else:
            evidence_status = "UNKNOWN"
        if rule.get("check_method") == "visual":
            evidence_status = "VISUAL_CHECK_REQUIRED"
        citation = rule.get("citation", {})
        entries.append({
            "requirement_id": rule_id,
            "authority": citation.get("authority", rule.get("authority")),
            "requirement_summary": rule.get("summary", ""),
            "publication_title": citation.get("publication_title", rule.get("publication_title")),
            "version_date": citation.get("version_date", rule.get("version_date")),
            "section": citation.get("section", rule.get("section")),
            "regulator": context["regulator"],
            "land_class": context["land_class"],
            "review_scope": context["review_scope"],
            "scope_status": context["scope_status"],
            "activity": context["disposition"],
            "stage": context["stage"],
            "plan_type": context["plan_type"],
            "applicability": "UNRESOLVED_APPLICABILITY",
            "check_method": rule.get("check_method", "text"),
            "input_evidence": ({"source_filename": evidence.get("source_filename"),
                                "page": page, "bbox_points": evidence.get("bbox_points"),
                                "source_text": evidence.get("source_text", evidence.get("observation"))}
                               if evidence else None),
            "observed_value": evidence.get("observation"),
            "expected_value": rule.get("expected_value"),
            "severity": rule.get("severity"),
            # Generation/extraction time does not establish source verification.
            "verified_at": None,
            "source_url": citation.get("source_url", rule.get("source_url")),
            "source_version": citation.get("version_date"),
            "source_page": citation.get("page"),
            "review_instruction": rule.get("review_instruction"),
            "source_status": "UNVERIFIED_CURRENT",
            "evidence_key": key,
            "evidence_status": evidence_status,
            "page": page,
            "bbox_points": evidence.get("bbox_points"),
            "observation": evidence.get("observation"),
            "candidate_count": evidence.get("candidate_count"),
            "candidate_pages": evidence.get("candidate_pages"),
            "status": "REVIEW_REQUIRED",
            "correction": "Verify current source clause and applicability; independently inspect drawing evidence.",
        })
    return {
        "scenario": dict(scenario),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": "REVIEW_REQUIRED",
        "assessment_type": "CANDIDATE_EVIDENCE_REVIEW_NOT_COMPLIANCE",
        "requirements": entries,
        "summary": {
            "total": len(entries),
            "observed_candidates": sum(e["evidence_status"] == "OBSERVED_CANDIDATE" for e in entries),
            "not_observed": sum(e["evidence_status"] == "NOT_OBSERVED_IN_SUPPLIED_EVIDENCE" for e in entries),
            "unknown": sum(e["evidence_status"] == "UNKNOWN" for e in entries),
            "visual_checks": sum(e["evidence_status"] == "VISUAL_CHECK_REQUIRED" for e in entries),
        },
    }
