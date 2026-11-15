"""Unsupported subject representations must not yield partial boundary metrics."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from geometry_handoff import prepare_geometry_handoff
from geometry_review import review_survey_geometry
from review_pipeline import review_inventory


class GeometryRepresentationTests(unittest.TestCase):
    def setUp(self):
        self.survey = {
            "coordinate_source": "EXPLICIT_SURVEY_COORDINATES",
            "crs_identifier": "INVENTED_METRIC",
            "crs_verified": True, "provenance_verified": True,
            "coordinate_roles_resolved": True, "closed_ring": True,
            "vertices": [[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]],
            "area_label": {"page": 1, "text": "Total area 1 ha", "tolerance_ha": 0},
        }
        self.spans = [{"page": 1, "text": "Total area 1 ha",
                       "bbox_points": [10, 10, 100, 20]}]

    def test_declared_unsupported_subject_cannot_report_partial_metrics(self):
        for change in [{"holes": [[[10, 10], [20, 10], [20, 20], [10, 20], [10, 10]]]},
                       {"parts": [[[200, 0], [210, 0], [210, 10], [200, 10], [200, 0]]]},
                       {"curves": [{"radius": 12}]},
                       {"geometry_type": "MultiPolygon"}]:
            with self.subTest(change=change):
                result = review_survey_geometry({**self.survey, **change}, plan_spans=self.spans)
                self.assertEqual(result.get("diagnostic_status"), "REPRESENTATION_UNRESOLVED")
                self.assertEqual(result["status"], "REVIEW_REQUIRED")
                for field in ("traverse", "polygon", "area_comparison"):
                    self.assertNotIn(field, result)

    def test_hole_pipeline_explains_why_no_boundary_measurement_was_computed(self):
        report = review_inventory({"spans": self.spans}, {}, [], survey_geometry={
            **self.survey, "holes": [[[10, 10], [20, 10], [20, 20], [10, 20], [10, 10]]]})
        self.assertEqual(report["geometry_handoff"]["readiness"], "VERIFY_CRS_AND_PROVENANCE")
        text = report["report_markdown"]
        self.assertIn("REPRESENTATION_UNRESOLVED", text)
        self.assertIn("No boundary measurements or area comparison were computed", text)
        for misleading in ("Polygon area (m²)", "Traverse misclosure (m)",
                           "WITHIN_SUPPLIED_TOLERANCE", "Calculated area (ha)"):
            self.assertNotIn(misleading, text)

    def test_empty_shape_metadata_preserves_supported_numerical_review(self):
        result = review_survey_geometry({**self.survey, "curves": [], "parts": [],
                                        "holes": [], "geometry_type": "Polygon"},
                                       plan_spans=self.spans)
        self.assertEqual(result["polygon"]["area_m2"], 10000)
        self.assertEqual(result["area_comparison"]["comparison"], "WITHIN_SUPPLIED_TOLERANCE")

    def test_malformed_shape_metadata_is_rejected_by_both_consumers(self):
        for change in [{"holes": None}, {"parts": "none"}, {"curves": {}},
                       {"geometry_type": []}]:
            for consumer in (review_survey_geometry,
                             lambda survey: prepare_geometry_handoff({}, {}, survey)):
                with self.subTest(change=change, consumer=consumer), self.assertRaises(ValueError):
                    consumer({**self.survey, **change})

    def test_readiness_requires_finite_numeric_xy_pairs(self):
        for vertices in [[None], ["invalid"], [[True, False]], [[float("nan"), 0]],
                         [[0, float("inf")]], [[1, 2, 3]], [["1", 2]]]:
            with self.subTest(vertices=vertices), self.assertRaises(ValueError):
                prepare_geometry_handoff({}, {}, {**self.survey, "vertices": vertices})
        # This is schema readiness; a single point is not accepted geometry.
        ready = prepare_geometry_handoff({}, {}, {**self.survey, "vertices": [[1, 2]]})
        self.assertEqual(ready["readiness"], "QA_INPUT_SUPPLIED")


if __name__ == "__main__":
    unittest.main()
