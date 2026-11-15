"""Invented predicates exercise typed three-valued applicability only."""
import copy
from decimal import Decimal
import itertools
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from clause_conditions import (evaluate_clause_conditions, evaluate_predicate,
                               prepare_fact_values)
from requirements import application_context


def definition(ident, kind, **changes):
    result = {"id": ident, "type": kind, "unit": None, "minimum": None,
              "maximum": None, "allowed_values": None,
              "provenance_required": False, "purpose": "applicability"}
    result.update(changes)
    return result


def record(value, provenance=None):
    return {"value": value, "provenance": provenance}


class ClauseConditionTests(unittest.TestCase):
    def setUp(self):
        self.defs = [definition("flag", "boolean"),
                     definition("other", "boolean"),
                     definition("length", "decimal", unit="m", minimum="0"),
                     definition("count", "integer", minimum=0),
                     definition("kind", "enum", allowed_values=["alpha", "beta"]),
                     definition("decision", "boolean", provenance_required=True,
                                purpose="manual_applicability")]
        self.provenance = {"source_id": "INVENTED-DECISION", "locator": "note:1"}

    def trace(self, predicate, facts=None, context=None):
        return evaluate_predicate(predicate, context or {},
                                  prepare_fact_values(self.defs, facts or {}))

    def test_known_false_zero_and_exact_decimal_remain_typed(self):
        prepared = prepare_fact_values(self.defs, {
            "flag": record(False), "count": record(0), "length": record("0.10"),
            "kind": record("alpha"), "decision": record(False, self.provenance)})
        self.assertIs(prepared["flag"]["value"], False)
        self.assertEqual(prepared["count"]["value"], 0)
        self.assertEqual(prepared["length"]["value"], Decimal("0.10"))
        self.assertTrue(prepared["decision"]["known"])
        self.assertIsNone(prepared["decision"]["issue"])

    def test_one_primary_fact_issue_follows_the_frozen_precedence(self):
        for facts, expected in (({}, "MISSING_FACT"),
                                ({"decision": record(None)}, "UNKNOWN_FACT"),
                                ({"decision": record("false")}, "INVALID_FACT_VALUE"),
                                ({"decision": record(True)}, "MISSING_PROVENANCE")):
            with self.subTest(facts=facts):
                value = prepare_fact_values(self.defs, facts)["decision"]
                self.assertFalse(value["known"])
                self.assertEqual(value["issue"], {"fact_id": "decision", "code": expected})

    def test_invalid_scalar_domain_and_decimal_encodings_stay_unknown(self):
        changes = [("flag", value) for value in (0, 1, "false", [], {})]
        changes += [("count", value) for value in (True, 1.0, -1, "1")]
        changes += [("length", value) for value in
                    (True, 1, 1.0, "NaN", "Infinity", ".5", "+1", "01.0", " 1", "1e3", "-1")]
        changes += [("kind", value) for value in (False, "gamma", "alpha ")]
        for name, value in changes:
            with self.subTest(name=name, value=value):
                prepared = prepare_fact_values(self.defs, {name: record(value)})
                self.assertFalse(prepared[name]["known"])
                self.assertEqual(prepared[name]["issue"]["code"], "INVALID_FACT_VALUE")

    def test_numeric_input_bounds_can_be_exclusive_without_constraining_literals(self):
        defs = [definition("length", "decimal", unit="m", minimum="0", maximum="1",
                           exclusive_minimum=True, exclusive_maximum=True)]
        for value, known in (("0", False), ("0.01", True), ("0.99", True), ("1", False)):
            with self.subTest(value=value):
                prepared = prepare_fact_values(defs, {"length": record(value)})
                self.assertEqual(prepared["length"]["known"], known)
        prepared = prepare_fact_values(defs, {"length": record("0.5")})
        result = evaluate_predicate({"gt": {"fact": "length", "value": "0"}}, {}, prepared)
        self.assertEqual(result["result"], "TRUE")

    def test_record_and_provenance_shapes_are_errors_even_for_unknown_values(self):
        invalid = [{"value": True}, {"value": True, "provenance": None, "status": "PASS"},
                   record(None, {}), record(None, {"source_id": "x", "locator": ""}),
                   record(None, {"source_id": "", "locator": "note:1"}),
                   record(True, {"source_id": "x", "locator": "note:1", "verified": True}),
                   record(True, "note:1")]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                prepare_fact_values(self.defs, {"flag": value})
        with self.assertRaises(ValueError):
            prepare_fact_values(self.defs, {"misspelled": record(True)})

    def test_all_and_any_follow_every_binary_three_valued_combination(self):
        literals = {"TRUE": {"const": True}, "FALSE": {"const": False},
                    "UNKNOWN": {"eq": {"fact": "flag", "value": True}}}
        all_expected = {("TRUE", "TRUE"): "TRUE", ("TRUE", "FALSE"): "FALSE",
                        ("TRUE", "UNKNOWN"): "UNKNOWN", ("FALSE", "TRUE"): "FALSE",
                        ("FALSE", "FALSE"): "FALSE", ("FALSE", "UNKNOWN"): "FALSE",
                        ("UNKNOWN", "TRUE"): "UNKNOWN", ("UNKNOWN", "FALSE"): "FALSE",
                        ("UNKNOWN", "UNKNOWN"): "UNKNOWN"}
        any_expected = {("TRUE", "TRUE"): "TRUE", ("TRUE", "FALSE"): "TRUE",
                        ("TRUE", "UNKNOWN"): "TRUE", ("FALSE", "TRUE"): "TRUE",
                        ("FALSE", "FALSE"): "FALSE", ("FALSE", "UNKNOWN"): "UNKNOWN",
                        ("UNKNOWN", "TRUE"): "TRUE", ("UNKNOWN", "FALSE"): "UNKNOWN",
                        ("UNKNOWN", "UNKNOWN"): "UNKNOWN"}
        for operator, expected in (("all", all_expected), ("any", any_expected)):
            for pair in itertools.product(literals, repeat=2):
                with self.subTest(operator=operator, pair=pair):
                    trace = self.trace({operator: [literals[key] for key in pair]})
                    self.assertEqual(trace["result"], expected[pair])
                    self.assertEqual(trace["nodes"][0]["result"], trace["result"])
                    self.assertEqual(len(trace["nodes"]), 3)
                    self.assertEqual(trace["blocking_fact_ids"],
                                     ["flag"] if expected[pair] == "UNKNOWN" else [])
                    if "UNKNOWN" in pair:
                        self.assertEqual(trace["fact_issues"], [{"fact_id": "flag",
                            "code": "MISSING_FACT", "blocking": expected[pair] == "UNKNOWN"}])

    def test_not_preserves_unknown_and_negates_only_known_booleans(self):
        for operand, expected in (({"const": True}, "FALSE"),
                                  ({"const": False}, "TRUE"),
                                  ({"eq": {"fact": "flag", "value": True}}, "UNKNOWN")):
            with self.subTest(operand=operand):
                self.assertEqual(self.trace({"not": operand})["result"], expected)

    def test_nested_nondecisive_issues_do_not_become_blockers(self):
        trace = self.trace({"all": [{"any": [{"const": True},
            {"eq": {"fact": "flag", "value": True}}]},
            {"eq": {"fact": "other", "value": True}}]})
        self.assertEqual(trace["result"], "UNKNOWN")
        self.assertEqual(trace["blocking_fact_ids"], ["other"])
        self.assertEqual(trace["fact_issues"], [
            {"fact_id": "flag", "code": "MISSING_FACT", "blocking": False},
            {"fact_id": "other", "code": "MISSING_FACT", "blocking": True}])

    def test_numeric_comparison_uses_decimal_values_and_all_ordered_operators(self):
        for operator, literal, expected in (("eq", "10.00", "TRUE"),
                ("lt", "10.00", "FALSE"), ("le", "10.00", "TRUE"),
                ("gt", "9.999999999", "TRUE"), ("ge", "10.000000001", "FALSE")):
            with self.subTest(operator=operator):
                trace = self.trace({operator: {"fact": "length", "value": literal}},
                                   {"length": record("10.0")})
                self.assertEqual(trace["result"], expected)
        self.assertEqual(self.trace({"in": {"fact": "length", "values": ["9", "10.00"]}},
                                   {"length": record("10.0")})["result"], "TRUE")

    def test_enum_boolean_and_context_comparisons_are_exact(self):
        self.assertEqual(self.trace({"eq": {"fact": "flag", "value": False}},
                                   {"flag": record(False)})["result"], "TRUE")
        self.assertEqual(self.trace({"in": {"fact": "kind", "values": ["beta"]}},
                                   {"kind": record("alpha")})["result"], "FALSE")
        trace = self.trace({"eq": {"context": "plan_type", "value": "compiled_plan"}},
                           context={"plan_type": "compiled_plan"})
        self.assertEqual(trace["result"], "TRUE")
        self.assertEqual(trace["nodes"][0]["operand"], {"origin": "context", "id": "plan_type"})

    def test_optional_context_none_is_unknown_without_core_scope_inference(self):
        trace = self.trace({"eq": {"context": "review_scope", "value": "alberta_crown_component"}},
                           context={"review_scope": None})
        self.assertEqual(trace["result"], "UNKNOWN")
        self.assertEqual(trace["blocking_fact_ids"], ["context:review_scope"])
        self.assertEqual(trace["fact_issues"], [{"fact_id": "context:review_scope",
                                               "code": "UNKNOWN_FACT", "blocking": True}])

    def test_declared_facts_cannot_collide_with_the_context_issue_namespace(self):
        with self.assertRaises(ValueError):
            prepare_fact_values([definition("context:review_scope", "boolean")], {})

    def test_direct_predicate_api_rejects_forged_or_incompatible_expressions(self):
        invalid = [{"const": "false"}, {"eval": "True"}, {"all": []},
                   {"eq": {"fact": "unknown", "value": True}},
                   {"eq": {"fact": "flag", "value": 1}},
                   {"gt": {"fact": "kind", "value": "alpha"}},
                   {"eq": {"fact": "length", "value": 1}},
                   {"in": {"fact": "length", "values": ["1", "1.0"]}},
                   {"in": {"fact": "flag", "value": [True]}},
                   {"eq": {"context": "private_attribute", "value": "x"}}]
        for predicate in invalid:
            with self.subTest(predicate=predicate), self.assertRaises(ValueError):
                self.trace(predicate)

    def test_resource_bounds_reject_oversized_fact_inputs_and_predicates(self):
        predicate = {"const": True}
        for _ in range(30):
            predicate = {"not": predicate}
        for value in (predicate, {"all": [{"const": True}] * 257}):
            with self.subTest(predicate=value), self.assertRaises(ValueError):
                self.trace(value)
        with self.assertRaises(ValueError):
            prepare_fact_values(self.defs, {"flag": record(True,
                {"source_id": "x", "locator": "x" * 4097})})

    def test_inputs_and_trace_results_are_not_mutated_or_shared(self):
        facts, context = {"length": record("10.0")}, {"plan_type": "survey_plan"}
        before = copy.deepcopy((self.defs, facts, context))
        prepared = prepare_fact_values(self.defs, facts)
        predicate = {"gt": {"fact": "length", "value": "9"}}
        first = evaluate_predicate(predicate, context, prepared)
        first["nodes"][0]["operand"]["id"] = "changed"
        second = evaluate_predicate(predicate, context, prepared)
        self.assertEqual(second["nodes"][0]["operand"]["id"], "length")
        self.assertEqual((self.defs, facts, context), before)

    def test_forged_prepared_flags_and_issue_shapes_are_explicit_errors(self):
        for mutate in (lambda p: p["flag"].update(known="false"),
                       lambda p: p["flag"]["issue"].update(code=[]),
                       lambda p: p["flag"].update(known=True, value=1, issue=None)):
            prepared = prepare_fact_values(self.defs, {})
            mutate(prepared)
            with self.subTest(prepared=prepared), self.assertRaises(ValueError):
                evaluate_predicate({"const": True}, {}, prepared)

    def test_two_bounded_source_predicates_can_form_a_larger_effective_trace(self):
        root = Path(__file__).resolve().parent
        catalogue = json.loads((root / "synthetic_clause_catalogue.json").read_text())
        catalogue["clauses"][0]["when"] = {"all": [{"const": True}] * 255}
        catalogue["clauses"][0]["checks"][0]["when"] = {"all": [{"const": True}] * 255}
        result = evaluate_clause_conditions(catalogue, {}, {})["check_results"]["ordinary_heading"]
        self.assertEqual(result["result"], "TRUE")
        self.assertEqual(len(result["nodes"]), 513)
        self.assertEqual(len({node["path"] for node in result["nodes"]}), 513)

    def test_frozen_cases_match_conditions_before_overrides(self):
        root = Path(__file__).resolve().parent
        catalogue = json.loads((root / "synthetic_clause_catalogue.json").read_text())
        cases = json.loads((root / "synthetic_clause_truth_cases.json").read_text())["cases"]
        for case in cases:
            context = application_context(case["input"]["scenario"])
            if context["scope_status"] != "IN_SCOPE" or context["missing_dimensions"] or context["invalid_dimensions"]:
                continue  # The workbook owns the pre-evaluation context stop gate.
            with self.subTest(case=case["case_id"]):
                result = evaluate_clause_conditions(catalogue, context, case["input"]["facts"])
                traces = result["check_results"]
                self.assertEqual({k: v["result"] for k, v in traces.items()},
                                 case["expected"]["effective_condition_results_before_overrides"])
                self.assertEqual({k: v["blocking_fact_ids"] for k, v in traces.items()
                                  if v["blocking_fact_ids"]}, case["expected"]["blocking_fact_ids_by_check"])
                self.assertEqual({k: v["fact_issues"] for k, v in traces.items() if v["fact_issues"]},
                                 case["expected"]["fact_issues_by_check"])
                for trace in traces.values():
                    paths = [node["path"] for node in trace["nodes"]]
                    self.assertEqual(len(paths), len(set(paths)))
                    self.assertEqual(trace["nodes"][0]["result"], trace["result"])


if __name__ == "__main__":
    unittest.main()
