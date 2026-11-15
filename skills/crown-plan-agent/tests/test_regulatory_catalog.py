"""Synthetic fail-closed catalogue tests."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from regulatory_catalog import candidate_applicability, load_candidate_catalog


class RegulatoryCatalogTests(unittest.TestCase):
    def setUp(self):
        self.path = Path(__file__).resolve().parents[1] / "engine" / "candidate_requirements.json"

    def test_load_is_unverified(self):
        entries = load_candidate_catalog(self.path)
        self.assertEqual(entries[0]["source_status"], "UNVERIFIED_CURRENT")

    def test_matching_scenario_is_candidate_not_pass(self):
        entries = load_candidate_catalog(self.path)
        result = candidate_applicability(entries, {"land_class": "alberta_crown", "regulator": "AER", "plan_type": "sketch",
                                "activity": "PLA", "stage": "initial"})
        self.assertEqual(result[0]["applicability_status"], "CANDIDATE_REVIEW")
        self.assertEqual(result[0]["status"], "REVIEW_REQUIRED")

    def test_unknown_scenario_fails_closed(self):
        entries = load_candidate_catalog(self.path)
        result = candidate_applicability(entries, {"plan_type": "sketch"})
        self.assertEqual(result[0]["applicability_status"], "UNRESOLVED_APPLICABILITY")

    def test_nonmatching_plan_type_not_selected(self):
        entries = load_candidate_catalog(self.path)
        entries = [entry for entry in entries
                   if entry["requirement_id"] == "CANDIDATE-PLAN-HEADING"]
        result = candidate_applicability(entries, {"land_class": "alberta_crown", "regulator": "AER", "plan_type": "compiled_plan",
                                 "activity": "PLA", "stage": "initial"})
        self.assertEqual(result[0]["applicability_status"], "NOT_SELECTED_FOR_REVIEW")

    def test_reject_forged_verified_source(self):
        original = json.loads(self.path.read_text(encoding="utf-8"))
        original["requirements"][0]["source_status"] = "VERIFIED_CURRENT"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(json.dumps(original), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_candidate_catalog(path)


if __name__ == "__main__":
    unittest.main()
