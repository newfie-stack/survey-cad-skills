"""Synthetic report renderer tests; no client data."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from deficiency_report import build_ledger
from report_markdown import render_review_markdown


class ReportMarkdownTests(unittest.TestCase):
    def test_render_review_only(self):
        ledger = build_ledger({"plan_type": "sketch"},
                              [{"requirement_id": "SYNTH-01", "evidence_key": "scale",
                                "summary": "Scale | bar"}],
                              {"scale": {"present": True, "page": 2}})
        rendered = render_review_markdown(ledger)
        self.assertIn("REVIEW_REQUIRED", rendered)
        self.assertIn("Scale \\| bar", rendered)
        self.assertIn("| 2 |", rendered)
        self.assertIn("not a regulatory compliance certificate", rendered)

    def test_detailed_review_contains_trace_and_applicability(self):
        ledger = build_ledger({"plan_type": "sketch"},
                              [{"requirement_id": "SYNTH-TRACE", "evidence_key": "scale",
                                "summary": "Synthetic scale"}],
                              {"scale": {"present": True, "page": 3,
                                         "bbox_points": [10, 20, 50, 30],
                                         "observation": "SCALE 1:5000"}})
        ledger["plan_type_review"] = {"status": "REVIEW_REQUIRED",
                                      "plan_type_status": "CANDIDATE_ONLY",
                                      "missing_or_invalid_fields": [],
                                      "notes": ["Verify Table A2"]}
        ledger["applicability_decisions"] = [
            {"requirement_id": "SYNTH-TRACE", "status": "REVIEW_REQUIRED",
             "applicability_status": "CANDIDATE_REVIEW", "missing_dimensions": []}
        ]
        ledger["requirements"][0]["source_review"] = {
            "source_status": "REVIEW_REQUIRED", "missing_or_invalid": ["section"]
        }
        rendered = render_review_markdown(ledger)
        for value in ("Plan type review", "Candidate applicability",
                      "Evidence trace", "SCALE 1:5000", "section",
                      "[10, 20, 50, 30]"):
            self.assertIn(value, rendered)

    def test_reject_forged_applicability_pass(self):
        ledger = build_ledger({}, [], {})
        ledger["applicability_decisions"] = [
            {"requirement_id": "SYNTH", "status": "PASS"}
        ]
        with self.assertRaises(ValueError):
            render_review_markdown(ledger)

    def test_reject_forged_source_review(self):
        ledger = build_ledger({}, [{"requirement_id": "SYNTH", "evidence_key": "x"}], {})
        ledger["requirements"][0]["source_review"] = {"source_status": "VERIFIED_CURRENT"}
        with self.assertRaises(ValueError):
            render_review_markdown(ledger)

    def test_reject_forged_pass(self):
        ledger = build_ledger({}, [{"requirement_id": "SYNTH", "evidence_key": "x"}], {})
        ledger["requirements"][0]["status"] = "PASS"
        with self.assertRaises(ValueError):
            render_review_markdown(ledger)

    def test_reject_non_review_report(self):
        with self.assertRaises(ValueError):
            render_review_markdown({"overall_status": "PASS", "assessment_type": "COMPLIANCE"})


if __name__ == "__main__":
    unittest.main()
