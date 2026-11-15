"""Synthetic Table A2 lookup tests."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from table_a2_lookup import lookup_plan_requirement, verify_disposition


class A2LookupTests(unittest.TestCase):
    def setUp(self):
        self.rows = [{"row": 51, "page": 8, "disposition": "LOC",
                      "purpose": "Pipeline", "activity": "Fresh Water",
                      "required_plan": "Sketch", "survey_monuments": "N/A"}]

    def test_disposition_only_requires_no_purpose_or_activity(self):
        result = verify_disposition(self.rows, " loc ")
        self.assertEqual(result["status"], "DISPOSITION_FOUND")
        self.assertEqual(result["matched_rows"], [{"row": 51, "page": 8}])
        self.assertEqual(result["regulatory_compliance"], "NOT_ASSESSED")

    def test_disposition_not_listed(self):
        result = verify_disposition(self.rows, "XYZ")
        self.assertEqual(result["status"], "DISPOSITION_NOT_IN_TABLE_A2")

    def test_disposition_missing(self):
        self.assertEqual(verify_disposition(self.rows, None)["status"],
                         "DISPOSITION_NOT_PROVIDED")

    def test_disposition_invalid(self):
        self.assertEqual(verify_disposition(self.rows, "PLA;LOC")["status"],
                         "INVALID_DISPOSITION_CODE")

    def test_exact_match(self):
        result = lookup_plan_requirement(self.rows, disposition="LOC",
                    purpose="Pipeline", activity="Fresh Water")
        self.assertEqual(result["row"], 51)
        self.assertEqual(result["required_plan"], "Sketch")
        self.assertEqual(result["regulatory_compliance"], "NOT_ASSESSED")

    def test_ambiguous_matches_unresolved(self):
        result = lookup_plan_requirement(self.rows + self.rows,
                    disposition="LOC", purpose="Pipeline", activity="Fresh Water")
        self.assertEqual(result["status"], "UNRESOLVED_APPLICABILITY")

    def test_unknown_activity_unresolved(self):
        result = lookup_plan_requirement(self.rows, disposition="LOC",
                    purpose="Pipeline", activity="Unknown")
        self.assertEqual(result["status"], "UNRESOLVED_APPLICABILITY")

    def test_explicit_blank_activity_can_match(self):
        rows = [{"row": 49, "page": 8, "disposition": "OSE",
                 "purpose": "Oil Sands Exploration", "activity": "",
                 "required_plan": "Sketch", "survey_monuments": "N/A"}]
        result = lookup_plan_requirement(rows, disposition="OSE",
                    purpose="Oil Sands Exploration", activity="")
        self.assertEqual(result["row"], 49)
        self.assertEqual(result["status"], "SOURCE_ROW_IDENTIFIED_REVIEW_REQUIRED")

    def test_missing_activity_is_not_assumed_blank(self):
        rows = [{"row": 49, "page": 8, "disposition": "OSE",
                 "purpose": "Oil Sands Exploration", "activity": "",
                 "required_plan": "Sketch", "survey_monuments": "N/A"}]
        result = lookup_plan_requirement(rows, disposition="OSE",
                    purpose="Oil Sands Exploration", activity=None)
        self.assertEqual(result["status"], "UNRESOLVED_APPLICABILITY")

    def test_missing_context_unresolved(self):
        result = lookup_plan_requirement(self.rows, disposition="LOC",
                    purpose="Pipeline", activity=None)
        self.assertEqual(result["status"], "UNRESOLVED_APPLICABILITY")


if __name__ == "__main__":
    unittest.main()
