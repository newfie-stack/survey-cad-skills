"""Prepare an explicitly selected dated-source workbook; never assess compliance.

This module consumes declared applicability facts and caller-declared observation
references. It does not read drawings, run adapters, or infer a source universe.
"""
from __future__ import annotations

from collections.abc import Collection, Mapping
from copy import deepcopy
from itertools import islice

from clause_conditions import evaluate_clause_conditions, prepare_fact_values
from clause_overrides import resolve_overrides
from clause_schema import ADAPTER_IDS, CONTEXT_FIELDS, validate_clause_catalogue
from coverage_inventory import _validate_inventory
from requirements import application_context

ASSESSMENT_TYPE = "DATED_SOURCE_CLAUSE_WORKBOOK_NOT_COMPLIANCE"
SELECTIONS = frozenset({"CANDIDATE_REVIEW", "NOT_SELECTED_FOR_REVIEW",
                        "UNRESOLVED_APPLICABILITY", "OUT_OF_SCOPE"})
STATE_FIELDS = ("selection_status", "condition_trace", "blocking_fact_ids", "fact_issues",
                "override_trace", "override_reason_codes")


def _observation_ids(value: object) -> set[str]:
    if (not isinstance(value, Collection) or isinstance(value, (str, bytes, bytearray, Mapping))
            or len(value) > len(ADAPTER_IDS)):
        raise ValueError("Observation availability requires a bounded non-string collection")
    items = list(islice(iter(value), len(ADAPTER_IDS) + 1))
    if (len(items) != len(value) or any(not isinstance(item, str) or item not in ADAPTER_IDS for item in items)
            or len(items) != len(set(items))):
        raise ValueError("Observation references must be unique known adapter IDs")
    return set(items)


def _not_evaluated() -> dict:
    return {"result": "NOT_EVALUATED", "nodes": [], "blocking_fact_ids": [], "fact_issues": []}


def _aggregate_selection(checks: list[dict]) -> str:
    statuses = {check["selection_status"] for check in checks}
    if "UNRESOLVED_APPLICABILITY" in statuses:
        return "UNRESOLVED_APPLICABILITY"
    if "CANDIDATE_REVIEW" in statuses:
        return "CANDIDATE_REVIEW"
    return "NOT_SELECTED_FOR_REVIEW"


def _workbook_counts(clauses: list[dict]) -> dict:
    linked = sum(any(check["adapter_links"] for check in clause["checks"]) for clause in clauses)
    selected = [check for clause in clauses for check in clause["checks"]
                if check["selection_status"] == "CANDIDATE_REVIEW"]
    return {
        "catalogued_clause_paths": len(clauses),
        "catalogued_manual_only_clauses": len(clauses) - linked,
        "catalogued_clauses_with_adapter_links": linked,
        "selected_clause_paths": sum(c["selection_status"] == "CANDIDATE_REVIEW" for c in clauses),
        "unselected_clause_paths": sum(c["selection_status"] == "NOT_SELECTED_FOR_REVIEW" for c in clauses),
        "unresolved_clause_paths": sum(c["selection_status"] == "UNRESOLVED_APPLICABILITY" for c in clauses),
        "out_of_scope_clause_paths": sum(c["selection_status"] == "OUT_OF_SCOPE" for c in clauses),
        "selected_required_manual_checks": sum(c["kind"] in {"required", "conditional_required"} for c in selected),
        "selected_guidance_checks": sum(c["kind"] in {"optional", "permission"} for c in selected),
        "selected_exemption_controls": sum(c["kind"] == "exemption" for c in selected),
        "available_observation_links": sum(len(c["observation_refs"]) for c in selected),
    }


def _aggregate_fact_issues(checks: list[dict], blockers: list[str]) -> list[dict]:
    issues = {(issue["fact_id"], issue["code"]) for check in checks for issue in check["fact_issues"]}
    return [{"fact_id": ident, "code": code, "blocking": ident in blockers}
            for ident, code in sorted(issues)]


def _coverage(catalogue: dict, inventory: dict | None) -> dict:
    if inventory is None:
        return {"universe_status": "NOT_SUPPLIED", "expected_clause_count": None,
                "unmapped_clause_ids": None, "atomic_obligation_completeness": "NOT_ASSESSED"}
    inventory = _validate_inventory(inventory)
    source = catalogue["source"]
    supplied = inventory["source"]
    if any(supplied[old] != source[new] for old, new in (
            ("publication_title", "title"), ("version_date", "version_date"),
            ("pdf_page_count", "page_count"))):
        raise ValueError("Explicit inventory does not match the selected source edition")
    pages = {clause["clause_id"]: clause["pdf_page"] for clause in inventory["clauses"]}
    for clause in catalogue["clauses"]:
        if pages.get(clause["id"]) != clause["citation"]["page"]:
            raise ValueError("Catalogued clause section/page does not match the explicit inventory")
    ids = {clause["id"] for clause in catalogue["clauses"]}
    return {"universe_status": "MATCHED", "expected_clause_count": len(pages),
            "unmapped_clause_ids": sorted(set(pages) - ids),
            "atomic_obligation_completeness": "NOT_ASSESSED"}


