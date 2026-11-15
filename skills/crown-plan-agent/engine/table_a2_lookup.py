"""Evidence-only Table A2 row lookup; no compliance determinations."""
from __future__ import annotations

import re

PLAN_LABELS = frozenset({"Sketch", "Surveyor Sketch", "Survey", "N/A"})
CONSULTATION_LABELS = frozenset({"PA", "AD", "AA", "N/A", "P/A", "PA*", "AA*", "N/A*"})


def _validate_rows(rows: object, *, plan_content: bool) -> None:
    """Check row shape only, without attesting source, revision or authority.

    Disposition-presence lookup accepts code/row/page records. Plan lookup also
    needs the content it will compare and return. Blank disposition cells exist
    in the supported publication; they must not inherit a neighbouring code.
    """
    if not isinstance(rows, list):
        raise ValueError("Table A2 rows must be a list")
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"Table A2 row {index + 1} must be an object")
        for field in ("row", "page"):
            if type(row.get(field)) is not int or row[field] < 1:
                raise ValueError(f"Table A2 row {index + 1}: {field} must be a positive integer")
        code = row.get("disposition")
        if not isinstance(code, str) or (code.strip() and disposition_code(code) is None):
            raise ValueError(f"Table A2 row {index + 1}: disposition must be blank or a three-letter code")
        if not plan_content:
            continue
        for field in ("purpose", "activity", "survey_monuments"):
            if not isinstance(row.get(field), str):
                raise ValueError(f"Table A2 row {index + 1}: {field} must be a string")
        if not isinstance(row.get("required_plan"), str) or row["required_plan"] not in PLAN_LABELS:
            raise ValueError(f"Table A2 row {index + 1}: unsupported required_plan")
        for field, labels in (("rtf_approval", {"Yes", "No"}),
                              ("rtf_authorization", {"Yes", "No"}),
                              ("consultation", CONSULTATION_LABELS)):
            value = row.get(field)
            if value is not None and (not isinstance(value, str) or value not in labels):
                raise ValueError(f"Table A2 row {index + 1}: unsupported {field}")
        footnote = row.get("footnote")
        if footnote is not None and (type(footnote) is not int or footnote < 1):
            raise ValueError(f"Table A2 row {index + 1}: footnote must be a positive integer or None")
        if row.get("definition") is not None and not isinstance(row["definition"], str):
            raise ValueError(f"Table A2 row {index + 1}: definition must be a string or None")


def disposition_code(value: object) -> str | None:
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z]{3}", value.strip()):
        return value.strip().upper()
    return None


def lookup_plan_requirement(rows: list[dict], *, disposition: str,
                            purpose: str, activity: str) -> dict:
    """Look up a validated row without establishing its current authority.

    Malformed rows raise ValueError before matching, even if they would not
    match this query. Missing query dimensions still return an unresolved result.
    """
    _validate_rows(rows, plan_content=True)
    if (not all(isinstance(v, str) and v.strip()
                for v in (disposition, purpose))
            or not isinstance(activity, str)):
        return {"status": "UNRESOLVED_APPLICABILITY", "matches": []}
    # A blank activity is valid only when explicitly supplied: Table A2 states
    # that a blank activity means the purpose fully describes the disposition.
    matches = [r for r in rows if
               r["disposition"].casefold() == disposition.strip().casefold()
               and r["purpose"].casefold() == purpose.strip().casefold()
               and r["activity"].casefold() == activity.strip().casefold()]
    if len(matches) != 1:
        return {"status": "UNRESOLVED_APPLICABILITY",
                "matches": [{"row": r["row"], "page": r["page"]} for r in matches]}
    row = matches[0]
    return {"status": "SOURCE_ROW_IDENTIFIED_REVIEW_REQUIRED",
            "row": row["row"], "page": row["page"],
            "required_plan": row["required_plan"],
            "survey_monuments": row["survey_monuments"],
            "rtf_approval": row.get("rtf_approval"),
            "rtf_authorization": row.get("rtf_authorization"),
            "consultation": row.get("consultation"),
            "footnote": row.get("footnote"),
            "source": "PLAR Table A2, October 28, 2026",
            "regulatory_compliance": "NOT_ASSESSED"}


def verify_disposition(rows: list[dict], disposition: str | None) -> dict:
    """Confirm a code appears in Table A2; do not infer a required plan."""
    _validate_rows(rows, plan_content=False)
    if not isinstance(disposition, str) or not disposition.strip():
        return {"status": "DISPOSITION_NOT_PROVIDED", "matched_rows": [],
                "regulatory_compliance": "NOT_ASSESSED"}
    code = disposition_code(disposition)
    if code is None:
        return {"status": "INVALID_DISPOSITION_CODE", "matched_rows": [],
                "regulatory_compliance": "NOT_ASSESSED"}
    matches = [{"row": row["row"], "page": row["page"]}
               for row in rows if row["disposition"].strip().upper() == code]
    return {"status": "DISPOSITION_FOUND" if matches else "DISPOSITION_NOT_IN_TABLE_A2",
            "disposition": code, "matched_rows": matches,
            "regulatory_compliance": "NOT_ASSESSED"}
