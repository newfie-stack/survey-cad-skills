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

    def test_opening_summary_reports_qc_when_crown_context_is_missing_or_unsupported(self):
        scenarios = [{}, {**self.scenario, "stage": "invented_tender"}]
        for index, scenario in enumerate(scenarios):
            with self.subTest(scenario=scenario):
                output = self.root / f"context-{index}.md"
                run_review(self.pdf, output, scenario, self.catalogue,
                           finished_plan_spec=self.spec)
                text = output.read_text(encoding="utf-8")
                summary = text.split("## Detailed evidence", 1)[0]
                checked = summary.split("### What was checked", 1)[1].split("###", 1)[0]
                attention = summary.split("### What needs attention", 1)[1].split("###", 1)[0]
                actions = summary.split("### Next steps", 1)[1]
                self.assertIn("5 selected", checked)
                for count in ("PASS=2", "FAIL=2", "REVIEW_REQUIRED=1"):
                    self.assertIn(count, checked)
                self.assertIn("drawing", checked.lower())
                self.assertIn("2 failed", attention)
                self.assertIn("1 unresolved", attention)
                self.assertIn("QC", actions)
                self.assertNotIn("No automated drawing checks", summary)
                self.assertIn("Information needed:", summary)
                self.assertIn("Status: REVIEW_REQUIRED", summary)
                self.assertIn("Regulatory compliance: NOT_ASSESSED", text)
                evidence = text.split("## Detailed evidence", 1)[1].split("## Plan type review", 1)[0]
                self.assertNotIn("| CANDIDATE-", evidence)

    def test_opening_summary_reports_generic_qc_without_selecting_out_of_scope_crown_checks(self):
        run_review(self.pdf, self.output, {"land_class": "federal"}, self.catalogue,
                   finished_plan_spec=self.spec)
        text = self.output.read_text(encoding="utf-8")
        summary = text.split("## Detailed evidence", 1)[0]
        checked = summary.split("### What was checked", 1)[1].split("###", 1)[0]
        self.assertIn("5 selected", checked)
        self.assertIn("FAIL=2", checked)
        self.assertIn("2 failed", summary)
        self.assertIn("1 unresolved", summary)
        self.assertIn("Crown requirements were not selected", summary)
        self.assertNotIn("Information needed:", summary)
        evidence = text.split("## Detailed evidence", 1)[1].split("## Plan type review", 1)[0]
        self.assertNotIn("| CANDIDATE-", evidence)
        self.assertIn("OUT_OF_SCOPE", text)
        self.assertIn("Status: REVIEW_REQUIRED", summary)

    def test_all_unresolved_qc_is_reported_as_execution_with_manual_followup(self):
        raster_pdf = self.root / "invented-raster.pdf"
        raster_spec = make_plan(raster_pdf, raster=True)
        run_review(raster_pdf, self.output, {}, self.catalogue,
                   finished_plan_spec=raster_spec)
        summary = self.output.read_text(encoding="utf-8").split("## Detailed evidence", 1)[0]
        checked = summary.split("### What was checked", 1)[1].split("###", 1)[0]
        attention = summary.split("### What needs attention", 1)[1].split("###", 1)[0]
        self.assertIn("5 selected", checked)
        for count in ("PASS=0", "FAIL=0", "REVIEW_REQUIRED=5"):
            self.assertIn(count, checked)
        self.assertIn("5 unresolved", attention)
        self.assertIn("QC", summary.split("### Next steps", 1)[1])
        self.assertNotIn("No automated drawing checks", summary)
        self.assertIn("Status: REVIEW_REQUIRED", summary)

    def test_passing_selected_qc_does_not_clear_authority_or_broader_drawing_review(self):
        spec = {**self.spec, "checks": [self.spec["checks"][2]]}
        run_review(self.pdf, self.output, self.scenario, self.catalogue,
                   finished_plan_spec=spec)
        summary = self.output.read_text(encoding="utf-8").split("## Detailed evidence", 1)[0]
        checked = summary.split("### What was checked", 1)[1].split("###", 1)[0]
        self.assertIn("1 selected", checked)
        for count in ("PASS=1", "FAIL=0", "REVIEW_REQUIRED=0"):
            self.assertIn(count, checked)
        self.assertIn("only", checked)
        self.assertIn("governing requirements have not been verified as current", summary)
        self.assertIn("beyond the selected", summary)
        self.assertIn("Regulatory compliance and professional acceptance have not been established", summary)
        self.assertIn("Status: REVIEW_REQUIRED", summary)

    def test_missing_context_without_opt_in_still_records_no_automated_drawing_checks(self):
        run_review(self.pdf, self.output, {}, self.catalogue)
        summary = self.output.read_text(encoding="utf-8").split("## Detailed evidence", 1)[0]
        checked = summary.split("### What was checked", 1)[1].split("###", 1)[0]
        self.assertIn("None recorded.", checked)
        self.assertIn("No automated drawing checks are recorded", summary)
        self.assertNotIn("drawing-QC", summary)

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
