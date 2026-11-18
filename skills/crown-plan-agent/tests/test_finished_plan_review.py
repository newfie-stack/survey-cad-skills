"""Error-injection acceptance for the real PDF QC reader, not mocked results."""
import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from finished_plan_fixture import make_plan
from pdf_inspector import extract_pdf


class FinishedPlanReviewTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("finished_plan_review"),
                             "The finished-plan PDF checking capability is not implemented")
        from finished_plan_review import review_finished_plan
        self.review = review_finished_plan
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pdf = Path(self.temp.name) / "invented.pdf"

    def results(self, **kwargs):
        spec = make_plan(self.pdf, **kwargs)
        report = self.review(self.pdf, spec)
        return {item["check_id"]: item for item in report["findings"]}, report, spec

    def test_clean_plan_has_no_confirmed_errors_and_visual_abstains(self):
        rows, report, _ = self.results()
        self.assertEqual([rows[k]["status"] for k in ("subject", "main_scale", "units_note", "area_sum")], ["PASS"] * 4)
        self.assertEqual(rows["north_arrow"]["status"], "REVIEW_REQUIRED")
        self.assertEqual(report["overall_status"], "REVIEW_REQUIRED")
        self.assertEqual(report["regulatory_status"], "NOT_ASSESSED")
        self.assertEqual(report["summary"], {"PASS": 4, "FAIL": 0, "REVIEW_REQUIRED": 1})

    def test_changed_subject_has_two_cited_conflicting_values(self):
        rows, report, _ = self.results(subject="LOT 8")
        self.assertEqual(rows["subject"]["status"], "FAIL")
        self.assertEqual(rows["subject"]["observed"], ["LOT 7", "LOT 8"])
        self.assertEqual(len(rows["subject"]["evidence"]), 2)
        self.assertTrue(all(e["page"] == 1 and e["bbox_points"] and e["text"] for e in rows["subject"]["evidence"]))
        self.assertIn("LOT 8", report["report_markdown"])
        self.assertTrue(rows["subject"]["correction"])

    def test_missing_required_note_is_a_failure_only_with_coverage(self):
        rows, _, spec = self.results(note=False)
        self.assertEqual(rows["units_note"]["status"], "FAIL")
        del spec["checks"][2]["regions"][0]["coverage_review"]
        rows = {r["check_id"]: r for r in self.review(self.pdf, spec)["findings"]}
        self.assertEqual(rows["units_note"]["status"], "REVIEW_REQUIRED")

    def test_inset_scale_does_not_satisfy_missing_main_scale(self):
        rows, _, _ = self.results(scale=None, inset=True)
        self.assertEqual(rows["main_scale"]["status"], "FAIL")
        self.assertEqual(rows["main_scale"]["observed"], [])

    def test_wrong_scale_does_not_match_expected_ratio(self):
        rows, _, _ = self.results(scale="1:2000")
        self.assertEqual(rows["main_scale"]["status"], "FAIL")
        self.assertEqual(rows["main_scale"]["observed"], [2000])

    def test_area_sum_error_is_detected_without_binary_rounding(self):
        rows, _, spec = self.results(total="0.301")
        self.assertEqual(rows["area_sum"]["status"], "FAIL")
        self.assertEqual(rows["area_sum"]["difference"], "0.001")
        spec["checks"][3]["tolerance"] = "0.001"
        report = self.review(self.pdf, spec)
        self.assertEqual(report["findings"][3]["status"], "PASS")

    def test_duplicate_total_remains_ambiguous(self):
        rows, _, _ = self.results(duplicate_total=True)
        self.assertEqual(rows["area_sum"]["status"], "REVIEW_REQUIRED")

    def test_raster_sheet_does_not_produce_omission_failures(self):
        rows, report, _ = self.results(raster=True)
        self.assertEqual(report["summary"], {"PASS": 0, "FAIL": 0, "REVIEW_REQUIRED": 5})
        self.assertTrue(all(r["status"] == "REVIEW_REQUIRED" for r in rows.values()))

    def test_rotated_sheet_preserves_unrotated_region_coordinates(self):
        rows, _, _ = self.results(rotated=True)
        self.assertEqual(rows["subject"]["status"], "PASS")
        self.assertEqual(rows["main_scale"]["status"], "PASS")

    def test_split_font_note_is_read_from_contiguous_text(self):
        rows, _, _ = self.results(split_note=True)
        self.assertEqual(rows["units_note"]["status"], "PASS")

    def test_identifiers_on_separate_pages_are_checked(self):
        rows, _, _ = self.results(subject="LOT 8", alternate_layout=True)
        self.assertEqual(rows["subject"]["status"], "FAIL")
        self.assertEqual([e["page"] for e in rows["subject"]["evidence"]], [1, 2])

    def test_qc_refuses_text_inventory_from_different_bytes(self):
        spec = make_plan(self.pdf)
        inventory = extract_pdf(self.pdf, include_vectors=False)
        inventory["source_sha256"] = "0" * 64
        with patch("finished_plan_review.extract_pdf", return_value=inventory):
            with self.assertRaisesRegex(ValueError, "Source PDF changed"):
                self.review(self.pdf, spec)

    def test_markdown_keeps_source_and_spec_links_literal(self):
        rows, _, spec = self.results()
        spec["checks"][0]["basis"] = "[external](https://example.invalid/a)"
        report = self.review(self.pdf, spec)["report_markdown"]
        self.assertNotIn("[external](", report)
        self.assertNotIn("https://", report)
        self.assertIn("&#91;external&#93;", report)

    def test_source_digest_mismatch_rejected(self):
        spec = make_plan(self.pdf)
        spec["source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source.*hash|SHA|digest"):
            self.review(self.pdf, spec)

    def test_unknown_fields_rejected_instead_of_ignored(self):
        spec = make_plan(self.pdf)
        spec["checks"][0]["expectd"] = "LOT 8"
        with self.assertRaisesRegex(ValueError, "Unknown|unknown"):
            self.review(self.pdf, spec)

    def test_duplicate_check_identifiers_rejected(self):
        spec = make_plan(self.pdf)
        spec["checks"][1]["id"] = "subject"
        with self.assertRaises(ValueError):
            self.review(self.pdf, spec)

    def test_invalid_region_never_silently_looks_empty(self):
        for page, box in ((True, [0, 0, 10, 10]), (2, [0, 0, 10, 10]),
                          (1, [0, 0, 700, 100]), (1, [10, 10, 0, 0]),
                          (1, [0, 0, float("nan"), 10])):
            with self.subTest(page=page, box=box):
                path = self.pdf.with_name(f"{len(list(self.pdf.parent.iterdir()))}.pdf")
                spec = make_plan(path)
                spec["checks"][0]["regions"][0].update(page=page, bbox_points=box)
                with self.assertRaises(ValueError):
                    self.review(path, spec)

    def test_numeric_inputs_are_bounded_and_not_coerced(self):
        for tolerance in (True, 0.1, "NaN", "Infinity", "-1", "1e999999"):
            with self.subTest(tolerance=tolerance):
                path = self.pdf.with_name(f"{len(list(self.pdf.parent.iterdir()))}.pdf")
                spec = make_plan(path)
                spec["checks"][3]["tolerance"] = tolerance
                with self.assertRaises(ValueError):
                    self.review(path, spec)

    def test_input_is_not_modified_and_hashes_are_reported(self):
        spec = make_plan(self.pdf)
        original = self.pdf.read_bytes()
        original_spec = copy.deepcopy(spec)
        report = self.review(self.pdf, spec)
        self.assertEqual(self.pdf.read_bytes(), original)
        self.assertEqual(spec, original_spec)
        self.assertEqual(report["source_sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(len(report["spec_sha256"]), 64)
        self.assertIn(report["source_sha256"], report["report_markdown"])

    def test_bad_coverage_declaration_is_rejected(self):
        spec = make_plan(self.pdf)
        spec["checks"][0]["regions"][0]["coverage_review"] = {"status": "TEXT_COMPLETE"}
        with self.assertRaises(ValueError):
            self.review(self.pdf, spec)

    def test_missing_comparison_field_is_not_an_invented_conflict(self):
        rows, _, _ = self.results(second_subject=False)
        self.assertEqual(rows["subject"]["status"], "REVIEW_REQUIRED")

    def test_repeated_identical_region_cannot_masquerade_as_two_subject_fields(self):
        spec = make_plan(self.pdf)
        spec["checks"][0]["regions"][1] = copy.deepcopy(spec["checks"][0]["regions"][0])
        with self.assertRaises(ValueError):
            self.review(self.pdf, spec)

    def test_overlapping_regions_sharing_one_observation_remain_unresolved(self):
        spec = make_plan(self.pdf)
        spec["checks"][0]["regions"][1]["bbox_points"] = [29, 59, 301, 91]
        report = self.review(self.pdf, spec)
        self.assertEqual(report["findings"][0]["status"], "REVIEW_REQUIRED")

    def test_label_prefix_is_not_allowed_to_match_a_longer_word(self):
        spec = make_plan(self.pdf)
        spec["checks"][0]["regions"][0]["label"] = "SUB"
        report = self.review(self.pdf, spec)
        self.assertEqual(report["findings"][0]["status"], "REVIEW_REQUIRED")

    def test_required_text_respects_explicit_label_context(self):
        spec = make_plan(self.pdf)
        spec["checks"][2]["regions"][0]["label"] = "OTHER NOTE:"
        report = self.review(self.pdf, spec)
        self.assertNotEqual(report["findings"][2]["status"], "PASS")

    def test_multiple_regions_required_for_same_text(self):
        spec = make_plan(self.pdf)
        spec["checks"][0]["regions"].pop()
        with self.assertRaises(ValueError):
            self.review(self.pdf, spec)


if __name__ == "__main__":
    unittest.main()
