"""Two-sheet LOC and MSL drafting exercises with entirely invented content."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pymupdf as fitz


CASE_IDS = (
    "loc_clean", "msl_rotated_clean", "loc_area_error", "loc_total_conflict",
    "msl_multiple_errors", "loc_rounded_total_control", "loc_raster_note_and_missing_arrow",
)

_NOTE = "DISTANCES ARE IN METRES"
_TOLERANCE_HA = "0.005"
_PREPARED_BY = "Invented drafting fixture author"


@dataclass(frozen=True)
class _Job:
    disposition: str
    identifier: str
    title: str
    revision: str
    scale: str
    denominator: int
    detail_scale: str
    sheet_size: tuple[int, int]
    map_box: tuple[int, int, int, int]
    area_box: tuple[int, int, int, int]
    note_box: tuple[int, int, int, int]
    title_box: tuple[int, int, int, int]


_LOC = _Job("LOC", "LOC910731", "PLAN OF ACCESS ROAD", "C", "1:5,000", 5000, "1:500", (842, 595),
            (40, 78, 556, 389), (580, 78, 800, 207), (580, 234, 800, 319), (580, 414, 800, 542))
_MSL = _Job("MSL", "MSL910842", "PLAN OF WELL SITE", "D", "1 : 2 000", 2000, "1:250", (595, 842),
            (42, 78, 553, 514), (42, 535, 287, 664), (309, 535, 553, 664), (42, 690, 553, 818))


def _job(case_id: str) -> _Job:
    if case_id not in CASE_IDS:
        raise ValueError(f"Unknown invented drafting case: {case_id!r}")
    return _MSL if case_id.startswith("msl_") else _LOC


def job_brief(case_id: str) -> str:
    """Return the same project instructions for every version of each drawing."""
    job = _job(case_id)
    return (
        f"Invented drafting job for {job.identifier}. Use the title {job.title} on the main sheet. "
        f"The main map and title block must identify {job.identifier}. Show current revision {job.revision} "
        f"on both sheets. Label the main view at 1:{job.denominator:,} and the detail at {job.detail_scale}. "
        f"Show the note '{_NOTE}' and a north arrow on the main sheet. Report the parts and total "
        f"in hectares. Any repeated total must agree, and the stated total must be within {_TOLERANCE_HA} ha "
        "of the sum of the parts. These are job instructions for this invented exercise.\n"
    )


def scenario(case_id: str) -> dict:
    """Return the declared Crown context used only for the invented review."""
    return {"land_class": "alberta_crown", "regulator": "AER", "stage": "initial",
            "disposition": _job(case_id).disposition, "plan_type": "sketch"}


def _region(page: fitz.Page, box: fitz.Rect, role: str, label: str | None = None,
            *, complete: bool = True) -> dict:
    region = {"page": page.number + 1, "bbox_points": list(box), "role": role}
    if label is not None:
        region["label"] = label
    if complete:
        region["coverage_review"] = {
            "status": "TEXT_COMPLETE", "reviewer": _PREPARED_BY,
            "method": "VISUAL_TO_TEXT_COMPARISON",
            "statement": "The selected fixture field is wholly represented as native text.",
        }
    return region


def _row(box: fitz.Rect, baseline: float) -> fitz.Rect:
    return fitz.Rect(box.x0 + 7, baseline - 15, box.x1 - 7, baseline + 4)


def _panel(page: fitz.Page, bounds: tuple[int, int, int, int], heading: str) -> fitz.Rect:
    box = fitz.Rect(bounds)
    page.draw_rect(box, width=0.8)
    page.insert_text((box.x0 + 12, box.y0 + 19), heading, fontname="hebo", fontsize=10)
    return box


def _sheet(document: fitz.Document, job: _Job, number: int) -> fitz.Page:
    width, height = job.sheet_size
    page = document.new_page(width=width, height=height)
    page.insert_text((27, 33), "INVENTED DRAFTING EXERCISE", fontname="hebo", fontsize=13)
    page.insert_text((width - 109, 33), f"SHEET {number} OF 2", fontsize=10)
    page.draw_rect(fitz.Rect(25, 52, width - 25, height - 16), width=1.1)
    return page


def _title_block(page: fitz.Page, job: _Job, title: str, revision: str, main_scale: str) -> dict:
    box = fitz.Rect(job.title_box)
    page.draw_rect(box, width=1)
    main = page.number == 0
    scale_label = "MAIN SCALE:" if main else "DETAIL SCALE:"
    rows = (
        (25, title, "plan title", None, 13, "hebo"),
        (46, f"DISPOSITION ID: {job.identifier}", "title block disposition identifier", "DISPOSITION ID:", 11, "helv"),
        (67, f"{scale_label} {main_scale if main else job.detail_scale}", "view scale", scale_label, 11, "helv"),
        (88, f"CURRENT REVISION: {revision}", "current sheet revision", "CURRENT REVISION:", 11, "helv"),
    )
    fields = {}
    for offset, value, role, label, size, font in rows:
        y = box.y0 + offset
        page.insert_text((box.x0 + 12, y), value, fontsize=size, fontname=font)
        page.draw_line((box.x0, y + 5), (box.x1, y + 5), width=0.5)
        fields[role] = _region(page, _row(box, y), role, label)
    page.insert_text((box.x0 + 12, box.y0 + 109), "MAIN PLAN" if main else "ACCESS DETAIL", fontsize=10)
    return fields


def _main_map(page: fitz.Page, job: _Job, identifier: str, show_north_arrow: bool) -> tuple[dict, dict]:
    box = _panel(page, job.map_box, "MAIN PLAN")
    x, y = box.x0 + 31, box.y0 + 66
    line_color = (0.15, 0.26, 0.34)
    if job.disposition == "LOC":
        page.draw_polyline([(x, y + 128), (x + 112, y + 95), (x + 216, y + 114), (x + 335, y + 64)],
                           color=line_color, width=1.2)
        page.draw_polyline([(x + 8, y + 152), (x + 114, y + 119), (x + 217, y + 138), (x + 343, y + 88)],
                           color=line_color, width=1.2)
        identifier_origin = (box.x0 + 13, box.y1 - 17)
        identifier_box = _row(box, identifier_origin[1])
        rotation = 0
    else:
        page.draw_rect(fitz.Rect(x + 118, y + 94, x + 324, y + 260), color=line_color, width=1.2)
        page.draw_line((x + 226, y + 94), (x + 226, y + 260), color=line_color, width=0.8)
        page.draw_polyline([(x + 162, y + 260), (x + 157, y + 302), (x + 84, y + 319)],
                           color=line_color, width=1.2)
        identifier_origin = (box.x1 - 22, box.y1 - 19)
        identifier_box = fitz.Rect(box.x1 - 39, box.y1 - 190, box.x1 - 6, box.y1 - 10)
        rotation = 90
    page.insert_text((x + 124, y + 82), "PART A", fontsize=10)
    page.insert_text((x + 269, y + 155), "PART B", fontsize=10)
    page.insert_text(identifier_origin, f"MAP ID: {identifier}", fontsize=11, rotate=rotation)

    ax, ay = box.x1 - 58, box.y0 + 64
    if show_north_arrow:
        page.draw_line((ax, ay), (ax, ay + 40), width=1.3)
        page.draw_polyline([(ax - 8, ay + 13), (ax, ay), (ax + 8, ay + 13)], width=1.3)
        page.insert_text((ax - 4, ay - 8), "N", fontname="hebo", fontsize=11)
    arrow_box = fitz.Rect(ax - 13, ay - 24, ax + 13, ay + 47)
    return (_region(page, identifier_box, "main map disposition identifier", "MAP ID:"),
            _region(page, arrow_box, "main map north arrow", complete=False))


def _area_table(page: fitz.Page, job: _Job, parts: tuple[str, str], totals: tuple[str, ...]) -> list[dict]:
    box = _panel(page, job.area_box, "AREA SCHEDULE (ha)")
    for label, amount, offset in zip(("PART A:", "PART B:"), parts, (43, 65)):
        page.insert_text((box.x0 + 12, box.y0 + offset), f"{label} {amount} ha", fontsize=11)
    page.draw_line((box.x0, box.y0 + 73), (box.x1, box.y0 + 73), width=0.5)
    for index, amount in enumerate(totals):
        page.insert_text((box.x0 + 12, box.y0 + 91 + 18 * index), f"TOTAL AREA: {amount} ha",
                         fontname="hebo", fontsize=11)
    return [
        _region(page, _row(box, box.y0 + 43), "first area part", "PART A:"),
        _region(page, _row(box, box.y0 + 65), "second area part", "PART B:"),
        _region(page, fitz.Rect(box.x0 + 7, box.y0 + 76, box.x1 - 7, box.y0 + 116),
                "final area total field", "TOTAL AREA:"),
    ]


def _notes(page: fitz.Page, job: _Job, raster: bool) -> dict:
    box = _panel(page, job.note_box, "GENERAL NOTES")
    strip = fitz.Rect(box.x0 + 7, box.y0 + 29, box.x0 + 197, box.y0 + 53)
    if raster:
        with fitz.open() as note_document:
            note_page = note_document.new_page(width=strip.width, height=strip.height)
            note_page.insert_text((5, 16), _NOTE, fontsize=11)
            pixels = note_page.get_pixmap(matrix=fitz.Matrix(2, 2), colorspace=fitz.csGRAY)
            page.insert_image(strip, pixmap=pixels)
    else:
        page.insert_text((strip.x0 + 5, strip.y0 + 16), _NOTE, fontsize=11)
    return _region(page, strip, "general notes units statement", complete=not raster)


def _detail(page: fitz.Page, job: _Job) -> None:
    box = _panel(page, job.map_box, "DETAIL - ACCESS CONNECTION")
    x, y = box.x0 + 74, box.y0 + 82
    page.draw_polyline([(x, y + 131), (x + 134, y + 61), (x + 294, y + 61)], width=1.2)
    page.draw_polyline([(x + 10, y + 155), (x + 140, y + 85), (x + 294, y + 85)], width=1.2)
    page.draw_line((x + 134, y + 22), (x + 134, y + 154), width=0.8, dashes="[6 3] 0")
    page.insert_text((x + 148, y + 45), "CONNECTION POINT", fontsize=10)
    history = _panel(page, job.area_box, "REVISION HISTORY")
    page.insert_text((history.x0 + 12, history.y0 + 43), "HISTORICAL REVISION: B", fontsize=11)
    page.insert_text((history.x0 + 12, history.y0 + 64), "Previous drawing issue", fontsize=10)


def make_drafting_plan(path: Path, case_id: str) -> dict:
    """Write a new invented PDF and bind its seven selected checks to the bytes."""
    job = _job(case_id)
    multiple = case_id == "msl_multiple_errors"
    hybrid = case_id == "loc_raster_note_and_missing_arrow"
    title = _LOC.title if multiple else job.title
    parts = ("0.147", "0.286") if case_id == "loc_rounded_total_control" else ("0.185", "0.245")
    totals = {
        "loc_area_error": ("0.450",),
        "loc_total_conflict": ("0.430", "0.440"),
        "loc_rounded_total_control": ("0.43", "0.430"),
    }.get(case_id, ("0.430",))
    with fitz.open() as document:
        document.set_metadata({"title": "Invented drafting exercise"})
        main = _sheet(document, job, 1)
        block = _title_block(main, job, title, job.revision, "1:250" if multiple else job.scale)
        map_id, arrow = _main_map(main, job, "MSL910843" if multiple else job.identifier, not hybrid)
        units = _notes(main, job, hybrid)
        area = _area_table(main, job, parts, totals)
        detail = _sheet(document, job, 2)
        detail_block = _title_block(detail, job, title, "C" if multiple else job.revision, job.scale)
        _detail(detail, job)
        source = document.tobytes(deflate=True, no_new_id=True)
    with path.open("xb") as output:
        output.write(source)

    checks = [
        {"id": "plan_title", "kind": "required_text", "description": "Main sheet plan title",
         "basis": "Invented job title", "regions": [block["plan title"]], "expected": job.title},
        {"id": "disposition", "kind": "same_text", "description": "Disposition identifier agreement",
         "basis": "The title block and main map identify the same disposition",
         "regions": [block["title block disposition identifier"], map_id]},
        {"id": "revision", "kind": "same_text", "description": "Current revision agreement across sheets",
         "basis": "Both sheets use the same current issue", "regions": [block["current sheet revision"],
                                                                       detail_block["current sheet revision"]]},
        {"id": "main_scale", "kind": "scale", "description": "Main sheet scale label",
         "basis": "Invented job main-view scale", "regions": [block["view scale"]],
         "expected_denominator": job.denominator},
        {"id": "units_note", "kind": "required_text", "description": "Distance units note",
         "basis": "Invented job notes", "regions": [units], "expected": _NOTE},
        {"id": "area_sum", "kind": "decimal_sum", "description": "Area schedule arithmetic",
         "basis": "The invented job specifies consistent totals and a rounding tolerance",
         "regions": area, "unit": "ha", "tolerance": _TOLERANCE_HA},
        {"id": "north_arrow", "kind": "visual", "description": "Main map north arrow",
         "basis": "Invented job main-view graphics", "regions": [arrow]},
    ]
    return {"schema_version": 1, "source_sha256": hashlib.sha256(source).hexdigest(),
            "prepared_by": _PREPARED_BY, "checks": checks}
