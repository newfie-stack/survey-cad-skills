"""Geometry proposals remain distinct from performed coordinate diagnostics."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from review_pipeline import review_inventory


class GeometryHandoffPipelineTests(unittest.TestCase):
    def test_missing_coordinates_propose_existing_skills_without_execution(self):
        report = review_inventory({"source_filename": "synthetic.pdf", "pages": 1,
                                   "spans": []}, {}, [])
        handoff = report.get("geometry_handoff", {})
        self.assertEqual(handoff.get("readiness"), "RECONSTRUCTION_INPUT_REQUIRED")
        self.assertEqual(handoff["execution_status"], "NOT_EXECUTED")
        self.assertNotIn("survey_geometry_review", report)
        self.assertIn("registered-plan-reconstruction", report["report_markdown"])
        self.assertIn("Specialist handoff: NOT_EXECUTED", report["report_markdown"])
        self.assertIn("No supplied-coordinate geometry diagnostics were executed", report["report_markdown"])

    def test_supplied_diagnostics_do_not_imply_specialist_acceptance(self):
        survey = {"coordinate_source": "EXPLICIT_SURVEY_COORDINATES",
                  "crs_identifier": "SYNTHETIC_METRIC", "crs_verified": True,
                  "closed_ring": True, "vertices": [[0, 0], [100, 0], [100, 20],
                                                      [0, 20], [0, 0]]}
        report = review_inventory({"spans": []}, {}, [], survey_geometry=survey)
        self.assertEqual(report.get("geometry_handoff", {}).get("readiness"),
                         "VERIFY_CRS_AND_PROVENANCE")
        self.assertEqual(report["survey_geometry_review"]["polygon"]["area_m2"], 2000)
        self.assertIn("Specialist handoff: NOT_EXECUTED", report["report_markdown"])
        self.assertNotIn("No supplied-coordinate geometry diagnostics were executed", report["report_markdown"])
        self.assertEqual(report["overall_status"], "REVIEW_REQUIRED")


if __name__ == "__main__":
    unittest.main()
