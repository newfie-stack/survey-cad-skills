"""Actual CLI input rejection, using invented files and no external requests."""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from review_cli import main

try:
    import fitz
except ImportError:
    fitz = None


@unittest.skipUnless(fitz is not None, "PyMuPDF unavailable")
class ReviewCLIInputTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.pdf = self.root / "synthetic.pdf"
        with fitz.open() as document:
            page = document.new_page()
            page.insert_text((50, 50), "SKETCH PLAN SHOWING: INVENTED EXAMPLE")
            page.insert_text((50, 70), "SCALE 1:5000")
            page.insert_text((50, 90), "LOC12345")
            document.save(self.pdf)
        self.scenario = {
            "land_class": "alberta_crown", "regulator": "AER",
            "disposition": "LOC", "stage": "initial", "plan_type": "sketch",
            "purpose": "Invented pipeline purpose", "subactivity": "",
        }
        self.geometry = {
            "coordinate_source": "EXPLICIT_SURVEY_COORDINATES",
            "crs_identifier": "SYNTHETIC_PROJECTED_METRIC",
            "crs_verified": True, "closed_ring": True,
            "vertices": [[0, 0], [100, 0], [100, 20], [0, 20], [0, 0]],
        }
        self.scenario_path = self.root / "scenario.json"
        self.scenario_path.write_text(json.dumps(self.scenario), encoding="utf-8")
        self.geometry_path = self.root / "geometry.json"
        self.geometry_path.write_text(json.dumps(self.geometry), encoding="utf-8")
        self.output = self.root / "review.md"
        self.cache = self.root / "reference-cache"

    def assert_input_error(self, kind):
        """Removing strict parsing must fail before an opted-in refresh can run."""
        stdout, stderr = io.StringIO(), io.StringIO()
        calls = []

        def refresh_sentinel(*args, **kwargs):
            calls.append("unexpected refresh")
            return {"refresh_status": "UNRESOLVED_SOURCE",
                    "reason": "Synthetic refresh sentinel; no network request"}

        args = [str(self.pdf), "--scenario", str(self.scenario_path),
                "--survey-geometry", str(self.geometry_path),
                "--output", str(self.output), "--reference-cache", str(self.cache),
                "--refresh-table-a2"]
        error = None
        with patch("review_cli.refresh_table_a2", side_effect=refresh_sentinel), \
                redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                main(args)
            except (Exception, SystemExit) as exc:
                error = exc
        self.assertIsInstance(error, SystemExit,
                              "Invalid JSON must produce a concise CLI input error")
        self.assertEqual(error.code, 2)
        self.assertIn("error:", stderr.getvalue())
        self.assertIn(kind + " JSON", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())
        self.assertFalse(self.output.exists())
        self.assertFalse(self.cache.exists())
        self.assertEqual(calls, [], "Rejected JSON must not initiate a source refresh")

    def test_duplicate_scenario_scope_is_rejected_before_refresh(self):
        raw = json.dumps(self.scenario).replace(
            '"land_class": "alberta_crown"',
            '"land_class": "private", "land_class": "alberta_crown"')
        self.scenario_path.write_text(raw, encoding="utf-8")
        self.assert_input_error("scenario")

    def test_duplicate_geometry_verification_is_rejected_before_refresh(self):
        raw = json.dumps(self.geometry).replace(
            '"crs_verified": true', '"crs_verified": false, "crs_verified": true')
        self.geometry_path.write_text(raw, encoding="utf-8")
        self.assert_input_error("survey geometry")

    def test_malformed_json_is_a_concise_input_error(self):
        for kind, path in (("scenario", self.scenario_path),
                           ("survey geometry", self.geometry_path)):
            with self.subTest(kind=kind):
                original = path.read_bytes()
                path.write_text('{"unfinished":', encoding="utf-8")
                self.assert_input_error(kind)
                path.write_bytes(original)

    def test_nonfinite_json_is_rejected_before_refresh(self):
        for kind, path, valid in (("scenario", self.scenario_path, self.scenario),
                                  ("survey geometry", self.geometry_path, self.geometry)):
            for number in ("NaN", "Infinity", "-Infinity", "1e999"):
                with self.subTest(kind=kind, number=number):
                    raw = json.dumps(valid)[:-1] + ', "untrusted_number": ' + number + '}'
                    path.write_text(raw, encoding="utf-8")
                    self.assert_input_error(kind)
            path.write_text(json.dumps(valid), encoding="utf-8")

    def test_nonobject_inputs_are_concise_input_errors(self):
        for kind, path, valid in (("scenario", self.scenario_path, self.scenario),
                                  ("survey geometry", self.geometry_path, self.geometry)):
            for raw in ("[]", "null", "false", "42", '"text"'):
                with self.subTest(kind=kind, raw=raw):
                    path.write_text(raw, encoding="utf-8")
                    self.assert_input_error(kind)
            path.write_text(json.dumps(valid), encoding="utf-8")

    def test_missing_input_files_are_concise_input_errors(self):
        for kind, path in (("scenario", self.scenario_path),
                           ("survey geometry", self.geometry_path)):
            with self.subTest(kind=kind):
                original = path.read_bytes()
                path.unlink()
                self.assert_input_error(kind)
                path.write_bytes(original)

    def test_valid_objects_preserve_blank_subactivity_and_geometry_review(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            result = main([str(self.pdf), "--scenario", str(self.scenario_path),
                           "--survey-geometry", str(self.geometry_path),
                           "--output", str(self.output),
                           "--reference-cache", str(self.cache), "--offline"])
        self.assertEqual(result, 0)
        report = self.output.read_text(encoding="utf-8")
        self.assertIn("not a regulatory compliance certificate", report)
        self.assertIn("Polygon area (m²): 2000", report)
        self.assertFalse(self.cache.exists())


if __name__ == "__main__":
    unittest.main()
