"""Plain-language actions derived from review evidence, never compliance."""
from __future__ import annotations

from math import isfinite

from requirements import application_context


_QUESTIONS = {
    "land_class": "What land class does the reviewed area cover?",
    "review_scope": "Which Alberta Crown component of the mixed-land plan is being reviewed?",
    "regulator": "Which authority regulates the application, AER or the Alberta provincial authority?",
    "disposition": "What is the exact three-letter disposition code?",
    "stage": "Is this an initial application, an amendment or a renewal?",
    "plan_type": "What plan type is proposed?",
    "purpose": "What is the exact application purpose?",
    "subactivity": "What is the exact Table A2 subactivity, including an explicitly blank activity if applicable?",
    "existing_plan_type": "What plan type is on file for the existing disposition?",
    "existing_length_m": "What is the total length in metres of the existing surveyed disposition?",
    "affected_quarter_sections": "How many quarter sections does the amendment affect?",
    "survey_scope_direction": "What current regulator direction resolves survey scope at exactly 6,500 metres?",
    "disposition_changed": "Has the disposition changed since its current plan was filed?",
    "disposition_issued_on": "When was the disposition issued, in YYYY-MM-DD form?",
}
_AREA_AMBIGUITIES = {
    "Conflicting total area values found. Confirm the activity total.",
    "Multiple table cells match the total area. Confirm the activity total.",
}


def _number(value: object) -> bool:
    try:
        return type(value) in (int, float) and isfinite(value)
    except OverflowError:
        return False


