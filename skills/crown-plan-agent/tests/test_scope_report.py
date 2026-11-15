"""Synthetic reports expose declared jurisdiction without implying ownership."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from regulatory_catalog import load_candidate_catalog
from review_pipeline import review_inventory


class ScopeReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = load_candidate_catalog(
            Path(__file__).resolve().parents[1] / "engine" / "candidate_requirements.json")

    def test_scope_and_component_are_visible_in_reports(self):
        base = {"regulator": "AER", "disposition": "LOC", "stage": "initial",
                "plan_type": "sketch", "purpose": "Synthetic"}
        for fields, expected in (
            ({"land_class": "private"}, "OUT_OF_SCOPE"),
            ({}, "UNRESOLVED_SCOPE"),
            ({"land_class": "mixed", "review_scope": "alberta_crown_component"}, "IN_SCOPE"),
        ):
            with self.subTest(fields=fields):
                report = review_inventory({"spans": []}, {**base, **fields}, self.catalogue)
                self.assertIn("Jurisdiction scope: " + expected, report["report_markdown"])
                if expected != "IN_SCOPE":
                    self.assertEqual(report["requirements"], [])
                if fields.get("land_class") == "mixed":
                    self.assertIn("Review component: alberta_crown_component", report["report_markdown"])
                self.assertEqual(report["overall_status"], "REVIEW_REQUIRED")


if __name__ == "__main__":
    unittest.main()
