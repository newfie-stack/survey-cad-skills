"""Synthetic review ledger tests; no real plans or legal certifications."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from deficiency_report import build_ledger


class DeficiencyReportTests(unittest.TestCase):
    def setUp(self):
        self.rules = [
            {"requirement_id": "SYNTH-1", "evidence_key": "scale",
             "summary": "Synthetic scale check", "section": "TEST"},
            {"requirement_id": "SYNTH-2", "evidence_key": "north",
             "summary": "Synthetic north arrow check", "section": "TEST"},
        ]

    def test_observed_is_not_regulatory_pass(self):
        report = build_ledger({"plan_type": "sketch"}, self.rules,
                              {"scale": {"present": True, "page": 1,
                                         "observation": "SCALE 1:5000"}})
        self.assertEqual(report["requirements"][0]["evidence_status"], "OBSERVED_CANDIDATE")
        self.assertEqual(report["requirements"][0]["status"], "REVIEW_REQUIRED")
        self.assertEqual(report["overall_status"], "REVIEW_REQUIRED")
        self.assertEqual(report["summary"]["unknown"], 1)

    def test_missing_observation_is_not_legal_fail(self):
        report = build_ledger({}, self.rules, {"north": {"present": False}})
        self.assertEqual(report["requirements"][1]["evidence_status"], "NOT_OBSERVED_IN_SUPPLIED_EVIDENCE")
        self.assertEqual(report["requirements"][1]["status"], "REVIEW_REQUIRED")

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            build_ledger({}, self.rules + [self.rules[0]], {})

    def test_invalid_page_rejected(self):
        with self.assertRaises(ValueError):
            build_ledger({}, self.rules, {"scale": {"present": True, "page": 0}})

    def test_invalid_presence_rejected(self):
        with self.assertRaises(ValueError):
            build_ledger({}, self.rules, {"scale": {"present": "yes"}})

    def test_declared_ledger_contract_keeps_unsupported_fields_unresolved(self):
        scenario = {"regulator": "AER", "disposition": "PLA", "stage": "initial",
                    "plan_type": "sketch"}
        entry = build_ledger(scenario, self.rules, {
            "scale": {"present": True, "page": 1, "observation": "SCALE 1:5000"}
        })["requirements"][0]
        required = {
            "requirement_id", "authority", "publication_title", "version_date", "section",
            "regulator", "activity", "stage", "plan_type", "applicability",
            "requirement_summary", "check_method", "input_evidence", "observed_value",
            "expected_value", "source_status", "evidence_status", "status", "severity",
            "correction", "verified_at",
        }
        self.assertTrue(required <= entry.keys(), required - entry.keys())
        self.assertEqual(entry["activity"], "PLA")
        self.assertEqual(entry["regulator"], "AER")
        self.assertEqual(entry["observed_value"], "SCALE 1:5000")
        self.assertEqual(entry["input_evidence"]["page"], 1)
        self.assertEqual(entry["applicability"], "UNRESOLVED_APPLICABILITY")
        for field in ("authority", "version_date", "expected_value", "severity", "verified_at"):
            self.assertIsNone(entry[field], field)
        self.assertEqual(entry["source_status"], "UNVERIFIED_CURRENT")
        self.assertEqual(entry["status"], "REVIEW_REQUIRED")


if __name__ == "__main__":
    unittest.main()