def prepare_clause_workbook(catalogue: dict, scenario: dict, facts: dict, *,
                            available_observation_ids: Collection[str] = (),
                            coverage_inventory: dict | None = None) -> dict:
    """Prepare review requests after context, condition and override gates.

    Basic catalogue/fact/reference validation also applies outside review scope.
    Scope stops predicate, override and evidence selection, not input validation.
    """
    validate_clause_catalogue(catalogue)
    prepare_fact_values(catalogue["facts"], facts)
    available = _observation_ids(available_observation_ids)
    coverage = _coverage(catalogue, coverage_inventory)
    normalized = application_context(scenario)
    context = {}
    for field in sorted(CONTEXT_FIELDS):
        value = normalized[field]
        # A valid-looking canonical code may still conflict with the legacy
        # activity alias. The alias is not retained in the workbook's context;
        # keep that dimension unresolved so validation can reproduce its gate.
        if field == "disposition" and field in normalized["invalid_dimensions"]:
            value = None
        if isinstance(value, str):
            if len(value) > 4096:
                raise ValueError("Context strings exceed the workbook limit")
            value = value.strip() or None
        elif value is not None:
            value = None
        context[field] = value
    if context["scope_status"] == "OUT_OF_SCOPE":
        gate, issues = "OUT_OF_SCOPE", ["OUT_OF_SCOPE:land_class"]
    else:
        issues = sorted({*("MISSING_CONTEXT:" + name for name in normalized["missing_dimensions"]),
                         *("INVALID_CONTEXT:" + name for name in normalized["invalid_dimensions"])})
        gate = ("UNRESOLVED_APPLICABILITY" if issues or context["scope_status"] != "IN_SCOPE" else None)
    conditions = overrides = None
    if gate is None:
        conditions = evaluate_clause_conditions(catalogue, context, facts)
        overrides = resolve_overrides(catalogue, conditions["clause_results"], conditions["check_results"])
    clauses = []
    for clause in catalogue["clauses"]:
        checks = []
        for check in clause["checks"]:
            state = (overrides["checks"][check["id"]] if overrides is not None else
                     {"selection_status": gate, "condition_trace": _not_evaluated(),
                      "blocking_fact_ids": [], "fact_issues": [], "override_trace": [],
                      "override_reason_codes": []})
            selected = state["selection_status"] == "CANDIDATE_REVIEW"
            unresolved = state["selection_status"] == "UNRESOLVED_APPLICABILITY"
            refs = [ident for ident in check["adapter_links"] if selected and ident in available]
            checks.append({"id": check["id"], "kind": check["kind"],
                           "citation": deepcopy(clause["citation"]),
                           **{key: deepcopy(state[key]) for key in STATE_FIELDS},
                           "questions": list(check["questions"]),
                           "review_requests": list(check["questions"]) if selected else [],
                           "pending_applicability_questions": list(check["questions"]) if unresolved else [],
                           "adapter_links": list(check["adapter_links"]), "observation_refs": refs,
                           "evidence_status": ("OBSERVATION_CANDIDATE_AVAILABLE" if refs else
                                               "MANUAL_REVIEW_REQUIRED" if selected else "NOT_EVALUATED"),
                           "status": "REVIEW_REQUIRED", "source_status": "UNVERIFIED_CURRENT"})
        selection = gate or _aggregate_selection(checks)
        blockers = sorted({ident for check in checks if check["selection_status"] == "UNRESOLVED_APPLICABILITY"
                           for ident in check["blocking_fact_ids"]})
        fact_issues = _aggregate_fact_issues(checks, blockers)
        clauses.append({"id": clause["id"], "kind": clause["kind"],
                        "citation": deepcopy(clause["citation"]), "summary": clause["summary"],
                        "selection_status": selection,
                        "condition_trace": deepcopy(conditions["clause_results"][clause["id"]]) if conditions else _not_evaluated(),
                        "blocking_fact_ids": blockers, "fact_issues": fact_issues,
                        "override_trace": [deepcopy(d) for d in overrides["override_decisions"]
                                           if d["by_clause_id"] == clause["id"]] if overrides else [],
                        "status": "REVIEW_REQUIRED", "source_status": "UNVERIFIED_CURRENT", "checks": checks})
    return {"assessment_type": ASSESSMENT_TYPE, "catalogue_id": catalogue["catalogue_id"],
            "source": deepcopy(catalogue["source"]), "context": context, "context_issues": issues,
            "clauses": clauses, "counts": _workbook_counts(clauses), "coverage": coverage,
            "overall_status": "REVIEW_REQUIRED", "source_status": "UNVERIFIED_CURRENT"}
