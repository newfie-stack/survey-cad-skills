"""Generate invented original PDFs, selections and actual CSVs outside the repo.

The fixed inputs express the fixture author's intent; expected results live in
the separate clause_evidence_truth.json oracle. No reports are synthesized here.
All review declarations concern invented evidence only.
"""
from __future__ import annotations

import argparse
import csv
from hashlib import sha256
import io
import json
from pathlib import Path
import sys

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "engine"))
from runtime_security import load_pdf_runtime

CASE_IDS = (
    "clean_exact_10km", "point_number_gap", "coordinate_precision", "category_unknown",
    "insufficient_observed", "one_cm_outside", "csv_coordinates_differ", "csv_frame_unresolved",
    "incomplete_table", "no_export", "detail_identity_mismatch", "existing_plan_label_mismatch",
    "missing_territory_complete", "missing_territory_unknown", "malformed_scale", "rotated_sheet",
    "alternate_territory_wording", "export_declared_but_not_supplied",
)
_FRAME = "INVENTED NAD83 UTM12 XY grid epoch2002; no actual survey"
_CRS = "INVENTED_PROJECTED_METRIC"


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _coverage(statement: str) -> dict:
    return {"status": "TEXT_COMPLETE", "method": "VISUAL_TO_TEXT_COMPARISON",
            "reviewer": "Invented fixture author", "statement": statement}


def _region(box: list[int], role: str, *, coverage: bool = False) -> dict:
    region = {"page": 1, "bbox_points": box, "role": role}
    if coverage:
        region["coverage_review"] = _coverage("The fixture author reviewed every printed item in this selected invented field.")
    return region


