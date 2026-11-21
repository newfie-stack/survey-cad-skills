"""Exclusive local intake artifacts and pre-native-parse input rejection."""
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from runtime_security import load_pdf_runtime
from intake_cli import main


class IntakeCLITests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.pdf = self.root / "invented.pdf"
        fitz = load_pdf_runtime()
        with fitz.open() as document:
            page = document.new_page(width=300, height=200)
            page.insert_text((40, 80), "Job: CPA-7")
            document.save(self.pdf)
        self.output = self.root / "map.json"
        self.ready = self.root / "ready.json"
        self.context = self.root / "contexts.json"
        self.spec = {"schema_version": 1, "source_sha256": hashlib.sha256(self.pdf.read_bytes()).hexdigest(),
                     "prepared_by": "Invented CLI reviewer", "checks": [{"id": "job", "kind": "required_text",
                     "description": "Current job", "basis": "Reviewed current titleblock", "expected": "CPA-7",
                     "regions": [{"page": 1, "bbox_points": [30, 60, 200, 100],
                                  "role": "current titleblock", "label": "Job:"}]}]}
        self.context.write_text(json.dumps(self.spec), encoding="utf-8")

    def args(self):
        return [str(self.pdf), "--output", str(self.output), "--context-spec", str(self.context),
                "--spec-output", str(self.ready)]

    def assert_rejected_before_pdf(self, args):
        previous = {path: path.read_bytes() if path.exists() else None for path in (self.output, self.ready)}
        with patch("intake_cli.discover_plan", side_effect=AssertionError("PDF parsed")), \
                patch("intake_cli.prepare_finished_plan", side_effect=AssertionError("PDF parsed")), \
                redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                main(args)
        self.assertEqual(error.exception.code, 2)
        for path, data in previous.items():
            if data is None:
                self.assertFalse(path.exists())
            else:
                self.assertEqual(path.read_bytes(), data)

    def test_inventory_only_and_preparation_write_portable_json(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main([str(self.pdf), "--output", str(self.output)]), 0)
        result = json.loads(self.output.read_text())
        self.assertTrue(result["line_candidates"])
        self.output.unlink()
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(self.args()), 0)
        prepared = json.loads(self.output.read_text())
        self.assertEqual(json.loads(self.ready.read_text()), prepared["spec"])
        self.assertEqual(prepared["resolutions"][0]["status"], "READY")

    def test_no_ready_checks_still_records_every_request_and_null_spec(self):
        self.spec["checks"][0]["regions"][0]["label"] = "Missing:"
        self.context.write_text(json.dumps(self.spec))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(self.args()), 0)
        self.assertIsNone(json.loads(self.ready.read_text()))
        self.assertEqual(len(json.loads(self.output.read_text())["resolutions"]), 1)

    def test_context_and_spec_destinations_are_paired(self):
        self.assert_rejected_before_pdf([str(self.pdf), "--output", str(self.output),
                                         "--context-spec", str(self.context)])
        self.assert_rejected_before_pdf([str(self.pdf), "--output", str(self.output),
                                         "--spec-output", str(self.ready)])

    def test_existing_aliasing_and_invalid_output_paths_fail_before_pdf(self):
        self.ready.write_text("preserve")
        self.assert_rejected_before_pdf(self.args())
        self.assertEqual(self.ready.read_text(), "preserve")
        self.ready.unlink()
        for destination in [self.pdf, self.context, self.root / "map.md", self.root / "missing/map.json"]:
            args = [str(self.pdf), "--output", str(destination)]
            self.assert_rejected_before_pdf(args)
        args = self.args()
        args[-1] = str(self.output)
        self.assert_rejected_before_pdf(args)

    def test_duplicate_unknown_oversized_and_hash_mismatched_contexts_fail_before_pdf(self):
        for raw in [json.dumps(self.spec).replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1'),
                    json.dumps({**self.spec, "unknown": True}), " " * 1_000_001,
                    json.dumps({**self.spec, "source_sha256": "0" * 64})]:
            self.context.write_text(raw)
            self.assert_rejected_before_pdf(self.args())

    def test_source_symlink_alias_is_not_overwritten(self):
        alias = self.root / "alias.json"
        alias.symlink_to(self.pdf)
        original = self.pdf.read_bytes()
        self.assert_rejected_before_pdf([str(self.pdf), "--output", str(alias)])
        self.assertEqual(self.pdf.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
