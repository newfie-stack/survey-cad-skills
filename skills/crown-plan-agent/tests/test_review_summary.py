"""Summary/intake behavior on invented reviews, without a source PDF."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ENGINE = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE))
try:
    from review_summary import build_review_summary
except ModuleNotFoundError as exc:
    if exc.name != "review_summary":
        raise
    build_review_summary = None

from deficiency_report import build_ledger
from regulatory_catalog import load_candidate_catalog
from review_pipeline import review_inventory


class ReviewSummaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = load_candidate_catalog(ENGINE / "candidate_requirements.json")

    def report(self, changes=None, *, spans=None, survey=None, rows=None):
        scenario = {"land_class": "alberta_crown", "regulator": "AER",
                    "stage": "initial", "disposition": "LOC", "plan_type": "sketch",
                    "purpose": "Invented Purpose", "subactivity": "Invented Activity"}
        scenario.update(changes or {})
        inventory = {"source_filename": "invented-inventory.pdf", "spans": spans or []}
        return review_inventory(inventory, scenario, self.catalogue,
                                survey_geometry=survey, table_a2_rows=rows)

    def summary(self, report):
        self.assertIsNotNone(build_review_summary, "The derived review summary is not implemented")
        return build_review_summary(report)

    def fields(self, summary):
        return [request["field"] for request in summary["input_requests"]]

    @staticmethod
    def survey(**changes):
        survey = {"coordinate_source": "EXPLICIT_SURVEY_COORDINATES",
                  "crs_identifier": "SYNTHETIC_METRIC", "crs_verified": True,
                  "closed_ring": True,
                  "vertices": [[0, 0], [20, 0], [20, 10], [0, 10], [0, 0]]}
        return {**survey, **changes}

    def test_empty_manual_ledger_does_not_claim_automated_work(self):
        result = self.summary(build_ledger({}, [], {}))
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["checked"], [])
        self.assertIn("No automated", " ".join(result["not_checked"]))
        self.assertNotIn("extracted", " ".join(result["checked"]).lower())

    def test_initial_missing_subactivity_is_requested_without_reasking_known_facts(self):
        report = self.report({"subactivity": None})
        before = deepcopy(report)
        result = self.summary(report)
        self.assertEqual(self.fields(result), ["subactivity"])
        self.assertEqual(result["context_question"].count("?"), 1)
        self.assertEqual(report, before)
        self.assertEqual(report["plan_type_review"]["plan_type_status"], "CANDIDATE_ONLY")

    def test_manual_evidence_is_not_mislabeled_as_extracted_text(self):
        scenario = self.report()["scenario"]
        ledger = build_ledger(scenario, [{"requirement_id": "INVENTED-REVIEW",
                                          "evidence_key": "invented_item"}],
                              {"invented_item": {"present": True, "observation": "Manually supplied evidence"}})
        checked = " ".join(self.summary(ledger)["checked"]).lower()
        self.assertIn("supplied evidence", checked)
        self.assertIn("1 evidence candidate", checked)
        self.assertNotIn("text candidate", checked)

    def test_explicit_blank_subactivity_is_preserved_for_a_blank_source_row(self):
        row = {"disposition": "LOC", "purpose": "Invented Purpose", "activity": "",
               "row": 1, "page": 4, "required_plan": "Sketch", "survey_monuments": "N/A"}
        report = self.report({"subactivity": ""}, rows=[row])
        result = self.summary(report)
        self.assertEqual(self.fields(result), [])
        self.assertIsNone(result["context_question"])
        self.assertEqual(report["plan_type_review"]["table_a2_comparison"], "MATCHES_TABLE_A2")
        self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_missing_base_context_is_deduplicated_into_one_question(self):
        result = self.summary(self.report({"regulator": None, "stage": None, "purpose": None}))
        fields = self.fields(result)
        self.assertEqual(len(fields), len(set(fields)))
        self.assertEqual(set(fields), {"regulator", "stage", "purpose"})
        self.assertNotIn("land_class", fields)
        self.assertNotIn("disposition", fields)
        self.assertEqual(result["context_question"].count("?"), 1)

    def test_valid_legacy_disposition_alias_is_not_requested_again(self):
        report = self.report()
        report["scenario"]["activity"] = report["scenario"].pop("disposition")
        self.assertNotIn("disposition", self.fields(self.summary(report)))

    def test_amendment_requests_only_the_missing_plan_of_record(self):
        result = self.summary(self.report({"stage": "amendment"}))
        self.assertEqual(self.fields(result), ["existing_plan_type"])

    def test_survey_amendment_requests_both_unresolved_measurement_inputs(self):
        result = self.summary(self.report({"stage": "amendment", "existing_plan_type": "survey_plan"}))
        self.assertEqual(set(self.fields(result)), {"existing_length_m", "affected_quarter_sections"})

    def test_full_retrace_precedence_suppresses_irrelevant_questions(self):
        cases = [
            {"existing_length_m": 6400, "affected_quarter_sections": None},
            {"existing_length_m": None, "affected_quarter_sections": 3},
            {"existing_length_m": 6500, "affected_quarter_sections": 3},
        ]
        for values in cases:
            with self.subTest(values=values):
                report = self.report({"stage": "amendment", "existing_plan_type": "survey_plan", **values})
                self.assertEqual(report["plan_type_review"]["amendment_review"]["route"], "FULL_RETRACE_CANDIDATE")
                self.assertEqual(self.fields(self.summary(report)), [])

    def test_exact_threshold_requires_direction_only_after_quarter_count_is_known(self):
        base = {"stage": "amendment", "existing_plan_type": "survey_plan", "existing_length_m": 6500}
        unknown = self.summary(self.report(base))
        self.assertEqual(self.fields(unknown), ["affected_quarter_sections"])
        known = self.summary(self.report({**base, "affected_quarter_sections": 2}))
        self.assertEqual(self.fields(known), ["survey_scope_direction"])
        self.assertIn("direction", " ".join(known["next_steps"]).lower())

    def test_known_itemized_amendment_does_not_reask_length_or_quarters(self):
        result = self.summary(self.report({"stage": "amendment", "existing_plan_type": "survey_plan",
                                           "existing_length_m": 7000, "affected_quarter_sections": 2}))
        self.assertEqual(self.fields(result), [])

    def test_supplied_threshold_direction_is_not_requested_again_or_used_as_approval(self):
        report = self.report({"stage": "amendment", "existing_plan_type": "survey_plan",
                              "existing_length_m": 6500, "affected_quarter_sections": 2,
                              "survey_scope_direction": "Invented direction supplied for separate source review"})
        result = self.summary(report)
        self.assertNotIn("survey_scope_direction", self.fields(result))
        self.assertEqual(report["plan_type_review"]["amendment_review"]["route"], "SURVEY_SCOPE_UNRESOLVED")
        self.assertIn("direction", " ".join(result["next_steps"]).lower())
        self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_unknown_workbook_facts_do_not_become_a_blanket_intake_question(self):
        from clause_workbook import prepare_clause_workbook
        report = self.report()
        catalogue = json.loads((ENGINE / "dated_clause_catalogue.json").read_text())
        report["clause_workbook"] = prepare_clause_workbook(catalogue, report["scenario"], {})
        result = self.summary(report)
        self.assertEqual(result["input_requests"], [])
        self.assertIsNone(result["context_question"])
        self.assertTrue(any("workbook" in action for action in result["next_steps"]))
        self.assertTrue(any("manual" in item for item in result["not_checked"]))

    def test_compiled_variant_does_not_inherit_numeric_amendment_questions(self):
        result = self.summary(self.report({"stage": "amendment", "plan_type": "compiled_plan",
                                           "existing_plan_type": "survey_plan"}))
        self.assertEqual(self.fields(result), [])

    def test_renewal_change_status_precedes_conditional_plan_record(self):
        unknown = self.summary(self.report({"stage": "renewal"}))
        self.assertEqual(self.fields(unknown), ["disposition_changed"])
        unchanged = self.summary(self.report({"stage": "renewal", "disposition_changed": False}))
        self.assertEqual(self.fields(unchanged), ["existing_plan_type"])
        changed = self.summary(self.report({"stage": "renewal", "disposition_changed": True}))
        self.assertEqual(self.fields(changed), [])
        self.assertIn("amendment", " ".join(changed["next_steps"]).lower())

    def test_renewal_legacy_issue_date_is_requested_only_for_the_actual_route(self):
        row = {"disposition": "LOC", "purpose": "Invented Purpose", "activity": "Invented Activity",
               "row": 1, "page": 4, "required_plan": "Survey", "survey_monuments": "N/A"}
        base = {"stage": "renewal", "disposition_changed": False, "existing_plan_type": "sketch"}
        result = self.summary(self.report(base, rows=[row]))
        self.assertEqual(self.fields(result), ["disposition_issued_on"])
        known = self.summary(self.report({**base, "disposition_issued_on": "2012-01-01"}, rows=[row]))
        self.assertEqual(self.fields(known), [])

    def test_renewal_row_lookup_requests_missing_activity_but_preserves_explicit_blank(self):
        row = {"disposition": "LOC", "purpose": "Invented Purpose", "activity": "",
               "row": 1, "page": 4, "required_plan": "Sketch", "survey_monuments": "N/A"}
        base = {"stage": "renewal", "disposition_changed": False,
                "existing_plan_type": "sketch"}
        unknown = self.report({**base, "subactivity": None}, rows=[row])
        self.assertEqual(self.fields(self.summary(unknown)), ["subactivity"])
        self.assertEqual(unknown["plan_type_review"]["renewal_review"]["comparison"],
                         "TABLE_A2_ROW_UNRESOLVED")
        blank = self.report({**base, "subactivity": ""}, rows=[row])
        self.assertEqual(self.fields(self.summary(blank)), [])
        self.assertEqual(blank["plan_type_review"]["renewal_review"]["comparison"],
                         "MATCHES_TABLE_A2")

    def test_out_of_scope_review_requests_no_crown_context(self):
        result = self.summary(self.report({"land_class": "private", "regulator": None, "stage": None,
                                           "plan_type": None, "purpose": None, "subactivity": None}))
        self.assertEqual(result["input_requests"], [])
        self.assertIsNone(result["context_question"])
        self.assertIn("outside", result["headline"].lower())
        self.assertFalse(any("Table A2" in item for item in result["next_steps"]))

    def test_supplied_inventory_is_not_reported_as_pdf_extraction_or_compliance(self):
        report = self.report(spans=[{"text": "SCALE 1:2000", "page": 1, "bbox_points": [10, 10, 80, 25]}])
        result = self.summary(report)
        checked = " ".join(result["checked"]).lower()
        self.assertIn("supplied text inventory", checked)
        self.assertIn("1 text candidate", checked)
        self.assertNotIn("extracted", checked)
        self.assertNotIn("passed", checked)
        self.assertNotIn("compliant", checked)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_source_freshness_action_is_not_repeated_for_each_requirement(self):
        result = self.summary(self.report())
        source_actions = [item for item in result["next_steps"] if "current source" in item.lower()]
        self.assertEqual(len(source_actions), 1)

    def test_unsupported_geometry_does_not_claim_measurements(self):
        result = self.summary(self.report(survey=self.survey(curves=[{"radius": 12}])))
        self.assertFalse(any("Calculated" in item for item in result["checked"]))
        self.assertIn("not computed", " ".join(result["not_checked"]))

    def test_unverified_crs_does_not_advertise_measurements_as_checked(self):
        result = self.summary(self.report(survey=self.survey(crs_verified=False)))
        self.assertFalse(any("Calculated" in item for item in result["checked"]))
        self.assertIn("unverified", " ".join(result["not_checked"]).lower())

    def test_verified_coordinate_diagnostics_are_separate_from_reconstruction(self):
        result = self.summary(self.report(survey=self.survey()))
        self.assertTrue(any("Calculated" in item and "closure" in item for item in result["checked"]))
        self.assertTrue(any("area" in item and "Calculated" in item for item in result["checked"]))
        self.assertIn("Octopus", " ".join(result["not_checked"]))
        self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_only_explicit_outside_traverse_tolerance_is_flagged(self):
        for tolerance, flagged in ((0.1, True), (0.2, False), (None, False)):
            with self.subTest(tolerance=tolerance):
                survey = self.survey(closed_ring=False, tolerance_m=tolerance,
                                     vertices=[[0, 0], [20, 0], [20, 10], [0, 10], [0, 0.2]])
                report = self.report(survey=survey)
                result = self.summary(report)
                alerts = [item for item in result["needs_attention"] if "misclosure" in item]
                self.assertEqual(bool(alerts), flagged)
                if flagged:
                    self.assertTrue(any("endpoint coordinates" in item for item in result["next_steps"]))
                self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_blocked_geometry_does_not_reuse_stale_tolerance_failure(self):
        for reason in ("unsupported", "unverified"):
            with self.subTest(reason=reason):
                report = self.report(survey=self.survey())
                geometry = report["survey_geometry_review"]
                geometry["traverse"]["within_supplied_tolerance"] = False
                if reason == "unsupported":
                    geometry["diagnostic_status"] = "REPRESENTATION_UNRESOLVED"
                else:
                    geometry["traverse"]["crs_status"] = "REVIEW_REQUIRED"
                result = self.summary(report)
                self.assertFalse(any("misclosure" in item for item in result["needs_attention"]))

    def test_conflicting_area_totals_surface_a_specific_action_once(self):
        spans = [{"text": text, "page": 1, "bbox_points": [10, 10+i*20, 100, 25+i*20]}
                 for i, text in enumerate(["TOTAL AREA: 0.020 ha", "TOTAL AREA: 0.021 ha"])]
        survey = self.survey(area_label={"page": 1, "text": "TOTAL AREA: 0.020 ha", "tolerance_ha": 0.001})
        report = self.report(spans=spans, survey=survey)
        self.assertEqual(report["survey_geometry_review"]["area_comparison"]["comparison"], "AREA_LABEL_UNRESOLVED")
        result = self.summary(report)
        self.assertTrue(any("area" in item.lower() and "ambiguous" in item.lower() for item in result["needs_attention"]))
        actions = [item for item in result["next_steps"] if "activity total area" in item.lower()]
        self.assertEqual(len(actions), 1)
        self.assertFalse(any("within" in item.lower() for item in result["checked"]))

    def test_unstructured_manual_observation_is_not_treated_as_area_ambiguity(self):
        ledger = build_ledger(self.report()["scenario"],
                              [{"requirement_id": "CANDIDATE-TOTAL-AREA", "evidence_key": "area"}],
                              {"area": {"observation": {"manual_note": "Invented unresolved observation"}}})
        result = self.summary(ledger)
        self.assertFalse(any("ambiguous" in item for item in result["needs_attention"]))

    def test_uncomputed_geometry_cannot_advertise_a_leftover_area_comparison(self):
        survey = self.survey(area_label={"page": 1, "text": "TOTAL AREA: 0.020 ha", "tolerance_ha": 0.001})
        report = self.report(survey=survey, spans=[{"text": "TOTAL AREA: 0.020 ha", "page": 1,
                                                 "bbox_points": [10, 10, 100, 25]}])
        report["survey_geometry_review"]["diagnostic_status"] = "REPRESENTATION_UNRESOLVED"
        result = self.summary(report)
        self.assertFalse(any("Calculated" in item or "within" in item.lower() for item in result["checked"]))
        self.assertIn("not computed", " ".join(result["not_checked"]))

    def test_summary_does_not_echo_raw_observations_or_scenario_strings(self):
        report = self.report({"purpose": "DO_NOT_REPEAT_THIS_PURPOSE"})
        report["requirements"][0]["observation"] = "DO_NOT_REPEAT_THIS_OBSERVATION"
        encoded = json.dumps(self.summary(report))
        self.assertNotIn("DO_NOT_REPEAT_THIS", encoded)

    def test_non_review_status_cannot_be_summarized_as_approved(self):
        report = self.report()
        report["overall_status"] = "PASS"
        with self.assertRaises(ValueError):
            self.summary(report)


if __name__ == "__main__":
    unittest.main()
