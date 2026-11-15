"""Conservative plan-type review based on official public guidance.

This module never replaces the current PLAR Table A1/A2, regulator decisions,
or an Alberta Land Surveyor's professional judgment.
"""
from __future__ import annotations

from datetime import date
from math import isfinite

from requirements import PLAN_TYPES, STAGES, application_context
from table_a2_lookup import disposition_code, lookup_plan_requirement

TABLE_A2_PLAN_TYPES = {"Sketch": "sketch", "Surveyor Sketch": "surveyor_sketch",
                       "Survey": "survey_plan"}
LINEAR_DISPOSITIONS = ("DPL", "PLA", "DLO", "LOC", "EZE")
LEGACY_CUTOFF = date(2010, 9, 1)


def review_renewal(scenario: dict, rows: list[dict] | None) -> dict:
    """Compare the documented active plan against the supplied Table A2."""
    existing = scenario.get("existing_plan_type")
    changed = scenario.get("disposition_changed")
    finding = {
        "existing_plan_type": existing if isinstance(existing, str) and existing in PLAN_TYPES else None,
        "source": "AER Manual 018, May 2025, sections 7.5.1–7.5.6",
    }
    if changed is True:
        return {**finding, "comparison": "AMENDMENT_BEFORE_RENEWAL"}
    if changed is not False:
        return {**finding, "comparison": "DISPOSITION_CHANGE_STATUS_REQUIRED"}
    if finding["existing_plan_type"] is None:
        return {**finding, "comparison": "PLAN_OF_RECORD_REQUIRED"}
    if rows is None:
        return {**finding, "comparison": "TABLE_A2_REQUIRED"}
    requirement = lookup_plan_requirement(
        rows, disposition=scenario.get("disposition", scenario.get("activity")),
        purpose=scenario.get("purpose"), activity=scenario.get("subactivity"))
    finding["requirement"] = requirement
    required = requirement.get("required_plan")
    if required is None:
        comparison = "TABLE_A2_ROW_UNRESOLVED"
    elif required == "N/A":
        comparison = "TABLE_A2_PLAN_TYPE_NOT_APPLICABLE"
    elif existing == TABLE_A2_PLAN_TYPES[required]:
        comparison = "MATCHES_TABLE_A2"
    elif existing == "survey_plan" and required in ("Sketch", "Surveyor Sketch"):
        comparison = "SURVEY_PLAN_SUBSTITUTION_REVIEW_REQUIRED"
    elif existing in ("hybrid_plan", "compiled_plan"):
        comparison = "PLAN_VARIANT_REVIEW_REQUIRED"
    elif existing == "sketch":
        try:
            issue_date = date.fromisoformat(scenario.get("disposition_issued_on", ""))
        except (TypeError, ValueError):
            comparison = "LEGACY_ISSUE_DATE_UNRESOLVED"
        else:
            comparison = ("LEGACY_SKETCH_VARIANCE_REVIEW" if issue_date < LEGACY_CUTOFF
                          else "DIFFERS_FROM_TABLE_A2")
    else:
        comparison = "DIFFERS_FROM_TABLE_A2"
    return {**finding, "comparison": comparison}


def review_amendment(scenario: dict) -> dict:
    """Route a documented plan of record to the applicable survey scope."""
    existing = scenario.get("existing_plan_type")
    code = disposition_code(scenario.get("disposition", scenario.get("activity")))
    length = scenario.get("existing_length_m")
    quarters = scenario.get("affected_quarter_sections")
    try:
        valid_length = type(length) in (int, float) and isfinite(length) and length > 0
    except OverflowError:
        valid_length = False
    valid_quarters = type(quarters) is int and quarters > 0
    finding = {
        "route": "AMENDMENT_PLAN_TYPE_UNRESOLVED",
        "comparison": "REVIEW_REQUIRED",
        "source": "AER Manual 018, May 2025, section 6.6",
        "instruction": "Review the OneStop plan of record, proposed changes and applicable amendment requirements.",
    }
    if not isinstance(existing, str) or existing not in PLAN_TYPES:
        finding["route"] = "PLAN_OF_RECORD_REQUIRED"
        return finding
    if scenario.get("plan_type") == "compiled_plan":
        finding.update(route="PLAN_VARIANT_REVIEW_REQUIRED",
                       source="Crown plan-content manual, May 30, 2024, section 3.6.1.1, page 14",
                       instruction="Confirm compiled-plan eligibility and current amendment direction. Section 3.6.1.1 excludes compiled plans from section 3.3 in the cited edition.")
        return finding
    if existing != "survey_plan" or code not in LINEAR_DISPOSITIONS:
        return finding
    finding.update(source="Crown plan-content manual, May 30, 2024, section 3.3.2, page 11",
                   route="SURVEY_SCOPE_UNRESOLVED",
                   instruction="Confirm total surveyed disposition length and affected quarters. If length is exactly 6.5 km and at most two quarters are affected, obtain direction on the survey scope.")
    if valid_quarters and quarters > 2:
        finding.update(route="FULL_RETRACE_CANDIDATE",
                       instruction="Section 3.3.2.3 calls for retracing the entire disposition.")
    elif valid_length and length < 6500:
        finding.update(route="FULL_RETRACE_CANDIDATE",
                       instruction="Section 3.3.2.2 calls for full retracement, except where it no longer defines the boundary.")
    elif valid_length and length > 6500 and valid_quarters:
        finding.update(route="ITEMIZED_SURVEY_CANDIDATE",
                       instruction="Review adjacent amendment boundaries under section 3.3.2.1 and the itemized-plan content under section 3.3.3. For additions or deletions, the digital polygon includes the entire amended disposition. Confirm OneStop Add eligibility separately.")
        if scenario.get("plan_type") in ("sketch", "surveyor_sketch"):
            finding["comparison"] = "ITEMIZED_SKETCH_CONFLICT"
    return finding


