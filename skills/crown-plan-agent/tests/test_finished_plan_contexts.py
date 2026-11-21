"""Exercise source-bound check preparation through the actual review command."""
import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from html import unescape
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from review_cli import main, run_review
from runtime_security import load_pdf_runtime


class FinishedPlanContextIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pdf = self.root / "invented.pdf"
        self.catalogue = Path(__file__).resolve().parents[1] / "engine/candidate_requirements.json"
        self.output = self.root / "review.md"
        self.scenario = self.root / "scenario.json"
        self.scenario.write_text("{}", encoding="utf-8")

    def source(self, *, duplicate=False):
        pdf = load_pdf_runtime()
        with pdf.open() as document:
            page = document.new_page(width=500, height=300)
            page.insert_text((40, 100), "Job: INTAKE-42", fontsize=12)
            page.insert_text((40, 111), "Date: 2026-11-21", fontsize=12)
            if duplicate:
                page.insert_text((40, 170), "Job: HISTORY-17", fontsize=12)
            document.save(self.pdf)
        return {"schema_version": 1, "source_sha256": hashlib.sha256(self.pdf.read_bytes()).hexdigest(),
                "prepared_by": "Invented layout reviewer", "checks": [{
                    "id": "current_job", "kind": "required_text",
                    "description": "Current job matches invented brief",
                    "basis": "Invented brief supplies INTAKE-42; panel context reviewed",
                    "expected": "INTAKE-42", "regions": [{
                        "page": 1, "bbox_points": [25, 75, 350, 200],
                        "role": "Reviewed current job panel", "label": "Job:"}]}]}

    def test_contexts_prepare_and_execute_actual_pdf_check(self):
        contexts = self.source()
        run_review(self.pdf, self.output, {}, self.catalogue,
                   finished_plan_contexts=contexts)
        report = unescape(self.output.read_text())
        opening = report.split("## Detailed evidence", 1)[0]
        self.assertIn("Prepared 1 of 1", opening)
        self.assertIn("PASS=1", opening)
        self.assertIn("Plan intake and check preparation", report)
        self.assertIn(contexts["source_sha256"], report)
        self.assertIn("Regulatory compliance: NOT_ASSESSED", report)
        self.assertEqual(hashlib.sha256(self.pdf.read_bytes()).hexdigest(), contexts["source_sha256"])

    def test_ambiguous_context_remains_visible_without_executed_check(self):
        contexts = self.source(duplicate=True)
        run_review(self.pdf, self.output, {}, self.catalogue,
                   finished_plan_contexts=contexts)
        report = unescape(self.output.read_text())
        opening = report.split("## Detailed evidence", 1)[0]
        self.assertIn("Prepared 0 of 1", opening)
        self.assertIn("1 unresolved", opening)
        self.assertIn("current_job", report)
        self.assertIn("HISTORY-17", report)
        self.assertNotIn("Executed 1 selected", opening)
        self.assertNotIn("## Finished-plan drawing QC", report)
        self.assertIn("Regulatory compliance: NOT_ASSESSED", report)

    def test_command_accepts_contexts_and_reports_its_actual_preparation(self):
        contexts = self.source()
        path = self.root / "contexts.json"
        path.write_text(json.dumps(contexts))
        with redirect_stdout(io.StringIO()):
            code = main([str(self.pdf), "--scenario", str(self.scenario),
                         "--output", str(self.output), "--offline",
                         "--reference-cache", str(self.root / "empty"),
                         "--finished-plan-contexts", str(path)])
        self.assertEqual(code, 0)
        self.assertIn("PASS=1", self.output.read_text())

    def test_spec_and_context_inputs_are_mutually_exclusive(self):
        self.source()
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            main([str(self.pdf), "--scenario", str(self.scenario), "--output", str(self.output),
                  "--finished-plan-spec", "unused.json", "--finished-plan-contexts", "unused.json"])
        self.assertEqual(error.exception.code, 2)
        self.assertFalse(self.output.exists())

    def test_direct_api_rejects_simultaneous_spec_and_contexts(self):
        contexts = self.source()
        with self.assertRaisesRegex(ValueError, "mutually exclusive|both"):
            run_review(self.pdf, self.output, {}, self.catalogue,
                       finished_plan_spec=contexts, finished_plan_contexts=contexts)
        self.assertFalse(self.output.exists())

    def test_wrong_digest_context_is_rejected_before_parsing_bad_pdf(self):
        contexts = self.source()
        self.pdf.write_bytes(b"%PDF-1.7\nnot a usable PDF\n")
        contexts["source_sha256"] = "0" * 64
        path = self.root / "wrong-contexts.json"
        path.write_text(json.dumps(contexts))
        captured = io.StringIO()
        with redirect_stderr(captured), self.assertRaises(SystemExit) as error:
            main([str(self.pdf), "--scenario", str(self.scenario), "--output", str(self.output),
                  "--finished-plan-contexts", str(path)])
        self.assertEqual(error.exception.code, 2)
        self.assertIn("digest", captured.getvalue().lower())
        self.assertFalse(self.output.exists())

    def test_source_change_after_unresolved_preparation_prevents_publication(self):
        from plan_intake import prepare_finished_plan
        contexts = self.source(duplicate=True)

        def prepare_then_change(pdf, request):
            result = prepare_finished_plan(pdf, request)
            self.pdf.write_bytes(self.pdf.read_bytes() + b"\n% source changed after intake\n")
            return result

        with patch("plan_intake.prepare_finished_plan", side_effect=prepare_then_change):
            with self.assertRaisesRegex(ValueError, "Source PDF changed"):
                run_review(self.pdf, self.output, {}, self.catalogue,
                           finished_plan_contexts=contexts)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
