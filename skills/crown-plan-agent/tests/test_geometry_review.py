"""Synthetic geometry provenance and integration checks."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from geometry_review import review_survey_geometry
from review_pipeline import review_inventory


class GeometryReviewTests(unittest.TestCase):
    def setUp(self):
        self.survey = {"coordinate_source": "EXPLICIT_SURVEY_COORDINATES",
                       "crs_identifier": "SYNTHETIC_PROJECTED_METRIC",
                       "crs_verified": True, "closed_ring": True,
                       "vertices": [[500000, 5600000], [500100, 5600000],
                                    [500100, 5600020], [500000, 5600020],
                                    [500000, 5600000]]}

    def test_closed_survey_geometry(self):
        result = review_survey_geometry(self.survey)
        self.assertAlmostEqual(result["polygon"]["area_m2"], 2000)
        self.assertEqual(result["traverse"]["misclosure_m"], 0)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_reject_pdf_page_coordinates(self):
        with self.assertRaises(ValueError):
            review_survey_geometry({**self.survey, "coordinate_source": "PDF_PAGE_POINTS"})

    def test_missing_crs_identifier(self):
        with self.assertRaises(ValueError):
            review_survey_geometry({**self.survey, "crs_identifier": ""})

    def test_unknown_crs_never_compliant(self):
        result = review_survey_geometry({**self.survey, "crs_verified": False})
        self.assertEqual(result["polygon"]["crs_status"], "REVIEW_REQUIRED")
        self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_selected_plan_area_comparison(self):
        label = {"page": 1, "text": "AREA 0.201 ha", "bbox_points": [10, 10, 50, 20]}
        survey = {**self.survey, "area_label": {"page": 1, "text": label["text"],
                                               "tolerance_ha": 0.002}}
        cases = [
            ({}, [label], "WITHIN_SUPPLIED_TOLERANCE"),
            ({"area_label": {**survey["area_label"], "tolerance_ha": 0.0001}},
             [label], "OUTSIDE_SUPPLIED_TOLERANCE"),
            ({}, [label, label], "AREA_LABEL_UNRESOLVED"),
            ({}, [], "AREA_LABEL_UNRESOLVED"),
            ({"crs_verified": False}, [label], "SURVEY_AREA_UNRESOLVED"),
            ({"closed_ring": False}, [label], "SURVEY_AREA_UNRESOLVED"),
        ]
        for changes, spans, expected in cases:
            with self.subTest(expected=expected):
                result = review_inventory({"spans": spans}, {}, [],
                                          survey_geometry={**survey, **changes})
                area = result["survey_geometry_review"]["area_comparison"]
                self.assertEqual(area["comparison"], expected)
                self.assertEqual(result["overall_status"], "REVIEW_REQUIRED")
                self.assertIn(expected, result["report_markdown"])

    def test_area_equal_to_tolerance_is_within_tolerance(self):
        label = {"page": 1, "text": "AREA 0.28 ha", "bbox_points": [10, 10, 50, 20]}
        survey = {**self.survey, "area_label": {"page": 1, "text": label["text"],
                                               "tolerance_ha": 0.08}}
        result = review_survey_geometry(survey, plan_spans=[label])
        self.assertEqual(result["area_comparison"]["comparison"], "WITHIN_SUPPLIED_TOLERANCE")


if __name__ == "__main__":
    unittest.main()