def build_review_summary(report: dict) -> dict:
    """Summarize recorded outcomes without inspecting files or inferring roles.

    Text inventories may be caller supplied. Coordinate calculations and source
    matches do not establish independent CRS, boundary or regulatory acceptance.
    Questions expose existing blockers; they never alter candidate eligibility.
    """
    if not isinstance(report, dict):
        raise TypeError("Review summary requires a report object")
    if report.get("overall_status", "REVIEW_REQUIRED") != "REVIEW_REQUIRED":
        raise ValueError("Only review-only reports can be summarized")
    scenario = report.get("scenario", {})
    if not isinstance(scenario, dict):
        raise TypeError("Review scenario must be an object")
    entries = report.get("requirements", [])
    if not isinstance(entries, list) or any(not isinstance(item, dict) for item in entries):
        raise ValueError("Review requirements must be a list of objects")
    if any(item.get("status") != "REVIEW_REQUIRED" for item in entries):
        raise ValueError("Unverified requirements cannot be summarized as approved")
    context = application_context(scenario)
    summary = {"status": "REVIEW_REQUIRED", "headline": "The review still needs independent confirmation.",
               "checked": [], "needs_attention": [], "not_checked": [],
               "input_requests": [], "context_question": None, "next_steps": []}

    def add(key, text):
        if text not in summary[key]:
            summary[key].append(text)

    def request(field):
        if not any(item["field"] == field for item in summary["input_requests"]):
            summary["input_requests"].append({"field": field, "question": _QUESTIONS[field]})

    finished = report.get("finished_plan_review")
    if finished is not None:
        if (not isinstance(finished, dict)
                or finished.get("assessment_scope") != "DRAWING_QC_ONLY"
                or finished.get("overall_status") != "REVIEW_REQUIRED"
                or finished.get("regulatory_status") != "NOT_ASSESSED"):
            raise ValueError("Only review-only drawing QC can be summarized")
        findings = finished.get("findings")
        statuses = ("PASS", "FAIL", "REVIEW_REQUIRED")
        if (not isinstance(findings, list) or not findings
                or any(not isinstance(item, dict) or item.get("status") not in statuses
                       for item in findings)):
            raise ValueError("Drawing QC requires recorded findings with supported statuses")
        counts = {status: sum(item["status"] == status for item in findings) for status in statuses}
        totals = "; ".join(f"{status}={counts[status]}" for status in statuses)
        add("checked", f"Executed {len(findings)} selected finished-plan drawing-QC checks ({totals}); results describe only the selected drawing comparisons.")
        if counts["FAIL"] or counts["REVIEW_REQUIRED"]:
            add("needs_attention", f"Selected drawing QC has {counts['FAIL']} failed and {counts['REVIEW_REQUIRED']} unresolved checks that need independent review.")
            add("next_steps", "Review the selected drawing-QC findings and resolve failed or unresolved checks in the Finished-plan drawing QC section.")
        add("not_checked", "Drawing coverage beyond the selected QC regions, graphical interpretation and field verification remain unchecked.")
        add("not_checked", "Regulatory compliance and professional acceptance have not been established.")

    if context["scope_status"] == "OUT_OF_SCOPE":
        summary["headline"] = "The declared land is outside this Alberta Crown review scope."
        add("not_checked", "Crown requirements were not selected for the declared land scope.")
        add("next_steps", "Use the requirements and reviewer appropriate to the declared land jurisdiction.")
        return summary

    plan = report.get("plan_type_review") or {}
    missing = set(context["missing_dimensions"] + context["invalid_dimensions"])
    for field in plan.get("missing_or_invalid_fields", []):
        missing.add({"recognized_stage": "stage", "recognized_plan_type": "plan_type"}.get(field, field))
    for field in ("land_class", "review_scope", "regulator", "disposition", "stage", "plan_type", "purpose"):
        if field in missing:
            request(field)

    in_scope = context["scope_status"] == "IN_SCOPE"
    if in_scope and context["regulator"] == "AER" and context["stage"] == "initial":
        if not isinstance(scenario.get("purpose"), str) or not scenario["purpose"].strip():
            request("purpose")
        if not isinstance(scenario.get("subactivity"), str):
            request("subactivity")

    amendment = plan.get("amendment_review") or {}
    route = amendment.get("route")
    if route == "PLAN_OF_RECORD_REQUIRED":
        request("existing_plan_type")
    elif route == "SURVEY_SCOPE_UNRESOLVED":
        length, quarters = scenario.get("existing_length_m"), scenario.get("affected_quarter_sections")
        valid_length = _number(length) and length > 0
        valid_quarters = type(quarters) is int and quarters > 0
        if not valid_length:
            request("existing_length_m")
        if not valid_quarters:
            request("affected_quarter_sections")
        elif valid_length and length == 6500 and quarters <= 2:
            direction = scenario.get("survey_scope_direction")
            if isinstance(direction, str) and direction.strip().casefold() not in {"", "unknown"}:
                add("next_steps", "Review and verify the supplied regulator direction on survey scope at exactly 6,500 metres.")
            else:
                request("survey_scope_direction")
                add("next_steps", "Obtain current regulator direction on survey scope at exactly 6,500 metres.")
            add("needs_attention", "Survey scope at the exact length threshold still needs source-backed direction review.")
    elif route == "FULL_RETRACE_CANDIDATE":
        add("next_steps", "Review the candidate full-retracement scope against the current requirements.")
    elif route == "ITEMIZED_SURVEY_CANDIDATE":
        add("next_steps", "Review the candidate itemized-survey scope and the proposed plan type.")
    elif route in {"AMENDMENT_PLAN_TYPE_UNRESOLVED", "PLAN_VARIANT_REVIEW_REQUIRED"}:
        add("next_steps", "Confirm the applicable amendment or variant requirements with the regulator.")

    renewal = plan.get("renewal_review") or {}
    comparison = renewal.get("comparison", plan.get("table_a2_comparison"))
    if comparison == "DISPOSITION_CHANGE_STATUS_REQUIRED":
        request("disposition_changed")
    elif comparison == "PLAN_OF_RECORD_REQUIRED":
        request("existing_plan_type")
    elif comparison == "LEGACY_ISSUE_DATE_UNRESOLVED":
        request("disposition_issued_on")
    elif comparison == "AMENDMENT_BEFORE_RENEWAL":
        add("needs_attention", "The recorded disposition change needs amendment review before renewal.")
        add("next_steps", "Review the proposed change as an amendment before proceeding with renewal.")
    elif comparison == "TABLE_A2_REQUIRED":
        add("next_steps", "Review the applicable current Table A2 source, reusing a copy already supplied when available.")
    if renewal and comparison in {"TABLE_A2_REQUIRED", "TABLE_A2_ROW_UNRESOLVED"}:
        if not isinstance(scenario.get("purpose"), str) or not scenario["purpose"].strip():
            request("purpose")
        if not isinstance(scenario.get("subactivity"), str):
            request("subactivity")
    if comparison == "MATCHES_TABLE_A2":
        add("checked", "The supplied plan type matches the identified Table A2 row; compliance is still unassessed.")
    elif comparison == "DIFFERS_FROM_TABLE_A2":
        add("needs_attention", "The supplied plan type differs from the identified Table A2 row.")
        add("next_steps", "Review the plan-type difference and any permitted exception with the regulator.")
    elif comparison in {"SURVEY_PLAN_SUBSTITUTION_REVIEW_REQUIRED", "PLAN_VARIANT_REVIEW_REQUIRED", "LEGACY_SKETCH_VARIANCE_REVIEW"}:
        add("needs_attention", "The plan-type substitution, variant or legacy variance needs separate review.")
    elif comparison == "TABLE_A2_ROW_UNRESOLVED":
        add("needs_attention", "An exact Table A2 row has not been resolved.")
        add("next_steps", "Confirm the exact purpose and activity against the supplied Table A2 source.")

    if entries:
        observed = sum(item.get("evidence_status") == "OBSERVED_CANDIDATE" for item in entries)
        basis = "supplied text inventory" if "extraction_status" in report else "supplied evidence"
        kind = "text" if "extraction_status" in report else "evidence"
        noun = "candidate" if observed == 1 else "candidates"
        items = "item" if len(entries) == 1 else "items"
        add("checked", f"Reviewed the {basis} for {len(entries)} candidate review {items}; found {observed} {kind} {noun}.")
        add("needs_attention", "Drawing details still need visual confirmation; text observations do not establish compliance.")
        add("next_steps", "Inspect the drawing details and unresolved evidence identified in the detailed review.")
    workbook = report.get("clause_workbook")
    if workbook is not None:
        add("not_checked", "The clause workbook prepares manual review questions; it does not inspect plan evidence.")
        add("next_steps", "Review the selected workbook questions and resolve their blocked applicability using source-backed facts.")
    unverified_sources = any(item.get("source_status") != "VERIFIED_CURRENT" for item in entries)
    if in_scope and (unverified_sources or workbook is not None or plan.get("regulatory_table_verified") is False):
        add("needs_attention", "The governing requirements have not been verified as current.")
        add("next_steps", "Verify the current sources and their applicability before making regulatory findings.")

    geometry = report.get("survey_geometry_review") or {}
    traverse, polygon = geometry.get("traverse") or {}, geometry.get("polygon") or {}
    if geometry.get("diagnostic_status") == "REPRESENTATION_UNRESOLVED":
        add("not_checked", "Measurements for the unsupported boundary representation were not computed.")
        add("next_steps", "Keep unsupported curves, holes or multipart boundaries intact for specialist review.")
    elif geometry and traverse.get("crs_status") != "VERIFIED":
        add("not_checked", "Geometry measurements remain unresolved because the coordinate reference system is unverified.")
    elif geometry:
        if _number(traverse.get("misclosure_m")):
            add("checked", "Calculated closure from the separately supplied coordinates.")
            if traverse.get("within_supplied_tolerance") is False:
                add("needs_attention", "The supplied traverse misclosure exceeds your tolerance.")
                add("next_steps", "Review the endpoint coordinates and the tolerance you supplied.")
        if polygon.get("crs_status") == "VERIFIED" and _number(polygon.get("area_m2")):
            add("checked", "Calculated area and perimeter for the supplied straight boundary.")
    else:
        add("not_checked", "No supplied-coordinate measurements are recorded.")
    area = geometry.get("area_comparison") or {}
    area_computed = (geometry.get("diagnostic_status") != "REPRESENTATION_UNRESOLVED"
                     and traverse.get("crs_status") == "VERIFIED"
                     and polygon.get("crs_status") == "VERIFIED"
                     and _number(area.get("calculated_ha")))
    ambiguous_area = area.get("comparison") == "AREA_LABEL_UNRESOLVED" or any(
        item.get("requirement_id") == "CANDIDATE-TOTAL-AREA"
        and item.get("evidence_status") == "UNKNOWN"
        and isinstance(item.get("observation"), str)
        and item.get("observation") in _AREA_AMBIGUITIES for item in entries)
    if ambiguous_area:
        add("needs_attention", "The activity total area is ambiguous; its comparison remains unresolved.")
        add("next_steps", "Confirm which activity total area describes the reviewed boundary before comparing areas.")
    elif area_computed and area.get("comparison") == "OUTSIDE_SUPPLIED_TOLERANCE":
        add("needs_attention", "The selected area label differs from the supplied-coordinate area beyond your tolerance.")
        add("next_steps", "Review the selected area label and the separately supplied boundary coordinates.")
    elif area_computed and area.get("comparison") == "WITHIN_SUPPLIED_TOLERANCE":
        add("checked", "Compared the selected area label with the supplied-coordinate area within your tolerance.")

    if not entries and not geometry and workbook is None and finished is None:
        add("not_checked", "No automated drawing checks are recorded.")
    add("not_checked", "No Octopus reconstruction execution is recorded in this review.")
    add("not_checked", "Regulatory compliance and professional acceptance have not been established.")
    if summary["input_requests"]:
        parts = [item["question"].rstrip("?") for item in summary["input_requests"]]
        summary["context_question"] = "Can you confirm the following in one reply: " + "; ".join(
            part[0].lower() + part[1:] for part in parts) + "?"
        summary["headline"] = "The review needs some missing information and independent checks."
        add("needs_attention", "Some information needed for this review is missing or invalid.")
        add("next_steps", "Answer the grouped context question using the application and existing records.")
    elif summary["checked"]:
        summary["headline"] = "The supplied evidence was reviewed; independent checks are still needed."
    else:
        summary["headline"] = "No automated drawing checks are recorded; an assisted review is still possible."
    return summary
