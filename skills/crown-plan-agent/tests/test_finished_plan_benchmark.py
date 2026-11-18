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

    def test_real_pdf_benchmark_records_supported_detections_and_known_limits(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "benchmark"
            report = self.run(output)
            self.assertEqual(report["case_count"], 16)
            self.assertTrue(report["all_expected_behaviors_matched"])
            self.assertEqual(report["false_alarms"], 0)
            self.assertEqual(report["detected_defects"], 11)
            self.assertEqual(report["missed_defects"], 3)
            self.assertEqual(report["known_defects"], 14)
            self.assertTrue((output / "benchmark.json").is_file())
            self.assertTrue((output / "benchmark.md").is_file())
            self.assertEqual(report["independent_reviewer_acceptance"], "NOT_PERFORMED")
            self.assertEqual(report["case_results"][0]["cli_qc_section_matches"], True)
            with self.assertRaises(FileExistsError):
                self.run(output)


if __name__ == "__main__":
    unittest.main()
