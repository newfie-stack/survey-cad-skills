"""Synthetic plan-type decision tests."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from plan_type_review import review_plan_type


class PlanTypeReviewTests(unittest.TestCase):
    def test_renewal_compares_active_plan_and_routes_legacy_sketch_for_review(self):
        row = {"disposition": "PLA", "purpose": "Pipeline", "activity": "Above Ground",
               "row": 56, "page": 9, "required_plan": "Survey", "survey_monuments": "1/4"}
        scenario = {"land_class": "alberta_crown", "regulator": "AER", "stage": "renewal", "activity": "PLA",
                    "purpose": "Pipeline", "subactivity": "Above Ground", "plan_type": "sketch",
                    "existing_plan_type": "survey_plan", "disposition_changed": False}
        for changes, expected in (
            ({}, "MATCHES_TABLE_A2"),
            ({"existing_plan_type": None}, "PLAN_OF_RECORD_REQUIRED"),
            ({"existing_plan_type": "sketch", "disposition_issued_on": "2010-08-31"},
             "LEGACY_SKETCH_VARIANCE_REVIEW"),
            ({"existing_plan_type": "sketch", "disposition_issued_on": "2010-09-01"},
             "DIFFERS_FROM_TABLE_A2"),
            ({"existing_plan_type": "sketch"}, "LEGACY_ISSUE_DATE_UNRESOLVED"),
            ({"disposition_changed": True}, "AMENDMENT_BEFORE_RENEWAL"),
            ({"disposition_changed": None}, "DISPOSITION_CHANGE_STATUS_REQUIRED"),
            ({"subactivity": "different"}, "TABLE_A2_ROW_UNRESOLVED"),
        ):
            with self.subTest(expected=expected):
                result = review_plan_type({**scenario, **changes}, table_a2_rows=[row])
                self.assertEqual(result["renewal_review"]["comparison"], expected)
                self.assertEqual(result["status"], "REVIEW_REQUIRED")
        result = review_plan_type(scenario)
        self.assertEqual(result["renewal_review"]["comparison"], "TABLE_A2_REQUIRED")

    def test_table_a2_plan_type_comparison_stays_review_only(self):
        scenario = {"land_class": "alberta_crown", "regulator": "AER", "activity": "PIL",
                    "purpose": "Pipeline Installation", "subactivity": "Header or Riser Site",
                    "stage": "initial", "plan_type": "sketch"}
        rows = [{"disposition": "PIL", "purpose": "Pipeline Installation",
                 "activity": "Header or Riser Site", "row": 64, "page": 9,
                 "required_plan": "Surveyor Sketch", "survey_monuments": "N/A"}]
        for proposed, expected in (("sketch", "DIFFERS_FROM_TABLE_A2"),
                                   ("surveyor_sketch", "MATCHES_TABLE_A2"),
                                   ("survey_plan", "SURVEY_PLAN_SUBSTITUTION_REVIEW_REQUIRED"),
                                   (None, "PROPOSED_PLAN_TYPE_UNRESOLVED")):
            with self.subTest(proposed=proposed):
                result = review_plan_type({**scenario, "plan_type": proposed}, table_a2_rows=rows)
                self.assertEqual(result["table_a2_comparison"], expected)
                self.assertEqual(result["table_a2_requirement"]["row"], 64)
                self.assertEqual(result["status"], "REVIEW_REQUIRED")
                self.assertFalse(result["regulatory_table_verified"])
        for changes in ({"stage": "amendment"}, {"regulator": "Alberta"},
                        {"subactivity": None}):
            result = review_plan_type({**scenario, **changes}, table_a2_rows=rows)
            self.assertNotIn("table_a2_requirement", result)

    def test_table_a2_does_not_pick_between_duplicate_rows(self):
        scenario = {"land_class": "alberta_crown", "regulator": "AER", "activity": "ABC", "purpose": "Synthetic",
                    "subactivity": "", "stage": "initial", "plan_type": "sketch"}
        row = {"disposition": "ABC", "purpose": "Synthetic", "activity": "",
               "row": 1, "page": 4, "required_plan": "N/A", "survey_monuments": "N/A"}
        unresolved = review_plan_type(scenario, table_a2_rows=[row, {**row, "row": 2}])
        self.assertEqual(unresolved["table_a2_comparison"], "TABLE_A2_ROW_UNRESOLVED")
        self.assertEqual(len(unresolved["table_a2_requirement"]["matches"]), 2)
        resolved = review_plan_type(scenario, table_a2_rows=[row])
        self.assertEqual(resolved["table_a2_comparison"], "TABLE_A2_PLAN_TYPE_NOT_APPLICABLE")

    def test_complete_case_remains_candidate(self):
        result = review_plan_type({"land_class": "alberta_crown", "regulator": "AER", "activity": "MSL",
            "purpose": "synthetic", "stage": "initial", "plan_type": "surveyor_sketch"})
        self.assertEqual(result["plan_type_status"], "CANDIDATE_ONLY")
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertFalse(result["regulatory_table_verified"])

    def test_amendment_requires_manual_table_check(self):
        result = review_plan_type({"land_class": "alberta_crown", "regulator": "AER", "activity": "PLA",
            "purpose": "synthetic", "stage": "amendment", "plan_type": "sketch"})
        self.assertEqual(result["amendment_review"]["route"], "PLAN_OF_RECORD_REQUIRED")
        self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_surveyed_linear_amendment_scope(self):
        scenario = {"land_class": "alberta_crown", "regulator": "AER", "activity": "LOC", "stage": "amendment",
                    "plan_type": "sketch", "existing_plan_type": "survey_plan"}
        for length, quarters, expected in (
            (6501, 2, "ITEMIZED_SURVEY_CANDIDATE"),
            (6499, 1, "FULL_RETRACE_CANDIDATE"),
            (6501, 3, "FULL_RETRACE_CANDIDATE"),
            (6500, 2, "SURVEY_SCOPE_UNRESOLVED"),
            (6500, 3, "FULL_RETRACE_CANDIDATE"),
            (6501, None, "SURVEY_SCOPE_UNRESOLVED"),
            (True, 2, "SURVEY_SCOPE_UNRESOLVED"),
        ):
            with self.subTest(length=length, quarters=quarters):
                review = review_plan_type({**scenario, "existing_length_m": length,
                                           "affected_quarter_sections": quarters})
                result = review["amendment_review"]
                self.assertEqual(result["route"], expected)
                self.assertEqual(review["status"], "REVIEW_REQUIRED")
                self.assertNotIn("table_a2_requirement", review)
        itemized = review_plan_type({**scenario, "existing_length_m": 7000,
                                     "affected_quarter_sections": 2})["amendment_review"]
        self.assertEqual(itemized["comparison"], "ITEMIZED_SKETCH_CONFLICT")

    def test_sketch_plan_of_record_does_not_inherit_survey_scope_rule(self):
        review = review_plan_type({"land_class": "alberta_crown", "regulator": "AER", "activity": "LOC", "stage": "amendment",
                                   "plan_type": "sketch", "existing_plan_type": "sketch",
                                   "existing_length_m": 7000, "affected_quarter_sections": 1})
        self.assertEqual(review["amendment_review"]["route"], "AMENDMENT_PLAN_TYPE_UNRESOLVED")

    def test_missing_purpose_is_unresolved(self):
        result = review_plan_type({"land_class": "alberta_crown", "regulator": "AER", "activity": "PLA",
            "stage": "initial", "plan_type": "sketch"})
        self.assertIn("purpose", result["missing_or_invalid_fields"])
        self.assertEqual(result["plan_type_status"], "UNRESOLVED")

    def test_invalid_plan_type_rejected_as_unresolved(self):
        result = review_plan_type({"land_class": "alberta_crown", "regulator": "AER", "activity": "PLA",
            "purpose": "synthetic", "stage": "initial", "plan_type": "made_up"})
        self.assertIn("recognized_plan_type", result["missing_or_invalid_fields"])

    def test_non_mapping_rejected(self):
        with self.assertRaises(TypeError):
            review_plan_type(None)


if __name__ == "__main__":
    unittest.main()
