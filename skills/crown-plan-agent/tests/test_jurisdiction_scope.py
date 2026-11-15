"""Synthetic jurisdiction gates; no private plans, network or legal certification."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from plan_type_review import review_plan_type
from regulatory_catalog import candidate_applicability, load_candidate_catalog
from requirements import application_context, applicability
from review_pipeline import review_inventory


class JurisdictionScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = load_candidate_catalog(
            Path(__file__).resolve().parents[1] / "engine" / "candidate_requirements.json")

    def setUp(self):
        self.scenario = {"regulator": "AER", "disposition": "LOC", "stage": "initial",
                         "plan_type": "sketch", "purpose": "Synthetic road",
                         "subactivity": "Synthetic access", "land_class": "alberta_crown"}
        self.rows = [{"disposition": "LOC", "purpose": "Synthetic road",
                      "activity": "Synthetic access", "row": 1, "page": 4,
                      "required_plan": "Survey", "survey_monuments": "1/4"}]
        self.inventory = {"spans": [{"text": "SCALE 1:5000", "page": 1}]}

    def test_explicit_non_crown_land_cannot_select_requirements(self):
        # Ignoring land_class would select Crown sections and fourteen checks.
        for land_class in ("private", "municipal", "federal", "other"):
            with self.subTest(land_class=land_class):
                scenario = {**self.scenario, "land_class": land_class}
                self.assertEqual(applicability(scenario)["sections"], [])
                decisions = candidate_applicability(self.catalogue, scenario)
                self.assertTrue(decisions)
                self.assertTrue(all(item["applicability_status"] == "OUT_OF_SCOPE"
                                    for item in decisions))
                report = review_inventory(self.inventory, scenario, self.catalogue,
                                          table_a2_rows=self.rows)
                self.assertEqual(report["requirements"], [])
                self.assertEqual(report["summary"]["total"], 0)
                self.assertEqual(report["plan_type_review"]["plan_type_status"], "OUT_OF_SCOPE")
                self.assertEqual(report["overall_status"], "REVIEW_REQUIRED")

    def test_missing_or_unknown_land_class_is_an_unresolved_dimension(self):
        for value in (None, "", " ", "unknown"):
            with self.subTest(value=value):
                scenario = {**self.scenario, "land_class": value}
                if value is None:
                    scenario.pop("land_class")
                context = application_context(scenario)
                self.assertEqual(context["scope_status"], "UNRESOLVED_SCOPE")
                self.assertEqual(context["missing_scope_dimensions"], ["land_class"])
                self.assertIn("land_class", context["missing_dimensions"])
                self.assertEqual(context["invalid_scope_dimensions"], [])
                self.assertEqual(applicability(scenario)["sections"], [])
                decisions = candidate_applicability(self.catalogue, scenario)
                self.assertTrue(all(item["applicability_status"] == "UNRESOLVED_APPLICABILITY"
                                    for item in decisions))
                report = review_inventory(self.inventory, scenario, self.catalogue)
                self.assertEqual(report["requirements"], [])
                self.assertEqual(report["overall_status"], "REVIEW_REQUIRED")

    def test_invalid_land_class_cannot_select_wildcard_checks(self):
        for value in ("unsupported", "*", 7, True, [], {}):
            with self.subTest(value=value):
                scenario = {**self.scenario, "land_class": value}
                context = application_context(scenario)
                self.assertEqual(context["scope_status"], "UNRESOLVED_SCOPE")
                self.assertEqual(context["invalid_scope_dimensions"], ["land_class"])
                self.assertIn("land_class", context["invalid_dimensions"])
                self.assertEqual(applicability(scenario)["sections"], [])
                self.assertTrue(all(item["applicability_status"] == "UNRESOLVED_APPLICABILITY"
                                    for item in candidate_applicability(self.catalogue, scenario)))

    def test_explicit_crown_land_keeps_candidate_content_review(self):
        context = application_context({**self.scenario, "land_class": " alberta_crown "})
        self.assertEqual(context["scope_status"], "IN_SCOPE")
        self.assertEqual(context["land_class"], "alberta_crown")
        self.assertIsNone(context["review_scope"])
        self.assertEqual(context["missing_dimensions"], [])
        self.assertEqual(context["invalid_dimensions"], [])
        self.assertEqual(applicability(self.scenario)["sections"],
                         ["Part 1", "Part 2", "Part 4.1"])
        report = review_inventory(self.inventory, self.scenario, self.catalogue)
        self.assertEqual(report["summary"]["total"], 14)
        self.assertEqual(report["plan_type_review"]["plan_type_status"], "CANDIDATE_ONLY")
        self.assertEqual(report["overall_status"], "REVIEW_REQUIRED")

    def test_mixed_land_requires_an_explicit_crown_component_review(self):
        for value in (None, "", " ", "unknown", "whole_plan", "private_component", 7, [], {}):
            with self.subTest(review_scope=value):
                scenario = {**self.scenario, "land_class": "mixed", "review_scope": value}
                context = application_context(scenario)
                self.assertEqual(context["scope_status"], "UNRESOLVED_SCOPE")
                self.assertIn("review_scope", context["missing_dimensions"]
                              + context["invalid_dimensions"])
                self.assertEqual(applicability(scenario)["sections"], [])
                self.assertTrue(all(item["applicability_status"] == "UNRESOLVED_APPLICABILITY"
                                    for item in candidate_applicability(self.catalogue, scenario)))
                self.assertEqual(review_plan_type(scenario)["plan_type_status"], "UNRESOLVED")
        scenario = {**self.scenario, "land_class": "mixed",
                    "review_scope": " alberta_crown_component "}
        context = application_context(scenario)
        self.assertEqual(context["scope_status"], "IN_SCOPE")
        self.assertEqual(context["land_class"], "mixed")
        self.assertEqual(context["review_scope"], "alberta_crown_component")
        self.assertEqual(context["missing_dimensions"], [])
        self.assertEqual(context["invalid_dimensions"], [])
        self.assertEqual(applicability(scenario)["sections"], ["Part 1", "Part 2", "Part 4.1"])
        self.assertEqual(review_inventory(self.inventory, scenario, self.catalogue)["summary"]["total"], 14)

    def test_scope_gate_blocks_each_specialized_plan_type_route(self):
        for stage in ("initial", "amendment", "renewal"):
            for scope, expected in (({"land_class": "private"}, "OUT_OF_SCOPE"),
                                    ({"land_class": None}, "UNRESOLVED"),
                                    ({"land_class": "mixed"}, "UNRESOLVED")):
                with self.subTest(stage=stage, scope=scope):
                    scenario = {**self.scenario, "stage": stage, "existing_plan_type": "survey_plan",
                                "existing_length_m": 7200, "affected_quarter_sections": 2,
                                "disposition_changed": False, **scope}
                    review = review_plan_type(scenario, table_a2_rows=self.rows)
                    self.assertEqual(review["plan_type_status"], expected)
                    self.assertNotIn("amendment_review", review)
                    self.assertNotIn("renewal_review", review)
                    self.assertNotIn("table_a2_requirement", review)
                    self.assertEqual(review["status"], "REVIEW_REQUIRED")

    def test_scope_gate_blocks_plan_specific_guidance_notes(self):
        for stage in ("initial", "amendment", "renewal"):
            for land_class in ("private", None, "mixed"):
                with self.subTest(stage=stage, land_class=land_class):
                    review = review_plan_type({**self.scenario, "stage": stage,
                                               "plan_type": "surveyor_sketch",
                                               "land_class": land_class})
                    notes = " ".join(review["notes"])
                    for instruction in ("Table A1", "7.5.1", "2025-31",
                                        "Public Lands Act section 23", "Alberta Land Surveyor"):
                        self.assertNotIn(instruction, notes)
        for scope in ({"land_class": "alberta_crown"},
                      {"land_class": "mixed", "review_scope": "alberta_crown_component"}):
            with self.subTest(scope=scope):
                review = review_plan_type({**self.scenario, "plan_type": "surveyor_sketch", **scope})
                notes = " ".join(review["notes"])
                self.assertIn("2025-31", notes)
                self.assertIn("Alberta Land Surveyor", notes)

    def test_out_of_scope_precedes_missing_other_context(self):
        scenario = {"land_class": "private"}
        self.assertEqual(review_plan_type(scenario)["plan_type_status"], "OUT_OF_SCOPE")
        self.assertTrue(all(item["applicability_status"] == "OUT_OF_SCOPE"
                            for item in candidate_applicability(self.catalogue, scenario)))

    def test_unresolved_proposed_type_can_identify_a2_row_only_in_crown_scope(self):
        for scope, can_identify in (({"land_class": "alberta_crown"}, True),
                                    ({"land_class": "mixed", "review_scope": "alberta_crown_component"}, True),
                                    ({"land_class": "private"}, False),
                                    ({"land_class": None}, False),
                                    ({"land_class": "mixed"}, False)):
            for proposed in (None, "unsupported"):
                with self.subTest(scope=scope, proposed=proposed):
                    scenario = {**self.scenario, "plan_type": proposed, **scope}
                    review = review_plan_type(scenario, table_a2_rows=self.rows)
                    if can_identify:
                        self.assertEqual(review["table_a2_requirement"]["row"], 1)
                        self.assertEqual(review["table_a2_comparison"], "PROPOSED_PLAN_TYPE_UNRESOLVED")
                    else:
                        self.assertNotIn("table_a2_requirement", review)


if __name__ == "__main__":
    unittest.main()
