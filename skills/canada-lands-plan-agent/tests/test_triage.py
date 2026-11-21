"""Synthetic-only tests; no client source, real plan, or regulatory approval."""
import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "engine" / "triage.py"
SPEC = importlib.util.spec_from_file_location("canada_lands_triage", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class TriageTests(unittest.TestCase):
    def test_off_lease_remediation_surface_permit_is_only_candidate(self):
        result = module.triage({
            "land_class": "first_nation_reserve",
            "iogc_confirmed": True,
            "purpose": "off_lease_remediation",
            "document_type": "surface_permit_sketch",
        })
        self.assertEqual(result["candidate_route"], "consider_iogc_surface_permit")
        self.assertEqual(result["route_status"], "REVIEW_REQUIRED")
        self.assertEqual(result["source_rule_verification"], "REVIEW_REQUIRED")
        self.assertEqual(result["regulatory_acceptance"], "NOT_ASSESSED")
        self.assertNotEqual(result["iogc_incidental_activities_table_applicability"], "PASS")

    def test_permanent_land_change_not_misidentified_as_remediation(self):
        result = module.triage({
            "land_class": "first_nation_reserve",
            "iogc_confirmed": True,
            "purpose": "new_permanent_land",
        })
        self.assertEqual(result["candidate_route"], "consider_surface_contract_amendment")

    def test_reclamation_by_itself_is_not_amendment(self):
        result = module.triage({
            "land_class": "first_nation_reserve",
            "iogc_confirmed": True,
            "purpose": "reclamation",
        })
        self.assertEqual(result["candidate_route"], "determine_underlying_transaction")

    def test_non_iogc_and_nonreserve_do_not_apply_iogc_rules(self):
        result = module.triage({
            "land_class": "first_nation_reserve",
            "iogc_confirmed": False,
            "purpose": "off_lease_remediation",
        })
        self.assertEqual(result["candidate_route"], "verify_administrator_and_standards")
        provincial = module.triage({"land_class": "provincial_crown"})
        self.assertEqual(provincial["route_status"], "NOT_APPLICABLE")
        self.assertEqual(provincial["iogc_incidental_activities_table_applicability"], "NOT_APPLICABLE")

    def test_area_accounting_is_independent_of_legal_area_requirements(self):
        result = module.triage({
            "land_class": "first_nation_reserve",
            "iogc_confirmed": True,
            "purpose": "off_lease_remediation",
            "workspace_area": {
                "total_ha": "0.4800", "within_row_ha": "0.0600",
                "outside_row_ha": "0.4200",
            },
        })
        self.assertEqual(result["area_arithmetic"]["status"], "PASS")
        self.assertEqual(result["area_arithmetic"]["check_type"], "arithmetic_only")
        self.assertEqual(result["iogc_incidental_activities_table_applicability"], "REVIEW_REQUIRED")

    def test_area_discrepancy_is_only_arithmetic_fail(self):
        result = module.check_workspace_areas({
            "total_ha": "0.4800", "within_row_ha": "0.0600",
            "outside_row_ha": "0.4000",
        })
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["check_type"], "arithmetic_only")

    def test_missing_or_invalid_area_never_passes(self):
        for area in (None, {}, {"total_ha": "1"}, {
            "total_ha": "-1", "within_row_ha": "0", "outside_row_ha": "0",
        }, {
            "total_ha": "NaN", "within_row_ha": "0", "outside_row_ha": "0",
        }):
            with self.subTest(area=area):
                self.assertEqual(module.check_workspace_areas(area)["status"], "REVIEW_REQUIRED")

    def test_malformed_input_rejected(self):
        for case in ([], {"purpose": []}, {"land_class": {}}, {"iogc_confirmed": "yes"}):
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    module.triage(case)
        self.assertEqual(module.triage({})["candidate_route"], "verify_land_class")


if __name__ == "__main__":
    unittest.main()