def review_plan_type(scenario: dict, *, table_a2_rows: list[dict] | None = None) -> dict:
    if not isinstance(scenario, dict):
        raise TypeError("Scenario must be a mapping")
    context = application_context(scenario)
    stage = context["stage"]
    plan_type = context["plan_type"]
    regulator = context["regulator"]
    purpose = scenario.get("purpose")
    missing = context["missing_dimensions"] + context["invalid_dimensions"]
    in_scope = context["scope_status"] == "IN_SCOPE"
    core_context_resolved = in_scope and not missing
    # A source row can still be identified without a proposed plan type; its
    # comparison stays unresolved until that proposal is supplied.
    table_context_resolved = in_scope and not any(field != "plan_type" for field in missing)
    normalized_scenario = {**scenario, "regulator": regulator, "stage": stage,
                           "plan_type": plan_type, "disposition": context["disposition"]}
    if not isinstance(purpose, str) or not purpose.strip():
        missing.append("purpose")
    if stage is not None and (not isinstance(stage, str) or stage not in STAGES):
        missing.append("recognized_stage")
    if plan_type is not None and (not isinstance(plan_type, str) or plan_type not in PLAN_TYPES):
        missing.append("recognized_plan_type")
    notes = [
        "Confirm any regulator-specific conditions or exceptions before accepting the plan type",
    ]
    if in_scope and stage == "initial":
        notes.append("Check the applicable current PLAR Table A1 or A2 entry for the exact purpose and activity")
    elif in_scope and stage == "renewal" and regulator == "AER":
        notes.append("Review the unchanged disposition and its plan on file against AER Manual 018, sections 7.5.1–7.5.6. Confirm any legacy plan variance separately.")
    if in_scope and regulator == "AER" and plan_type == "surveyor_sketch":
        notes.append("AER Bulletin 2025-31 describes surveyor sketches for oil sands and coal mineral surface leases; do not generalize to other leases")
        notes.append("The AER may still require a survey plan under Public Lands Act section 23")
    if in_scope and plan_type == "surveyor_sketch":
        notes.append("Confirm preparation and signature by an Alberta Land Surveyor")
    review = {
        "status": "REVIEW_REQUIRED",
        "plan_type_status": ("OUT_OF_SCOPE" if context["scope_status"] == "OUT_OF_SCOPE"
                             else "UNRESOLVED" if missing or not in_scope else "CANDIDATE_ONLY"),
        "scope_status": context["scope_status"],
        "land_class": context["land_class"],
        "review_scope": context["review_scope"],
        "missing_or_invalid_fields": sorted(set(missing)),
        "notes": notes,
        "source_references": [
            "https://www.alberta.ca/survey-sketch-plans",
            "https://www.aer.ca/about-aer/media-centre/bulletins/bulletin-2025-31",
        ],
        "regulatory_table_verified": False,
    }
    if core_context_resolved and stage == "amendment" and regulator == "AER":
        review["amendment_review"] = review_amendment(normalized_scenario)
    if core_context_resolved and stage == "renewal" and regulator == "AER":
        review["renewal_review"] = review_renewal(normalized_scenario, table_a2_rows)
    if (table_context_resolved and table_a2_rows is not None and regulator == "AER" and stage == "initial"
            and scenario.get("subactivity") is not None and purpose is not None):
        requirement = lookup_plan_requirement(
            table_a2_rows, disposition=context["disposition"],
            purpose=purpose, activity=scenario["subactivity"])
        review["table_a2_requirement"] = requirement
        required = requirement.get("required_plan")
        if required is None:
            comparison = "TABLE_A2_ROW_UNRESOLVED"
        elif required == "N/A":
            comparison = "TABLE_A2_PLAN_TYPE_NOT_APPLICABLE"
        elif not isinstance(plan_type, str) or plan_type not in PLAN_TYPES:
            comparison = "PROPOSED_PLAN_TYPE_UNRESOLVED"
        elif plan_type == TABLE_A2_PLAN_TYPES[required]:
            comparison = "MATCHES_TABLE_A2"
        elif plan_type == "survey_plan" and required in ("Sketch", "Surveyor Sketch"):
            comparison = "SURVEY_PLAN_SUBSTITUTION_REVIEW_REQUIRED"
            notes.append("Table A2 PDF page 18 discusses a plan of survey in place of a sketch or surveyor sketch. Confirm regulator instructions and monument requirements.")
        elif plan_type in ("hybrid_plan", "compiled_plan"):
            comparison = "PLAN_VARIANT_REVIEW_REQUIRED"
        else:
            comparison = "DIFFERS_FROM_TABLE_A2"
        review["table_a2_comparison"] = comparison
        review["proposed_plan_type"] = plan_type if isinstance(plan_type, str) and plan_type in PLAN_TYPES else None
    return review
