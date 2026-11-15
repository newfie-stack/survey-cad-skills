"""Frozen invented cases test the separate, opt-in dated-source workbook."""
import copy
import json
import sys
import unittest
from collections import deque
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from clause_workbook import prepare_clause_workbook

ROOT = Path(__file__).resolve().parent
PARTITIONS = {"selected": "CANDIDATE_REVIEW", "unselected": "NOT_SELECTED_FOR_REVIEW",
              "unresolved": "UNRESOLVED_APPLICABILITY", "out_of_scope": "OUT_OF_SCOPE"}


def fixture(name):
    return json.loads((ROOT / ("synthetic_clause_" + name + ".json")).read_text())


def records(workbook):
    return {check["id"]: check for clause in workbook["clauses"] for check in clause["checks"]}


def invented_inventory(catalogue):
    clauses = [{"clause_id": c["id"], "pdf_page": c["citation"]["page"],
                "summary": c["summary"], "requirement_status": c["kind"],
                "review_scope": [], "exceptions": [], "review_notes": [],
                "candidate_requirement_ids": [], "reference_only_requirement_ids": []}
               for c in catalogue["clauses"]]
    clauses.append({**copy.deepcopy(clauses[-1]), "clause_id": "4.1.1"})
    return {"schema_version": 1, "source_status": "UNVERIFIED_CURRENT",
            "source": {"publication_title": catalogue["source"]["title"],
                       "version_date": catalogue["source"]["version_date"],
                       "source_url": catalogue["source"]["url"],
                       "pdf_page_count": catalogue["source"]["page_count"]},
            "review_scope": "Invented explicit universe", "clauses": clauses}


