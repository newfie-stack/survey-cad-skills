"""Bounded, non-normative Canada Lands routing and workspace arithmetic.

This does not inspect drawings, establish land rights, or certify compliance.
All regulatory applicability remains REVIEW_REQUIRED until source/plan review.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any

MAX_INPUT_BYTES = 262_144
BOOKKEEPING_ROUNDING_HA = Decimal("0.0001")
# Defensive arithmetic bound, not a land-area regulation or survey tolerance.
MAX_INPUT_AREA_HA = Decimal("1000000000000")


def _area(value: Any) -> Decimal:
    """Convert text/number to a finite nonnegative hectare quantity."""
    if isinstance(value, bool) or value is None:
        raise ValueError("Area must be a finite nonnegative number in hectares.")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Area must be a finite nonnegative number in hectares.") from exc
    if not result.is_finite() or result < 0:
        raise ValueError("Area must be a finite nonnegative number in hectares.")
    if result > MAX_INPUT_AREA_HA:
        raise ValueError("Area exceeds defensive numeric input bound; verify source units.")
    return result


def check_workspace_areas(workspace: dict[str, Any] | None) -> dict[str, Any]:
    """Check only the arithmetic of an explicitly supplied area register.

    The tolerance accounts for four-decimal-place hectare tabulation, not any
    survey or positional closure tolerance. No geometry is derived here.
    """
    if workspace is None:
        return {"status": "REVIEW_REQUIRED", "reason": "No area register supplied."}
    if not isinstance(workspace, dict):
        return {"status": "REVIEW_REQUIRED", "reason": "Area register must be an object."}
    needed = ("total_ha", "within_row_ha", "outside_row_ha")
    if any(key not in workspace for key in needed):
        return {"status": "REVIEW_REQUIRED", "reason": "Incomplete total/within/outside area register."}
    try:
        total, within, outside = (_area(workspace[key]) for key in needed)
    except ValueError as exc:
        return {"status": "REVIEW_REQUIRED", "reason": str(exc)}
    difference = total - within - outside
    if abs(difference) <= BOOKKEEPING_ROUNDING_HA:
        return {
            "status": "PASS",
            "reason": "Supplied hectare figures reconcile within tabulation rounding.",
            "difference_ha": str(difference),
            "check_type": "arithmetic_only",
        }
    return {
        "status": "FAIL",
        "reason": "Supplied total differs from within-ROW plus outside-ROW quantities.",
        "difference_ha": str(difference),
        "check_type": "arithmetic_only",
    }


def triage(case: dict[str, Any]) -> dict[str, Any]:
    """Choose a *candidate* process without asserting an applicable legal rule."""
    if not isinstance(case, dict):
        raise ValueError("Case input must be a JSON object.")

    land_class = case.get("land_class", "unknown")
    iogc = case.get("iogc_confirmed")
    purpose = case.get("purpose", "unknown")
    document = case.get("document_type", "unknown")
    if any(not isinstance(item, str) for item in (land_class, purpose, document)):
        raise ValueError("land_class, purpose and document_type must be strings.")
    if iogc is not None and not isinstance(iogc, bool):
        raise ValueError("iogc_confirmed must be true, false or null.")

    if land_class == "provincial_crown":
        candidate, why = (
            "route_to_provincial_crown_agent",
            "Provincial Crown lands are outside this skill's Canada Lands scope.",
        )
        status = "NOT_APPLICABLE"
    elif land_class not in {"first_nation_reserve", "other_canada_lands"}:
        candidate, why = (
            "verify_land_class",
            "Canada Lands jurisdiction has not been established.",
        )
        status = "REVIEW_REQUIRED"
    elif land_class != "first_nation_reserve" or iogc is not True:
        candidate, why = (
            "verify_administrator_and_standards",
            "IOGC jurisdiction is not confirmed; use the governing land regime.",
        )
        status = "REVIEW_REQUIRED"
    elif purpose == "off_lease_remediation":
        candidate, why = (
            "consider_iogc_surface_permit",
            "IOGC identifies short-term off-lease remediation as a possible Surface Permit activity.",
        )
        status = "REVIEW_REQUIRED"
    elif purpose == "new_permanent_land":
        candidate, why = (
            "consider_surface_contract_amendment",
            "New permanent contract lands may require an amendment and survey.",
        )
        status = "REVIEW_REQUIRED"
    elif purpose == "partial_surrender":
        candidate, why = (
            "consider_partial_surrender_survey",
            "Retained and surrendered land extents require plan-type review.",
        )
        status = "REVIEW_REQUIRED"
    elif purpose in {"reclamation", "remediation", "existing_asbuilt"}:
        candidate, why = (
            "determine_underlying_transaction",
            "The work purpose or as-built alone does not establish a tenure amendment.",
        )
        status = "REVIEW_REQUIRED"
    else:
        candidate, why = (
            "confirm_transaction",
            "A documented transaction is needed before choosing a survey route.",
        )
        status = "REVIEW_REQUIRED"

    ia_applicability = "NOT_APPLICABLE" if status == "NOT_APPLICABLE" else "REVIEW_REQUIRED"
    if land_class == "first_nation_reserve" and iogc is True:
        if document in {"surface_permit_sketch", "asbuilt_exhibit"}:
            ia_note = "Do not automatically apply the formal survey-plan IA table rule to a sketch or exhibit."
        elif document in {"application_survey_plan", "clsr_survey_plan"}:
            ia_note = "Check the applicable IOGC Surface Lease/ROW IA table criteria against the current instructions."
        else:
            ia_note = "Identify the document type before deciding whether an IA table is required."
    else:
        ia_note = "IOGC plan-specific IA requirements have not been established."

    return {
        "candidate_route": candidate,
        "route_status": status,
        "route_reason": why,
        "iogc_incidental_activities_table_applicability": ia_applicability,
        "ia_basis_note": ia_note,
        "area_arithmetic": check_workspace_areas(case.get("workspace_area")),
        "regulatory_acceptance": "NOT_ASSESSED",
        "plan_visual_review": "NOT_EXECUTED",
        "source_rule_verification": "REVIEW_REQUIRED",
        "warning": "Candidate route only; verify current sources, contract, First Nation requirements and survey instructions.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_json", type=Path, help="Private local JSON case input")
    args = parser.parse_args()
    try:
        if args.case_json.stat().st_size > MAX_INPUT_BYTES:
            raise ValueError("Case JSON exceeds the size limit.")
        case = json.loads(args.case_json.read_text(encoding="utf-8"))
        result = triage(case)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        parser.exit(status=2, message=f"Invalid case input: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
