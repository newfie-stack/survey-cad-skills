"""Wholly invented area schedules; no real drawing or project content.

One reallocation changes two summary amounts while every parcel row and the
grand total remain unchanged. Selected checks are returned to the test author;
they are never embedded in the PDF or reviewer job brief.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pymupdf as pdf


CASE_IDS = ("area_split_clean", "area_split_shift")
_ROWS = (
    ("PARCEL A", "0.135", "0.210", "0.345"),
    ("PARCEL B", "0.245", "0.090", "0.335"),
    ("PARCEL C", "0.320", "0.150", "0.470"),
)


def _validate_case(case_id: str) -> None:
    if case_id not in CASE_IDS:
        raise ValueError(f"Unknown invented area-schedule case: {case_id!r}")


def job_brief(case_id: str) -> str:
    """Identical ordinary review context for both versions; no defect hint."""
    _validate_case(case_id)
    return (
        "# Invented office drawing review\n\n"
        "Review issue D4 of schedule AX-572 against its own printed information. "
        "The three parcels and the locator diagram are wholly invented. Areas "
        "are in hectares. The locator is diagrammatic and not to scale; no "
        "survey geometry, external records or regulatory decision is required. "
        "Report discrepancies with their source locations and retain anything "
        "you cannot verify as unresolved.\n"
    )


def _text(page, x, y, value, *, bold=False, size=11):
    page.insert_text((x, y), value, fontname="hebo" if bold else "helv", fontsize=size)


def _value(page, x, y, amount, role):
    _text(page, x, y, f"{amount} ha")
    return {"page": 1, "bbox_points": [x - 2, y - 13, x + 74, y + 4], "role": role}


def _sum(cid, description, parts, total, tolerance):
    return {
        "id": cid, "kind": "decimal_sum", "description": description,
        "basis": (
            "Same-subject, same-unit invented schedule arithmetic. The tolerance "
            "is the sum of half-unit rounding bounds for the selected 0.001 ha "
            "printed cells, not a survey-area tolerance."
        ),
        "regions": [*parts, total], "unit": "ha", "tolerance": tolerance,
    }


def make_plan(path: Path, case_id: str) -> dict:
    """Write a new native-text PDF and return source-bound selected checks."""
    _validate_case(case_id)
    new_total, existing_total = ("0.820", "0.330") if case_id == "area_split_shift" else ("0.700", "0.450")
    fields = {"new": [], "existing": [], "parcel": []}
    with pdf.open() as document:
        document.set_metadata({"title": "Invented area schedule", "author": "Invented Test Office"})
        page = document.new_page(width=1000, height=700)
        page.draw_rect(pdf.Rect(24, 24, 976, 676))
        _text(page, 42, 54, "INVENTED DRAWING - NOT A SURVEY PLAN", bold=True, size=16)
        _text(page, 42, 84, "Office area schedule / AX-572 / issue D4", size=14)
        _text(page, 42, 116, "PARCEL AREA SCHEDULE", bold=True)
        for x, heading in ((42, "PARCEL"), (212, "NEW CUT"), (345, "EXISTING CLEARING"), (505, "TOTAL")):
            _text(page, x, 148, heading, bold=True, size=10)
        for i, (name, new, existing, total) in enumerate(_ROWS):
            y = 184 + i * 46
            _text(page, 42, y, name)
            fields["new"].append(_value(page, 212, y, new, name + " new cut"))
            fields["existing"].append(_value(page, 345, y, existing, name + " existing clearing"))
            fields["parcel"].append(_value(page, 505, y, total, name + " total area"))
        page.draw_rect(pdf.Rect(646, 120, 958, 326))
        _text(page, 663, 146, "AREA SUMMARY", bold=True)
        _text(page, 663, 184, "NEW CUT:")
        summary_new = _value(page, 868, 184, new_total, "Summary new-cut area")
        _text(page, 663, 230, "EXISTING CLEARING:")
        summary_existing = _value(page, 868, 230, existing_total, "Summary existing-clearing area")
        page.draw_line((656, 254), (948, 254))
        _text(page, 663, 286, "GRAND TOTAL:", bold=True)
        grand = _value(page, 868, 286, "1.150", "Summary grand total")

        _text(page, 42, 376, "PARCEL LOCATOR - NOT TO SCALE", bold=True)
        for x, label in ((42, "A"), (221, "B"), (400, "C")):
            page.draw_rect(pdf.Rect(x, 400, x + 145, 530))
            _text(page, x + 63, 470, label, bold=True, size=18)
        _text(page, 42, 578, "Locator boxes identify schedule rows; their dimensions do not represent the stated areas.", size=10)
        _text(page, 663, 376, "OFFICE NOTES", bold=True)
        _text(page, 663, 406, "Areas shown in hectares.")
        _text(page, 663, 436, "Schedule AX-572 / current issue D4.")
        _text(page, 663, 466, "All identities and quantities are invented.", size=10)
        _text(page, 42, 650, "Synthetic QA exercise / sheet 1 of 1", size=10)
        contents = document.tobytes(garbage=4, deflate=True, no_new_id=True)
    with Path(path).open("xb") as target:
        target.write(contents)
    checks = [
        _sum("grand_total", "Displayed category summaries add to grand total",
             [summary_new, summary_existing], grand, "0.0015"),
        _sum("parcel_total", "Displayed parcel totals add to grand total", fields["parcel"], grand, "0.0020"),
        _sum("new_cut_sum", "New-cut parcel amounts agree with their category summary",
             fields["new"], summary_new, "0.0020"),
        _sum("existing_clearing_sum", "Existing-clearing parcel amounts agree with their category summary",
             fields["existing"], summary_existing, "0.0020"),
    ]
    return {"schema_version": 1, "source_sha256": hashlib.sha256(contents).hexdigest(),
            "prepared_by": "Invented area-schedule fixture author", "checks": checks}
