"""Invented cross-layer review cases, not regulatory compliance acceptance.

The dated manual supplies review paths. Fictional application facts and table
rows exercise their orchestration without claiming current-source verification,
complete obligation coverage, or facts extracted from any real drawing.
"""
import copy
import sys
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "engine"))

from clause_schema import load_clause_catalogue
from coverage_inventory import load_inventory
from regulatory_catalog import load_candidate_catalog
from review_pipeline import review_inventory


class RegulatoryPipelineCasesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = load_candidate_catalog(SKILL / "engine/candidate_requirements.json")
        cls.clauses = load_clause_catalogue(SKILL / "engine/dated_clause_catalogue.json")
        cls.coverage = load_inventory()

    def setUp(self):
        self.scenario = {
            "land_class": "alberta_crown", "regulator": "AER", "disposition": "LOC",
            "stage": "initial", "plan_type": "sketch",
            "purpose": "Synthetic corridor purpose", "subactivity": "Synthetic trial activity",
        }
        self.inventory = {
            "source_filename": "invented-regulatory-case.pdf", "pages": 1,
            "status": "TEXT_INVENTORY_ONLY", "spans": [
                {"text": "SKETCH", "page": 1, "bbox_points": [10, 10, 80, 20]},
                {"text": "SCALE 1:5000", "page": 1, "bbox_points": [10, 30, 100, 40]},
            ],
        }

    def table_row(self, required_plan):
        # This fictional row is a lookup input, not a transcription of Table A2.
        return {"disposition": "LOC", "purpose": "Synthetic corridor purpose",
                "activity": "Synthetic trial activity", "row": 1, "page": 4,
                "required_plan": required_plan, "survey_monuments": "N/A"}

    @staticmethod
    def facts(**values):
        return {key: {"value": value, "provenance": {
            "source_id": "INVENTED-APPLICATION", "locator": "Synthetic fact register"}}
                for key, value in values.items()}

    def review(self, *, scenario=None, inventory=None, facts=None, rows=None):
        return review_inventory(
            self.inventory if inventory is None else inventory,
            self.scenario if scenario is None else scenario,
            self.candidates, table_a2_rows=rows,
            clause_catalogue=self.clauses, clause_facts={} if facts is None else facts,
            clause_inventory=self.coverage,
        )

    @staticmethod
    def requirement(report, ident):
        return next(item for item in report["requirements"] if item["requirement_id"] == ident)

    @staticmethod
    def clause(report, ident):
        return next(item for item in report["clause_workbook"]["clauses"] if item["id"] == ident)

    def assert_review_only(self, report):
        self.assertEqual(report["overall_status"], "REVIEW_REQUIRED")
        self.assertEqual(report["plan_type_review"]["status"], "REVIEW_REQUIRED")
        self.assertFalse(report["plan_type_review"]["regulatory_table_verified"])
        self.assertEqual(report["review_summary"]["status"], "REVIEW_REQUIRED")
        self.assertEqual(report["clause_workbook"]["source_status"], "UNVERIFIED_CURRENT")
        self.assertEqual(report["clause_workbook"]["coverage"]["atomic_obligation_completeness"],
                         "NOT_ASSESSED")
        for item in report["requirements"]:
            self.assertEqual(item["status"], "REVIEW_REQUIRED")
            self.assertEqual(item["source_status"], "UNVERIFIED_CURRENT")
        self.assertIn("not a regulatory compliance certificate", report["report_markdown"])
        self.assertIn("Dated-source clause workbook", report["report_markdown"])

    def test_observed_sketch_heading_does_not_resolve_a_conflicting_table_row(self):
        report = self.review(rows=[self.table_row("Survey")])
        self.assertEqual(self.requirement(report, "CANDIDATE-PLAN-HEADING")["evidence_status"],
                         "OBSERVED_CANDIDATE")
        self.assertEqual(report["plan_type_review"]["table_a2_comparison"], "DIFFERS_FROM_TABLE_A2")
        heading = self.clause(report, "1.2.1.1")["checks"][0]
        self.assertEqual(heading["selection_status"], "CANDIDATE_REVIEW")
        self.assertTrue(heading["review_requests"])
        self.assertEqual(heading["observation_refs"], [])
        self.assertEqual(heading["evidence_status"], "MANUAL_REVIEW_REQUIRED")
        self.assertIn("differs from the identified Table A2 row",
                      " ".join(report["review_summary"]["needs_attention"]))
        self.assertIn("Comparison: DIFFERS_FROM_TABLE_A2", report["report_markdown"])
        self.assert_review_only(report)

    def test_removing_scale_text_keeps_the_applicable_manual_question(self):
        baseline = self.review(rows=[self.table_row("Sketch")])
        without_scale = copy.deepcopy(self.inventory)
        without_scale["spans"].pop(1)
        missing = self.review(inventory=without_scale, rows=[self.table_row("Sketch")])
        self.assertEqual(self.requirement(baseline, "CANDIDATE-PLAN-SCALE")["evidence_status"],
                         "OBSERVED_CANDIDATE")
        scale = self.requirement(missing, "CANDIDATE-PLAN-SCALE")
        self.assertEqual(scale["evidence_status"], "UNKNOWN")
        self.assertIsNone(scale["input_evidence"])
        self.assertEqual(missing["plan_type_review"]["table_a2_comparison"], "MATCHES_TABLE_A2")
        question = self.clause(missing, "1.2.2.3")["checks"][0]
        self.assertEqual(question["selection_status"], "CANDIDATE_REVIEW")
        self.assertTrue(question["review_requests"])
        self.assertEqual(question["evidence_status"], "MANUAL_REVIEW_REQUIRED")
        self.assertEqual(question["observation_refs"], [])
        self.assertEqual(missing["clause_workbook"], baseline["clause_workbook"])
        self.assertIn("CANDIDATE-PLAN-SCALE |", missing["report_markdown"])
        self.assertIn("Drawing details still need visual confirmation",
                      " ".join(missing["review_summary"]["needs_attention"]))
        self.assert_review_only(missing)

    def test_matching_row_and_complete_citation_do_not_verify_current_authority(self):
        report = self.review(rows=[self.table_row("Sketch")])
        scale = self.requirement(report, "CANDIDATE-PLAN-SCALE")
        self.assertTrue(scale["source_review"]["citation_complete"])
        self.assertEqual(scale["source_review"]["source_status"], "REVIEW_REQUIRED")
        self.assertIsNone(scale["verified_at"])
        self.assertEqual(report["plan_type_review"]["table_a2_comparison"], "MATCHES_TABLE_A2")
        self.assertEqual(report["plan_type_review"]["table_a2_requirement"]["regulatory_compliance"],
                         "NOT_ASSESSED")
        self.assertIn("have not been verified as current",
                      " ".join(report["review_summary"]["needs_attention"]))
        self.assertIn("Compliance: NOT_ASSESSED", report["report_markdown"])
        self.assert_review_only(report)

    def test_compiled_amendment_keeps_replacement_questions_when_evidence_is_unknown(self):
        scenario = {**self.scenario, "stage": "amendment", "plan_type": "compiled_plan",
                    "existing_plan_type": "survey_plan", "existing_length_m": 7000,
                    "affected_quarter_sections": 2}
        inventory = copy.deepcopy(self.inventory)
        inventory["spans"][0]["text"] = (
            "COMPILED PLAN FROM EXISTING SURVEYS FOR THE PURPOSE OF SYNTHETIC TRIAL")
        report = self.review(scenario=scenario, inventory=inventory, facts=self.facts(
            existing_is_surveyed=True, is_linear=True, existing_length_m="7000",
            affected_quarter_sections=2))
        self.assertEqual(report["plan_type_review"]["amendment_review"]["route"],
                         "PLAN_VARIANT_REVIEW_REQUIRED")
        excluded = {item["requirement_id"] for item in report["excluded_from_evidence_review"]}
        self.assertIn("CANDIDATE-PLAN-HEADING", excluded)
        self.assertEqual(self.requirement(report, "CANDIDATE-COMPILED-PLAN-HEADING")["evidence_status"],
                         "OBSERVED_CANDIDATE")
        self.assertEqual(self.requirement(report, "CANDIDATE-COMPILED-DECLARATION")["evidence_status"],
                         "VISUAL_CHECK_REQUIRED")
        for ident in ("1.2.1.1", "3.1.2.1", "3.2.1.1", "3.3.2.1"):
            with self.subTest(clause=ident):
                row = self.clause(report, ident)
                self.assertEqual(row["selection_status"], "NOT_SELECTED_FOR_REVIEW")
                self.assertTrue(all(not check["review_requests"] for check in row["checks"]))
        for ident in ("1.2.2.1", "1.3.6.3", "3.6.1.2", "3.6.1.3"):
            with self.subTest(retained=ident):
                row = self.clause(report, ident)
                self.assertEqual(row["selection_status"], "CANDIDATE_REVIEW")
                self.assertTrue(all(check["review_requests"] for check in row["checks"]))
        declaration = self.clause(report, "3.6.1.3")
        self.assertTrue(all(check["evidence_status"] == "MANUAL_REVIEW_REQUIRED"
                            and not check["observation_refs"] for check in declaration["checks"]))
        ordinary = self.clause(report, "3.1.2.1")["checks"][0]
        self.assertIn("REPLACED_BY_OVERRIDE", ordinary["override_reason_codes"])
        self.assertIn("Confirm the applicable amendment or variant requirements",
                      " ".join(report["review_summary"]["next_steps"]))
        self.assertIn("PLAN_VARIANT_REVIEW_REQUIRED", report["report_markdown"])
        self.assert_review_only(report)

    def test_hybrid_amendment_retains_ordinary_and_itemized_review_paths(self):
        scenario = {**self.scenario, "stage": "amendment", "plan_type": "hybrid_plan",
                    "existing_plan_type": "survey_plan", "existing_length_m": 7000,
                    "affected_quarter_sections": 2}
        inventory = copy.deepcopy(self.inventory)
        inventory["spans"][0]["text"] = "PLAN SHOWING SURVEY (HYBRID) OF SYNTHETIC TRIAL"
        report = self.review(scenario=scenario, inventory=inventory, facts=self.facts(
            existing_is_surveyed=True, is_linear=True, existing_length_m="7000",
            affected_quarter_sections=2, uses_itemized_survey=True, amendment_change_kind="add"))
        self.assertEqual(report["plan_type_review"]["amendment_review"]["route"],
                         "ITEMIZED_SURVEY_CANDIDATE")
        self.assertEqual(self.requirement(report, "CANDIDATE-HYBRID-PLAN-HEADING")["evidence_status"],
                         "OBSERVED_CANDIDATE")
        for ident in ("1.2.1.1", "3.1.2.1", "3.3.2.1", "3.3.3.1", "3.5.1.1"):
            with self.subTest(clause=ident):
                row = self.clause(report, ident)
                self.assertEqual(row["selection_status"], "CANDIDATE_REVIEW")
                self.assertTrue(any(check["review_requests"] for check in row["checks"]))
        self.assertEqual(self.clause(report, "3.6.1.3")["selection_status"], "NOT_SELECTED_FOR_REVIEW")
        self.assertIn("candidate itemized-survey scope",
                      " ".join(report["review_summary"]["next_steps"]))
        self.assertIn("Survey scope: ITEMIZED_SURVEY_CANDIDATE", report["report_markdown"])
        self.assert_review_only(report)

    def test_renewal_uses_the_existing_sketch_despite_a_proposed_survey_heading(self):
        scenario = {**self.scenario, "stage": "renewal", "plan_type": "survey_plan",
                    "existing_plan_type": "sketch", "disposition_changed": False,
                    "disposition_issued_on": "2010-08-31"}
        inventory = copy.deepcopy(self.inventory)
        inventory["spans"][0]["text"] = "SURVEY"
        report = self.review(scenario=scenario, inventory=inventory,
                             rows=[self.table_row("Survey")])
        renewal = report["plan_type_review"]["renewal_review"]
        self.assertEqual(renewal["existing_plan_type"], "sketch")
        self.assertEqual(renewal["comparison"], "LEGACY_SKETCH_VARIANCE_REVIEW")
        self.assertEqual(self.requirement(report, "CANDIDATE-PLAN-HEADING")["evidence_status"],
                         "OBSERVED_CANDIDATE")
        self.assertEqual(self.clause(report, "3.1.2.1")["selection_status"], "CANDIDATE_REVIEW")
        self.assertEqual(self.clause(report, "3.3.2.1")["selection_status"], "NOT_SELECTED_FOR_REVIEW")
        self.assertNotIn("disposition_issued_on",
                         [item["field"] for item in report["review_summary"]["input_requests"]])
        self.assertIn("legacy variance needs separate review",
                      " ".join(report["review_summary"]["needs_attention"]))
        self.assertIn("Plan type on file: sketch", report["report_markdown"])
        self.assertIn("Comparison: LEGACY_SKETCH_VARIANCE_REVIEW", report["report_markdown"])
        self.assert_review_only(report)

    def test_provincial_regulator_keeps_manual_paths_without_an_aer_amendment_route(self):
        scenario = {**self.scenario, "stage": "amendment", "plan_type": "survey_plan",
                    "existing_plan_type": "survey_plan", "existing_length_m": 7000,
                    "affected_quarter_sections": 2}
        facts = self.facts(existing_is_surveyed=True, is_linear=True, existing_length_m="7000",
                           affected_quarter_sections=2)
        aer = self.review(scenario=scenario, facts=facts)
        provincial = self.review(scenario={**scenario, "regulator": "Alberta"}, facts=facts)
        self.assertEqual(aer["plan_type_review"]["amendment_review"]["route"],
                         "ITEMIZED_SURVEY_CANDIDATE")
        self.assertNotIn("amendment_review", provincial["plan_type_review"])
        for report in (aer, provincial):
            self.assertEqual(self.requirement(report, "CANDIDATE-PLAN-SCALE")["evidence_status"],
                             "OBSERVED_CANDIDATE")
            self.assertEqual(self.clause(report, "3.3.2.1")["selection_status"], "CANDIDATE_REVIEW")
            self.assertTrue(self.clause(report, "3.3.2.1")["checks"][0]["review_requests"])
            self.assert_review_only(report)
        self.assertIn("AER amendment plan review", aer["report_markdown"])
        self.assertNotIn("AER amendment plan review", provincial["report_markdown"])
        self.assertNotIn("candidate itemized-survey scope",
                         " ".join(provincial["review_summary"]["next_steps"]))

    def test_scope_and_unknown_regulator_block_plausible_text_and_clause_requests(self):
        cases = (
            ({"land_class": "private"}, "OUT_OF_SCOPE", "OUT_OF_SCOPE", []),
            ({"land_class": "mixed"}, "UNRESOLVED_APPLICABILITY", "UNRESOLVED", ["review_scope"]),
            ({"regulator": "Synthetic authority"}, "UNRESOLVED_APPLICABILITY", "UNRESOLVED", ["regulator"]),
        )
        for changes, selection, plan_status, requests in cases:
            with self.subTest(context=changes):
                report = self.review(scenario={**self.scenario, **changes},
                                     rows=[self.table_row("Survey")], facts=self.facts(is_access_road=True))
                self.assertEqual(report["requirements"], [])
                self.assertTrue(all(item["applicability_status"] == selection
                                    for item in report["applicability_decisions"]))
                self.assertEqual(report["plan_type_review"]["plan_type_status"], plan_status)
                for key in ("table_a2_requirement", "amendment_review", "renewal_review"):
                    self.assertNotIn(key, report["plan_type_review"])
                for clause in report["clause_workbook"]["clauses"]:
                    self.assertEqual(clause["selection_status"], selection)
                    for check in clause["checks"]:
                        self.assertEqual(check["review_requests"], [])
                        self.assertEqual(check["observation_refs"], [])
                        self.assertEqual(check["evidence_status"], "NOT_EVALUATED")
                self.assertEqual([item["field"] for item in report["review_summary"]["input_requests"]],
                                 requests)
                self.assertIn(selection, report["report_markdown"])
                self.assert_review_only(report)

    def test_explicit_mixed_crown_component_enables_only_a_declared_component_review(self):
        report = self.review(scenario={**self.scenario, "land_class": "mixed",
                                      "review_scope": "alberta_crown_component"},
                             rows=[self.table_row("Sketch")])
        self.assertEqual(report["plan_type_review"]["scope_status"], "IN_SCOPE")
        self.assertEqual(report["plan_type_review"]["table_a2_comparison"], "MATCHES_TABLE_A2")
        self.assertEqual(self.requirement(report, "CANDIDATE-PLAN-SCALE")["evidence_status"],
                         "OBSERVED_CANDIDATE")
        self.assertEqual(self.clause(report, "1.2.1.1")["selection_status"], "CANDIDATE_REVIEW")
        self.assertEqual(report["review_summary"]["input_requests"], [])
        self.assertIn("Scope is limited to the declared Alberta Crown component",
                      report["report_markdown"])
        self.assert_review_only(report)


if __name__ == "__main__":
    unittest.main()
