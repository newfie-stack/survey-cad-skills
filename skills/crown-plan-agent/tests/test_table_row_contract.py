"""Invented rows exercise the public lookup boundary, without source attestation."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from plan_type_review import review_plan_type
from table_a2_lookup import lookup_plan_requirement, verify_disposition


class TableRowContractTests(unittest.TestCase):
    def setUp(self):
        self.row = {"row": 51, "page": 8, "disposition": "LOC", "purpose": "Pipeline",
                    "activity": "Fresh Water", "required_plan": "Sketch",
                    "survey_monuments": "N/A"}

    def lookup(self, rows):
        return lookup_plan_requirement(rows, disposition="LOC", purpose="Pipeline",
                                       activity="Fresh Water")

    def test_unknown_plan_labels_are_rejected_before_plan_comparison(self):
        for value in ("Unknown", "sketch", "", None, [], True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.lookup([{**self.row, "required_plan": value}])

    def test_nonmatching_malformed_row_cannot_make_a_match_appear_unique(self):
        with self.assertRaises(ValueError):
            self.lookup([self.row, {**self.row, "disposition": "PLA", "required_plan": "Unknown"}])

    def test_rows_must_be_a_list_of_objects(self):
        for rows in (None, {}, (self.row,), "rows", [None], ["row"], [[]]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.lookup(rows)

    def test_lookup_requires_all_content_fields(self):
        for field in self.row:
            row = {key: value for key, value in self.row.items() if key != field}
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.lookup([row])

    def test_row_and_page_locators_require_positive_nonboolean_integers(self):
        for field in ("row", "page"):
            for value in (0, -1, True, 1.0, "1", None):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.lookup([{**self.row, field: value}])

    def test_row_content_requires_strings_and_valid_disposition_syntax(self):
        for field in ("disposition", "purpose", "activity", "survey_monuments"):
            for value in (None, [], {}, 1, True):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.lookup([{**self.row, field: value}])
        for value in ("LO", "LOC;PLA", "123", "ŁOC"):
            with self.subTest(disposition=value), self.assertRaises(ValueError):
                self.lookup([{**self.row, "disposition": value}])

    def test_optional_row_fields_reject_wrong_types_or_unsupported_labels(self):
        invalid = {
            "rtf_approval": (True, [], "Maybe"),
            "rtf_authorization": (0, {}, "yes"),
            "consultation": (False, [], "Unknown"),
            "footnote": (False, 0, -1, "1", 1.0),
            "definition": (True, [], 2),
        }
        for field, values in invalid.items():
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.lookup([{**self.row, field: value}])

    def test_blank_disposition_rows_are_retained_without_inventing_a_code(self):
        rows = [self.row, {**self.row, "row": 52, "disposition": ""}]
        result = self.lookup(rows)
        self.assertEqual(result["row"], 51)
        self.assertEqual(verify_disposition(rows, "LOC")["matched_rows"], [{"row": 51, "page": 8}])

    def test_optional_evidence_remains_unknown_or_exactly_supplied(self):
        result = self.lookup([self.row])
        for field in ("rtf_approval", "rtf_authorization", "consultation", "footnote"):
            self.assertIsNone(result[field])
        row = {**self.row, "rtf_approval": "Yes", "rtf_authorization": "No",
               "consultation": "PA*", "footnote": 2, "definition": "Invented row definition"}
        result = self.lookup([row])
        self.assertEqual((result["rtf_approval"], result["rtf_authorization"],
                          result["consultation"], result["footnote"]), ("Yes", "No", "PA*", 2))
        self.assertEqual(result["status"], "SOURCE_ROW_IDENTIFIED_REVIEW_REQUIRED")
        self.assertEqual(result["regulatory_compliance"], "NOT_ASSESSED")
        self.assertNotIn("source_status", result)
        result = self.lookup([{**self.row, "rtf_approval": None, "rtf_authorization": None,
                               "consultation": None, "footnote": None, "definition": None}])
        self.assertIsNone(result["consultation"])

    def test_case_insensitive_trimmed_query_and_ambiguity_are_preserved(self):
        before = copy.deepcopy(self.row)
        result = lookup_plan_requirement([self.row], disposition=" loc ", purpose=" pipeline ",
                                         activity=" fresh water ")
        self.assertEqual(result["row"], 51)
        self.assertEqual(self.row, before)
        ambiguous = self.lookup([self.row, {**self.row, "row": 52}])
        self.assertEqual(ambiguous, {"status": "UNRESOLVED_APPLICABILITY",
                                     "matches": [{"row": 51, "page": 8}, {"row": 52, "page": 8}]})

    def test_code_only_lookup_preserves_minimal_record_contract(self):
        result = verify_disposition([{"disposition": "LOC", "row": 51, "page": 8}], "LOC")
        self.assertEqual(result["status"], "DISPOSITION_FOUND")
        self.assertEqual(result["regulatory_compliance"], "NOT_ASSESSED")
        for row in ({"disposition": 1, "row": 51, "page": 8},
                    {"disposition": "LOC", "row": True, "page": 8},
                    {"disposition": "LOC", "row": 51}, None):
            with self.subTest(row=row), self.assertRaises(ValueError):
                verify_disposition([row], "LOC")

    def test_initial_and_renewal_reject_bad_rows_without_mapping_errors(self):
        scenario = {"land_class": "alberta_crown", "regulator": "AER", "disposition": "LOC",
                    "stage": "initial", "plan_type": "sketch", "purpose": "Pipeline",
                    "subactivity": "Fresh Water", "existing_plan_type": "sketch",
                    "disposition_changed": False}
        for stage in ("initial", "renewal"):
            with self.subTest(stage=stage), self.assertRaises(ValueError):
                review_plan_type({**scenario, "stage": stage},
                                 table_a2_rows=[{**self.row, "required_plan": "Unknown"}])


if __name__ == "__main__":
    unittest.main()
