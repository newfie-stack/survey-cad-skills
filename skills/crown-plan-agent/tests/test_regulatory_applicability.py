"""Invented applicability cases against dated paths, not current compliance."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "engine"))

from clause_schema import load_bounded_json, load_clause_catalogue
from clause_workbook import prepare_clause_workbook
from clause_workbook_markdown import render_clause_workbook
from coverage_inventory import load_inventory
from regulatory_catalog import load_candidate_catalog
from review_pipeline import review_inventory


class RegulatoryReviewBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = load_candidate_catalog(SKILL / "engine/candidate_requirements.json")
        cls.clauses = load_clause_catalogue(SKILL / "engine/dated_clause_catalogue.json")
        cls.coverage = load_inventory()

    def review(self, scenario, facts=None):
        return review_inventory(
            {"source_filename": "invented-regulatory-inventory.json", "pages": 1, "spans": []},
            scenario, self.catalogue, clause_catalogue=self.clauses,
            clause_facts={} if facts is None else facts, clause_inventory=self.coverage,
        )


class RegulatoryAliasConflictTests(RegulatoryReviewBase):
    def setUp(self):
        self.scenario = {"land_class": "alberta_crown", "regulator": "AER",
                         "disposition": "LOC", "stage": "initial", "plan_type": "sketch",
                         "purpose": "Invented purpose", "subactivity": "Invented activity"}

    def test_conflicting_aliases_produce_a_report_and_no_active_review_paths(self):
        for legacy in ("PLA", None, "not-a-code"):
            with self.subTest(legacy=legacy):
                scenario = {**self.scenario, "activity": legacy}
                report = self.review(scenario)
                self.assertEqual(report["requirements"], [])
                workbook = report["clause_workbook"]
                self.assertEqual(workbook["context_issues"], ["INVALID_CONTEXT:disposition"])
                self.assertIsNone(workbook["context"]["disposition"])
                self.assertTrue(all(row["selection_status"] == "UNRESOLVED_APPLICABILITY"
                                    for row in workbook["clauses"]))
                for row in workbook["clauses"]:
                    for check in row["checks"]:
                        self.assertEqual(check["review_requests"], [])
                        self.assertEqual(check["pending_applicability_questions"], check["questions"])
                        self.assertEqual(check["condition_trace"]["result"], "NOT_EVALUATED")
                requests = {item["field"] for item in report["review_summary"]["input_requests"]}
                self.assertIn("disposition", requests)
                self.assertEqual(report["overall_status"], "REVIEW_REQUIRED")
                self.assertIn("Dated-source clause workbook", report["report_markdown"])

    def test_equivalent_aliases_keep_their_valid_context(self):
        for legacy in ("LOC", "loc", " LOC "):
            with self.subTest(legacy=legacy):
                report = self.review({**self.scenario, "activity": legacy})
                workbook = report["clause_workbook"]
                self.assertEqual(workbook["context"]["disposition"], "LOC")
                self.assertEqual(workbook["context_issues"], [])
                general = next(row for row in workbook["clauses"] if row["id"] == "1.3.6.2")
                self.assertEqual(general["selection_status"], "CANDIDATE_REVIEW")
                self.assertTrue(report["requirements"])

    def test_renderer_still_rejects_a_conflict_hidden_by_a_valid_looking_code(self):
        workbook = prepare_clause_workbook(self.clauses, {**self.scenario, "activity": "PLA"}, {})
        self.assertIsNone(workbook["context"]["disposition"])
        forged = copy.deepcopy(workbook)
        forged["context"]["disposition"] = "LOC"
        with self.assertRaises(ValueError):
            render_clause_workbook(forged)


class RegulatoryApplicabilityMatrixTests(RegulatoryReviewBase):
    def test_independent_scenarios_survive_the_full_review_pipeline(self):
        path = SKILL / "tests/fixtures/regulatory_applicability_cases.json"
        self.assertTrue(path.is_file(), "Independent regulatory applicability matrix is missing")
        matrix = load_bounded_json(path)
        self.assertEqual(matrix["evidence_class"], "WHOLLY_INVENTED_SYNTHETIC")
        for field in ("title", "version_date", "url"):
            self.assertEqual(matrix["source_basis"][field], self.clauses["source"][field])
        cases = matrix["cases"]
        self.assertTrue(cases, "An empty matrix cannot protect any applicability decision")
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        tested_families = set()
        for case in cases:
            with self.subTest(case=case["id"]):
                tested_families.add(case["family"])
                self.assertTrue(case["expected_clauses"] or case["expected_checks"],
                                "Each case must pin a source-specific decision")
                scenario = {**matrix["base_scenario"], **case["scenario_changes"]}
                no_provenance = set(case.get("without_provenance", []))
                facts = {
                    ident: {"value": value, "provenance": None if ident in no_provenance else {
                        "source_id": "INVENTED-" + case["id"], "locator": "Invented applicability facts"}}
                    for ident, value in case["facts"].items()
                }
                before = copy.deepcopy((scenario, facts))
                report = self.review(scenario, facts)
                self.assertEqual((scenario, facts), before)
                workbook = report["clause_workbook"]
                clauses = {row["id"]: row for row in workbook["clauses"]}
                for expected in case["expected_clauses"]:
                    row = clauses[expected["id"]]
                    self.assertEqual(row["selection_status"], expected["selection_status"], expected["id"])
                    if "blocking_fact_ids" in expected:
                        self.assertEqual(row["blocking_fact_ids"], expected["blocking_fact_ids"], expected["id"])
                for expected in case["expected_checks"]:
                    row = clauses[expected["clause_id"]]
                    check = next(item for item in row["checks"] if item["id"] == expected["id"])
                    self.assertEqual(check["selection_status"], expected["selection_status"], expected["id"])
                    if "blocking_fact_ids" in expected:
                        self.assertEqual(check["blocking_fact_ids"], expected["blocking_fact_ids"], expected["id"])
                    if "kind" in expected:
                        self.assertEqual(check["kind"], expected["kind"], expected["id"])
                for issue in case.get("expected_fact_issues", []):
                    self.assertIn({"fact_id": issue["fact_id"], "code": issue["code"], "blocking": True},
                                  clauses[issue["clause_id"]]["fact_issues"])
                self.assertEqual(workbook["source_status"], "UNVERIFIED_CURRENT")
                self.assertEqual(workbook["overall_status"], "REVIEW_REQUIRED")
                self.assertEqual(workbook["coverage"]["universe_status"], "MATCHED")
                self.assertEqual(workbook["coverage"]["atomic_obligation_completeness"], "NOT_ASSESSED")
                self.assertEqual(report["overall_status"], "REVIEW_REQUIRED")
                self.assertFalse(report["plan_type_review"]["regulatory_table_verified"])
                for row in report["requirements"]:
                    self.assertEqual(row["status"], "REVIEW_REQUIRED")
                    self.assertEqual(row["source_status"], "UNVERIFIED_CURRENT")
                for row in workbook["clauses"]:
                    self.assertEqual(row["status"], "REVIEW_REQUIRED")
                    for check in row["checks"]:
                        self.assertEqual(check["source_status"], "UNVERIFIED_CURRENT")
                        self.assertEqual(check["observation_refs"], [])
                        if check["selection_status"] == "CANDIDATE_REVIEW":
                            self.assertEqual(check["review_requests"], check["questions"])
                            self.assertEqual(check["evidence_status"], "MANUAL_REVIEW_REQUIRED")
                        else:
                            self.assertEqual(check["review_requests"], [])
                            self.assertEqual(check["evidence_status"], "NOT_EVALUATED")
                self.assertTrue(report["review_inputs"]["clause_workbook_requested"])
                self.assertIn("Dated-source clause workbook", report["report_markdown"])
        self.assertTrue({"pla_length", "mixed_land", "msl_area", "rtf_family", "compiled_bearing"}
                        <= tested_families, "Keep independent coverage across the key scenario families")


if __name__ == "__main__":
    unittest.main()
