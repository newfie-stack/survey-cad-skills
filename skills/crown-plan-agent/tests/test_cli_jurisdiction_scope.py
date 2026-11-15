"""Offline source-routing tests with invented plans and explicit land classes."""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from review_cli import main, run_review

try:
    import fitz
except ImportError:
    fitz = None


@unittest.skipUnless(fitz is not None, "PyMuPDF unavailable")
class CLIJurisdictionScopeTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.pdf = self.root / "synthetic-scope.pdf"
        with fitz.open() as document:
            page = document.new_page()
            page.insert_text((50, 50), "SKETCH")
            page.insert_text((50, 70), "SCALE 1:5000")
            page.insert_text((50, 90), "PLA 123456")
            document.save(self.pdf)
        self.scenario = {"land_class": "alberta_crown", "regulator": "AER",
                         "disposition": "PLA", "stage": "initial", "plan_type": "sketch",
                         "purpose": "synthetic"}
        self.catalogue = Path(__file__).resolve().parents[1] / "engine" / "candidate_requirements.json"

    def test_out_of_scope_land_never_requests_crown_sources(self):
        for land_class in ("private", "municipal", "federal", "other"):
            for regulator in ("AER", "Alberta"):
                with self.subTest(land_class=land_class, regulator=regulator):
                    output = self.root / f"{land_class}-{regulator}.md"
                    run_review(self.pdf, output, {**self.scenario, "land_class": land_class,
                                                  "regulator": regulator}, self.catalogue)
                    result = output.read_text(encoding="utf-8")
                    self.assertIn("Status: OUT_OF_SCOPE", result)
                    self.assertNotIn("OBSERVED_CANDIDATE", result)
                    self.assertNotIn("VISUAL_CHECK_REQUIRED", result)
                    self.assertNotIn("Download the current PLAR Table A2 PDF", result)
                    self.assertNotIn("Review the current PLAR Table A1", result)
                    self.assertNotIn("PLAR Table A2 disposition verification", result)

    def test_unknown_or_unspecified_mixed_land_requests_scope_before_plar(self):
        for index, fields in enumerate(({"land_class": None}, {"land_class": "unknown"},
                                        {"land_class": "unsupported"}, {"land_class": []},
                                        {"land_class": "mixed"},
                                        {"land_class": "mixed", "review_scope": "unknown"})):
            with self.subTest(fields=fields):
                output = self.root / f"unknown-{index}.md"
                scenario = {**self.scenario, **fields}
                if fields["land_class"] is None:
                    scenario.pop("land_class")
                run_review(self.pdf, output, scenario, self.catalogue)
                result = output.read_text(encoding="utf-8")
                self.assertIn("Confirm land_class", result)
                self.assertIn("review_scope", result)
                self.assertNotIn("Download the current PLAR Table A2 PDF", result)
                self.assertNotIn("Review the current PLAR Table A1", result)
                self.assertNotIn("OBSERVED_CANDIDATE", result)

    def test_cache_is_ignored_without_confirmed_crown_scope(self):
        cache = self.root / "cache"
        cache.mkdir()
        (cache / "plar_table_a2.pdf").write_bytes(b"synthetic-unused-cache")
        for index, land_class in enumerate(("private", "unknown", "mixed", None)):
            with self.subTest(land_class=land_class):
                scenario = {**self.scenario, "land_class": land_class}
                path = self.root / f"cache-scenario-{index}.json"
                path.write_text(json.dumps(scenario), encoding="utf-8")
                output = self.root / f"cache-review-{index}.md"
                stdout = io.StringIO()
                with patch("review_cli.extract_a2_rows", return_value=[]) as extract, \
                        patch("review_cli.refresh_table_a2") as refresh, redirect_stdout(stdout):
                    self.assertEqual(main([str(self.pdf), "--scenario", str(path),
                                           "--reference-cache", str(cache), "--output", str(output)]), 0)
                extract.assert_not_called()
                refresh.assert_not_called()
                result = output.read_text(encoding="utf-8")
                self.assertNotIn("PLAR Table A2 disposition verification", result)
                self.assertNotIn("Download the current PLAR Table A2 PDF", stdout.getvalue())
                if land_class != "private":
                    self.assertIn("Confirm land_class", stdout.getvalue())

    def test_explicit_a2_flags_need_confirmed_crown_scope_before_io(self):
        cache = self.root / "cache"
        cache.mkdir()
        (cache / "plar_table_a2.pdf").write_bytes(b"synthetic-unused-cache")
        for index, land_class in enumerate(("private", "mixed", "unknown", None)):
            for option, flags in enumerate((["--table-a2-pdf", str(self.pdf)],
                                            ["--refresh-table-a2"],
                                            ["--table-a2-url", "https://www.alberta.ca/synthetic-a2.pdf"])):
                with self.subTest(land_class=land_class, flags=flags):
                    path = self.root / f"explicit-scenario-{index}.json"
                    path.write_text(json.dumps({**self.scenario, "land_class": land_class}),
                                    encoding="utf-8")
                    output = self.root / f"explicit-review-{index}-{option}.md"
                    with patch("review_cli.extract_pdf", return_value={"spans": []}) as extract, \
                            patch("review_cli.extract_a2_rows", return_value=[]) as extract_a2, \
                            patch("review_cli.refresh_table_a2", return_value={
                                "refresh_status": "CHECKED_OFFICIAL_SOURCE"}) as refresh, \
                            redirect_stderr(io.StringIO()):
                        with self.assertRaises(SystemExit):
                            main([str(self.pdf), "--scenario", str(path), "--output", str(output),
                                  "--reference-cache", str(cache), *flags])
                    self.assertFalse(output.exists())
                    extract.assert_not_called()
                    extract_a2.assert_not_called()
                    refresh.assert_not_called()

    def test_direct_a2_input_needs_confirmed_crown_scope_before_extraction(self):
        for land_class in ("private", "mixed", "unknown", None):
            with self.subTest(land_class=land_class):
                output = self.root / f"direct-{land_class}.md"
                with patch("review_cli.extract_pdf", return_value={"spans": []}) as extract, \
                        patch("review_cli.extract_a2_rows", return_value=[]):
                    with self.assertRaisesRegex(ValueError, "scope|Scope|SCOPE"):
                        run_review(self.pdf, output, {**self.scenario, "land_class": land_class},
                                   self.catalogue, a2_pdf=self.pdf)
                extract.assert_not_called()
                self.assertFalse(output.exists())

    def test_confirmed_crown_and_mixed_crown_component_keep_source_routing(self):
        for index, fields in enumerate(({"land_class": " alberta_crown "},
                                        {"land_class": "mixed", "review_scope": "alberta_crown_component"})):
            for regulator, expected in (("AER", "Download the current PLAR Table A2 PDF"),
                                         ("Alberta", "Review the current PLAR Table A1")):
                with self.subTest(fields=fields, regulator=regulator):
                    output = self.root / f"confirmed-{index}-{regulator}.md"
                    run_review(self.pdf, output, {**self.scenario, **fields, "regulator": regulator},
                               self.catalogue)
                    self.assertIn(expected, output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
