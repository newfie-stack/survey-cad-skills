"""Invented variant headings retain general content and dated-source exceptions."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from coverage_inventory import audit_coverage, load_inventory
from regulatory_catalog import candidate_applicability, load_candidate_catalog
from review_pipeline import review_inventory


class PlanVariantCatalogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = load_candidate_catalog(
            Path(__file__).resolve().parents[1] / "engine" / "candidate_requirements.json")

    def scenario(self, kind):
        return {"land_class": "alberta_crown", "regulator": "AER",
                "disposition": "LOC", "stage": "initial", "plan_type": kind,
                "purpose": "Invented purpose"}

    def selected_ids(self, kind):
        return {entry["requirement_id"] for entry in candidate_applicability(
            self.rules, self.scenario(kind))
            if entry["applicability_status"] == "CANDIDATE_REVIEW"}

    def review(self, kind, *texts):
        spans = [{"text": text, "page": 1, "bbox_points": [10, i * 20 + 10, 500, i * 20 + 20]}
                 for i, text in enumerate(texts)]
        return review_inventory({"spans": spans, "source_filename": "invented.pdf"},
                                self.scenario(kind), self.rules)

    def heading(self, report, kind):
        ident = "CANDIDATE-" + kind.upper() + "-PLAN-HEADING"
        return next(entry for entry in report["requirements"]
                    if entry["requirement_id"] == ident)

    def test_all_variants_retain_general_content_with_separate_heading_routes(self):
        self.assertEqual(len(self.rules), 17)
        ordinary = self.selected_ids("sketch")
        general = ordinary - {"CANDIDATE-PLAN-HEADING"}
        self.assertEqual(len(general), 13)
        for kind in ("sketch", "surveyor_sketch", "survey_plan"):
            with self.subTest(kind=kind):
                self.assertEqual(self.selected_ids(kind), ordinary)
        self.assertEqual(self.selected_ids("hybrid_plan"), general | {
            "CANDIDATE-HYBRID-PLAN-HEADING"})
        self.assertEqual(self.selected_ids("compiled_plan"), general | {
            "CANDIDATE-COMPILED-PLAN-HEADING", "CANDIDATE-COMPILED-DECLARATION"})

    def test_variant_heading_candidates_require_prescribed_full_span_prefixes(self):
        for kind, variant, title, section, source_page in (
            ("hybrid_plan", "hybrid", "Plan Showing Survey (Hybrid) of Invented Subject", "3.5.1.1", 12),
            ("compiled_plan", "compiled", "Compiled Plan from Existing Surveys for the Purpose of Invented Subject", "3.6.1.2", 14),
        ):
            for text in (title, title.upper(), "  " + title.replace(" ", "  ") + "  "):
                with self.subTest(kind=kind, text=text):
                    report = self.review(kind, text)
                    entry = self.heading(report, variant)
                    self.assertEqual(entry["evidence_status"], "OBSERVED_CANDIDATE")
                    self.assertEqual(entry["observation"], text)
                    self.assertEqual(entry["page"], 1)
                    self.assertEqual(entry["status"], "REVIEW_REQUIRED")
                    self.assertEqual(entry["source_status"], "UNVERIFIED_CURRENT")
                    self.assertEqual(entry["section"], section)
                    self.assertEqual(entry["source_page"], source_page)
                    self.assertEqual(entry["version_date"], "2024-05-30")
                    self.assertEqual(report["overall_status"], "REVIEW_REQUIRED")

    def test_bare_variant_words_references_and_near_prefixes_are_not_headings(self):
        cases = (
            ("hybrid_plan", "hybrid", ("hybrid", "survey (hybrid)",
                "See Plan Showing Survey (Hybrid) of Invented Subject",
                "Plan Showing Survey (Hybrid) offices", "Plan Showing Survey Hybrid of Invented Subject")),
            ("compiled_plan", "compiled", ("compiled", "compiled plan",
                "Reference: Compiled Plan from Existing Surveys for the Purpose of Invented Subject",
                "Compiled Plan from Existing Surveys for the Purpose offices",
                "Compiled Plan Showing Invented Subject")),
        )
        for kind, variant, texts in cases:
            for text in texts:
                with self.subTest(kind=kind, text=text):
                    self.assertEqual(self.heading(self.review(kind, text), variant)["evidence_status"],
                                     "UNKNOWN")

    def test_wrong_variant_heading_does_not_match_the_proposed_variant(self):
        hybrid = "Plan Showing Survey (Hybrid) of Invented Subject"
        compiled = "Compiled Plan from Existing Surveys for the Purpose of Invented Subject"
        for kind, variant, text in (("hybrid_plan", "hybrid", compiled),
                                    ("compiled_plan", "compiled", hybrid)):
            with self.subTest(kind=kind):
                self.assertEqual(self.heading(self.review(kind, text), variant)["evidence_status"], "UNKNOWN")

    def test_conflicting_recognized_heading_types_remain_unresolved(self):
        hybrid = "Plan Showing Survey (Hybrid) of Invented Subject"
        compiled = "Compiled Plan from Existing Surveys for the Purpose of Invented Subject"
        for kind, variant, titles in (("hybrid_plan", "hybrid", (hybrid, "SURVEY")),
                                     ("compiled_plan", "compiled", (compiled, "SKETCH")),
                                     ("hybrid_plan", "hybrid", (hybrid, compiled))):
            with self.subTest(kind=kind, titles=titles):
                entry = self.heading(self.review(kind, *titles), variant)
                self.assertEqual(entry["evidence_status"], "UNKNOWN")
                self.assertIn("Multiple different plan-type labels", entry["observation"])
        ordinary = self.review("survey_plan", "SURVEY", hybrid)
        entry = next(item for item in ordinary["requirements"]
                     if item["requirement_id"] == "CANDIDATE-PLAN-HEADING")
        self.assertEqual(entry["evidence_status"], "UNKNOWN")
        self.assertIn("Multiple different plan-type labels", entry["observation"])

    def test_compiled_declaration_is_a_manual_appendix_d_review(self):
        report = self.review("compiled_plan", "Signed by Invented Surveyor")
        entry = next(item for item in report["requirements"]
                     if item["requirement_id"] == "CANDIDATE-COMPILED-DECLARATION")
        self.assertEqual(entry["section"], "3.6.1.3")
        self.assertEqual(entry["source_page"], 14)
        self.assertEqual(entry["check_method"], "visual")
        self.assertEqual(entry["evidence_status"], "VISUAL_CHECK_REQUIRED")
        self.assertIn("Appendix D", entry["review_instruction"])
        self.assertNotIn("Commissioner", entry["review_instruction"])
        self.assertNotIn("CANDIDATE-PLAN-HEADING", self.selected_ids("compiled_plan"))

    def test_new_variant_routes_cannot_bypass_land_scope(self):
        for kind in ("hybrid_plan", "compiled_plan"):
            for land in (None, "private", "mixed"):
                with self.subTest(kind=kind, land=land):
                    scenario = {**self.scenario(kind), "land_class": land}
                    selected = [entry for entry in candidate_applicability(self.rules, scenario)
                                if entry["applicability_status"] == "CANDIDATE_REVIEW"]
                    self.assertEqual(selected, [])

    def test_new_mappings_cover_only_the_three_implemented_variant_clauses(self):
        audit = audit_coverage(self.rules, load_inventory())
        expected = {"3.5.1.1": ["CANDIDATE-HYBRID-PLAN-HEADING"],
                    "3.6.1.2": ["CANDIDATE-COMPILED-PLAN-HEADING"],
                    "3.6.1.3": ["CANDIDATE-COMPILED-DECLARATION"]}
        clauses = {item["clause_id"]: item for item in audit["clauses"]}
        for clause, ids in expected.items():
            self.assertEqual(clauses[clause]["mapped_candidate_ids"], ids)
        self.assertEqual(clauses["3.6.1.1"]["mapped_candidate_ids"], [])
        self.assertEqual(audit["counts"]["mapped_candidate_clauses"], 29)
        self.assertEqual(audit["counts"]["unmapped_clauses"], 115)


if __name__ == "__main__":
    unittest.main()
