"""Create review-only observations from a PDF inventory.

Only explicit text candidate matches are recorded. Absence of a text match
means unknown, not proof that a graphical element is missing.
"""
from __future__ import annotations

import re
from area_table import TOTAL_AREA, total_area_evidence
from deficiency_report import build_ledger

NUMERICAL_SCALE = re.compile(
    r"^\s*(?:SCALE\s*[:=]?\s*)?1\s*:\s*[1-9]\d*(?:[ ,]\d{3})*(?![\d.,])\b",
    re.IGNORECASE,
)
PLAN_HEADINGS = {"sketch": "sketch", "surveyor_sketch": "surveyor sketch",
                 "survey_plan": "survey", "hybrid_plan": "hybrid",
                 "compiled_plan": "compiled"}
ORDINARY_HEADINGS = {"sketch", "surveyor sketch", "survey"}
PLAN_SHOWING_HEADING = re.compile(
    r"(?:(sketch|surveyor sketch|survey) plan showing|plan of (survey) showing)\b\s*:?\s*.*")
VARIANT_HEADINGS = {
    "hybrid": re.compile(r"plan showing survey \(hybrid\) of\b\s*:?\s*.*"),
    "compiled": re.compile(r"compiled plan from existing surveys for the purpose of\b\s*:?\s*.*"),
}


def normalized_text(value: object) -> str:
    return " ".join(value.casefold().split()) if isinstance(value, str) else ""


def recognized_heading(candidate: str) -> str | None:
    """Identify supported whole-span title candidates, including cited variants.

    Short ordinary labels are retained for compatibility. Bare variant names
    never count as the more specific prescribed hybrid or compiled headings.
    """
    if candidate in ORDINARY_HEADINGS:
        return candidate
    heading = PLAN_SHOWING_HEADING.fullmatch(candidate)
    if heading:
        return heading[1] or heading[2]
    return next((kind for kind, pattern in VARIANT_HEADINGS.items()
                 if pattern.fullmatch(candidate)), None)


def inventory_review(inventory: dict, scenario: dict, rules: list[dict]) -> dict:
    if not isinstance(inventory, dict) or not isinstance(inventory.get("spans"), list):
        raise TypeError("Expected PDF inventory with text spans")
    observations = {}
    for rule in rules:
        key = rule.get("evidence_key")
        phrases = rule.get("text_candidates", [])
        method = rule.get("check_method", "text")
        if not isinstance(phrases, list) or not all(isinstance(x, str) and x.strip() for x in phrases):
            raise ValueError("text_candidates must be nonempty strings")
        if method == "visual" or (method == "text" and not phrases):
            continue
        expected = (PLAN_HEADINGS.get(normalized_text(scenario.get("plan_type")), "")
                    if method == "plan_heading" else normalized_text(scenario.get(key)))
        recognized_headings = set()
        area_ambiguity = None
        matches = []
        for span in inventory["spans"]:
            text = span.get("text", "")
            if not isinstance(text, str):
                continue
            if method == "numerical_scale":
                matched = NUMERICAL_SCALE.search(text) is not None
            elif method == "total_area":
                area_match = TOTAL_AREA.fullmatch(text.strip())
                matched = area_match is not None
            elif method in ("plan_heading", "scenario_text"):
                candidate = normalized_text(text)
                if method == "plan_heading":
                    candidate = recognized_heading(candidate)
                    if candidate is not None:
                        recognized_headings.add(candidate)
                if method == "scenario_text":
                    label = key.removesuffix("_name")
                    candidate = re.sub(rf"^{re.escape(label)}(?: name)?\s*:\s*", "", candidate)
                matched = bool(expected) and candidate == expected
            else:
                matched = any(term.casefold() in text.casefold() for term in phrases)
            if matched:
                matches.append(span)
        if method == "total_area":
            matches, area_ambiguity = total_area_evidence(inventory["spans"])
        if len(recognized_headings) > 1:
            observations[key] = {"observation": "Multiple different plan-type labels found. Confirm the main heading."}
        elif area_ambiguity:
            observations[key] = {"observation": area_ambiguity}
        elif matches:
            first = matches[0]
            observations[key] = {
                "present": True,
                "source_filename": inventory.get("source_filename"),
                "page": first.get("page"),
                "bbox_points": first.get("bbox_points"),
                "observation": first.get("text"),
                "source_text": first.get("cell_text", first.get("text")),
                "candidate_count": len(matches),
                "candidate_pages": sorted({span["page"] for span in matches
                                           if type(span.get("page")) is int}),
            }
    result = build_ledger(scenario, rules, observations)
    result["source_sha256"] = inventory.get("source_sha256")
    result["extraction_status"] = inventory.get("status", "UNKNOWN")
    result["limitations"] = [
        "Text candidate matches are not visual feature verification",
        "Unmatched text remains UNKNOWN, never regulatory FAIL",
        "Regulatory source applicability has not been verified",
    ]
    return result
