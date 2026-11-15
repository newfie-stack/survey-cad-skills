"""Invented exemptions/replacements cannot silently select ordinary routes."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from clause_conditions import evaluate_clause_conditions
from clause_overrides import resolve_overrides
from requirements import application_context


class ClauseOverrideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parent
        cls.catalogue = json.loads((cls.root / "synthetic_clause_catalogue.json").read_text())
        cls.request = json.loads((cls.root / "synthetic_clause_input.json").read_text())

    def resolve(self, catalogue=None, request=None):
        catalogue = catalogue if catalogue is not None else self.catalogue
        request = request if request is not None else self.request
        conditions = evaluate_clause_conditions(catalogue, application_context(request["scenario"]),
                                                 request["facts"])
        return resolve_overrides(catalogue, conditions["clause_results"], conditions["check_results"])

    def test_frozen_core_cases_match_atomic_partitions_and_cited_decisions(self):
        cases = json.loads((self.root / "synthetic_clause_truth_cases.json").read_text())["cases"]
        statuses = {"selected": "CANDIDATE_REVIEW", "unselected": "NOT_SELECTED_FOR_REVIEW",
                    "unresolved": "UNRESOLVED_APPLICABILITY", "out_of_scope": "OUT_OF_SCOPE"}
        for case in cases:
            context = application_context(case["input"]["scenario"])
            if context["scope_status"] != "IN_SCOPE" or context["missing_dimensions"] or context["invalid_dimensions"]:
                continue  # The workbook owns the pre-evaluation scope stop gate.
            with self.subTest(case=case["case_id"]):
                result = self.resolve(request=case["input"])
                checks, expected = result["checks"], case["expected"]
                for name, status in statuses.items():
                    self.assertEqual({ident for ident, value in checks.items()
                                      if value["selection_status"] == status},
                                     set(expected["check_partitions"][name]))
                self.assertEqual(result["override_decisions"], expected["override_decisions"])
                self.assertEqual({ident: value["blocking_fact_ids"] for ident, value in checks.items()
                                  if value["blocking_fact_ids"]}, expected["blocking_fact_ids_by_check"])
                self.assertEqual({ident: value["fact_issues"] for ident, value in checks.items()
                                  if value["fact_issues"]}, expected["fact_issues_by_check"])
                self.assertEqual({ident: value["override_reason_codes"] for ident, value in checks.items()
                                  if value["override_reason_codes"]}, expected["override_reason_codes_by_target"])

    def test_all_eight_frozen_override_cases_preserve_targets_and_providers(self):
        cases = json.loads((self.root / "synthetic_clause_override_cases.json").read_text())["cases"]
        self.assertEqual(len(cases), 8)
        for case in cases:
            with self.subTest(case=case["case_id"]):
                result = self.resolve(case["catalogue"], case["input"])
                expected = case["expected"]
                target = result["checks"][expected["target_check_id"]]
                self.assertEqual(target["selection_status"], expected["target_selection_status"])
                reason = expected.get("target_reason_code", expected.get("reason_code"))
                self.assertIn(reason, target["override_reason_codes"])
                for ident in expected["replacement_provider_check_ids"]:
                    provider = result["checks"][ident]
                    self.assertEqual(provider["selection_status"],
                                     expected["replacement_provider_selection_status"])
                    if "provider_reason_code" in expected and expected["provider_reason_code"] != "UNKNOWN_FACT":
                        self.assertIn(expected["provider_reason_code"], provider["override_reason_codes"])
                if "target_blocking_fact_ids" in expected:
                    self.assertEqual(target["blocking_fact_ids"], expected["target_blocking_fact_ids"])
                if "provider_blocking_fact_ids" in expected:
                    for ident in expected["replacement_provider_check_ids"]:
                        self.assertEqual(result["checks"][ident]["blocking_fact_ids"],
                                         expected["provider_blocking_fact_ids"])
                decisions = {item["by_clause_id"]: item for item in result["override_decisions"]}
                for ident, truth in expected["controller_condition_results"].items():
                    self.assertEqual(decisions[ident]["condition_result"], truth)
                    self.assertEqual(decisions[ident]["citation"], {"section": ident, "page": 3})

    def test_true_exemption_clears_an_unknown_target_without_losing_raw_trace(self):
        catalogue = copy.deepcopy(self.catalogue)
        catalogue["clauses"][0]["checks"][0]["when"] = {
            "eq": {"fact": "has_details", "value": True}}
        request = copy.deepcopy(self.request)
        request["facts"].pop("has_details")
        check = self.resolve(catalogue, request)["checks"]["ordinary_heading"]
        self.assertEqual(check["condition_trace"]["result"], "UNKNOWN")
        self.assertEqual(check["condition_trace"]["blocking_fact_ids"], ["has_details"])
        self.assertEqual(check["selection_status"], "NOT_SELECTED_FOR_REVIEW")
        self.assertEqual(check["blocking_fact_ids"], [])
        self.assertEqual(check["fact_issues"], [{"fact_id": "has_details",
                                               "code": "MISSING_FACT", "blocking": False}])

    def test_single_unknown_exemption_does_not_fall_through_to_required(self):
        catalogue = copy.deepcopy(self.catalogue)
        catalogue["clauses"][4]["when"] = {"eq": {"fact": "special_applies", "value": True}}
        request = copy.deepcopy(self.request)
        request["scenario"]["plan_type"] = "survey_plan"
        request["facts"]["special_applies"] = {"value": None, "provenance": None}
        check = self.resolve(catalogue, request)["checks"]["ordinary_heading"]
        self.assertEqual(check["selection_status"], "UNRESOLVED_APPLICABILITY")
        self.assertEqual(check["blocking_fact_ids"], ["special_applies"])
        self.assertEqual(check["fact_issues"], [{"fact_id": "special_applies",
                                               "code": "UNKNOWN_FACT", "blocking": True}])
        self.assertIn("OVERRIDE_APPLICABILITY_UNRESOLVED", check["override_reason_codes"])

    def test_two_true_replacements_are_a_confirmed_conflict(self):
        fixture = json.loads((self.root / "synthetic_clause_override_cases.json").read_text())["cases"][2]
        request = copy.deepcopy(fixture["input"])
        request["facts"]["special_applies"] = {"value": True,
            "provenance": {"source_id": "INVENTED-REVIEW", "locator": "note:1"}}
        result = self.resolve(fixture["catalogue"], request)
        for ident in ("ordinary_heading", "compiled_certificate", "alternative_certificate"):
            check = result["checks"][ident]
            self.assertEqual(check["selection_status"], "UNRESOLVED_APPLICABILITY")
            self.assertIn("CONFLICTING_OVERRIDES", check["override_reason_codes"])

    def test_unknown_override_on_false_target_never_blocks_the_old_path(self):
        catalogue = copy.deepcopy(self.catalogue)
        catalogue["clauses"][0]["checks"][0]["when"] = {"const": False}
        catalogue["clauses"][4]["when"] = {"eq": {"fact": "special_applies", "value": True}}
        request = copy.deepcopy(self.request)
        request["facts"]["special_applies"] = {"value": None, "provenance": None}
        check = self.resolve(catalogue, request)["checks"]["ordinary_heading"]
        self.assertEqual(check["selection_status"], "NOT_SELECTED_FOR_REVIEW")
        self.assertEqual(check["blocking_fact_ids"], [])
        self.assertTrue(all(item["blocking"] is False for item in check["fact_issues"]))
        self.assertIn("CONDITION_FALSE", check["override_reason_codes"])

    def test_input_and_independent_output_objects_are_not_mutated_or_shared(self):
        catalogue, request = copy.deepcopy(self.catalogue), copy.deepcopy(self.request)
        before = copy.deepcopy((catalogue, request))
        conditions = evaluate_clause_conditions(catalogue, application_context(request["scenario"]), request["facts"])
        traces_before = copy.deepcopy(conditions)
        result = resolve_overrides(catalogue, conditions["clause_results"], conditions["check_results"])
        result["override_decisions"][0]["citation"]["page"] = 999
        self.assertEqual(result["checks"]["ordinary_heading"]["override_trace"][0]["citation"]["page"], 3)
        self.assertEqual(conditions, traces_before)
        self.assertEqual((catalogue, request), before)

    def test_bad_missing_or_scope_gated_traces_are_rejected(self):
        conditions = evaluate_clause_conditions(self.catalogue,
            application_context(self.request["scenario"]), self.request["facts"])
        for mutate in (
            lambda c: c["check_results"].pop("ordinary_heading"),
            lambda c: c["clause_results"]["3.1.1"].update(result="PASS"),
            lambda c: c["clause_results"]["3.1.1"].update(result="NOT_EVALUATED", nodes=[]),
            lambda c: c["clause_results"]["3.1.1"]["nodes"][0].update(path="unrooted"),
            lambda c: c["check_results"]["ordinary_heading"].update(blocking_fact_ids=["unknown"]),
        ):
            value = copy.deepcopy(conditions)
            mutate(value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                resolve_overrides(self.catalogue, value["clause_results"], value["check_results"])

    def test_empty_catalogue_has_no_invented_paths_or_controls(self):
        catalogue = copy.deepcopy(self.catalogue)
        catalogue["clauses"] = []
        self.assertEqual(resolve_overrides(catalogue, {}, {}),
                         {"checks": {}, "override_decisions": []})

    def test_forged_logical_results_and_orphan_paths_are_rejected(self):
        conditions = evaluate_clause_conditions(self.catalogue,
            application_context(self.request["scenario"]), self.request["facts"])
        for change in ("false_all", "missing_child", "extra_leaf_child"):
            value = copy.deepcopy(conditions)
            trace = value["check_results"]["ordinary_heading"]
            if change == "false_all":
                trace["result"] = trace["nodes"][0]["result"] = "FALSE"
            elif change == "missing_child":
                trace["nodes"][2]["path"] = "$.all[9]"
            else:
                trace["nodes"].append({"path": "$.all[1].all[0]", "operator": "const",
                                        "result": "TRUE", "operand": None})
            with self.subTest(change=change), self.assertRaises(ValueError):
                resolve_overrides(self.catalogue, value["clause_results"], value["check_results"])

    def test_raw_trace_blockers_must_follow_its_unknown_operands(self):
        request = copy.deepcopy(self.request)
        request["facts"]["length_m"]["value"] = "10.01"
        request["facts"]["special_applies"] = {"value": None, "provenance": None}
        conditions = evaluate_clause_conditions(self.catalogue,
            application_context(request["scenario"]), request["facts"])
        trace = conditions["check_results"]["extension_review"]
        trace["blocking_fact_ids"] = ["has_details"]
        trace["fact_issues"] = [{"fact_id": "has_details", "code": "UNKNOWN_FACT", "blocking": True}]
        with self.assertRaises(ValueError):
            resolve_overrides(self.catalogue, conditions["clause_results"], conditions["check_results"])


if __name__ == "__main__":
    unittest.main()
