"""Synthetic integrated Crown plan review; no real plan content."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from regulatory_catalog import load_candidate_catalog
from review_pipeline import review_inventory


class ReviewPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = load_candidate_catalog(
            Path(__file__).resolve().parents[1] / "engine" / "candidate_requirements.json"
        )

    def test_complete_candidate_is_review_only(self):
        inventory = {"status": "TEXT_AND_VECTOR_INVENTORY_ONLY",
                     "spans": [{"text": "SCALE 1:5000", "page": 1,
                                "bbox_points": [10, 10, 80, 25]}]}
        scenario = {"land_class": "alberta_crown", "plan_type": "sketch", "activity": "PLA", "stage": "initial",
                    "regulator": "AER", "purpose": "synthetic"}
        report = review_inventory(inventory, scenario, self.catalogue)
        self.assertEqual(report["summary"]["observed_candidates"], 1)
        self.assertEqual(report["requirements"][0]["status"], "REVIEW_REQUIRED")
        self.assertEqual(report["requirements"][0]["source_status"], "UNVERIFIED_CURRENT")
        self.assertEqual(report["requirements"][0].get("applicability"), "CANDIDATE_REVIEW")
        self.assertIn("SYNTH", "SYNTH")
        self.assertIn("not a regulatory compliance certificate", report["report_markdown"])

    def test_explicit_survey_geometry_in_report(self):
        scenario = {"land_class": "alberta_crown", "plan_type": "sketch", "activity": "PLA", "stage": "initial",
                    "regulator": "AER", "purpose": "synthetic"}
        survey = {"coordinate_source": "EXPLICIT_SURVEY_COORDINATES",
                  "crs_identifier": "SYNTHETIC_METRIC", "crs_verified": True,
                  "closed_ring": True,
                  "vertices": [[500000, 5600000], [500100, 5600000],
                               [500100, 5600020], [500000, 5600020],
                               [500000, 5600000]]}
        result = review_inventory({"spans": []}, scenario, self.catalogue,
                                  survey_geometry=survey)
        self.assertIn("Polygon area (m²): 2000", result["report_markdown"])
        self.assertIn("not PDF page points", result["report_markdown"])
        self.assertEqual(result["overall_status"], "REVIEW_REQUIRED")

    def test_pdf_points_rejected_as_survey_geometry(self):
        scenario = {"land_class": "alberta_crown", "plan_type": "sketch", "activity": "PLA", "stage": "initial",
                    "regulator": "AER", "purpose": "synthetic"}
        survey = {"coordinate_source": "PDF_PAGE_POINTS", "crs_identifier": "fake",
                  "crs_verified": False, "closed_ring": False,
                  "vertices": [[0,0],[1,0],[1,1]]}
        with self.assertRaises(ValueError):
            review_inventory({"spans": []}, scenario, self.catalogue,
                             survey_geometry=survey)

    def test_unknown_stage_cannot_trigger_evidence_review(self):
        scenario = {"land_class": "alberta_crown", "plan_type": "sketch", "activity": "PLA",
                    "regulator": "AER", "purpose": "synthetic"}
        report = review_inventory({"spans": [{"text": "SCALE 1:5000", "page": 1}]},
                                  scenario, self.catalogue)
        self.assertEqual(report["requirements"], [])
        self.assertEqual(report["excluded_from_evidence_review"][0]["applicability_status"],
                         "UNRESOLVED_APPLICABILITY")

    def test_compiled_plan_does_not_select_ordinary_heading(self):
        scenario = {"land_class": "alberta_crown", "plan_type": "compiled_plan", "activity": "PLA",
                    "stage": "initial", "regulator": "AER", "purpose": "synthetic"}
        heading = [entry for entry in self.catalogue
                   if entry["requirement_id"] == "CANDIDATE-PLAN-HEADING"]
        report = review_inventory({"spans": []}, scenario, heading)
        self.assertEqual(report["requirements"], [])
        self.assertEqual(report["excluded_from_evidence_review"][0]["applicability_status"],
                         "NOT_SELECTED_FOR_REVIEW")

    def test_input_artifact_is_preserved_with_page_evidence(self):
        scenario = {"land_class": "alberta_crown", "plan_type": "sketch", "activity": "PLA", "stage": "initial",
                    "regulator": "AER", "purpose": "synthetic"}
        inventory = {"source_filename": "synthetic-source.pdf", "spans": [
            {"text": "SCALE 1:5000", "page": 2, "bbox_points": [10, 10, 80, 25]}]}
        report = review_inventory(inventory, scenario, self.catalogue)
        evidence = report["requirements"][0].get("input_evidence", {})
        self.assertEqual(evidence.get("source_filename"), "synthetic-source.pdf")
        self.assertEqual(evidence["page"], 2)
        self.assertIn("Input artifact: synthetic-source.pdf", report["report_markdown"])

    def test_missing_application_activity_has_specific_next_step(self):
        scenario = {"land_class": "alberta_crown", "plan_type": "sketch",
                    "disposition": "LOC", "stage": "initial", "regulator": "AER",
                    "purpose": "Synthetic waterline"}
        report = review_inventory({"spans": []}, scenario, self.catalogue)
        self.assertIn("review_summary", report)
        requested = [item["field"] for item in report["review_summary"]["input_requests"]]
        self.assertIn("subactivity", requested)
        self.assertNotIn("regulator", requested)
        self.assertNotIn("land_class", requested)
        self.assertEqual(report["overall_status"], "REVIEW_REQUIRED")
        self.assertIn("subactivity", report["report_markdown"].casefold())
        self.assertNotIn("Missing or invalid context: none recorded", report["report_markdown"])
        self.assertNotIn("PDF extraction completed", report["report_markdown"])


if __name__ == "__main__":
    unittest.main()
