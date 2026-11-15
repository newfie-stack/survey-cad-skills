"""Opt-in dated workbooks do not change the legacy observation review."""
import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

import fitz

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "engine"))
from regulatory_catalog import load_candidate_catalog
from review_pipeline import review_inventory
from review_cli import main, run_review


class ClauseIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.scenario = {"land_class": "alberta_crown", "regulator": "AER",
                         "disposition": "LOC", "stage": "initial", "plan_type": "sketch",
                         "purpose": "Invented purpose", "subactivity": "Invented activity"}
        self.inventory = {"source_filename": "invented.pdf", "pages": 1, "spans": [
            {"text": "SKETCH", "page": 1, "bbox_points": [10, 10, 60, 20]}]}
        self.catalogue = load_candidate_catalog(SKILL / "engine/candidate_requirements.json")
        self.clause_path = SKILL / "tests/synthetic_clause_catalogue.json"
        self.clauses = json.loads(self.clause_path.read_text())
        self.facts = {"has_details": {"value": False, "provenance": None},
                      "length_m": {"value": "9", "provenance": None}}

    def test_opt_in_adds_a_separate_workbook_without_changing_observations(self):
        before = copy.deepcopy((self.inventory, self.scenario, self.clauses, self.facts))
        legacy = review_inventory(self.inventory, self.scenario, self.catalogue)
        opted = review_inventory(self.inventory, self.scenario, self.catalogue,
                                 clause_catalogue=self.clauses, clause_facts=self.facts)
        self.assertNotIn("clause_workbook", legacy)
        self.assertNotIn("Dated-source clause workbook", legacy["report_markdown"])
        self.assertEqual(opted["requirements"], legacy["requirements"])
        self.assertEqual(opted["summary"], legacy["summary"])
        workbook = opted["clause_workbook"]
        self.assertEqual(workbook["catalogue_id"], "INVENTED-CONDITIONAL-001")
        self.assertEqual(workbook["counts"]["catalogued_clause_paths"], 6)
        self.assertEqual(workbook["overall_status"], "REVIEW_REQUIRED")
        self.assertEqual(workbook["source_status"], "UNVERIFIED_CURRENT")
        self.assertIn("Dated-source clause workbook", opted["report_markdown"])
        self.assertEqual((self.inventory, self.scenario, self.clauses, self.facts), before)

    def test_legacy_observation_ids_are_not_automatically_bound(self):
        report = review_inventory(self.inventory, self.scenario, self.catalogue,
                                  clause_catalogue=self.clauses, clause_facts=self.facts)
        heading = next(check for clause in report["clause_workbook"]["clauses"]
                       for check in clause["checks"] if check["id"] == "ordinary_heading")
        self.assertEqual(heading["observation_refs"], [])
        self.assertEqual(heading["evidence_status"], "MANUAL_REVIEW_REQUIRED")
        observed = next(row for row in report["requirements"]
                        if row["requirement_id"] == "CANDIDATE-PLAN-HEADING")
        self.assertEqual(observed["evidence_status"], "OBSERVED_CANDIDATE")

    def test_workbook_inputs_require_an_explicit_catalogue(self):
        for inputs in ({"clause_facts": {}}, {"clause_inventory": {}}):
            with self.subTest(inputs=inputs), self.assertRaises(ValueError):
                review_inventory(self.inventory, self.scenario, self.catalogue, **inputs)

    def test_private_scope_stays_outside_in_both_layers(self):
        report = review_inventory(self.inventory, {**self.scenario, "land_class": "private"},
                                  self.catalogue, clause_catalogue=self.clauses,
                                  clause_facts={})
        self.assertEqual(report["requirements"], [])
        workbook = report["clause_workbook"]
        self.assertTrue(all(row["selection_status"] == "OUT_OF_SCOPE"
                            for row in workbook["clauses"]))
        self.assertTrue(all(not check["review_requests"] for clause in workbook["clauses"]
                            for check in clause["checks"]))

    def test_cli_rejects_dependent_flags_before_reading_inputs(self):
        for option in ("--clause-facts", "--clause-inventory"):
            errors = io.StringIO()
            with self.subTest(option=option), redirect_stderr(errors), \
                 patch("review_cli.extract_pdf") as extract, \
                 patch("review_cli.refresh_table_a2") as refresh:
                with self.assertRaises(SystemExit) as stopped:
                    main(["missing.pdf", "--scenario", "missing.json", "--output", "review.md",
                          option, "also-missing.json"])
                self.assertEqual(stopped.exception.code, 2)
                self.assertIn("requires --clause-catalogue", errors.getvalue())
                extract.assert_not_called()
                refresh.assert_not_called()

    def test_cli_generates_offline_workbook_and_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf, scenario, facts, output = [root / name for name in
                                           ("invented.pdf", "scenario.json", "facts.json", "review.md")]
            with fitz.open() as document:
                document.new_page().insert_text((40, 60), "SKETCH")
                document.save(pdf)
            scenario.write_text(json.dumps(self.scenario), encoding="utf-8")
            facts.write_text(json.dumps(self.facts), encoding="utf-8")
            args = [str(pdf), "--scenario", str(scenario), "--output", str(output),
                    "--offline", "--reference-cache", str(root / "empty-cache"),
                    "--clause-catalogue", str(self.clause_path), "--clause-facts", str(facts)]
            with redirect_stdout(io.StringIO()), patch("review_cli.refresh_table_a2") as refresh:
                self.assertEqual(main(args), 0)
                refresh.assert_not_called()
            text = output.read_text()
            self.assertIn("INVENTED-CONDITIONAL-001", text)
            self.assertIn("Dated-source clause workbook", text)
            self.assertIn("UNVERIFIED_CURRENT", text)
            with self.assertRaises(FileExistsError):
                main(args)
            self.assertEqual(output.read_text(), text)

    def test_cli_invalid_workbook_cannot_trigger_extraction_or_refresh(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scenario, bad = root / "scenario.json", root / "bad.json"
            scenario.write_text(json.dumps(self.scenario), encoding="utf-8")
            bad.write_text('{"source_status":"VERIFIED_CURRENT"}', encoding="utf-8")
            errors = io.StringIO()
            with redirect_stderr(errors), patch("review_cli.extract_pdf") as extract, \
                 patch("review_cli.refresh_table_a2") as refresh:
                with self.assertRaises(SystemExit) as stopped:
                    main(["missing.pdf", "--scenario", str(scenario), "--output", str(root / "out.md"),
                          "--refresh-table-a2", "--clause-catalogue", str(bad)])
                self.assertEqual(stopped.exception.code, 2)
                self.assertIn("Invalid clause workbook inputs", errors.getvalue())
                extract.assert_not_called()
                refresh.assert_not_called()
            self.assertFalse((root / "out.md").exists())

    def test_direct_api_invalid_workbook_stops_before_source_inspection(self):
        invalid_inputs = (
            {"clause_catalogue": {"source_status": "VERIFIED_CURRENT"}},
            {"clause_facts": {}},
            {"clause_inventory": {}},
            {"clause_catalogue": self.clauses,
             "clause_facts": {"undeclared": {"value": True, "provenance": None}}},
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, inputs in enumerate(invalid_inputs):
                output = root / f"review-{index}.md"
                with self.subTest(inputs=inputs), \
                     patch("review_cli.load_candidate_catalog") as load, \
                     patch("review_cli.extract_pdf") as extract, \
                     patch("review_cli.extract_a2_rows") as rows:
                    with self.assertRaises(ValueError):
                        run_review(root / "missing.pdf", output, self.scenario,
                                   SKILL / "engine/candidate_requirements.json", **inputs)
                    load.assert_not_called()
                    extract.assert_not_called()
                    rows.assert_not_called()
                    self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
