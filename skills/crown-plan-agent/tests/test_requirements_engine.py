"""Synthetic, offline checks. No client data, PDF, internet or compliance certification."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from requirements import applicability, evaluate, inspect_text, load_catalog


class RequirementsEngineTests(unittest.TestCase):
    def test_catalog_has_no_claim_of_current_verification(self):
        catalog = load_catalog()
        self.assertTrue(catalog["sources"])
        self.assertTrue(all(s["current_status"] != "VERIFIED_CURRENT" for s in catalog["sources"]))

    def test_latest_a2_listing_requires_exact_table_review(self):
        catalog = load_catalog()
        source = next(s for s in catalog["sources"] if s["id"] == "GOA-PLAR-TABLE-A2")
        self.assertEqual(source["latest_catalogue_update_observed"], "2026-10-28")
        self.assertEqual(source["verification_priority"], "HIGH")
        self.assertNotEqual(source["current_status"], "VERIFIED_CURRENT")

    def test_no_duplicate_catalogue_source_ids(self):
        sources = load_catalog()["sources"]
        ids = [source["id"] for source in sources]
        self.assertEqual(len(ids), len(set(ids)))

    def test_sketch_and_survey_plan_are_not_conflated(self):
        base = {"land_class": "alberta_crown", "regulator": "AER", "activity": "LOC", "stage": "amendment"}
        sketch = applicability({**base, "plan_type": "sketch"})["sections"]
        survey = applicability({**base, "plan_type": "survey_plan"})["sections"]
        self.assertIn("Part 2", sketch)
        self.assertNotIn("Part 3", sketch)
        self.assertIn("Part 3", survey)
        self.assertNotIn("Part 2", survey)
        self.assertIn("Part 3.3", survey)

    def test_unknown_plan_type_stays_unresolved(self):
        self.assertEqual(applicability({"plan_type": "unknown"})["status"], "REVIEW_REQUIRED")

    def test_invalid_context_does_not_select_content_sections(self):
        base = {"land_class": "alberta_crown", "regulator": "AER", "disposition": "LOC", "stage": "amendment",
                "plan_type": "survey_plan"}
        for field, value in (("regulator", "unknown"), ("stage", "not_a_stage"),
                             ("disposition", "???"), ("plan_type", "unknown")):
            with self.subTest(field=field):
                result = applicability({**base, field: value})
                self.assertEqual(result["sections"], [])
                self.assertEqual(result["applicability_status"], "UNRESOLVED_APPLICABILITY")
                self.assertIn(field, result["invalid_dimensions"])

    def test_disposition_alias_selects_the_same_content_sections(self):
        result = applicability({"land_class": "alberta_crown", "regulator": "Alberta", "disposition": " loc ",
                                "stage": "amendment", "plan_type": "survey_plan"})
        self.assertEqual(result["sections"], ["Part 1", "Part 3", "Part 4.1", "Part 3.3"])

    def test_evidence_does_not_become_compliance_without_authority(self):
        rule = {"id": "SYNTH-01", "evidence_key": "legal_description_present"}
        finding = evaluate(rule, {"legal_description_present": False})
        self.assertEqual(finding["evidence_status"], "FAIL")
        self.assertEqual(finding["status"], "REVIEW_REQUIRED")
        self.assertEqual(finding["source_status"], "UNVERIFIED_CURRENT")

    def test_missing_evidence_is_not_pass(self):
        finding = evaluate({"id": "SYNTH-02", "evidence_key": "north_arrow_present"}, {}, True)
        self.assertEqual(finding["status"], "REVIEW_REQUIRED")

    def test_authority_attestation_rejects_nonboolean_values(self):
        for value in ("false", "true", "", 0, 1, None, [], {"verified": True}):
            with self.subTest(value=value), self.assertRaises(TypeError):
                evaluate({"id": "SYNTH-03", "evidence_key": "x"}, {"x": True}, value)

    def test_text_presence_is_not_visual_pass(self):
        finding = inspect_text("SCALE 1:5000; SKETCH PLAN", {"scale": ("scale",), "north_arrow": ("north arrow",)})
        self.assertTrue(finding["scale"]["found_in_text"])
        self.assertFalse(finding["north_arrow"]["found_in_text"])
        self.assertTrue(all(x["status"] == "REVIEW_REQUIRED" for x in finding.values()))


if __name__ == "__main__":
    unittest.main()
