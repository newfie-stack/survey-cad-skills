"""Wholly invented plan sheets; no real project data or requirements."""
from __future__ import annotations

import hashlib
from pathlib import Path

import fitz


def region(page, box, label=None, complete=True):
    value = {"page": page, "bbox_points": box, "role": "invented test field"}
    if label is not None:
        value["label"] = label
    if complete:
        value["coverage_review"] = {
            "status": "TEXT_COMPLETE", "reviewer": "synthetic fixture author",
            "method": "VISUAL_TO_TEXT_COMPARISON",
            "statement": "Invented fixture only; selected text/empty region is fully represented."
        }
    return value


def make_plan(path: Path, *, subject="LOT 7", note=True, scale="1:5000",
              total="0.300", inset=True, second_subject=True,
              raster=False, rotated=False, duplicate_total=False,
              split_note=False, alternate_layout=False, north_arrow=True):
    doc = fitz.open()
    page = doc.new_page(width=600, height=700)
    page.insert_text((30, 30), "INVENTED BENCHMARK - NOT A SURVEY PLAN")
    title = "SUBJECT: LOT 7"
    page.insert_text((40, 80), title)
    if second_subject:
        page.insert_text((40, 125), "SUBJECT: " + subject)
    page.insert_text((350, 80), "ADJACENT: LOT 99")
    if scale:
        page.insert_text((40, 170), "SCALE " + scale)
    if inset:
        page.insert_text((350, 170), "INSET SCALE 1:200")
    if note:
        if split_note:
            page.insert_text((40, 215), "DISTANCES ARE", fontname="hebo")
            page.insert_text((135, 215), "IN METRES", fontname="helv")
        else:
            page.insert_text((40, 215), "DISTANCES ARE IN METRES")
    page.insert_text((40, 270), "PART A: 0.100 ha")
    page.insert_text((40, 305), "PART B: 0.200 ha")
    page.insert_text((40, 340), "TOTAL: " + total + " ha")
    if duplicate_total:
        page.insert_text((40, 354), "TOTAL: 0.400 ha")
    # A graphical north arrow; the checker must abstain on semantics.
    if north_arrow:
        page.draw_line((500, 450), (500, 390))
        page.draw_line((500, 390), (490, 410))
        page.draw_line((500, 390), (510, 410))
        page.insert_text((497, 382), "N")
    page.draw_rect(fitz.Rect(40, 400, 300, 590))
    page.insert_text((55, 430), "ILLUSTRATIVE SUBJECT BOUNDARY")
    if raster:
        pix = page.get_pixmap()
        image = pix.tobytes("png")
        doc.close()
        doc = fitz.open()
        page = doc.new_page(width=600, height=700)
        page.insert_image(page.rect, stream=image)
    if rotated:
        page.set_rotation(90)
    # Alternate layout uses a second sheet to exercise page identity.
    if alternate_layout:
        other = doc.new_page(width=600, height=700)
        other.insert_text((40, 80), "SUBJECT: " + subject)
    doc.save(path)
    doc.close()
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    subject_regions = [region(1, [30, 60, 300, 90], "SUBJECT:"),
                       region(2 if alternate_layout else 1,
                              [30, 60, 300, 90] if alternate_layout else [30, 105, 300, 135], "SUBJECT:")]
    checks = [
        {"id": "subject", "kind": "same_text", "description": "Subject identifiers agree",
         "basis": "Internal consistency of two selected subject fields", "regions": subject_regions},
        {"id": "main_scale", "kind": "scale", "description": "Main-plan scale",
         "basis": "Synthetic drafting expectation, not a regulatory clause",
         "regions": [region(1, [30, 150, 300, 180])], "expected_denominator": 5000},
        {"id": "units_note", "kind": "required_text", "description": "Units note",
         "basis": "Synthetic job instruction, not a regulatory clause",
         "regions": [region(1, [30, 195, 300, 225])], "expected": "DISTANCES ARE IN METRES"},
        {"id": "area_sum", "kind": "decimal_sum", "description": "Area total agrees with parts",
         "basis": "Invented job requires one stated total for these selected part rows; internal arithmetic, not a survey boundary area",
         "regions": [region(1, [30, 250, 300, 280], "PART A:"),
                     region(1, [30, 285, 300, 315], "PART B:"),
                     region(1, [30, 320, 300, 365], "TOTAL:")],
         "unit": "ha", "tolerance": "0.000"},
        {"id": "north_arrow", "kind": "visual", "description": "North arrow visual review",
         "basis": "Invented job requires a north arrow in the main view; graphical recognition is outside this deterministic pass",
         "regions": [region(1, [470, 360, 530, 460], complete=False)]},
    ]
    return {"schema_version": 1, "source_sha256": h,
            "prepared_by": "synthetic fixture author", "checks": checks}
