"""Invented applications against the explicitly selected dated manual paths.

These source-backed expectations do not establish current regulatory authority.
No real plan, application record or survey coordinates are used.
"""
import sys
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "engine"))
from clause_schema import load_clause_catalogue
from clause_workbook import prepare_clause_workbook
from coverage_inventory import load_inventory


class DatedClauseCatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = load_clause_catalogue(SKILL / "engine/dated_clause_catalogue.json")
        cls.inventory = load_inventory()

    def setUp(self):
        self.context = {"land_class": "alberta_crown", "regulator": "AER",
                        "disposition": "LOC", "stage": "initial", "plan_type": "sketch"}

    @staticmethod
    def facts(**values):
        return {key: {"value": value, "provenance": {
            "source_id": "INVENTED-APPLICATION", "locator": "Invented fact register"}}
                for key, value in values.items()}

    def workbook(self, *, context=None, **facts):
        return prepare_clause_workbook(self.catalogue, context or self.context,
                                       self.facts(**facts), coverage_inventory=self.inventory)

    @staticmethod
    def clause(workbook, ident):
        return next(row for row in workbook["clauses"] if row["id"] == ident)

    def test_all_numbered_clauses_have_explicit_dated_paths(self):
        actual = {c["id"]: c for c in self.catalogue["clauses"]}
        self.assertEqual(len(actual), 144)
        self.assertEqual(set(actual), {c["clause_id"] for c in self.inventory["clauses"]})
        for clause in self.inventory["clauses"]:
            with self.subTest(clause=clause["clause_id"]):
                path = actual[clause["clause_id"]]
                self.assertEqual(path["kind"], clause["requirement_status"])
                self.assertEqual(path["citation"]["page"], clause["pdf_page"])
                self.assertEqual(path["citation"]["section"], clause["clause_id"])
        workbook = self.workbook()
        self.assertEqual(workbook["coverage"]["unmapped_clause_ids"], [])
        self.assertEqual(workbook["coverage"]["expected_clause_count"], 144)
        self.assertEqual(workbook["coverage"]["atomic_obligation_completeness"], "NOT_ASSESSED")
        self.assertEqual(workbook["source_status"], "UNVERIFIED_CURRENT")

    def test_loc_does_not_by_itself_trigger_access_road_length_reporting(self):
        missing = self.workbook()
        self.assertEqual(self.clause(missing, "1.3.6.6")["selection_status"],
                         "UNRESOLVED_APPLICABILITY")
        waterline = self.workbook(is_access_road=False)
        self.assertEqual(self.clause(waterline, "1.3.6.6")["selection_status"],
                         "NOT_SELECTED_FOR_REVIEW")
        road = self.workbook(is_access_road=True)
        self.assertEqual(self.clause(road, "1.3.6.6")["selection_status"], "CANDIDATE_REVIEW")

    def test_compiled_exemptions_and_replacement_keep_other_general_questions(self):
        compiled = self.workbook(context={**self.context, "plan_type": "compiled_plan",
                                         "stage": "amendment"})
        for ident in ("1.2.1.1", "3.1.2.1", "3.2.1.1", "3.3.2.1", "3.3.3.1"):
            with self.subTest(clause=ident):
                self.assertEqual(self.clause(compiled, ident)["selection_status"],
                                 "NOT_SELECTED_FOR_REVIEW")
        for ident in ("1.2.2.1", "1.3.6.3", "3.6.1.2", "3.6.1.3"):
            with self.subTest(clause=ident):
                row = self.clause(compiled, ident)
                self.assertEqual(row["selection_status"], "CANDIDATE_REVIEW")
                self.assertTrue(any(check["review_requests"] for check in row["checks"]))
        self.assertTrue(self.clause(compiled, "3.1.2.1")["checks"][0]["override_trace"])

    def test_hybrid_is_not_given_the_compiled_heading_or_declaration_exemption(self):
        hybrid = self.workbook(context={**self.context, "plan_type": "hybrid_plan"})
        for ident in ("1.2.1.1", "3.1.2.1", "3.5.1.1"):
            self.assertEqual(self.clause(hybrid, ident)["selection_status"], "CANDIDATE_REVIEW")

    def test_partial_dimension_permissions_do_not_remove_independent_ties(self):
        result = self.workbook(is_linear=True, manual_sketch_extent_dimensions_required=False)
        self.assertEqual(self.clause(result, "2.1.1.2")["selection_status"],
                         "NOT_SELECTED_FOR_REVIEW")
        self.assertEqual(self.clause(result, "2.1.1.6")["selection_status"], "CANDIDATE_REVIEW")
        self.assertTrue(self.clause(result, "2.1.1.6")["checks"][0]["review_requests"])

    def test_parallel_corridor_threshold_is_strict_and_zero_is_invalid(self):
        base = dict(is_linear=True, is_access_road=True, is_right_of_way=False,
                    has_parallel_boundaries=True, manual_sketch_extent_dimensions_required=True)
        for width, expected in (("45.719", "CANDIDATE_REVIEW"),
                                ("45.72", "NOT_SELECTED_FOR_REVIEW"),
                                ("0", "UNRESOLVED_APPLICABILITY")):
            with self.subTest(width=width):
                result = self.workbook(**base, corridor_width_m=width)
                self.assertEqual(self.clause(result, "2.1.1.4")["selection_status"], expected)

    def test_material_exploration_exempts_only_timber_breakdown(self):
        for peat in (True, False):
            with self.subTest(peat=peat):
                result = self.workbook(context={**self.context, "disposition": "SME"},
                                       peat_related=peat, tda_confirmation_applies=True)
                self.assertEqual(self.clause(result, "1.3.6.4")["selection_status"],
                                 "NOT_SELECTED_FOR_REVIEW")
                for ident in ("1.3.6.2", "1.3.6.3"):
                    self.assertEqual(self.clause(result, ident)["selection_status"], "CANDIDATE_REVIEW")

    def test_wetland_purpose_is_required_for_loc_bank_paths_including_surveys(self):
        unrelated = self.workbook(manual_wetland_reservoir_scope_applies=False)
        self.assertEqual(self.clause(unrelated, "4.5.1.1")["selection_status"],
                         "NOT_SELECTED_FOR_REVIEW")
        survey = self.workbook(context={**self.context, "plan_type": "survey_plan"},
                               manual_wetland_reservoir_scope_applies=True,
                               full_supply_level_applicable=False)
        self.assertEqual(self.clause(survey, "4.5.1.1")["selection_status"], "CANDIDATE_REVIEW")

    def test_itemized_sketch_conflict_is_not_hidden_by_the_survey_family_gate(self):
        context = {**self.context, "stage": "amendment"}
        result = self.workbook(context=context, existing_is_surveyed=True, uses_itemized_sketch=True)
        row = self.clause(result, "3.3.3.1")
        prohibition = next(c for c in row["checks"] if c["id"] == "C_3_3_3_1_09")
        self.assertEqual(prohibition["selection_status"], "CANDIDATE_REVIEW")
        self.assertTrue(prohibition["review_requests"])
        self.assertTrue(all(not c["review_requests"] for c in row["checks"][:-1]))

    def test_exact_6500m_gap_requires_recorded_direction_instead_of_a_default_route(self):
        # PDF11, sections3.3.2.1/.2 use strict >/<6.5km. Neither states equality.
        context = {**self.context, "stage": "amendment", "plan_type": "survey_plan"}
        base = dict(existing_is_surveyed=True, is_linear=True,
                    existing_length_m="6500", affected_quarter_sections=2)
        result = self.workbook(context=context, **base)
        for ident in ("3.3.2.1", "3.3.2.2"):
            with self.subTest(clause=ident):
                row = self.clause(result, ident)
                self.assertEqual(row["selection_status"], "UNRESOLVED_APPLICABILITY")
                self.assertEqual(row["blocking_fact_ids"], ["manual_exact_6500m_survey_scope"])
                self.assertTrue(all(not check["review_requests"] for check in row["checks"]))
        self.assertEqual(self.clause(result, "3.3.2.3")["selection_status"], "NOT_SELECTED_FOR_REVIEW")
        facts = self.facts(**base, manual_exact_6500m_survey_scope="itemized")
        facts["manual_exact_6500m_survey_scope"]["provenance"] = None
        unrecorded = prepare_clause_workbook(self.catalogue, context, facts)
        for ident in ("3.3.2.1", "3.3.2.2"):
            row = self.clause(unrecorded, ident)
            self.assertEqual(row["selection_status"], "UNRESOLVED_APPLICABILITY")
            self.assertIn({"fact_id": "manual_exact_6500m_survey_scope",
                           "code": "MISSING_PROVENANCE", "blocking": True}, row["fact_issues"])

    def test_recorded_exact_6500m_direction_selects_only_its_review_path(self):
        for kind in ("survey_plan", "hybrid_plan"):
            for direction, itemized, retrace in (
                ("itemized", "CANDIDATE_REVIEW", "NOT_SELECTED_FOR_REVIEW"),
                ("full_retrace", "NOT_SELECTED_FOR_REVIEW", "CANDIDATE_REVIEW"),
            ):
                with self.subTest(kind=kind, direction=direction):
                    result = self.workbook(context={**self.context, "stage": "amendment", "plan_type": kind},
                        existing_is_surveyed=True, is_linear=True, existing_length_m="6500.0",
                        affected_quarter_sections=2, manual_exact_6500m_survey_scope=direction)
                    self.assertEqual(self.clause(result, "3.3.2.1")["selection_status"], itemized)
                    self.assertEqual(self.clause(result, "3.3.2.2")["selection_status"], retrace)
                    self.assertEqual(result["overall_status"], "REVIEW_REQUIRED")
                    self.assertEqual(result["source_status"], "UNVERIFIED_CURRENT")

    def test_either_side_of_6500m_keeps_strict_source_inequalities(self):
        # An equality-only manual interpretation must not widen either literal
        # source branch or override a known length on the other side.
        for length, direction, itemized, retrace in (
            ("6499.999999999", "itemized", "NOT_SELECTED_FOR_REVIEW", "CANDIDATE_REVIEW"),
            ("6500.000000001", "full_retrace", "CANDIDATE_REVIEW", "NOT_SELECTED_FOR_REVIEW"),
        ):
            with self.subTest(length=length):
                result = self.workbook(context={**self.context, "stage": "amendment", "plan_type": "survey_plan"},
                    existing_is_surveyed=True, is_linear=True, existing_length_m=length,
                    affected_quarter_sections=2, manual_exact_6500m_survey_scope=direction)
                self.assertEqual(self.clause(result, "3.3.2.1")["selection_status"], itemized)
                self.assertEqual(self.clause(result, "3.3.2.2")["selection_status"], retrace)

    def test_more_than_two_quarters_requires_retrace_review_without_known_length(self):
        # Section3.3.2.3 has no length condition; an unknown length cannot hide it.
        for length in (None, "6499.999", "6500", "6500.001"):
            with self.subTest(length=length):
                facts = dict(existing_is_surveyed=True, is_linear=True,
                             affected_quarter_sections=3, manual_exact_6500m_survey_scope="itemized")
                if length is not None:
                    facts["existing_length_m"] = length
                result = self.workbook(context={**self.context, "stage": "amendment", "plan_type": "survey_plan"},
                                       **facts)
                retrace = self.clause(result, "3.3.2.3")
                self.assertEqual(retrace["selection_status"], "CANDIDATE_REVIEW")
                self.assertEqual(retrace["blocking_fact_ids"], [])
                self.assertTrue(retrace["checks"][0]["review_requests"])
                self.assertEqual(self.clause(result, "3.3.2.1")["selection_status"], "NOT_SELECTED_FOR_REVIEW")

    def test_final_sketch_material_relief_has_narrow_type_phase_and_activity_scope(self):
        # PDF16, section4.4.2.3 is a final sketch in the overlapping SML/RML
        # branch. Lifecycle amendment alone does not make a submission final.
        cases = (
            ("SML", "sketch", "final", True, "CANDIDATE_REVIEW"),
            ("RML", "sketch", "final", True, "CANDIDATE_REVIEW"),
            ("SML", "sketch", "application", True, "NOT_SELECTED_FOR_REVIEW"),
            ("SML", "sketch", "as_built", True, "NOT_SELECTED_FOR_REVIEW"),
            ("SML", "sketch", None, True, "UNRESOLVED_APPLICABILITY"),
            ("SML", "sketch", "final", False, "NOT_SELECTED_FOR_REVIEW"),
            ("SME", "sketch", "final", True, "NOT_SELECTED_FOR_REVIEW"),
            ("SML", "survey_plan", "final", True, "NOT_SELECTED_FOR_REVIEW"),
            ("SML", "hybrid_plan", "final", True, "NOT_SELECTED_FOR_REVIEW"),
            ("SML", "compiled_plan", "final", True, "NOT_SELECTED_FOR_REVIEW"),
        )
        for code, kind, phase, overlap, expected in cases:
            with self.subTest(code=code, kind=kind, phase=phase, overlap=overlap):
                facts = {"overlaps_oilsands_msl": overlap}
                if phase is not None:
                    facts["submission_phase"] = phase
                result = self.workbook(context={**self.context, "disposition": code,
                                               "stage": "amendment", "plan_type": kind}, **facts)
                row = self.clause(result, "4.4.2.3")
                self.assertEqual(row["selection_status"], expected)
                if expected != "CANDIDATE_REVIEW":
                    self.assertTrue(all(not check["review_requests"] for check in row["checks"]))

    def test_surveyor_sketch_relief_needs_explicit_recorded_interpretation(self):
        context = {**self.context, "disposition": "SML", "plan_type": "surveyor_sketch"}
        base = dict(overlaps_oilsands_msl=True, submission_phase="final")
        for interpretation, expected in ((None, "UNRESOLVED_APPLICABILITY"),
                                          (False, "NOT_SELECTED_FOR_REVIEW"),
                                          (True, "CANDIDATE_REVIEW")):
            with self.subTest(interpretation=interpretation):
                facts = dict(base)
                if interpretation is not None:
                    facts["manual_final_sketch_relief_for_surveyor_sketch"] = interpretation
                result = self.workbook(context=context, **facts)
                self.assertEqual(self.clause(result, "4.4.2.3")["selection_status"], expected)
        facts = self.facts(**base, manual_final_sketch_relief_for_surveyor_sketch=True)
        facts["manual_final_sketch_relief_for_surveyor_sketch"]["provenance"] = None
        unrecorded = prepare_clause_workbook(self.catalogue, context, facts)
        row = self.clause(unrecorded, "4.4.2.3")
        self.assertEqual(row["selection_status"], "UNRESOLVED_APPLICABILITY")
        self.assertIn("manual_final_sketch_relief_for_surveyor_sketch", row["blocking_fact_ids"])

    def test_optional_precision_and_coordinate_permission_stay_in_guidance_counts(self):
        # The source says consultant identification/rounding may be used and
        # permits listed sketch coordinate sources; absence is not a deficiency.
        choices = dict(area_rounding_to_0_999_ha_applies=False,
                       area_rounding_to_9_99_ha_applies=False,
                       area_rounding_10_ha_or_more_applies=False)
        baseline = self.workbook(**choices)
        adopted = self.workbook(**{**choices, "area_rounding_to_0_999_ha_applies": True})
        self.assertEqual(adopted["counts"]["selected_guidance_checks"],
                         baseline["counts"]["selected_guidance_checks"] + 1)
        self.assertEqual(adopted["counts"]["selected_required_manual_checks"],
                         baseline["counts"]["selected_required_manual_checks"])
        for ident, kind in (("1.2.2.2", "optional"), ("1.3.6.1", "optional"), ("2.1.1.1", "permission")):
            row = self.clause(baseline, ident)
            self.assertEqual(row["kind"], kind)
            self.assertTrue(all(check["kind"] == kind for check in row["checks"]))
            for check in row["checks"]:
                self.assertEqual(check["status"], "REVIEW_REQUIRED")
                self.assertEqual(check["source_status"], "UNVERIFIED_CURRENT")

    def test_missing_scope_and_excluded_scope_cannot_request_any_clause_review(self):
        for land, status in ((None, "UNRESOLVED_APPLICABILITY"), ("private", "OUT_OF_SCOPE")):
            with self.subTest(land=land):
                result = self.workbook(context={**self.context, "land_class": land})
                self.assertTrue(all(row["selection_status"] == status for row in result["clauses"]))
                self.assertTrue(all(not c["review_requests"] for row in result["clauses"]
                                    for c in row["checks"]))


if __name__ == "__main__":
    unittest.main()
