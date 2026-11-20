"""Scoring must expose misses/false alarms rather than reward universal abstention."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


class FinishedPlanBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("finished_plan_benchmark"),
                             "Finished-plan benchmark scorer is not implemented")
        from finished_plan_benchmark import score_case, run_benchmark
        self.score = score_case
        self.run = run_benchmark

    def test_abstention_does_not_count_as_a_detected_defect(self):
        result = self.score({"a": "FAIL", "b": "PASS", "c": "REVIEW_REQUIRED"}, ["a"],
                            [{"check_id": k, "status": "REVIEW_REQUIRED"} for k in "abc"])
        self.assertEqual(result["detected_defects"], 0)
        self.assertEqual(result["missed_defects"], 1)
        self.assertEqual(result["correct_abstentions"], 1)
        self.assertFalse(result["expected_behavior_matched"])

    def test_expected_abstention_on_known_defect_is_still_a_miss(self):
        result = self.score({"a": "REVIEW_REQUIRED"}, ["a"], [{"check_id": "a", "status": "REVIEW_REQUIRED"}])
        self.assertEqual(result["missed_defects"], 1)
        self.assertTrue(result["expected_behavior_matched"])
        self.assertEqual(result["detected_defects"], 0)

    def test_unexpected_fail_is_a_false_alarm(self):
        result = self.score({"a": "PASS"}, [], [{"check_id": "a", "status": "FAIL"}, {"check_id": "unexpected", "status": "FAIL"}])
        self.assertEqual(result["false_alarms"], 2)
        self.assertFalse(result["expected_behavior_matched"])

    def test_missing_results_cannot_disappear_from_score(self):
        result = self.score({"a": "FAIL", "b": "PASS"}, ["a"], [])
        self.assertEqual(result["missed_defects"], 1)
        self.assertEqual(result["missing_checks"], ["a", "b"])
        self.assertFalse(result["expected_behavior_matched"])

    def test_duplicate_or_invalid_results_rejected(self):
        for results in ([{"check_id": "a", "status": "PASS"}] * 2,
                        [{"check_id": "a", "status": "APPROVED"}]):
            with self.assertRaises(ValueError):
                self.score({"a": "PASS"}, [], results)

    def test_pass_on_a_planted_defect_is_reported_as_false_clearance(self):
        result = self.score({"note": "REVIEW_REQUIRED"}, ["note"],
                            [{"check_id": "note", "status": "PASS"}])
        self.assertEqual(result["false_clearance_ids"], ["note"])
        self.assertEqual(result["false_clearances"], 1)
        self.assertFalse(result["regression_gate_passed"])

    def test_capability_gap_can_improve_without_rewriting_frozen_expected_status(self):
        result = self.score({"graphic": "REVIEW_REQUIRED"}, ["graphic"],
                            [{"check_id": "graphic", "status": "FAIL"}],
                            policies={"graphic": "capability_gap"})
        self.assertEqual(result["detected_defects"], 1)
        self.assertEqual(result["missed_defects"], 0)
        self.assertTrue(result["regression_gate_passed"])
        self.assertFalse(result["expected_behavior_matched"])

    def test_missing_coverage_must_not_be_gamed_into_a_detection(self):
        for status in ("PASS", "FAIL"):
            with self.subTest(status=status):
                result = self.score({"note": "REVIEW_REQUIRED"}, ["note"],
                                    [{"check_id": "note", "status": status}],
                                    policies={"note": "must_abstain"})
                self.assertFalse(result["regression_gate_passed"])
                self.assertEqual(result["regression_failure_ids"], ["note"])

    def test_new_detection_cannot_hide_a_lost_supported_detection(self):
        result = self.score({"total": "FAIL", "graphic": "REVIEW_REQUIRED"},
                            ["total", "graphic"],
                            [{"check_id": "total", "status": "REVIEW_REQUIRED"},
                             {"check_id": "graphic", "status": "FAIL"}],
                            policies={"total": "must_detect", "graphic": "capability_gap"})
        self.assertEqual(result["detected_defects"], 1)
        self.assertEqual(result["regression_failure_ids"], ["total"])
        self.assertFalse(result["regression_gate_passed"])

    def test_clean_controls_still_reject_false_alarms(self):
        result = self.score({"scale": "PASS"}, [],
                            [{"check_id": "scale", "status": "FAIL"}],
                            policies={"scale": "must_pass"})
        self.assertEqual(result["false_alarms"], 1)
        self.assertFalse(result["regression_gate_passed"])

    def test_abstained_defects_are_separate_from_clear_manual_controls(self):
        result = self.score({"missing_arrow": "REVIEW_REQUIRED", "present_arrow": "REVIEW_REQUIRED"},
                            ["missing_arrow"],
                            [{"check_id": name, "status": "REVIEW_REQUIRED"}
                             for name in ("missing_arrow", "present_arrow")])
        self.assertEqual(result["abstained_defect_ids"], ["missing_arrow"])
        self.assertEqual(result["clear_abstention_ids"], ["present_arrow"])
        self.assertEqual(result["detected_defects"], 0)

    def test_invalid_or_inconsistent_regression_policies_are_rejected(self):
        for policies in ({}, {"extra": "must_pass"}, {"a": "anything"},
                         {"a": "capability_gap"}, {"a": "must_detect"}):
            with self.subTest(policies=policies):
                with self.assertRaises(ValueError):
                    self.score({"a": "PASS"}, [], [{"check_id": "a", "status": "PASS"}],
                               policies=policies)

    def test_unresolved_counts_are_explicit_by_cohort_and_category(self):
        from benchmark_scoring import summarize_cases
        first = self.score({"graphic": "REVIEW_REQUIRED", "id": "PASS"}, [],
                           [{"check_id": "graphic", "status": "REVIEW_REQUIRED"},
                            {"check_id": "id", "status": "PASS"}])
        second = self.score({"graphic": "REVIEW_REQUIRED", "total": "FAIL"}, ["total"],
                            [{"check_id": "graphic", "status": "REVIEW_REQUIRED"},
                             {"check_id": "total", "status": "FAIL"}])
        report = summarize_cases([
            {**first, "cohort": "legacy", "categories": {"graphic": "visual", "id": "identity"}},
            {**second, "cohort": "drafting", "categories": {"graphic": "visual", "total": "area"}},
        ])
        self.assertEqual(report["unresolved"], 2)
        self.assertEqual(report["by_cohort"]["legacy"]["unresolved"], 1)
        self.assertEqual(report["by_cohort"]["drafting"]["unresolved"], 1)
        self.assertEqual(report["by_category"]["visual"]["unresolved"], 2)
        self.assertEqual(report["by_category"]["area"]["unresolved"], 0)

    def test_real_pdf_benchmark_records_supported_detections_and_known_limits(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "benchmark"
            report = self.run(output)
            self.assertEqual(report["case_count"], 23)
            self.assertTrue(report["regression_gate_passed"])
            self.assertEqual(report["false_alarms"], 0)
            self.assertEqual(report["false_clearances"], 0)
            self.assertGreaterEqual(report["detected_defects"], 18)
            self.assertLessEqual(report["missed_defects"], 3)
            self.assertEqual(report["known_defects"], 21)
            self.assertEqual(report["by_cohort"]["legacy"]["case_count"], 16)
            self.assertEqual(report["by_cohort"]["legacy"]["known_defects"], 14)
            self.assertGreaterEqual(report["by_cohort"]["legacy"]["detected_defects"], 12)
            self.assertEqual(report["by_cohort"]["drafting"]["known_defects"], 7)
            self.assertLessEqual(report["by_cohort"]["legacy"]["unresolved"], 23)
            self.assertLessEqual(report["by_cohort"]["drafting"]["unresolved"], 8)
            self.assertEqual(report["by_category"]["revision"]["detected_defects"], 1)
            self.assertFalse(report["all_defects_detected"])
            self.assertTrue((output / "benchmark.json").is_file())
            self.assertTrue((output / "benchmark.md").is_file())
            markdown = (output / "benchmark.md").read_text()
            cohort_section = markdown.split("## Cohorts\n", 1)[1].split("## Check categories", 1)[0]
            category_section = markdown.split("## Check categories\n", 1)[1].split("## Follow-up", 1)[0]
            cohort_rows = [[cell.strip() for cell in line.strip("|").split("|")]
                           for line in cohort_section.splitlines() if line.startswith("|")]
            category_rows = [[cell.strip() for cell in line.strip("|").split("|")]
                             for line in category_section.splitlines() if line.startswith("|")]
            self.assertEqual(cohort_rows[0][-1], "Unresolved")
            self.assertEqual(category_rows[0][-1], "Unresolved")
            for name, buckets, rows in (("legacy", report["by_cohort"], cohort_rows),
                                        ("drafting", report["by_cohort"], cohort_rows),
                                        ("visual", report["by_category"], category_rows)):
                cells = next(row for row in rows if row[0] == name)
                self.assertEqual(cells[-1], str(buckets[name]["unresolved"]))
            self.assertEqual(report["independent_reviewer_acceptance"], "NOT_PERFORMED")
            self.assertEqual(report["case_results"][0]["cli_qc_section_matches"], True)
            self.assertTrue(all(row["cli_summary_matches"] for row in report["case_results"]))
            cases = {row["case_id"]: row for row in report["case_results"]}
            self.assertEqual(cases["competing_totals"]["actual"]["area_sum"], "FAIL")
            self.assertEqual(cases["unverified_note_omission"]["actual"]["units_note"], "REVIEW_REQUIRED")
            self.assertEqual(cases["loc_rounded_total_control"]["false_alarms"], 0)
            self.assertEqual(cases["msl_multiple_errors"]["detected_defects"], 4)
            with self.assertRaises(FileExistsError):
                self.run(output)


if __name__ == "__main__":
    unittest.main()
