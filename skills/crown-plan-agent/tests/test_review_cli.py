"""Synthetic offline CLI integration, no client plans."""
import json
import io
import sys
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from review_cli import main, run_review

try:
    import fitz
except ImportError:
    fitz = None


@unittest.skipUnless(fitz is not None, "PyMuPDF unavailable")
class ReviewCLITests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.pdf = self.root / "synthetic.pdf"
        document = fitz.open()
        page = document.new_page()
        page.insert_text((50, 50), "SCALE 1:5000")
        page.insert_text((50, 65), "TOTAL AREA: 0.200 ha")
        document.save(str(self.pdf))
        document.close()
        self.scenario = {"land_class": "alberta_crown", "plan_type": "sketch", "activity": "PLA",
                         "stage": "initial", "regulator": "AER",
                         "purpose": "synthetic"}
        self.output = self.root / "review.md"
        self.catalogue = Path(__file__).resolve().parents[1] / "engine" / "candidate_requirements.json"

    def test_end_to_end_report(self):
        run_review(self.pdf, self.output, self.scenario, self.catalogue)
        result = self.output.read_text(encoding="utf-8")
        self.assertIn("OBSERVED_CANDIDATE", result)
        self.assertIn("Section: 1.2.2.3", result)
        self.assertIn("Section: 1.3.1.1", result)
        self.assertIn("VISUAL_CHECK_REQUIRED", result)
        self.assertIn("REVIEW_REQUIRED", result)
        self.assertTrue(self.pdf.exists())

    def test_provincial_review_requests_manual_table_a1_review(self):
        run_review(self.pdf, self.output, {**self.scenario, "regulator": " Alberta "},
                   self.catalogue)
        result = self.output.read_text(encoding="utf-8")
        self.assertIn("PLAR Table A1 manual review", result)
        self.assertIn("Review the current PLAR Table A1", result)
        self.assertIn("REVIEW_REQUIRED", result)
        self.assertNotIn("PLAR Table A2 disposition verification", result)
        self.assertNotIn("Download the current PLAR Table A2 PDF", result)

    def test_unknown_regulator_requires_confirmation_before_source_selection(self):
        for regulator in (None, "unsupported"):
            with self.subTest(regulator=regulator):
                output = self.root / f"unknown-{regulator}.md"
                scenario = {**self.scenario, "regulator": regulator}
                run_review(self.pdf, output, scenario, self.catalogue)
                result = output.read_text(encoding="utf-8")
                self.assertIn("Confirm the regulator before selecting the applicable PLAR table", result)
                self.assertNotIn("PLAR Table A2 disposition verification", result)
                self.assertNotIn("Download the current PLAR Table A2 PDF", result)

    def test_direct_non_aer_a2_input_is_rejected_before_extraction(self):
        with patch("review_cli.extract_pdf") as extract:
            with self.assertRaises(ValueError):
                run_review(self.pdf, self.output, {**self.scenario, "regulator": "Alberta"},
                           self.catalogue, a2_pdf=self.pdf)
        extract.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_non_aer_cli_ignores_cached_a2(self):
        cache = self.root / "references"
        cache.mkdir()
        (cache / "plar_table_a2.pdf").write_bytes(b"synthetic-unused-cache")
        for regulator, expected in (("Alberta", "Review the current PLAR Table A1"),
                                     ("unsupported", "Confirm the regulator"),
                                     (None, "Confirm the regulator")):
            with self.subTest(regulator=regulator):
                scenario_path = self.root / f"scenario-{regulator}.json"
                scenario_path.write_text(json.dumps({**self.scenario, "regulator": regulator}),
                                         encoding="utf-8")
                output = self.root / f"cached-{regulator}.md"
                stdout = io.StringIO()
                with patch("review_cli.extract_a2_rows", return_value=[]) as extract, \
                        patch("review_cli.refresh_table_a2") as refresh, redirect_stdout(stdout):
                    self.assertEqual(main([str(self.pdf), "--scenario", str(scenario_path),
                                           "--reference-cache", str(cache), "--output", str(output)]), 0)
                result = output.read_text(encoding="utf-8")
                self.assertIn(expected, result)
                self.assertIn(expected, stdout.getvalue())
                self.assertNotIn("PLAR Table A2 disposition verification", result)
                extract.assert_not_called()
                refresh.assert_not_called()

    def test_non_aer_explicit_a2_flags_are_rejected_before_extraction_or_refresh(self):
        cache = self.root / "references"
        cache.mkdir()
        (cache / "plar_table_a2.pdf").write_bytes(b"synthetic-unused-cache")
        for regulator in ("Alberta", "unsupported", None):
            for index, flags in enumerate((
                    ["--table-a2-pdf", str(self.pdf)], ["--refresh-table-a2"],
                    ["--table-a2-url", "https://www.alberta.ca/synthetic-table-a2.pdf"])):
                with self.subTest(regulator=regulator, flags=flags):
                    scenario_path = self.root / f"flags-{regulator}.json"
                    scenario_path.write_text(json.dumps({**self.scenario, "regulator": regulator}),
                                             encoding="utf-8")
                    output = self.root / f"flags-{regulator}-{index}.md"
                    with patch("review_cli.extract_pdf", return_value={"spans": []}) as extract, \
                            patch("review_cli.extract_a2_rows", return_value=[]) as a2_extract, \
                            patch("review_cli.refresh_table_a2", return_value={
                                "refresh_status": "CHECKED_OFFICIAL_SOURCE"}) as refresh, \
                            redirect_stderr(io.StringIO()):
                        with self.assertRaises(SystemExit):
                            main([str(self.pdf), "--scenario", str(scenario_path),
                                  "--reference-cache", str(cache), "--output", str(output), *flags])
                    self.assertFalse(output.exists())
                    extract.assert_not_called()
                    a2_extract.assert_not_called()
                    refresh.assert_not_called()

    def test_amendment_report_cites_survey_scope(self):
        scenario = {**self.scenario, "stage": "amendment", "activity": "LOC",
                    "existing_plan_type": "survey_plan", "existing_length_m": 7200,
                    "affected_quarter_sections": 2}
        run_review(self.pdf, self.output, scenario, self.catalogue)
        result = self.output.read_text(encoding="utf-8")
        self.assertIn("Survey scope: ITEMIZED_SURVEY_CANDIDATE", result)
        self.assertIn("Comparison: ITEMIZED_SKETCH_CONFLICT", result)
        self.assertIn("section 3.3.2, page 11", result)
        self.assertIn("Confirm OneStop Add eligibility separately", result)

    def test_renewal_report_identifies_plan_on_file_and_source_row(self):
        scenario = {**self.scenario, "stage": "renewal", "activity": "PLA",
                    "purpose": "Pipeline", "subactivity": "Above Ground",
                    "existing_plan_type": "survey_plan", "disposition_changed": False}
        row = {"disposition": "PLA", "purpose": "Pipeline", "activity": "Above Ground",
               "row": 56, "page": 9, "required_plan": "Survey", "survey_monuments": "1/4"}
        with patch("review_cli.extract_a2_rows", return_value=[row]):
            run_review(self.pdf, self.output, scenario, self.catalogue, a2_pdf=self.pdf)
        result = self.output.read_text(encoding="utf-8")
        self.assertIn("Plan type on file: survey_plan", result)
        self.assertIn("Comparison: MATCHES_TABLE_A2", result)
        self.assertIn("Row: 56", result)
        self.assertIn("Compliance: NOT_ASSESSED", result)

    def test_heading_and_applicant_evidence_remains_review_only(self):
        with fitz.open(str(self.pdf)) as document:
            page = document[0]
            page.insert_text((50, 90), "SURVEYOR SKETCH")
            page.insert_text((50, 110), "Applicant: Fictional Survey Client Ltd.")
            page.insert_text((50, 130), "Fictional County")
            page.insert_text((50, 150), "WITHIN NE 12-34-5 W6M")
            document.saveIncr()
        scenario = {**self.scenario, "plan_type": "surveyor_sketch",
                    "applicant_name": "Fictional Survey Client Ltd.",
                    "municipality_name": "Another County"}
        run_review(self.pdf, self.output, scenario, self.catalogue)
        result = self.output.read_text(encoding="utf-8")
        for rule in ("PLAN-HEADING", "APPLICANT"):
            self.assertRegex(result, rf"CANDIDATE-{rule} \|[^\n]+OBSERVED_CANDIDATE \| 1")
        self.assertRegex(result, r"CANDIDATE-MUNICIPALITY \|[^\n]+UNKNOWN")
        self.assertRegex(result, r"CANDIDATE-LEGAL-DESCRIPTION \|[^\n]+VISUAL_CHECK_REQUIRED")
        self.assertRegex(result, r"CANDIDATE-LEGEND \|[^\n]+VISUAL_CHECK_REQUIRED")
        self.assertIn("Section: 1.2.1.1", result)
        self.assertIn("Section: 1.2.2.1", result)
        self.assertIn("Section: 1.2.3.1", result)

    def test_title_text_matching_rejects_partial_names_and_wrong_plan_type(self):
        with fitz.open(str(self.pdf)) as document:
            page = document[0]
            page.insert_text((50, 90), "SURVEYOR SKETCH")
            page.insert_text((50, 110), "Applicant: Fictional Survey Client Ltd. Holdings")
            document.saveIncr()
        scenario = {**self.scenario, "applicant_name": "Fictional Survey Client Ltd."}
        run_review(self.pdf, self.output, scenario, self.catalogue)
        result = self.output.read_text(encoding="utf-8")
        for rule in ("PLAN-HEADING", "APPLICANT"):
            self.assertRegex(result, rf"CANDIDATE-{rule} \|[^\n]+UNKNOWN")

    def test_conflicting_plan_headings_remain_unresolved(self):
        with fitz.open(str(self.pdf)) as document:
            document[0].insert_text((50, 90), "SKETCH")
            document[0].insert_text((50, 110), "SURVEY")
            document.saveIncr()
        run_review(self.pdf, self.output, self.scenario, self.catalogue)
        result = self.output.read_text(encoding="utf-8")
        self.assertRegex(result, r"CANDIDATE-PLAN-HEADING \|[^\n]+UNKNOWN")
        self.assertIn("Multiple different plan-type labels found", result)

    def test_plan_showing_heading_is_recognized(self):
        with fitz.open(str(self.pdf)) as document:
            document[0].insert_text((50, 90), "SKETCH PLAN SHOWING:")
            document[0].insert_text((50, 110), "SURVEY PLAN NO. 1234")
            document.saveIncr()
        run_review(self.pdf, self.output, self.scenario, self.catalogue)
        result = self.output.read_text(encoding="utf-8")
        self.assertRegex(result, r"CANDIDATE-PLAN-HEADING \|[^\n]+OBSERVED_CANDIDATE")

    def test_total_area_excludes_component_areas_and_requires_hectares(self):
        with fitz.open(str(self.pdf)) as document:
            page = document[0]
            page.add_redact_annot(fitz.Rect(40, 55, 200, 72))
            page.apply_redactions()
            page.insert_text((50, 90), "AREA WITHIN EXISTING DISPOSITIONS: 0.100 ha")
            page.insert_text((50, 110), "TOTAL AREA: 3000 m2")
            page.insert_text((50, 130), "TOTAL ACTIVITY AREA: 0.300 ha")
            document.saveIncr()
        run_review(self.pdf, self.output, self.scenario, self.catalogue)
        result = self.output.read_text(encoding="utf-8")
        self.assertRegex(result, r"CANDIDATE-TOTAL-AREA \|[^\n]+OBSERVED_CANDIDATE")
        self.assertIn("Observation: TOTAL ACTIVITY AREA: 0.300 ha", result)
        self.assertRegex(result, r"CANDIDATE-ACTIVITY-OUTLINE \|[^\n]+VISUAL_CHECK_REQUIRED")
        self.assertRegex(result, r"CANDIDATE-NEARBY-INTERESTS \|[^\n]+VISUAL_CHECK_REQUIRED")

    def test_conflicting_total_area_values_remain_unresolved(self):
        with fitz.open(str(self.pdf)) as document:
            page = document[0]
            page.insert_text((50, 90), "TOTAL AREA: 0.300 ha")
            page.insert_text((50, 110), "TOTAL AREA: 0.400 ha")
            document.saveIncr()
        run_review(self.pdf, self.output, self.scenario, self.catalogue)
        result = self.output.read_text(encoding="utf-8")
        self.assertRegex(result, r"CANDIDATE-TOTAL-AREA \|[^\n]+UNKNOWN")
        self.assertIn("Conflicting total area values", result)

    def test_total_area_in_a_measurement_table(self):
        def add_table(page, *, second_value=False):
            for position, label in [
                ((307, 120), "Total"), ((285, 135), "ha."),
                ((340, 135), "ac."), ((200, 135), "Within (ha.)"),
                ((284, 150), "2.400"), ((339, 150), "5.931"),
                ((200, 150), "1.500"),
            ]:
                page.insert_text(position, label, fontsize=9)
            if second_value:
                page.insert_text((284, 165), "3.400", fontsize=9)
        for ambiguous in (False, True):
            with self.subTest(ambiguous=ambiguous), fitz.open() as document:
                source = self.root / f"table-{ambiguous}.pdf"
                report = self.root / f"table-{ambiguous}.md"
                add_table(document.new_page(), second_value=ambiguous)
                document.save(source)
                survey = {"coordinate_source": "EXPLICIT_SURVEY_COORDINATES",
                          "crs_identifier": "SYNTHETIC_METRIC", "crs_verified": True,
                          "closed_ring": True,
                          "vertices": [[0, 0], [200, 0], [200, 120], [0, 120], [0, 0]],
                          "area_label": {"source": "table_total", "page": 1,
                                         "text": "2.400", "tolerance_ha": 0}}
                run_review(source, report, self.scenario, self.catalogue, survey_geometry=survey)
                result = report.read_text(encoding="utf-8")
                if ambiguous:
                    self.assertRegex(result, r"CANDIDATE-TOTAL-AREA \|[^\n]+UNKNOWN")
                    self.assertIn("Comparison: AREA_LABEL_UNRESOLVED", result)
                else:
                    self.assertRegex(result, r"CANDIDATE-TOTAL-AREA \|[^\n]+OBSERVED_CANDIDATE")
                    self.assertIn("Observation: 2.400 ha (Total column)", result)
                    self.assertIn("Comparison: WITHIN_SUPPLIED_TOLERANCE", result)
                    self.assertIn("Selected evidence: Measurement table hectare total", result)
                    survey["area_label"]["text"] = "5.931"
                    wrong_cell_report = self.root / "wrong-table-cell.md"
                    run_review(source, wrong_cell_report, self.scenario, self.catalogue,
                               survey_geometry=survey)
                    self.assertIn("Comparison: AREA_LABEL_UNRESOLVED",
                                  wrong_cell_report.read_text(encoding="utf-8"))
                    self.assertNotIn("Observation: 5.931 ha", result)
                    self.assertNotIn("Observation: 1.500 ha", result)

    def test_scale_bar_numbers_and_scale_notes_do_not_count_as_numerical_scale(self):
        with fitz.open(str(self.pdf)) as document:
            document[0].add_redact_annot(fitz.Rect(40, 30, 150, 55))
            document[0].apply_redactions()
            document[0].insert_text((50, 90), "NOT TO SCALE")
            document[0].insert_text((50, 110), "Scale bar: 0 10 20 m")
            document.saveIncr()
        run_review(self.pdf, self.output, self.scenario, self.catalogue)
        result = self.output.read_text(encoding="utf-8")
        self.assertIn("| CANDIDATE-PLAN-SCALE |", result)
        self.assertNotIn("OBSERVED_CANDIDATE", result)
        self.assertIn("VISUAL_CHECK_REQUIRED", result)

    def test_no_overwrite(self):
        self.output.write_text("existing", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            run_review(self.pdf, self.output, self.scenario, self.catalogue)
        self.assertEqual(self.output.read_text(), "existing")

    def test_drawing_text_presence_is_independent_of_table_and_purpose(self):
        with fitz.open(str(self.pdf)) as document:
            document[0].insert_text((50, 80), "REFERENCE: PIL 123456")
            document.saveIncr()
        scenario = {**self.scenario, "activity": "PIL", "disposition": "pil"}
        run_review(self.pdf, self.output, scenario, self.catalogue)
        result = self.output.read_text(encoding="utf-8")
        self.assertIn("DISPOSITION_OBSERVED_IN_DRAWING_TEXT", result)
        self.assertIn("PDF page 1", result)
        self.assertNotIn("Optional Table A2 plan requirement", result)

    def test_drawing_text_export_does_not_match_code_inside_words(self):
        export = self.root / "drawing.txt"
        export.write_text("LOCATION\nXLOC123\n", encoding="utf-8")
        scenario = {**self.scenario, "activity": "LOC"}
        run_review(self.pdf, self.output, scenario, self.catalogue, drawing_text=export)
        result = self.output.read_text(encoding="utf-8")
        self.assertIn("DISPOSITION_NOT_OBSERVED_IN_DRAWING_TEXT", result)
        self.assertIn("REVIEW_REQUIRED", result)

    def test_cli_uses_local_table_without_network_and_reports_both_checks(self):
        export = self.root / "drawing.txt"
        export.write_text("LOCATION\nLOC 123456\n", encoding="utf-8")
        source = self.root / "uploaded-table-a2.pdf"
        source.touch()
        scenario_path = self.root / "scenario.json"
        scenario_path.write_text(json.dumps({**self.scenario, "activity": "LOC"}),
                                 encoding="utf-8")
        rows = [{"disposition": "LOC", "row": 51, "page": 8}]
        with patch("review_cli.extract_a2_rows", return_value=rows) as extract, \
                patch("review_cli.refresh_table_a2") as refresh:
            main([str(self.pdf), "--scenario", str(scenario_path),
                  "--table-a2-pdf", str(source), "--drawing-text", str(export),
                  "--output", str(self.output)])
        refresh.assert_not_called()
        extract.assert_called_once_with(source)
        result = self.output.read_text(encoding="utf-8")
        self.assertIn("DISPOSITION_FOUND", result)
        self.assertIn("DISPOSITION_OBSERVED_IN_DRAWING_TEXT", result)
        self.assertIn("Export line 2", result)
        self.assertIn("Source currency: UNVERIFIED", result)

    def test_default_cli_requests_upload_when_table_is_missing(self):
        scenario_path = self.root / "scenario.json"
        scenario_path.write_text(json.dumps(self.scenario), encoding="utf-8")
        with patch("review_cli.refresh_table_a2") as refresh:
            main([str(self.pdf), "--scenario", str(scenario_path),
                  "--reference-cache", str(self.root / "empty"), "--output", str(self.output)])
        refresh.assert_not_called()
        self.assertIn("Download the current PLAR Table A2 PDF",
                      self.output.read_text(encoding="utf-8"))

    def test_cli_entrypoint(self):
        scenario_path = self.root / "scenario.json"
        scenario_path.write_text(json.dumps(self.scenario), encoding="utf-8")
        self.assertEqual(main([str(self.pdf), "--offline", "--scenario", str(scenario_path),
                               "--output", str(self.output)]), 0)
        self.assertTrue(self.output.exists())

    def test_cli_with_separate_survey_geometry(self):
        scenario_path = self.root / "scenario.json"
        scenario_path.write_text(json.dumps(self.scenario), encoding="utf-8")
        survey_path = self.root / "survey.json"
        survey = {"coordinate_source": "EXPLICIT_SURVEY_COORDINATES",
                  "crs_identifier": "SYNTHETIC_PROJECTED_METRIC",
                  "crs_verified": True, "closed_ring": True,
                  "area_label": {"page": 1, "text": "TOTAL AREA: 0.200 ha", "tolerance_ha": 0},
                  "vertices": [[500000, 5600000], [500100, 5600000],
                               [500100, 5600020], [500000, 5600020],
                               [500000, 5600000]]}
        survey_path.write_text(json.dumps(survey), encoding="utf-8")
        main([str(self.pdf), "--offline", "--scenario", str(scenario_path),
              "--survey-geometry", str(survey_path), "--output", str(self.output)])
        result = self.output.read_text(encoding="utf-8")
        self.assertIn("Polygon area (m²): 2000", result)
        self.assertIn("Comparison: WITHIN_SUPPLIED_TOLERANCE", result)
        self.assertRegex(result, r"CANDIDATE-TOTAL-AREA \|[^\n]+OBSERVED_CANDIDATE")
        self.assertIn("explicit survey coordinates", result)

    def test_cli_rejects_pdf_coordinates_as_survey(self):
        scenario_path = self.root / "scenario.json"
        scenario_path.write_text(json.dumps(self.scenario), encoding="utf-8")
        survey_path = self.root / "survey.json"
        survey_path.write_text(json.dumps({
            "coordinate_source": "PDF_PAGE_POINTS",
            "crs_identifier": "NOT_SURVEY", "crs_verified": False,
            "closed_ring": False, "vertices": [[0,0],[1,0],[1,1]]
        }), encoding="utf-8")
        with self.assertRaises(ValueError):
            main([str(self.pdf), "--offline", "--scenario", str(scenario_path),
                  "--survey-geometry", str(survey_path), "--output", str(self.output)])
        self.assertFalse(self.output.exists())

    def test_explicit_refresh_runs_before_review(self):
        cache = self.root / "references"
        cache.mkdir()
        (cache / "plar_table_a2.pdf").write_bytes(b"mocked-by-extractor")
        scenario_path = self.root / "scenario.json"
        scenario_path.write_text(json.dumps(self.scenario), encoding="utf-8")
        with patch("review_cli.extract_a2_rows", return_value=[]), patch("review_cli.refresh_table_a2", return_value={
            "refresh_status": "CHECKED_OFFICIAL_SOURCE"}) as refresh:
            self.assertEqual(main([str(self.pdf), "--refresh-table-a2", "--scenario", str(scenario_path),
                                   "--reference-cache", str(self.root / "references"),
                                   "--output", str(self.output)]), 0)
        refresh.assert_called_once()
        self.assertTrue(self.output.exists())

    def test_successful_refresh_without_pdf_blocks_report(self):
        scenario_path = self.root / "scenario.json"
        scenario_path.write_text(json.dumps(self.scenario), encoding="utf-8")
        with patch("review_cli.refresh_table_a2", return_value={
            "refresh_status": "CHECKED_OFFICIAL_SOURCE"}):
            with self.assertRaises(SystemExit):
                main([str(self.pdf), "--refresh-table-a2", "--scenario", str(scenario_path),
                      "--reference-cache", str(self.root / "references"),
                      "--output", str(self.output)])
        self.assertFalse(self.output.exists())

    def test_conflicting_disposition_fields_fail_closed(self):
        scenario = {**self.scenario, "disposition": "LOC"}
        with patch("review_cli.extract_a2_rows", return_value=[]):
            with self.assertRaises(ValueError):
                run_review(self.pdf, self.output, scenario, self.catalogue,
                           a2_pdf=self.pdf)
        self.assertFalse(self.output.exists())

    def test_unresolved_refresh_blocks_review(self):
        scenario_path = self.root / "scenario.json"
        scenario_path.write_text(json.dumps(self.scenario), encoding="utf-8")
        with patch("review_cli.refresh_table_a2", return_value={
            "refresh_status": "UNRESOLVED_SOURCE", "reason": "ambiguous"}):
            with self.assertRaises(SystemExit):
                main([str(self.pdf), "--refresh-table-a2", "--scenario", str(scenario_path),
                      "--reference-cache", str(self.root / "references"),
                      "--output", str(self.output)])
        self.assertFalse(self.output.exists())

    def test_reject_wrong_output_extension(self):
        with self.assertRaises(ValueError):
            run_review(self.pdf, self.root / "report.pdf", self.scenario, self.catalogue)


if __name__ == "__main__":
    unittest.main()
