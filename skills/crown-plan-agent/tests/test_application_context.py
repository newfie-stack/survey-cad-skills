"""Synthetic context regressions using the shipped candidate catalogue offline."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from plan_type_review import review_plan_type
from regulatory_catalog import candidate_applicability, load_candidate_catalog
from review_pipeline import review_inventory


class ApplicationContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = load_candidate_catalog(
            Path(__file__).resolve().parents[1] / "engine" / "candidate_requirements.json")

    def setUp(self):
        self.scenario = {"land_class": "alberta_crown", "regulator": "AER", "disposition": "PLA", "stage": "initial",
                         "plan_type": "sketch", "purpose": "synthetic"}
        self.inventory = {"spans": [{"text": "SCALE 1:5000", "page": 1}]}

    def test_missing_context_cannot_select_default_checks(self):
        for field in ("regulator", "disposition", "stage", "plan_type"):
            for value in (None, "", " "):
                with self.subTest(field=field, value=value):
                    scenario = {**self.scenario, field: value}
                    if value is None:
                        scenario.pop(field)
                    decisions = candidate_applicability(self.catalogue, scenario)
                    self.assertTrue(decisions)
                    self.assertTrue(all(item["applicability_status"] == "UNRESOLVED_APPLICABILITY"
                                        for item in decisions))
                    self.assertTrue(all(field in item["missing_dimensions"] for item in decisions))
                    report = review_inventory(self.inventory, scenario, self.catalogue)
                    self.assertEqual(report["requirements"], [])
                    self.assertEqual(report["summary"]["total"], 0)
                    self.assertEqual(report["overall_status"], "REVIEW_REQUIRED")

    def test_invalid_context_cannot_select_wildcard_default_checks(self):
        for field, values in (
                ("regulator", ("unsupported", "*", 7, [])),
                ("disposition", ("not-a-code", "*", 7, [])),
                ("stage", ("not_a_stage", "*", 7, [])),
                ("plan_type", ("not_a_plan_type", "*", 7, []))):
            for value in values:
                with self.subTest(field=field, value=value):
                    scenario = {**self.scenario, field: value}
                    # Exercise the legacy alias too: the original wildcard bug
                    # arose even with an explicit nonempty activity and stage.
                    if field != "disposition":
                        scenario["activity"] = scenario.pop("disposition")
                    decisions = candidate_applicability(self.catalogue, scenario)
                    self.assertTrue(all(item["applicability_status"] == "UNRESOLVED_APPLICABILITY"
                                        for item in decisions))
                    self.assertTrue(all(field in item.get("invalid_dimensions", []) for item in decisions))
                    report = review_inventory(self.inventory, scenario, self.catalogue)
                    self.assertEqual(report["requirements"], [])
                    self.assertEqual(report["summary"]["observed_candidates"], 0)
                    self.assertEqual(report["overall_status"], "REVIEW_REQUIRED")
                    self.assertEqual(report["plan_type_review"]["plan_type_status"], "UNRESOLVED")

    def test_supported_context_and_disposition_aliases_remain_candidates(self):
        for regulator in ("AER", "Alberta"):
            for aliases in ({"disposition": "PLA"}, {"activity": "PLA"},
                            {"disposition": " pla ", "activity": "PLA"}):
                with self.subTest(regulator=regulator, aliases=aliases):
                    scenario = {k: v for k, v in self.scenario.items() if k != "disposition"}
                    scenario.update(regulator=regulator, **aliases)
                    report = review_inventory(self.inventory, scenario, self.catalogue)
                    self.assertEqual(report["summary"]["total"], 14)
                    self.assertEqual(report["summary"]["observed_candidates"], 1)
                    self.assertTrue(all(item["applicability_status"] == "CANDIDATE_REVIEW"
                                        for item in report["requirements"]))
                    self.assertTrue(all(item["status"] == "REVIEW_REQUIRED"
                                        for item in report["requirements"]))
                    self.assertEqual(report["plan_type_review"]["plan_type_status"], "CANDIDATE_ONLY")

    def test_conflicting_disposition_aliases_are_unresolved(self):
        report = review_inventory(self.inventory, {**self.scenario, "activity": "LOC"},
                                  self.catalogue)
        self.assertEqual(report["requirements"], [])
        self.assertTrue(all("disposition" in item.get("invalid_dimensions", [])
                            for item in report["applicability_decisions"]))

    def test_invalid_regulator_cannot_be_a_candidate_plan_type(self):
        result = review_plan_type({**self.scenario, "activity": "PLA", "regulator": "unsupported"})
        self.assertEqual(result["plan_type_status"], "UNRESOLVED")
        self.assertIn("regulator", result["missing_or_invalid_fields"])

    def test_amendment_uses_normalized_proposed_plan_type(self):
        result = review_plan_type({**self.scenario, "regulator": " AER ",
                                   "disposition": " loc ", "stage": " amendment ",
                                   "plan_type": " sketch ", "existing_plan_type": "survey_plan",
                                   "existing_length_m": 7200, "affected_quarter_sections": 2})
        self.assertEqual(result["plan_type_status"], "CANDIDATE_ONLY")
        self.assertEqual(result["amendment_review"]["comparison"], "ITEMIZED_SKETCH_CONFLICT")

    def test_unresolved_core_context_cannot_select_specialized_routes(self):
        row = {"disposition": "LOC", "purpose": "synthetic", "activity": "",
               "row": 1, "page": 4, "required_plan": "Survey", "survey_monuments": "1/4"}
        for stage in ("initial", "amendment", "renewal"):
            for field in ("regulator", "disposition", "stage", "plan_type"):
                for value in (None, "unsupported"):
                    with self.subTest(stage=stage, field=field, value=value):
                        scenario = {**self.scenario, "disposition": "LOC", "stage": stage,
                                    "existing_plan_type": "survey_plan", "existing_length_m": 7200,
                                    "affected_quarter_sections": 2, "disposition_changed": False,
                                    "subactivity": "", field: value}
                        if value is None:
                            scenario.pop(field)
                        result = review_plan_type(scenario, table_a2_rows=[row])
                        self.assertEqual(result["plan_type_status"], "UNRESOLVED")
                        self.assertNotIn("amendment_review", result)
                        self.assertNotIn("renewal_review", result)
                        if stage == "initial" and field == "plan_type":
                            self.assertEqual(result["table_a2_requirement"]["row"], 1)
                            self.assertEqual(result["table_a2_comparison"], "PROPOSED_PLAN_TYPE_UNRESOLVED")
                        else:
                            self.assertNotIn("table_a2_requirement", result)
                            self.assertNotIn("table_a2_comparison", result)

    def test_missing_purpose_preserves_known_amendment_scope_review(self):
        result = review_plan_type({"land_class": "alberta_crown", "regulator": "AER", "disposition": "LOC", "stage": "amendment",
                                   "plan_type": "sketch", "existing_plan_type": "survey_plan",
                                   "existing_length_m": 7200, "affected_quarter_sections": 2})
        self.assertEqual(result["plan_type_status"], "UNRESOLVED")
        self.assertEqual(result["missing_or_invalid_fields"], ["purpose"])
        self.assertEqual(result["amendment_review"]["comparison"], "ITEMIZED_SKETCH_CONFLICT")


if __name__ == "__main__":
    unittest.main()
