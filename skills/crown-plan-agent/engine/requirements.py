"""Offline Crown plan applicability and evidence-gate engine.

Source catalogue is an historical inventory, not a live legal authority.
No user documents or private plans are loaded by this module.
"""
from __future__ import annotations
import json
from pathlib import Path

from table_a2_lookup import disposition_code

ROOT = Path(__file__).resolve().parent
STATUSES = {"PASS", "FAIL", "REVIEW_REQUIRED", "NOT_APPLICABLE"}
PLAN_TYPES = {"sketch", "surveyor_sketch", "survey_plan", "hybrid_plan", "compiled_plan"}
STAGES = frozenset({"initial", "amendment", "renewal"})
REGULATORS = frozenset({"AER", "Alberta"})
OUT_OF_SCOPE_LAND_CLASSES = frozenset({"private", "municipal", "federal", "other"})


def load_catalog(path: Path | None = None) -> dict:
    data = json.loads((path or ROOT / "source_catalog.json").read_text(encoding="utf-8"))
    if not isinstance(data.get("sources"), list):
        raise ValueError("Invalid source catalog")
    return data


def jurisdiction_scope(scenario: dict) -> dict:
    """Resolve the declared Crown review scope, without inferring land ownership.

    Mixed-land plans may select Crown candidates only for an explicitly named
    Alberta Crown component. A regulator or disposition code cannot establish
    jurisdiction in place of a land-class declaration.
    """
    land_class = scenario.get("land_class")
    review_scope = scenario.get("review_scope")
    if isinstance(land_class, str):
        land_class = land_class.strip()
    if isinstance(review_scope, str):
        review_scope = review_scope.strip()
    missing = []
    invalid = []
    status = "UNRESOLVED_SCOPE"
    if land_class is None or (isinstance(land_class, str) and land_class in ("", "unknown")):
        missing.append("land_class")
    elif not isinstance(land_class, str):
        invalid.append("land_class")
    elif land_class in OUT_OF_SCOPE_LAND_CLASSES:
        status = "OUT_OF_SCOPE"
    elif land_class == "alberta_crown":
        status = "IN_SCOPE"
    elif land_class == "mixed":
        if review_scope is None or (isinstance(review_scope, str) and review_scope in ("", "unknown")):
            missing.append("review_scope")
        elif review_scope == "alberta_crown_component":
            status = "IN_SCOPE"
        else:
            invalid.append("review_scope")
    else:
        invalid.append("land_class")
    return {"scope_status": status, "land_class": land_class, "review_scope": review_scope,
            "missing_scope_dimensions": missing, "invalid_scope_dimensions": invalid}


def application_context(scenario: dict) -> dict:
    """Validate supported context before selecting any requirement candidates.

    AER and Alberta are the supported regulator labels. Other labels remain
    unresolved. A three-letter disposition code is only a syntax check, not
    confirmation of its authority, jurisdiction or presence in a PLAR table.
    Scope dimensions join the existing dimension gates so wildcard requirements
    cannot select Crown candidates for unknown or unsupported land classes.
    """
    if not isinstance(scenario, dict):
        raise TypeError("Scenario must be an object")
    context = {"regulator": scenario.get("regulator"),
               "disposition": scenario.get("disposition", scenario.get("activity")),
               "stage": scenario.get("stage"), "plan_type": scenario.get("plan_type")}
    missing = []
    invalid = []
    supported = {"regulator": REGULATORS, "stage": STAGES, "plan_type": PLAN_TYPES}
    for field, value in context.items():
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)
        elif field == "disposition":
            context[field] = disposition_code(value)
            if context[field] is None:
                invalid.append(field)
        elif not isinstance(value, str) or value.strip() not in supported[field]:
            invalid.append(field)
        else:
            context[field] = value.strip()
    if ("disposition" in scenario and "activity" in scenario
            and context["disposition"] is not None
            and disposition_code(scenario["activity"]) != context["disposition"]):
        invalid.append("disposition")
    scope = jurisdiction_scope(scenario)
    return {**context, **scope,
            "missing_dimensions": missing + scope["missing_scope_dimensions"],
            "invalid_dimensions": sorted(set(invalid + scope["invalid_scope_dimensions"]))}


def applicability(scenario: dict) -> dict:
    """Return candidate 2024 content sections; never certify current authority."""
    context = application_context(scenario)
    scope = {key: context[key] for key in ("scope_status", "land_class", "review_scope")}
    if context["scope_status"] == "OUT_OF_SCOPE":
        return {"status": "REVIEW_REQUIRED", "sections": [], **scope,
                "applicability_status": "OUT_OF_SCOPE",
                "missing_dimensions": context["missing_dimensions"],
                "invalid_dimensions": context["invalid_dimensions"],
                "reason": "Declared land class is outside the Alberta Crown review scope"}
    if context["missing_dimensions"] or context["invalid_dimensions"]:
        return {"status": "REVIEW_REQUIRED", "sections": [], **scope,
                "applicability_status": "UNRESOLVED_APPLICABILITY",
                "missing_dimensions": context["missing_dimensions"],
                "invalid_dimensions": context["invalid_dimensions"],
                "reason": "Unresolved application context"}
    kind = context["plan_type"]
    sections = ["Part 1"]
    if kind in {"sketch", "surveyor_sketch"}:
        sections.append("Part 2")
    else:
        sections.append("Part 3")
    if context["disposition"] in {"PLA", "DPL", "LOC", "DLO", "EZE", "REA", "VCE", "RVC"}:
        sections.append("Part 4.1")
    if (context["stage"] in {"amendment", "renewal"}
            and kind not in {"sketch", "surveyor_sketch", "compiled_plan"}):
        sections.append("Part 3.3")
    return {"status": "REVIEW_REQUIRED", "sections": sections, **scope,
            "reason": "Applicability is provisional pending live source and activity verification"}


def evaluate(rule: dict, evidence: dict, current_authority_verified: bool = False) -> dict:
    """Keep observed evidence distinct from normative compliance.

    Rules must specify a concrete evidence key. Missing or ambiguous evidence
    cannot be marked PASS. Only current verified authority permits legal PASS/FAIL.
    """
    if type(current_authority_verified) is not bool:
        raise TypeError("Current-authority attestation must be an explicit boolean")
    key = rule.get("evidence_key")
    if not isinstance(key, str) or not key:
        raise ValueError("Rule requires evidence_key")
    value = evidence.get(key)
    observed = value is not None
    source_status = "VERIFIED_CURRENT" if current_authority_verified else "UNVERIFIED_CURRENT"
    if not observed:
        evidence_status = "REVIEW_REQUIRED"
    elif value is False:
        evidence_status = "FAIL"
    elif value is True:
        evidence_status = "PASS"
    else:
        evidence_status = "REVIEW_REQUIRED"
    status = evidence_status if current_authority_verified else "REVIEW_REQUIRED"
    return {"rule_id": rule.get("id"), "source_status": source_status,
            "evidence_status": evidence_status, "status": status}


def inspect_text(text: str, keywords: dict[str, tuple[str, ...]]) -> dict:
    """Locate text candidates, not certify visual presence or regulatory PASS."""
    if not isinstance(text, str):
        raise TypeError("Text must be a string")
    folded = " ".join(text.casefold().split())
    return {key: {"found_in_text": any(token.casefold() in folded for token in terms),
                  "status": "REVIEW_REQUIRED"} for key, terms in keywords.items()}
