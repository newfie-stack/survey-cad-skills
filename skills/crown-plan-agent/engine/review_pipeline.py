"""End-to-end conservative Crown plan review orchestration.

No unverified catalogue item can become a compliance finding.
"""
from __future__ import annotations

from geometry_handoff import prepare_geometry_handoff
from geometry_review import review_survey_geometry
from inventory_review import inventory_review
from plan_type_review import review_plan_type
from regulatory_catalog import candidate_applicability
from report_markdown import render_review_markdown
from review_summary import build_review_summary
from source_review import review_source_record


def review_inventory(inventory: dict, scenario: dict, catalogue: list[dict],
                     survey_geometry: dict | None = None, *,
                     table_a2_rows: list[dict] | None = None,
                     clause_catalogue: dict | None = None,
                     clause_facts: dict | None = None,
                     clause_inventory: dict | None = None) -> dict:
    """Join plan-type review, candidate applicability and observed PDF text."""
    if clause_catalogue is None and (clause_facts is not None or clause_inventory is not None):
        raise ValueError("Clause facts/inventory require an explicit clause catalogue")
    workbook = None
    if clause_catalogue is not None:
        from clause_workbook import prepare_clause_workbook
        workbook = prepare_clause_workbook(
            clause_catalogue, scenario, {} if clause_facts is None else clause_facts,
            coverage_inventory=clause_inventory)
    plan_review = review_plan_type(scenario, table_a2_rows=table_a2_rows)
    decisions = candidate_applicability(catalogue, scenario)
    by_id = {item["requirement_id"]: item for item in decisions}
    eligible = [rule for rule in catalogue
                if by_id[rule["requirement_id"]]["applicability_status"] == "CANDIDATE_REVIEW"]
    ledger = inventory_review(inventory, scenario, eligible)
    ledger["source_filename"] = inventory.get("source_filename")
    ledger["review_inputs"] = {
        "text_inventory_supplied": True,
        "table_a2_rows_supplied": table_a2_rows is not None,
        "survey_geometry_supplied": survey_geometry is not None,
        "clause_workbook_requested": clause_catalogue is not None,
    }
    for item in ledger["requirements"]:
        rule = next(rule for rule in eligible if rule["requirement_id"] == item["requirement_id"])
        item["applicability_status"] = "CANDIDATE_REVIEW"
        item["applicability"] = "CANDIDATE_REVIEW"
        item["source_review"] = review_source_record(rule.get("citation", {}))
        item["source_status"] = "UNVERIFIED_CURRENT"
    ledger["plan_type_review"] = plan_review
    ledger["applicability_decisions"] = decisions
    ledger["excluded_from_evidence_review"] = [
        item for item in decisions if item["applicability_status"] != "CANDIDATE_REVIEW"
    ]
    ledger["geometry_handoff"] = prepare_geometry_handoff(inventory, scenario, survey_geometry)
    if survey_geometry is not None:
        ledger["survey_geometry_review"] = review_survey_geometry(
            survey_geometry, plan_spans=inventory.get("spans"))
    ledger["overall_status"] = "REVIEW_REQUIRED"
    if workbook is not None:
        ledger["clause_workbook"] = workbook
    ledger["review_summary"] = build_review_summary(ledger)
    ledger["report_markdown"] = render_review_markdown(ledger)
    return ledger
