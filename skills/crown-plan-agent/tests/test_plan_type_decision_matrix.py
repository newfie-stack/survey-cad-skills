"""Independent invented cases for the documented, review-only decision table."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from plan_type_review import review_plan_type
from requirements import applicability


class PlanTypeDecisionMatrixTests(unittest.TestCase):
    def setUp(self):
        self.base = {"land_class": "alberta_crown", "regulator": "AER",
                     "disposition": "LOC", "stage": "initial", "plan_type": "sketch",
                     "purpose": "Invented purpose", "subactivity": "Invented activity"}

    def row(self, required):
        return {"disposition": "LOC", "purpose": "Invented purpose",
                "activity": "Invented activity", "required_plan": required,
                "row": 1, "page": 4, "survey_monuments": "N/A"}

    def amendment(self, **fields):
        result = review_plan_type({**self.base, "stage": "amendment",
                                   "existing_plan_type": "survey_plan", **fields})
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertFalse(result["regulatory_table_verified"])
        self.assertNotIn("table_a2_requirement", result)
        return result["amendment_review"]

    def test_all_documented_linear_codes_use_same_threshold_edges(self):
        cases = [(6499, 1, "FULL_RETRACE_CANDIDATE"),
                 (6500, 1, "SURVEY_SCOPE_UNRESOLVED"),
                 (6500, 2, "SURVEY_SCOPE_UNRESOLVED"),
                 (6501, 2, "ITEMIZED_SURVEY_CANDIDATE"),
                 (6500, 3, "FULL_RETRACE_CANDIDATE"),
                 (6501, 3, "FULL_RETRACE_CANDIDATE")]
        for code in ("DPL", "PLA", "DLO", "LOC", "EZE"):
            for length, quarters, route in cases:
                with self.subTest(code=code, length=length, quarters=quarters):
                    review = self.amendment(disposition=code, existing_length_m=length,
                                            affected_quarter_sections=quarters)
                    self.assertEqual(review["route"], route)

    def test_invalid_lengths_stay_unresolved_unless_quarters_establish_full_retrace(self):
        invalid = [None, 0, -1, True, False, "7000", float("nan"),
                   float("inf"), -float("inf"), 10**400, [], {}]
        for length in invalid:
            for quarters, expected in [(2, "SURVEY_SCOPE_UNRESOLVED"),
                                       (3, "FULL_RETRACE_CANDIDATE")]:
                with self.subTest(length=length, quarters=quarters):
                    self.assertEqual(self.amendment(existing_length_m=length,
                        affected_quarter_sections=quarters)["route"], expected)

    def test_compiled_proposal_does_not_inherit_ordinary_amendment_survey_scope(self):
        for length, quarters in ((6400, 1), (7000, 2), (7000, 3)):
            with self.subTest(length=length, quarters=quarters):
                review = self.amendment(plan_type="compiled_plan", existing_length_m=length,
                                        affected_quarter_sections=quarters)
                self.assertEqual(review["route"], "PLAN_VARIANT_REVIEW_REQUIRED")
                self.assertIn("3.6.1.1", review["source"])
                self.assertEqual(review["comparison"], "REVIEW_REQUIRED")
        self.assertEqual(self.amendment(plan_type="compiled_plan", existing_plan_type=None,
            existing_length_m=6400, affected_quarter_sections=1)["route"],
            "PLAN_OF_RECORD_REQUIRED")
        # The compiled exception must not suppress the hybrid's general survey route.
        self.assertEqual(self.amendment(plan_type="hybrid_plan", existing_length_m=6400,
            affected_quarter_sections=1)["route"], "FULL_RETRACE_CANDIDATE")

    def test_compiled_content_sections_preserve_the_amendment_exemption(self):
        for stage in ("amendment", "renewal"):
            with self.subTest(stage=stage):
                result = applicability({**self.base, "plan_type": "compiled_plan", "stage": stage})
                self.assertNotIn("Part 3.3", result["sections"])
                self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_invalid_quarters_cannot_establish_itemized_scope(self):
        for quarters in (None, 0, -1, True, False, 1.5, 2.0, "2", [], {}):
            for length, expected in [(7000, "SURVEY_SCOPE_UNRESOLVED"),
                                     (6400, "FULL_RETRACE_CANDIDATE")]:
                with self.subTest(length=length, quarters=quarters):
                    self.assertEqual(self.amendment(existing_length_m=length,
                        affected_quarter_sections=quarters)["route"], expected)

    def test_other_record_types_and_non_linear_codes_do_not_inherit_survey_route(self):
        for existing in ("sketch", "surveyor_sketch", "hybrid_plan", "compiled_plan"):
            with self.subTest(existing=existing):
                self.assertEqual(self.amendment(existing_plan_type=existing,
                    existing_length_m=7000, affected_quarter_sections=3)["route"],
                    "AMENDMENT_PLAN_TYPE_UNRESOLVED")
        for code in ("MSL", "MLL", "PIL", "ABC"):
            with self.subTest(code=code):
                self.assertEqual(self.amendment(disposition=code, existing_length_m=7000,
                    affected_quarter_sections=3)["route"], "AMENDMENT_PLAN_TYPE_UNRESOLVED")

    def test_unknown_existing_plan_stays_unknown_across_amendment_and_renewal(self):
        for existing in (None, "", "unknown", "arbitrary", " survey_plan ", True, []):
            for stage in ("amendment", "renewal"):
                with self.subTest(existing=existing, stage=stage):
                    result = review_plan_type({**self.base, "stage": stage,
                        "existing_plan_type": existing, "disposition_changed": False,
                        "existing_length_m": 7000, "affected_quarter_sections": 3},
                        table_a2_rows=[self.row("Survey")])
                    finding = result[stage + "_review"]
                    self.assertEqual(finding["route" if stage == "amendment" else "comparison"],
                                     "PLAN_OF_RECORD_REQUIRED")

    def test_initial_exact_mappings_variants_substitution_and_na_precedence(self):
        cases = [
            ("Sketch", "sketch", "MATCHES_TABLE_A2"),
            ("Surveyor Sketch", "surveyor_sketch", "MATCHES_TABLE_A2"),
            ("Survey", "survey_plan", "MATCHES_TABLE_A2"),
            ("Survey", "surveyor_sketch", "DIFFERS_FROM_TABLE_A2"),
            ("Surveyor Sketch", "sketch", "DIFFERS_FROM_TABLE_A2"),
            ("Sketch", "survey_plan", "SURVEY_PLAN_SUBSTITUTION_REVIEW_REQUIRED"),
            ("Surveyor Sketch", "survey_plan", "SURVEY_PLAN_SUBSTITUTION_REVIEW_REQUIRED"),
            ("Survey", "hybrid_plan", "PLAN_VARIANT_REVIEW_REQUIRED"),
            ("Sketch", "compiled_plan", "PLAN_VARIANT_REVIEW_REQUIRED"),
            ("N/A", "hybrid_plan", "TABLE_A2_PLAN_TYPE_NOT_APPLICABLE"),
            ("N/A", None, "TABLE_A2_PLAN_TYPE_NOT_APPLICABLE"),
        ]
        for required, proposed, expected in cases:
            with self.subTest(required=required, proposed=proposed):
                result = review_plan_type({**self.base, "plan_type": proposed},
                                          table_a2_rows=[self.row(required)])
                self.assertEqual(result["table_a2_comparison"], expected)
                self.assertEqual(result["status"], "REVIEW_REQUIRED")
                self.assertFalse(result["regulatory_table_verified"])

    def test_renewal_change_flags_require_actual_booleans_before_other_checks(self):
        for changed in (None, "false", "true", 0, 1, [], {}):
            with self.subTest(changed=changed):
                result = review_plan_type({**self.base, "stage": "renewal",
                    "existing_plan_type": "survey_plan", "disposition_changed": changed},
                    table_a2_rows=[self.row("Survey")])
                self.assertEqual(result["renewal_review"]["comparison"],
                                 "DISPOSITION_CHANGE_STATUS_REQUIRED")
        result = review_plan_type({**self.base, "stage": "renewal",
            "existing_plan_type": None, "disposition_changed": True}, table_a2_rows=None)
        self.assertEqual(result["renewal_review"]["comparison"], "AMENDMENT_BEFORE_RENEWAL")

    def test_renewal_mappings_variants_and_na_do_not_establish_eligibility(self):
        cases = [
            ("Sketch", "sketch", "MATCHES_TABLE_A2"),
            ("Surveyor Sketch", "surveyor_sketch", "MATCHES_TABLE_A2"),
            ("Survey", "survey_plan", "MATCHES_TABLE_A2"),
            ("Sketch", "survey_plan", "SURVEY_PLAN_SUBSTITUTION_REVIEW_REQUIRED"),
            ("Surveyor Sketch", "survey_plan", "SURVEY_PLAN_SUBSTITUTION_REVIEW_REQUIRED"),
            ("Survey", "surveyor_sketch", "DIFFERS_FROM_TABLE_A2"),
            ("Survey", "hybrid_plan", "PLAN_VARIANT_REVIEW_REQUIRED"),
            ("Sketch", "compiled_plan", "PLAN_VARIANT_REVIEW_REQUIRED"),
            ("N/A", "compiled_plan", "TABLE_A2_PLAN_TYPE_NOT_APPLICABLE"),
        ]
        for required, existing, expected in cases:
            with self.subTest(required=required, existing=existing):
                result = review_plan_type({**self.base, "stage": "renewal",
                    "existing_plan_type": existing, "disposition_changed": False},
                    table_a2_rows=[self.row(required)])
                self.assertEqual(result["renewal_review"]["comparison"], expected)
                self.assertEqual(result["status"], "REVIEW_REQUIRED")
                self.assertFalse(result["regulatory_table_verified"])

    def test_legacy_dates_require_valid_date_and_only_apply_to_sketch_mismatch(self):
        cases = [(None, "LEGACY_ISSUE_DATE_UNRESOLVED"),
                 ("invalid", "LEGACY_ISSUE_DATE_UNRESOLVED"),
                 ("2010-02-30", "LEGACY_ISSUE_DATE_UNRESOLVED"),
                 (True, "LEGACY_ISSUE_DATE_UNRESOLVED"),
                 ("2010-08-31", "LEGACY_SKETCH_VARIANCE_REVIEW"),
                 ("2010-09-01", "DIFFERS_FROM_TABLE_A2"),
                 ("2010-09-02", "DIFFERS_FROM_TABLE_A2")]
        base = {**self.base, "stage": "renewal", "existing_plan_type": "sketch",
                "disposition_changed": False}
        for issued, expected in cases:
            with self.subTest(issued=issued):
                result = review_plan_type({**base, "disposition_issued_on": issued},
                                          table_a2_rows=[self.row("Survey")])
                self.assertEqual(result["renewal_review"]["comparison"], expected)
        match = review_plan_type({**base, "disposition_issued_on": "2010-08-31"},
                                 table_a2_rows=[self.row("Sketch")])
        self.assertEqual(match["renewal_review"]["comparison"], "MATCHES_TABLE_A2")

    def test_renewal_missing_or_duplicate_row_details_stay_unresolved(self):
        base = {**self.base, "stage": "renewal", "existing_plan_type": "survey_plan",
                "disposition_changed": False}
        for changes, rows, expected in [
            ({}, None, "TABLE_A2_REQUIRED"),
            ({}, [self.row("Survey"), {**self.row("Survey"), "row": 2}], "TABLE_A2_ROW_UNRESOLVED"),
            ({"purpose": None}, [self.row("Survey")], "TABLE_A2_ROW_UNRESOLVED"),
            ({"subactivity": None}, [self.row("Survey")], "TABLE_A2_ROW_UNRESOLVED"),
        ]:
            with self.subTest(changes=changes, expected=expected):
                result = review_plan_type({**base, **changes}, table_a2_rows=rows)
                self.assertEqual(result["renewal_review"]["comparison"], expected)

    def test_provincial_stages_do_not_select_aer_specialized_routes(self):
        for stage in ("initial", "amendment", "renewal"):
            result = review_plan_type({**self.base, "regulator": "Alberta", "stage": stage,
                "existing_plan_type": "survey_plan", "disposition_changed": False},
                table_a2_rows=[self.row("Survey")])
            for key in ("amendment_review", "renewal_review", "table_a2_requirement"):
                self.assertNotIn(key, result)


if __name__ == "__main__":
    unittest.main()
