"""Inspect the invented source directly, independently of drawing QC verdicts."""
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import pymupdf as fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from finished_plan_spec import validate_spec


EXPECTED_CASES = (
    "loc_clean", "msl_rotated_clean", "loc_area_error", "loc_total_conflict",
    "msl_multiple_errors", "loc_rounded_total_control", "loc_raster_note_and_missing_arrow",
)
EXPECTED_KINDS = {
    "plan_title": "required_text", "disposition": "same_text", "revision": "same_text",
    "main_scale": "scale", "units_note": "required_text", "area_sum": "decimal_sum",
    "north_arrow": "visual",
}
NOTE = "DISTANCES ARE IN METRES"


def selected_text(document, region):
    return document[region["page"] - 1].get_text(clip=fitz.Rect(region["bbox_points"])).splitlines()


def render_region(document, region):
    return document[region["page"] - 1].get_pixmap(
        clip=fitz.Rect(region["bbox_points"]), matrix=fitz.Matrix(2, 2), colorspace=fitz.csGRAY,
    )


class DraftingPlanFixtureTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("drafting_plan_fixture"),
                             "The two-layout drafting fixture factory is not implemented")
        import drafting_plan_fixture

        self.fixture = drafting_plan_fixture
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def make_plan(self, case_id):
        directory = self.directory / case_id
        directory.mkdir()
        path = directory / "invented-plan.pdf"
        spec = validate_spec(self.fixture.make_drafting_plan(path, case_id))
        self.assertEqual(spec["source_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        checks = {check["id"]: check for check in spec["checks"]}
        self.assertEqual({key: check["kind"] for key, check in checks.items()}, EXPECTED_KINDS)
        return path, checks

    def test_every_source_has_two_marked_sheets_and_neutral_job_inputs(self):
        self.assertEqual(self.fixture.CASE_IDS, EXPECTED_CASES)
        for case_id in EXPECTED_CASES:
            with self.subTest(case=case_id):
                path, checks = self.make_plan(case_id)
                msl = case_id.startswith("msl_")
                clean_case = "msl_rotated_clean" if msl else "loc_clean"
                brief = self.fixture.job_brief(case_id)
                self.assertEqual(brief, self.fixture.job_brief(clean_case))
                for wanted in (
                    "PLAN OF WELL SITE" if msl else "PLAN OF ACCESS ROAD",
                    "MSL910842" if msl else "LOC910731",
                    "revision D" if msl else "revision C",
                    "1:2,000" if msl else "1:5,000", NOTE, "north arrow", "0.005 ha",
                ):
                    self.assertIn(wanted, brief)
                self.assertEqual(self.fixture.scenario(case_id), {
                    "land_class": "alberta_crown", "regulator": "AER", "stage": "initial",
                    "disposition": "MSL" if msl else "LOC", "plan_type": "sketch",
                })
                with fitz.open(path) as document:
                    self.assertEqual(len(document), 2)
                    for sheet_number, page in enumerate(document, start=1):
                        self.assertEqual((page.rect.width, page.rect.height), (595, 842) if msl else (842, 595))
                        self.assertIn("INVENTED DRAFTING EXERCISE", page.get_text())
                        self.assertIn(f"SHEET {sheet_number} OF 2", page.get_text())
                    public_inputs = (brief, str(document.metadata), *(page.get_text() for page in document),
                                     json.dumps(checks))
                for artifact in public_inputs:
                    for forbidden in (*EXPECTED_CASES, "PASS", "FAIL", "REVIEW_REQUIRED", "known_defects"):
                        self.assertNotIn(forbidden, artifact)

    def test_title_identifiers_current_revisions_and_scales_are_in_distinct_fields(self):
        examples = {
            "loc_clean": ("PLAN OF ACCESS ROAD", "LOC910731", "LOC910731", "C", "C", "1:5,000", "1:500", 5000),
            "msl_rotated_clean": ("PLAN OF WELL SITE", "MSL910842", "MSL910842", "D", "D", "1 : 2 000", "1:250", 2000),
            "msl_multiple_errors": ("PLAN OF ACCESS ROAD", "MSL910842", "MSL910843", "D", "C", "1:250", "1:250", 2000),
        }
        for case_id, (title, block_id, map_id, rev1, rev2, scale, detail, expectation) in examples.items():
            with self.subTest(case=case_id):
                path, checks = self.make_plan(case_id)
                with fitz.open(path) as document:
                    self.assertEqual(selected_text(document, checks["plan_title"]["regions"][0]), [title])
                    ids = checks["disposition"]["regions"]
                    self.assertEqual([region["label"] for region in ids], ["DISPOSITION ID:", "MAP ID:"])
                    self.assertEqual([selected_text(document, region) for region in ids],
                                     [[f"DISPOSITION ID: {block_id}"], [f"MAP ID: {map_id}"]])
                    lines = [line for block in document[0].get_text(
                        "dict", clip=fitz.Rect(ids[1]["bbox_points"]))["blocks"] for line in block["lines"]]
                    self.assertEqual([line["dir"] for line in lines], [(1.0, 0.0) if expectation == 5000 else (0.0, -1.0)])
                    whole_page = document[0].get_text("dict")
                    map_spans = [span for block in whole_page["blocks"] if block["type"] == 0
                                 for line in block["lines"] for span in line["spans"]
                                 if span["text"] == f"MAP ID: {map_id}"]
                    self.assertEqual(len(map_spans), 1)
                    self.assertTrue(fitz.Rect(ids[1]["bbox_points"]).contains(fitz.Rect(map_spans[0]["bbox"])))
                    revisions = checks["revision"]["regions"]
                    self.assertEqual([region["page"] for region in revisions], [1, 2])
                    self.assertEqual([selected_text(document, region) for region in revisions],
                                     [[f"CURRENT REVISION: {rev1}"], [f"CURRENT REVISION: {rev2}"]])
                    self.assertIn("REVISION HISTORY", document[1].get_text())
                    self.assertIn("HISTORICAL REVISION: B", document[1].get_text())
                    self.assertEqual(selected_text(document, checks["main_scale"]["regions"][0]),
                                     [f"MAIN SCALE: {scale}"])
                    self.assertIn(f"DETAIL SCALE: {detail}", document[1].get_text())
                self.assertEqual(checks["main_scale"]["expected_denominator"], expectation)
                self.assertEqual(checks["plan_title"]["expected"],
                                 "PLAN OF ACCESS ROAD" if expectation == 5000 else "PLAN OF WELL SITE")

    def test_area_table_contains_literal_parts_and_explicit_total_candidates(self):
        examples = {
            "loc_clean": ("0.185", "0.245", ["0.430"]),
            "msl_rotated_clean": ("0.185", "0.245", ["0.430"]),
            "loc_area_error": ("0.185", "0.245", ["0.450"]),
            "loc_total_conflict": ("0.185", "0.245", ["0.430", "0.440"]),
            "msl_multiple_errors": ("0.185", "0.245", ["0.430"]),
            "loc_rounded_total_control": ("0.147", "0.286", ["0.43", "0.430"]),
            "loc_raster_note_and_missing_arrow": ("0.185", "0.245", ["0.430"]),
        }
        for case_id, (part_a, part_b, totals) in examples.items():
            with self.subTest(case=case_id):
                path, checks = self.make_plan(case_id)
                area = checks["area_sum"]
                self.assertEqual((area["unit"], area["tolerance"]), ("ha", "0.005"))
                self.assertEqual([region["label"] for region in area["regions"]],
                                 ["PART A:", "PART B:", "TOTAL AREA:"])
                self.assertEqual(area["regions"][-1]["coverage_review"]["status"], "TEXT_COMPLETE")
                with fitz.open(path) as document:
                    self.assertEqual([selected_text(document, region) for region in area["regions"]], [
                        [f"PART A: {part_a} ha"], [f"PART B: {part_b} ha"],
                        [f"TOTAL AREA: {total} ha" for total in totals],
                    ])

    def test_hybrid_uses_a_visible_image_for_the_note_and_has_no_arrow(self):
        clean_path, clean_checks = self.make_plan("loc_clean")
        hybrid_path, hybrid_checks = self.make_plan("loc_raster_note_and_missing_arrow")
        note = hybrid_checks["units_note"]["regions"][0]
        arrow = hybrid_checks["north_arrow"]["regions"][0]
        self.assertEqual(note["bbox_points"], clean_checks["units_note"]["regions"][0]["bbox_points"])
        self.assertEqual(arrow, clean_checks["north_arrow"]["regions"][0])
        self.assertNotIn("coverage_review", note)
        with fitz.open(clean_path) as clean, fitz.open(hybrid_path) as hybrid:
            self.assertEqual(selected_text(clean, note), [NOTE])
            self.assertEqual(selected_text(hybrid, note), [])
            images = hybrid[0].get_image_info()
            self.assertEqual(len(images), 1)
            image_box = fitz.Rect(images[0]["bbox"])
            self.assertTrue(fitz.Rect(note["bbox_points"]).contains(image_box))
            for check_id, check in hybrid_checks.items():
                if check_id != "units_note":
                    for region in check["regions"]:
                        if region["page"] == 1:
                            self.assertFalse(image_box.intersects(fitz.Rect(region["bbox_points"])))
            native_ink = {index for index, shade in enumerate(render_region(clean, note).samples) if shade < 128}
            raster_ink = {index for index, shade in enumerate(render_region(hybrid, note).samples) if shade < 128}
            self.assertGreater(len(native_ink), 200)
            self.assertGreater(len(native_ink & raster_ink) / len(native_ink | raster_ink), 0.9)
            self.assertIn("N", selected_text(clean, arrow))
            self.assertTrue(any(shade < 128 for shade in render_region(clean, arrow).samples))
            self.assertEqual(selected_text(hybrid, arrow), [])
            self.assertEqual(set(render_region(hybrid, arrow).samples), {255})

    def test_frozen_truth_preserves_supported_detections_and_the_graphical_miss(self):
        truth = json.loads((Path(__file__).parent / "fixtures" / "drafting_plan_truth.json").read_text(encoding="utf-8"))
        self.assertEqual(truth["schema_version"], 1)
        self.assertEqual(truth["evidence_class"], "WHOLLY_INVENTED_SYNTHETIC")
        self.assertEqual(truth["independent_reviewer_acceptance"], "NOT_PERFORMED")
        self.assertEqual(truth["categories"], {
            "plan_title": "title", "disposition": "identity", "revision": "revision", "main_scale": "scale",
            "units_note": "notes", "area_sum": "area", "north_arrow": "visual",
        })
        self.assertEqual(set(truth["cases"]), set(EXPECTED_CASES))
        defect_ids = {
            "loc_area_error": ["area_sum"], "loc_total_conflict": ["area_sum"],
            "msl_multiple_errors": ["plan_title", "disposition", "revision", "main_scale"],
            "loc_raster_note_and_missing_arrow": ["north_arrow"],
        }
        for case_id, answer in truth["cases"].items():
            with self.subTest(case=case_id):
                defects = defect_ids.get(case_id, [])
                expected = {key: "FAIL" if key in defects else "PASS" for key in EXPECTED_KINDS}
                expected["north_arrow"] = "REVIEW_REQUIRED"
                self.assertEqual(answer["known_defects"], defects)
                if case_id == "loc_raster_note_and_missing_arrow":
                    expected["units_note"] = "REVIEW_REQUIRED"
                    self.assertEqual(answer["policy_overrides"], {"north_arrow": "capability_gap"})
                else:
                    self.assertNotIn("policy_overrides", answer)
                self.assertEqual(answer["expected"], expected)

    def test_existing_output_is_preserved(self):
        path, _ = self.make_plan("loc_clean")
        original = path.read_bytes()
        with self.assertRaises(FileExistsError):
            self.fixture.make_drafting_plan(path, "msl_rotated_clean")
        self.assertEqual(path.read_bytes(), original)