class ClauseWorkbookTests(unittest.TestCase):
    def setUp(self):
        self.catalogue = fixture("catalogue")
        self.inputs = fixture("input")

    def check_frozen_case(self, index):
        case = fixture("truth_cases")["cases"][index]
        result = prepare_clause_workbook(self.catalogue, **case["input"])
        expected = case["expected"]
        checks = records(result)
        for kind, status in PARTITIONS.items():
            self.assertEqual(sorted(i for i, c in checks.items() if c["selection_status"] == status),
                             sorted(expected["check_partitions"][kind]))
            self.assertEqual(sorted(c["id"] for c in result["clauses"] if c["selection_status"] == status),
                             sorted(expected["clause_partitions"][kind]))
        self.assertEqual({i: c["condition_trace"]["result"] for i, c in checks.items()},
                         expected["effective_condition_results_before_overrides"])
        self.assertEqual({i: c["blocking_fact_ids"] for i, c in checks.items() if c["blocking_fact_ids"]},
                         expected["blocking_fact_ids_by_check"])
        self.assertEqual({i: c["fact_issues"] for i, c in checks.items() if c["fact_issues"]},
                         expected["fact_issues_by_check"])
        self.assertEqual(result["context_issues"], expected["context_issue_codes"])
        decisions = [d for c in result["clauses"] for d in c["override_trace"]]
        key = lambda d: (d["by_clause_id"], d["action"], d["targets"])
        self.assertEqual(sorted(decisions, key=key), sorted(expected["override_decisions"], key=key))
        self.assertEqual({i: c["override_reason_codes"] for i, c in checks.items() if c["override_reason_codes"]},
                         expected["override_reason_codes_by_target"])
        self.assertEqual({i: c["evidence_status"] for i, c in checks.items()}, expected["evidence_status_by_check"])
        self.assertEqual({i: c["observation_refs"] for i, c in checks.items() if c["observation_refs"]},
                         expected["observation_refs_by_check"])
        self.assertEqual(result["counts"], expected["counts"])
        self.assertEqual(result["coverage"], expected["coverage"])
        self.assertEqual(result["overall_status"], "REVIEW_REQUIRED")
        self.assertEqual(result["source_status"], "UNVERIFIED_CURRENT")
        for clause in result["clauses"]:
            for item in [clause, *clause["checks"]]:
                self.assertEqual(item["status"], "REVIEW_REQUIRED")
                self.assertEqual(item["source_status"], "UNVERIFIED_CURRENT")
        for check in checks.values():
            self.assertEqual(check["review_requests"], check["questions"]
                             if check["selection_status"] == "CANDIDATE_REVIEW" else [])
            self.assertEqual(check["pending_applicability_questions"], check["questions"]
                             if check["selection_status"] == "UNRESOLVED_APPLICABILITY" else [])

    def test_explicit_inventory_matches_exact_source_and_lists_gaps(self):
        inventory = invented_inventory(self.catalogue)
        result = prepare_clause_workbook(self.catalogue, **{**self.inputs, "coverage_inventory": inventory})
        self.assertEqual(result["coverage"], {"universe_status": "MATCHED",
                         "expected_clause_count": 7, "unmapped_clause_ids": ["4.1.1"],
                         "atomic_obligation_completeness": "NOT_ASSESSED"})

    def test_inventory_mismatch_or_forged_authority_is_rejected(self):
        variants = []
        for field, value in [("publication_title", "Different"), ("version_date", "2001-01-01"),
                             ("pdf_page_count", 4)]:
            data = invented_inventory(self.catalogue); data["source"][field] = value; variants.append(data)
        data = invented_inventory(self.catalogue); data["clauses"][0]["pdf_page"] = 2; variants.append(data)
        data = invented_inventory(self.catalogue); data["clauses"].pop(0); variants.append(data)
        data = invented_inventory(self.catalogue); data["source_status"] = "VERIFIED_CURRENT"; variants.append(data)
        for data in variants:
            with self.subTest(data=data), self.assertRaises(ValueError):
                prepare_clause_workbook(self.catalogue, **{**self.inputs, "coverage_inventory": data})

    def test_no_inventory_or_observation_binding_is_inferred(self):
        catalogue = copy.deepcopy(self.catalogue)
        catalogue["source"].update(title="Content Requirements for Survey Plans and Sketches for Dispositions on Crown Lands",
                                   version_date="2024-05-30", page_count=17, classification="DATED_MANUAL")
        ordinary = fixture("truth_cases")["cases"][0]["input"]
        scenario = {**ordinary["scenario"], "available_observation_ids": ["CANDIDATE-PLAN-HEADING"]}
        result = prepare_clause_workbook(catalogue, scenario, ordinary["facts"])
        self.assertEqual(result["coverage"]["universe_status"], "NOT_SUPPLIED")
        self.assertIsNone(result["coverage"]["unmapped_clause_ids"])
        self.assertEqual(records(result)["ordinary_heading"]["observation_refs"], [])
        self.assertEqual(records(result)["ordinary_heading"]["evidence_status"], "MANUAL_REVIEW_REQUIRED")

    def test_observation_ids_are_explicit_bounded_unique_known_collections(self):
        for invalid in [None, "CANDIDATE-PLAN-HEADING", b"x", {"CANDIDATE-PLAN-HEADING": True},
                        iter(["CANDIDATE-PLAN-HEADING"]), ["unknown"], [True],
                        ["CANDIDATE-PLAN-HEADING"] * 2, [["CANDIDATE-PLAN-HEADING"]]]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                prepare_clause_workbook(self.catalogue, self.inputs["scenario"], self.inputs["facts"],
                                        available_observation_ids=invalid)
        ordinary = fixture("truth_cases")["cases"][0]["input"]
        for value in [[], (), set(), frozenset(), deque()]:
            prepare_clause_workbook(self.catalogue, ordinary["scenario"], ordinary["facts"], available_observation_ids=value)

    def test_scope_stops_predicates_but_not_basic_fact_validation(self):
        for scenario in [{**self.inputs["scenario"], "land_class": "private"},
                         {k: v for k, v in self.inputs["scenario"].items() if k != "plan_type"}]:
            for facts in [{"unknown": {"value": True, "provenance": None}},
                          {"has_details": {"value": True}},
                          {"has_details": {"value": True, "provenance": {"source_id": "", "locator": "x"}}}]:
                with self.subTest(scenario=scenario, facts=facts), self.assertRaises(ValueError):
                    prepare_clause_workbook(self.catalogue, scenario, facts)
            with patch("clause_workbook.evaluate_clause_conditions", side_effect=AssertionError("predicate ran")), \
                    patch("clause_workbook.resolve_overrides", side_effect=AssertionError("override ran")):
                result = prepare_clause_workbook(self.catalogue, scenario, self.inputs["facts"])
                self.assertTrue(all(c["condition_trace"]["result"] == "NOT_EVALUATED" for c in records(result).values()))

    def test_input_and_result_collections_do_not_alias(self):
        before = copy.deepcopy((self.catalogue, self.inputs))
        result = prepare_clause_workbook(self.catalogue, **self.inputs)
        result["source"]["title"] = "Changed"
        result["clauses"][0]["checks"][0]["questions"].append("Changed")
        self.assertEqual((self.catalogue, self.inputs), before)
        fresh = prepare_clause_workbook(self.catalogue, **self.inputs)
        self.assertNotEqual(fresh["source"]["title"], "Changed")

    def test_frozen_override_cases_preserve_target_and_provider_states(self):
        for case in fixture("override_cases")["cases"]:
            with self.subTest(case=case["case_id"]):
                result = prepare_clause_workbook(case["catalogue"], **case["input"])
                checks = records(result); expected = case["expected"]
                self.assertEqual(checks[expected["target_check_id"]]["selection_status"], expected["target_selection_status"])
                if expected.get("reason_code"):
                    self.assertIn(expected["reason_code"], checks[expected["target_check_id"]]["override_reason_codes"])
                for ident in expected.get("replacement_provider_check_ids", []):
                    self.assertEqual(checks[ident]["selection_status"], expected["replacement_provider_selection_status"])


def _frozen_test(index):
    def test(self): self.check_frozen_case(index)
    return test


for _index in range(10):
    setattr(ClauseWorkbookTests, f"test_frozen_truth_{_index + 1:02}", _frozen_test(_index))


if __name__ == "__main__":
    unittest.main()
