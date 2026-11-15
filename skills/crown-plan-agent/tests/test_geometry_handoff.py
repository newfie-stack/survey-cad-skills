"""Invented handoff inputs; specialist execution and legal acceptance stay separate."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from geometry_handoff import prepare_geometry_handoff
from geometry_review import review_survey_geometry


class GeometryHandoffTests(unittest.TestCase):
    def setUp(self):
        self.survey = {
            "coordinate_source": "EXPLICIT_SURVEY_COORDINATES",
            "crs_identifier": "INVENTED_LOCAL_METRIC",
            "crs_verified": True,
            "provenance_verified": True,
            "coordinate_roles_resolved": True,
            "closed_ring": True,
            "vertices": [[7, 11], [31, 11], [31, 24], [7, 24], [7, 11]],
        }

    def test_missing_coordinates_propose_ordered_specialists_without_execution(self):
        inventory = {"source_filename": "invented-plan.pdf", "pages": 3,
                     "source_id": "invented-source-id", "spans": [],
                     "vectors": [{"page": 2, "endpoints_points": [2, 4, 8, 6]}]}
        result = prepare_geometry_handoff(inventory, {})
        self.assertEqual(result["readiness"], "RECONSTRUCTION_INPUT_REQUIRED")
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["execution_status"], "NOT_EXECUTED")
        self.assertEqual(result["source"], {
            "filename": "invented-plan.pdf", "source_id": "invented-source-id",
            "pages": [2], "page_count": 3})
        self.assertEqual([item["name"] for item in result["requested_skills"]], [
            "survey-plan-evidence-interpretation", "registered-plan-reconstruction",
            "survey-dxf-cad-construction"])
        for item in result["requested_skills"]:
            self.assertEqual(item["availability"], "UNVERIFIED")
            self.assertEqual(item["execution_status"], "NOT_EXECUTED")
        self.assertNotIn("survey_geometry", result)
        self.assertNotIn("vertices", result)

    def test_missing_source_identity_and_page_count_stay_unknown(self):
        result = prepare_geometry_handoff({}, {})
        self.assertEqual(result["source"], {
            "filename": None, "source_id": None, "pages": [], "page_count": None})

    def test_source_identity_rejects_containers_that_could_leak_coordinates(self):
        for inventory in [{"source_filename": ["invented-plan.pdf"]},
                          {"source_id": {"vertices": [[7, 11], [31, 11]]}}]:
            with self.subTest(inventory=inventory), self.assertRaises(ValueError):
                prepare_geometry_handoff(inventory, {})

    def test_available_page_locators_are_retained_without_inventing_page_count(self):
        result = prepare_geometry_handoff({"spans": [{"page": 4}, {"page": 2}],
                                           "curves": [{"page": 4}]}, {})
        self.assertEqual(result["source"]["pages"], [2, 4])
        self.assertIsNone(result["source"]["page_count"])

    def test_gis_specialist_is_requested_only_by_explicit_boolean(self):
        for scenario, expected in [({}, False), ({"gis_requested": False}, False),
                                   ({"gis_requested": True}, True)]:
            with self.subTest(scenario=scenario):
                result = prepare_geometry_handoff({}, scenario)
                names = [item["name"] for item in result["requested_skills"]]
                self.assertEqual("shapefile-validator" in names, expected)
                if expected:
                    self.assertEqual(names[-1], "shapefile-validator")
        with self.assertRaises(ValueError):
            prepare_geometry_handoff({}, {"gis_requested": "true"})

    def test_contract_requires_identity_raw_observations_and_control_provenance(self):
        result = prepare_geometry_handoff({}, {})
        inputs = {item["name"]: item for item in result["required_inputs"]}
        self.assertTrue({"source_locator", "feature_identity", "bearing_basis_and_units",
                         "raw_observations", "control_and_spatial_alignment"} <= inputs.keys())
        artifacts = {item["name"] for item in result["expected_return_artifacts"]}
        self.assertTrue({"source_and_feature_register", "observation_register", "control_network",
                         "review_dxf", "review_preview", "accepted_coordinate_json",
                         "unresolved_items"} <= artifacts)
        self.assertEqual(result["coordinate_input_contract"]["consumer"],
                         "geometry_review.review_survey_geometry")

    def test_verified_explicit_input_is_qa_ready_without_specialist_execution_claim(self):
        result = prepare_geometry_handoff({}, {}, self.survey)
        self.assertEqual(result["readiness"], "QA_INPUT_SUPPLIED")
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["execution_status"], "NOT_EXECUTED")
        self.assertEqual(result["acceptance_blockers"], [])
        self.assertNotIn("polygon", result)
        self.assertNotIn("traverse", result)
        self.assertNotIn(json.dumps(self.survey["vertices"]), json.dumps(result))
        self.assertEqual(review_survey_geometry(self.survey)["polygon"]["area_m2"], 312)

    def test_qa_ready_coordinates_do_not_request_reconstruction_again(self):
        for scenario, expected in [({}, []), ({"gis_requested": True}, ["shapefile-validator"])]:
            with self.subTest(scenario=scenario):
                result = prepare_geometry_handoff({}, scenario, self.survey)
                self.assertEqual(result["readiness"], "QA_INPUT_SUPPLIED")
                self.assertEqual([item["name"] for item in result["requested_skills"]], expected)

    def test_legacy_geometry_still_runs_math_but_handoff_requires_provenance(self):
        legacy = {key: value for key, value in self.survey.items()
                  if key not in ("provenance_verified", "coordinate_roles_resolved")}
        self.assertEqual(review_survey_geometry(legacy)["polygon"]["area_m2"], 312)
        result = prepare_geometry_handoff({}, {}, legacy)
        self.assertEqual(result["readiness"], "VERIFY_CRS_AND_PROVENANCE")
        self.assertIn("PROVENANCE_UNVERIFIED", result["acceptance_blockers"])
        self.assertIn("COORDINATE_ROLES_UNRESOLVED", result["acceptance_blockers"])
        self.assertEqual([item["name"] for item in result["requested_skills"]], [
            "survey-plan-evidence-interpretation", "registered-plan-reconstruction",
            "survey-dxf-cad-construction"])

    def test_each_unresolved_acceptance_flag_blocks_qa_readiness(self):
        for field, blocker in [("crs_verified", "CRS_UNVERIFIED"),
                               ("provenance_verified", "PROVENANCE_UNVERIFIED"),
                               ("coordinate_roles_resolved", "COORDINATE_ROLES_UNRESOLVED")]:
            with self.subTest(field=field):
                result = prepare_geometry_handoff({}, {}, {**self.survey, field: False})
                self.assertEqual(result["readiness"], "VERIFY_CRS_AND_PROVENANCE")
                self.assertIn(blocker, result["acceptance_blockers"])

    def test_pdf_points_and_missing_metric_crs_cannot_be_qa_ready(self):
        for change, blocker in [({"coordinate_source": "PDF_PAGE_POINTS"},
                                 "EXPLICIT_SURVEY_COORDINATES_REQUIRED"),
                                ({"crs_identifier": ""}, "CRS_IDENTIFIER_REQUIRED"),
                                ({"vertices": []}, "ORDERED_COORDINATES_REQUIRED")]:
            with self.subTest(change=change):
                result = prepare_geometry_handoff({}, {}, {**self.survey, **change})
                self.assertEqual(result["readiness"], "VERIFY_CRS_AND_PROVENANCE")
                self.assertIn(blocker, result["acceptance_blockers"])

    def test_curves_multipart_and_holes_remain_separate_unresolved_specialist_results(self):
        for change in [{"curves": [{"radius": 19}]}, {"parts": [[[7, 11]]]},
                       {"holes": [[[10, 15]]]}, {"geometry_type": "MultiPolygon"}]:
            with self.subTest(change=change):
                result = prepare_geometry_handoff({}, {}, {**self.survey, **change})
                self.assertEqual(result["readiness"], "VERIFY_CRS_AND_PROVENANCE")
                self.assertIn("SPECIALIST_GEOMETRY_OUTSIDE_QA_SCOPE",
                              result["acceptance_blockers"])

    def test_input_types_are_checked_without_repeating_geometry_diagnostics(self):
        for inputs in [([], {}, None), ({}, [], None), ({}, {}, [])]:
            with self.subTest(inputs=inputs), self.assertRaises(TypeError):
                prepare_geometry_handoff(*inputs)
        for change in [{"vertices": "7,11"}, {"crs_verified": "true"},
                       {"closed_ring": 1}, {"coordinate_roles_resolved": 1}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                prepare_geometry_handoff({}, {}, {**self.survey, **change})
        # Closure and geometric validity belong to the existing diagnostic engine.
        result = prepare_geometry_handoff({}, {}, {**self.survey, "vertices": [[7, 11]]})
        self.assertEqual(result["readiness"], "QA_INPUT_SUPPLIED")

    def test_caller_data_and_independent_result_contracts_are_not_mutated(self):
        inventory, scenario = {"pages": 2}, {"gis_requested": True}
        before = copy.deepcopy((inventory, scenario, self.survey))
        first = prepare_geometry_handoff(inventory, scenario, self.survey)
        self.assertEqual((inventory, scenario, self.survey), before)
        first["required_inputs"][0]["fields"].append("invented-mutation")
        second = prepare_geometry_handoff({}, {})
        self.assertNotIn("invented-mutation", second["required_inputs"][0]["fields"])


if __name__ == "__main__":
    unittest.main()
