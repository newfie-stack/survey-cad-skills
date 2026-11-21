"""Reject invented preparation success and retain unresolved source evidence."""
from copy import deepcopy
from html import unescape
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from intake_reporting import preparation_counts, render_intake_preparation


def prepared():
    return {"assessment_scope": "SOURCE_BOUND_CHECK_PREPARATION",
            "overall_status": "REVIEW_REQUIRED", "regulatory_status": "NOT_ASSESSED",
            "source_sha256": "a" * 64,
            "resolutions": [{"check_id": "job", "status": "READY", "regions": []}],
            "visual_tasks": [],
            "spec": {"schema_version": 1, "source_sha256": "a" * 64,
                     "prepared_by": "Invented reviewer", "checks": [{
                         "id": "job", "kind": "required_text", "description": "Current job",
                         "basis": "Invented brief", "expected": "DEMO-41",
                         "regions": [{"page": 1, "bbox_points": [10, 20, 80, 60],
                                      "role": "Reviewed current field", "label": "JOB:"}]}]}}


class IntakeReportingTests(unittest.TestCase):
    def test_ready_count_is_bound_to_the_actual_generated_spec(self):
        data = prepared()
        self.assertEqual(preparation_counts(data)["ready"], 1)
        data["spec"]["checks"][0]["id"] = "different"
        with self.assertRaisesRegex(ValueError, "match every ready"):
            preparation_counts(data)

    def test_normative_or_unknown_status_cannot_be_rendered_as_preparation(self):
        for field, value in (("overall_status", "PASS"), ("regulatory_status", "PASS"),
                             ("assessment_scope", "CERTIFIED")):
            data = prepared()
            data[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                render_intake_preparation(data)

    def test_prepared_spec_cannot_change_source_identity(self):
        data = prepared()
        data["spec"]["source_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "source identity"):
            preparation_counts(data)

    def test_unresolved_request_is_not_counted_ready_and_keeps_candidate_text_literal(self):
        data = prepared()
        data["spec"] = None
        data["resolutions"][0].update(status="REVIEW_REQUIRED", reason="Two current/history fields",
            regions=[{"page": 1, "role": "Current panel", "reason": "Competing values",
                      "matching_candidates": [{"text": "JOB: DEMO-41"},
                                               {"text": "JOB: [HISTORY](https://example.invalid)"}]}])
        counts = preparation_counts(data)
        self.assertEqual((counts["ready"], counts["unresolved"]), (0, 1))
        output = render_intake_preparation(data)
        self.assertIn("JOB: DEMO-41", unescape(output))
        self.assertIn("HISTORY", output)
        self.assertNotIn("[HISTORY](https://example.invalid)", output)
        self.assertIn("were not executed", output)

    def test_duplicate_resolution_cannot_double_count_a_ready_check(self):
        data = prepared()
        data["resolutions"].append(deepcopy(data["resolutions"][0]))
        with self.assertRaisesRegex(ValueError, "distinct"):
            preparation_counts(data)


if __name__ == "__main__":
    unittest.main()
