"""Opt-in finished-plan checking through the existing offline review command."""
import copy
import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from pdf_inspector import extract_pdf
from review_cli import main, run_review
from finished_plan_spec import load_spec
from finished_plan_fixture import make_plan


class FinishedPlanCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pdf = self.root / "synthetic.pdf"
        self.spec = make_plan(self.pdf, subject="LOT 8", total="0.400")
        self.spec_path = self.root / "checks.json"
        self.spec_path.write_text(json.dumps(self.spec), encoding="utf-8")
        self.scenario = {"land_class": "alberta_crown", "regulator": "AER", "stage": "initial",
                         "disposition": "LOC", "plan_type": "sketch"}
        self.scenario_path = self.root / "scenario.json"
        self.scenario_path.write_text(json.dumps(self.scenario), encoding="utf-8")
        self.catalogue = Path(__file__).resolve().parents[1] / "engine" / "candidate_requirements.json"
        self.output = self.root / "review.md"

    def test_existing_command_appends_qc_and_keeps_regulatory_gates(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main([str(self.pdf), "--scenario", str(self.scenario_path),
                                   "--output", str(self.output), "--offline", "--reference-cache", str(self.root / "empty"),
                                   "--finished-plan-spec", str(self.spec_path)]), 0)
        text = self.output.read_text(encoding="utf-8")
        self.assertIn("Finished-plan drawing QC", text)
        self.assertIn("FAIL=2", text)
        self.assertIn("Regulatory compliance: NOT_ASSESSED", text)
        self.assertIn("REVIEW_REQUIRED", text)
        self.assertIn(self.spec["source_sha256"], text)

    def test_qc_and_standard_pdf_markup_publish_together(self):
        annotated = self.root / "marked.pdf"
        run_review(self.pdf, self.output, self.scenario, self.catalogue,
                   annotated_pdf=annotated, finished_plan_spec=self.spec)
        text = self.output.read_text(encoding="utf-8")
        self.assertIn("Finished-plan drawing QC", text)
        self.assertIn("Marked-up PDF review copy", text)
        self.assertTrue(annotated.is_file())

    def test_combined_review_refuses_inventory_from_different_bytes(self):
        inventory = extract_pdf(self.pdf, include_vectors=False)
        inventory["source_sha256"] = "0" * 64
        with patch("review_cli.extract_pdf", return_value=inventory):
            with self.assertRaisesRegex(ValueError, "Source PDF changed"):
                run_review(self.pdf, self.output, self.scenario, self.catalogue,
                           finished_plan_spec=self.spec)
        self.assertFalse(self.output.exists())

    def test_default_review_output_is_unchanged(self):
        run_review(self.pdf, self.output, self.scenario, self.catalogue)
        text = self.output.read_text(encoding="utf-8")
        self.assertNotIn("Finished-plan drawing QC", text)
        self.assertIn("Drawing-text disposition evidence", text)

    def test_direct_entrypoint_rejects_stale_spec_without_output(self):
        self.spec["source_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            run_review(self.pdf, self.output, self.scenario, self.catalogue,
                       finished_plan_spec=self.spec)
        self.assertFalse(self.output.exists())

    def test_spec_preflight_runs_before_opted_in_refresh(self):
        self.spec["source_sha256"] = "0" * 64
        self.spec_path.write_text(json.dumps(self.spec), encoding="utf-8")
        with patch("review_cli.refresh_table_a2") as refresh, redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main([str(self.pdf), "--scenario", str(self.scenario_path), "--output", str(self.output),
                      "--finished-plan-spec", str(self.spec_path), "--refresh-table-a2"])
        refresh.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_existing_output_and_original_pdf_are_preserved(self):
        self.output.write_text("keep existing review", encoding="utf-8")
        original = self.pdf.read_bytes()
        with self.assertRaises(FileExistsError):
            run_review(self.pdf, self.output, self.scenario, self.catalogue,
                       finished_plan_spec=self.spec)
        self.assertEqual(self.output.read_text(encoding="utf-8"), "keep existing review")
        self.assertEqual(self.pdf.read_bytes(), original)

    def test_unknown_land_keeps_crown_checks_gated_but_explicit_generic_qc_runs(self):
        run_review(self.pdf, self.output, {"land_class": "federal"}, self.catalogue,
                   finished_plan_spec=self.spec)
        text = self.output.read_text(encoding="utf-8")
        self.assertIn("OUT_OF_SCOPE", text)
        self.assertIn("DRAWING", text.upper())
        self.assertIn("Regulatory compliance: NOT_ASSESSED", text)
        self.assertIn("FAIL=2", text)

    def test_duplicate_json_key_is_rejected(self):
        self.spec_path.write_text('{"schema_version":1,"schema_version":2}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            load_spec(self.spec_path)

    def test_large_spec_is_rejected(self):
        self.spec_path.write_text(" " * 1_000_001, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "size limit"):
            load_spec(self.spec_path)

    def test_nonfinite_json_is_rejected(self):
        self.spec_path.write_text('{"v":NaN}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Non-finite"):
            load_spec(self.spec_path)


if __name__ == "__main__":
    unittest.main()
