"""A correct grand total must not hide a shifted category breakdown.

The literals and expected verdicts here are hand-derived, not read back from
the fixture's specification. This is selected-region regression coverage;
the answer-free export is available for a separate assisted review.
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from finished_plan_review import render_finished_plan, review_finished_plan
from review_cli import main as review_main


class AreaClassificationRegressionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(
            importlib.util.find_spec("area_classification_fixture"),
            "The invented category-breakdown regression fixture is missing",
        )
        import area_classification_fixture

        self.fixture = area_classification_fixture
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def make(self, case):
        path = self.root / f"{case}.pdf"
        spec = self.fixture.make_plan(path, case)
        self.assertEqual(spec["source_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        return path, spec

    def test_category_shift_is_detected_while_both_grand_total_checks_pass(self):
        path, spec = self.make("area_split_shift")
        report = review_finished_plan(path, spec)
        actual = {item["check_id"]: item for item in report["findings"]}
        self.assertEqual({key: item["status"] for key, item in actual.items()}, {
            "grand_total": "PASS", "parcel_total": "PASS",
            "new_cut_sum": "FAIL", "existing_clearing_sum": "FAIL",
        })
        self.assertEqual(actual["new_cut_sum"]["expected"], "0.700")
        self.assertEqual(actual["new_cut_sum"]["observed"], ["0.135", "0.245", "0.320", "0.820"])
        self.assertEqual(actual["existing_clearing_sum"]["expected"], "0.450")
        self.assertEqual(actual["existing_clearing_sum"]["observed"], ["0.210", "0.090", "0.150", "0.330"])
        for key in ("new_cut_sum", "existing_clearing_sum"):
            self.assertEqual(actual[key]["difference"], "0.120")
            self.assertEqual(actual[key]["tolerance"], "0.0020")
        self.assertEqual(report["overall_status"], "REVIEW_REQUIRED")
        self.assertEqual(report["regulatory_status"], "NOT_ASSESSED")

    def test_clean_breakdown_has_no_failed_comparisons(self):
        path, spec = self.make("area_split_clean")
        report = review_finished_plan(path, spec)
        self.assertEqual({item["check_id"]: item["status"] for item in report["findings"]}, {
            "grand_total": "PASS", "parcel_total": "PASS",
            "new_cut_sum": "PASS", "existing_clearing_sum": "PASS",
        })

    def test_total_only_selection_does_not_claim_to_discover_unselected_categories(self):
        path, spec = self.make("area_split_shift")
        totals_only = copy.deepcopy(spec)
        totals_only["checks"] = [check for check in spec["checks"]
                                 if check["id"] in {"grand_total", "parcel_total"}]
        report = review_finished_plan(path, totals_only)
        self.assertEqual({item["check_id"]: item["status"] for item in report["findings"]},
                         {"grand_total": "PASS", "parcel_total": "PASS"})
        self.assertEqual(report["overall_status"], "REVIEW_REQUIRED")

    def test_original_pdf_rows_and_grand_total_are_unchanged_between_versions(self):
        for case, new_total, existing_total in (
            ("area_split_clean", "0.700", "0.450"),
            ("area_split_shift", "0.820", "0.330"),
        ):
            with self.subTest(case=case):
                path, _ = self.make(case)
                with pymupdf.open(path) as document:
                    text = " ".join(document[0].get_text().split())
                    self.assertIn("INVENTED", text)
                    self.assertIn("PARCEL A 0.135 ha 0.210 ha 0.345 ha", text)
                    self.assertIn("PARCEL B 0.245 ha 0.090 ha 0.335 ha", text)
                    self.assertIn("PARCEL C 0.320 ha 0.150 ha 0.470 ha", text)
                    self.assertIn(f"NEW CUT: {new_total} ha", text)
                    self.assertIn(f"EXISTING CLEARING: {existing_total} ha", text)
                    self.assertIn("GRAND TOTAL: 1.150 ha", text)
                    self.assertEqual(document.embfile_names(), [])
                    pixels = document[0].get_pixmap(matrix=pymupdf.Matrix(1, 1))
                    self.assertGreater(pixels.width * pixels.height, 0)

    def test_frozen_truth_records_one_reallocation_issue_not_two_defects(self):
        truth = json.loads((Path(__file__).parent / "fixtures" / "area_classification_truth.json").read_text())
        self.assertEqual(truth["evidence_class"], "WHOLLY_INVENTED_SYNTHETIC")
        self.assertEqual(truth["cases"]["area_split_clean"]["known_issues"], [])
        case = truth["cases"]["area_split_shift"]
        self.assertEqual(len(case["known_issues"]), 1)
        issue, = case["known_issues"]
        self.assertEqual(set(issue["affected_checks"]), {"new_cut_sum", "existing_clearing_sum"})
        for case_id, expected in truth["cases"].items():
            with self.subTest(case=case_id):
                path, spec = self.make(case_id)
                report = review_finished_plan(path, spec)
                actual = {item["check_id"]: item["status"] for item in report["findings"]}
                self.assertEqual(actual, expected["expected_checks"])
                detected = [item["id"] for item in expected["known_issues"]
                            if all(actual[key] == "FAIL" for key in item["affected_checks"])]
                self.assertEqual(len(detected), 0 if case_id == "area_split_clean" else 1)

    def test_existing_cli_reports_categories_without_rejecting_the_correct_grand_total(self):
        path, spec = self.make("area_split_shift")
        spec_path, scenario, output = (self.root / name for name in ("checks.json", "scenario.json", "review.md"))
        spec_path.write_text(json.dumps(spec))
        scenario.write_text(json.dumps({"land_class": "alberta_crown", "regulator": "AER",
                                        "stage": "initial", "disposition": "LOC", "plan_type": "sketch"}))
        with contextlib.redirect_stdout(io.StringIO()):
            exit_code = review_main([str(path), "--scenario", str(scenario), "--finished-plan-spec", str(spec_path),
                                     "--offline", "--reference-cache", str(self.root / "empty-cache"),
                                     "--output", str(output)])
        self.assertEqual(exit_code, 0)
        report = review_finished_plan(path, spec)
        self.assertIn(render_finished_plan(report), output.read_text())

    def test_exported_review_packet_is_neutral_and_contains_no_selectors_or_answers(self):
        from export_drafting_exercise import export_exercise

        packets = []
        for case in ("area_split_clean", "area_split_shift"):
            destination = self.root / case
            try:
                manifest = export_exercise(destination, case)
            except ValueError as error:
                self.fail(f"The existing exercise exporter does not support the category regression: {error}")
            packet = destination / "review_inputs"
            self.assertEqual({path.name for path in packet.iterdir()}, {"plan.pdf", "job-brief.md", "REVIEW.md"})
            with pymupdf.open(packet / "plan.pdf") as document:
                contents = " ".join(page.get_text() for page in document) + json.dumps(document.metadata)
                self.assertEqual(document.embfile_names(), [])
            contents += (packet / "job-brief.md").read_text() + (packet / "REVIEW.md").read_text()
            for forbidden in ("area_split_clean", "area_split_shift", "bbox_points", "coverage_review",
                              "known_issues", "affected_checks", "expected_checks", "PASS", "FAIL"):
                self.assertNotIn(forbidden, contents)
            for relative, digest in manifest["files"].items():
                self.assertEqual(hashlib.sha256((destination / relative).read_bytes()).hexdigest(), digest)
            packets.append(packet)
        self.assertEqual((packets[0] / "job-brief.md").read_bytes(), (packets[1] / "job-brief.md").read_bytes())
        self.assertEqual((packets[0] / "REVIEW.md").read_bytes(), (packets[1] / "REVIEW.md").read_bytes())


if __name__ == "__main__":
    unittest.main()