def make_example(folder: str | Path, case_id: str) -> dict[str, Path | None]:
    """Create a fresh invented evidence directory; never overwrite prior inputs."""
    if case_id not in CASE_IDS:
        raise ValueError("Unknown invented clause-evidence example")
    root = Path(folder)
    root.mkdir(parents=True, exist_ok=False)
    pdf = root / "invented-hybrid-plan.pdf"
    brief = root / "job-brief.md"
    brief.write_text(
        "# Invented integration example\n\n"
        "No real land, client or survey. For fixture testing only.\n"
        "The subject is Alberta Crown land, AER LOC, initial application, hybrid plan, "
        "Pipeline/Fresh Water. The activity is in unsurveyed territory. Detail A and its "
        "main-plan reference describe the same invented detail, including the same existing plan.\n"
        "All tabulated points use the same invented projected metric frame. The two OC "
        "records and governing EC record are author-assigned evidence roles for this fixture.\n",
        encoding="utf-8")
    # Each tuple is the original printed ID, northing, easting and category.
    rows = [["1", "6000000.00", "500000.00", "OC"],
            ["2", "6001000.00", "500000.00", "OC"],
            ["3", "6000000.00", "510000.00", "EC"]]
    if case_id == "point_number_gap":
        rows[2][0] = "4"
    if case_id == "coordinate_precision":
        rows[0][2] = "500000.0"
    if case_id == "category_unknown":
        rows[2][3] = "CP"
    if case_id == "insufficient_observed":
        rows[1][3] = "EC"
    if case_id == "one_cm_outside":
        rows[2][2] = "510000.01"
    native_selections = []
    runtime = load_pdf_runtime()
    with runtime.open() as document:
        page = document.new_page(width=700, height=800)
        page.insert_text((50, 38), "INVENTED HYBRID PLAN - NOT A REAL SURVEY", fontsize=12)
        page.insert_text((50, 75), "MAIN SCALE " + ("1:2,50" if case_id == "malformed_scale" else "1:2500"), fontsize=10)
        if case_id not in ("missing_territory_complete", "missing_territory_unknown"):
            page.insert_text((50, 110), "UNSURVEYED LANDS" if case_id == "alternate_territory_wording"
                             else "UNSURVEYED TERRITORY", fontsize=10)
        page.insert_text((50, 145), "DETAIL A", fontsize=10)
        page.insert_text((50, 180), "DETAIL B" if case_id == "detail_identity_mismatch" else "DETAIL A", fontsize=10)
        page.insert_text((50, 220), "PLAN 999 1234", fontsize=10)
        page.insert_text((50, 255), "PLAN 999 1235" if case_id == "existing_plan_label_mismatch" else "PLAN 999 1234", fontsize=10)
        for x, text in ((50, "POINT"), (160, "NORTHING"), (340, "EASTING"), (520, "TYPE")):
            page.insert_text((x, 310), text, fontsize=10)
        for index, values in enumerate(rows):
            y = 345 + 40 * index
            selected = {}
            for field, x, text in zip(("point_id", "northing", "easting", "type"), (50, 160, 340, 520), values):
                page.insert_text((x, y), text, fontsize=10)
                width = 145 if field in ("northing", "easting") else 60
                selected[field] = _region([x - 4, y - 12, x + width, y + 4], "Invented " + field)
            native_selections.append(selected)
        page.insert_text((50, 500), "All coordinates, roles and declarations are invented test data.", fontsize=10)
        if case_id == "rotated_sheet":
            page.set_rotation(90)
        # Suppress random document IDs. No source PDF is committed to the repo.
        pdf.write_bytes(document.tobytes(garbage=4, deflate=True, no_new_id=True))
    digest = sha256(pdf.read_bytes()).hexdigest()
    declarations = {"crs_identifier": _CRS, "coordinate_frame_id": _FRAME, "coordinate_units": "m",
                    "crs_verified": True, "provenance_verified": True, "coordinate_roles_resolved": True}
    hybrid = {**declarations, "schema_version": 1, "source_sha256": digest,
              "prepared_by": "Invented integration fixture author", "rows": native_selections,
              "table_complete": (None if case_id == "incomplete_table" else _coverage(
                  "The complete invented three-row table and every native field were reviewed against this source."))}
    drawing_checks = [
        {"id": "main_scale", "kind": "scale", "description": "Main-plan numerical scale",
         "basis": "Dated1.2.2.3 numerical label only; graphical bar remains manual",
         "regions": [_region([45, 60, 400, 80], "Invented main-plan scale", coverage=True)]},
        {"id": "territory", "kind": "required_text", "description": "Unsurveyed territory annotation",
         "basis": "Dated1.3.3.5 selected body annotation only", "expected": "UNSURVEYED TERRITORY",
         "regions": [_region([45, 95, 400, 116], "Invented main-plan territory note",
                             coverage=case_id != "missing_territory_unknown")]},
        {"id": "detail_refs", "kind": "same_text", "description": "Same detail's paired identities",
         "basis": "Dated1.3.7.1 paired detail/reference text only", "regions": [
             _region([45, 130, 300, 150], "Invented detail identity"),
             _region([45, 165, 300, 185], "Its invented main-plan reference")]},
        {"id": "existing_plan_refs", "kind": "same_text", "description": "Same existing plan's paired labels",
         "basis": "Dated1.3.7.3 paired labels only; plotting remains manual", "regions": [
             _region([45, 205, 300, 225], "Invented existing-plan detail label"),
             _region([45, 240, 300, 260], "Its invented main-plan label")]},
    ]
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(("point_id", "easting", "northing", "type"))
    for index, (identifier, northing, easting, category) in enumerate(rows):
        if case_id == "csv_coordinates_differ" and index == 2:
            easting = "510000.01"
        writer.writerow((identifier, easting, northing, category))
    export_bytes = buffer.getvalue().encode("utf-8")
    export_spec = {**declarations, "schema_version": 1, "format": "CSV_POINT_EXPORT", "origin_kind": "CAD",
                   "source_sha256": sha256(export_bytes).hexdigest(), "complete": True}
    if case_id == "csv_frame_unresolved":
        export_spec["coordinate_frame_id"] = "DIFFERENT INVENTED FRAME - NO TRANSFORM ALLOWED"
    point_export = None
    if case_id not in ("no_export", "export_declared_but_not_supplied"):
        point_export = root / "invented-cad-points.csv"
        point_export.write_bytes(export_bytes)
    spec = {"schema_version": 1, "source_sha256": digest, "prepared_by": "Invented integration fixture author",
            "hybrid_table": hybrid, "point_export": None if case_id == "no_export" else export_spec,
            "drawing": {"spec": {"schema_version": 1, "source_sha256": digest,
                                    "prepared_by": "Invented integration fixture author", "checks": drawing_checks},
                        "bindings": [
                            {"workbook_check_id": "C_1_2_2_3_01", "drawing_check_id": "main_scale"},
                            {"workbook_check_id": "C_1_3_3_5_01", "drawing_check_id": "territory"},
                            {"workbook_check_id": "C_1_3_7_1_02", "drawing_check_id": "detail_refs"},
                            {"workbook_check_id": "C_1_3_7_3_02", "drawing_check_id": "existing_plan_refs"}]}}
    scenario = {"land_class": "alberta_crown", "regulator": "AER", "disposition": "LOC",
                "stage": "initial", "plan_type": "hybrid_plan", "purpose": "Pipeline", "subactivity": "Fresh Water"}
    brief_sha = sha256(brief.read_bytes()).hexdigest()
    facts = {field: {"value": True, "provenance": {"source_id": brief_sha, "locator": "job-brief.md: fixture facts"}}
             for field in ("is_unsurveyed_territory", "has_details", "details_show_existing_plans")}
    files = {"pdf": pdf, "point_export": point_export, "brief": brief,
             "spec": root / "evidence-spec.json", "scenario": root / "scenario.json", "facts": root / "facts.json"}
    for key, value in (("spec", spec), ("scenario", scenario), ("facts", facts)):
        _write_json(files[key], value)
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New directory outside the repository for invented examples")
    parser.add_argument("--case", choices=CASE_IDS)
    args = parser.parse_args(argv)
    target = args.output.resolve()
    if target.is_relative_to(SKILL) or any((parent / ".git").exists() and target.is_relative_to(parent)
                                         for parent in SKILL.parents):
        parser.error("Generated PDFs must stay outside the installed skill and repository")
    if args.case:
        make_example(target, args.case)
    else:
        target.mkdir(parents=True, exist_ok=False)
        for case_id in CASE_IDS:
            make_example(target / case_id, case_id)
    print("Invented evidence generated:", target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
