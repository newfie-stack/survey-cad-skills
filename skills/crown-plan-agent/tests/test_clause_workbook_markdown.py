"""The renderer accepts only consistent review-only workbook views."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from clause_workbook import prepare_clause_workbook
from clause_workbook_markdown import render_clause_workbook

ROOT = Path(__file__).resolve().parent


def fixture(name):
    return json.loads((ROOT / ("synthetic_clause_" + name + ".json")).read_text())


class ClauseWorkbookMarkdownTests(unittest.TestCase):
    def setUp(self):
        self.catalogue = fixture("catalogue")
        self.cases = fixture("truth_cases")["cases"]
        self.workbook = prepare_clause_workbook(self.catalogue, **self.cases[0]["input"])

    def test_identity_scope_and_reference_limits_are_prominent(self):
        text = render_clause_workbook(self.workbook)
        self.assertTrue(text.startswith("## Dated-source clause workbook\n"))
        for value in ["INVENTED-CONDITIONAL-001", "Invented Manual for Conditional Review Tests", "2000-01-01",
                      "INVENTED", "UNVERIFIED_CURRENT", "REVIEW_REQUIRED", "NOT_ASSESSED", "NOT_SUPPLIED"]:
            self.assertIn(value, text)
        self.assertIn("Caller-declared observation references", text)
        self.assertIn("No adapters were executed by this workbook", text)
        self.assertIn("Compare the ordinary heading", text)

    def test_pending_questions_and_optional_guidance_stay_distinct(self):
        unresolved = render_clause_workbook(prepare_clause_workbook(self.catalogue, **self.cases[3]["input"]))
        self.assertIn("Questions pending applicability", unresolved)
        self.assertIn(r"has\_details", unresolved)
        optional = render_clause_workbook(prepare_clause_workbook(self.catalogue, **self.cases[4]["input"]))
        self.assertIn("Guidance review", optional)
        self.assertIn("absence is not a deficiency", optional)

    def test_every_frozen_truth_and_override_view_renders(self):
        for case in self.cases:
            with self.subTest(case=case["case_id"]):
                render_clause_workbook(prepare_clause_workbook(self.catalogue, **case["input"]))
        for case in fixture("override_cases")["cases"]:
            with self.subTest(case=case["case_id"]):
                render_clause_workbook(prepare_clause_workbook(case["catalogue"], **case["input"]))

    def test_forged_statuses_are_rejected_at_every_level(self):
        for location, key, value in [("top", "overall_status", "PASS"), ("top", "source_status", "VERIFIED_CURRENT"),
                                     ("clause", "status", "PASS"), ("clause", "source_status", "VERIFIED_CURRENT"),
                                     ("check", "status", "FAIL"), ("check", "source_status", "VERIFIED_CURRENT"),
                                     ("check", "evidence_status", "PASS")]:
            with self.subTest(location=location, key=key):
                data = copy.deepcopy(self.workbook)
                item = data if location == "top" else data["clauses"][0]
                if location == "check": item = item["checks"][0]
                item[key] = value
                with self.assertRaises(ValueError): render_clause_workbook(data)

    def test_nested_shapes_ids_enums_counts_and_references_are_checked(self):
        mutations = [
            lambda d: d.update(extra="hidden"),
            lambda d: d["source"].update(source_status="VERIFIED_CURRENT"),
            lambda d: d["source"].update(version_date="yesterday"),
            lambda d: d["source"].update(url="http://example.org/source"),
            lambda d: d["clauses"][0].update(status="NOT_APPLICABLE"),
            lambda d: d["clauses"][0].update(id="not.a.clause"),
            lambda d: d["clauses"][0]["citation"].update(page=999),
            lambda d: d["clauses"][0]["checks"][0].update(id=""),
            lambda d: d["clauses"][1]["checks"][0].update(id="ordinary_heading"),
            lambda d: d["clauses"][0]["checks"][0].update(kind="mixed"),
            lambda d: d["clauses"][0]["checks"][0].update(selection_status="NOT_APPLICABLE"),
            lambda d: d["clauses"][0]["checks"][0].update(observation_refs=["UNKNOWN-ADAPTER"]),
            lambda d: d["clauses"][0]["checks"][0].update(review_requests=[]),
            lambda d: d["clauses"][0]["checks"][0].update(questions=[{"status": "PASS"}]),
            lambda d: d["clauses"][0]["checks"][0]["condition_trace"].update(result="PASS"),
            lambda d: d["clauses"][0]["checks"][0]["condition_trace"]["nodes"][0].update(operator="eval"),
            lambda d: d["counts"].update(selected_clause_paths=True),
            lambda d: d["counts"].update(available_observation_links=99),
            lambda d: d["coverage"].update(atomic_obligation_completeness="VERIFIED"),
            lambda d: d["context"].update(scope_status="VERIFIED"),
            lambda d: d["context"].update(land_class="private"),
            lambda d: d["clauses"][4]["override_trace"][0].update(effect="APPROVED"),
            lambda d: d["clauses"][4]["override_trace"][0].update(targets=["unknown_check"]),
            lambda d: d["clauses"][3]["fact_issues"].clear(),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                data = copy.deepcopy(self.workbook); mutate(data)
                with self.assertRaises(ValueError): render_clause_workbook(data)

    def test_gated_context_cannot_smuggle_requests_or_executed_traces(self):
        for case_index in [2, 9]:
            result = prepare_clause_workbook(self.catalogue, **self.cases[case_index]["input"])
            result["clauses"][0]["checks"][0]["review_requests"] = ["Do this now"]
            with self.assertRaises(ValueError): render_clause_workbook(result)

    def test_malformed_enum_containers_raise_value_error(self):
        mutations = [
            lambda d: d["clauses"][0]["condition_trace"].update(result=[]),
            lambda d: d["clauses"][0]["condition_trace"]["nodes"][0].update(operator={}),
            lambda d: d["clauses"][0]["condition_trace"]["nodes"][0].update(result=[]),
            lambda d: d["clauses"][0].update(selection_status=[]),
            lambda d: d["clauses"][4]["override_trace"][0].update(action=[]),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                data = copy.deepcopy(self.workbook); mutate(data)
                with self.assertRaises(ValueError): render_clause_workbook(data)

    def test_renderer_does_not_mutate_workbook(self):
        before = copy.deepcopy(self.workbook)
        render_clause_workbook(self.workbook)
        self.assertEqual(self.workbook, before)

    def test_known_true_obligation_cannot_be_hidden_by_recounting(self):
        result = copy.deepcopy(self.workbook)
        check = result["clauses"][0]["checks"][0]
        check.update(selection_status="NOT_SELECTED_FOR_REVIEW", review_requests=[],
                     observation_refs=[], evidence_status="NOT_EVALUATED")
        result["counts"]["selected_required_manual_checks"] -= 1
        result["counts"]["available_observation_links"] -= 1
        with self.assertRaises(ValueError): render_clause_workbook(result)

    def test_fabricated_missing_context_cannot_hide_valid_paths(self):
        result = prepare_clause_workbook(self.catalogue, **self.cases[2]["input"])
        result["context"] = copy.deepcopy(self.workbook["context"])
        with self.assertRaises(ValueError): render_clause_workbook(result)

    def test_contradictory_logical_trace_cannot_hide_an_obligation(self):
        result = copy.deepcopy(self.workbook)
        check = result["clauses"][0]["checks"][0]
        # A synthetic all node cannot be FALSE when both retained children are TRUE.
        check["condition_trace"]["result"] = "FALSE"
        check["condition_trace"]["nodes"][0]["result"] = "FALSE"
        check.update(selection_status="NOT_SELECTED_FOR_REVIEW", review_requests=[],
                     observation_refs=[], evidence_status="NOT_EVALUATED")
        result["counts"]["selected_required_manual_checks"] -= 1
        result["counts"]["available_observation_links"] -= 1
        with self.assertRaises(ValueError): render_clause_workbook(result)


if __name__ == "__main__":
    unittest.main()
