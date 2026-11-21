"""Replay independently labelled invented PDFs through combined and CLI paths."""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "engine"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clause_schema import load_clause_catalogue
from clause_evidence_examples import CASE_IDS, make_example
from regulatory_evidence import review_regulatory_evidence

TRUTH = json.loads((Path(__file__).resolve().parent / "fixtures/clause_evidence_truth.json").read_text())


class CombinedClauseEvidenceExamplesTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.catalogue_path = SKILL / "engine/dated_clause_catalogue.json"
        self.catalogue = load_clause_catalogue(self.catalogue_path)

    def test_generator_and_independent_oracle_cover_the_same_cases(self):
        self.assertEqual(set(CASE_IDS), set(TRUTH["cases"]))
        self.assertEqual(len(CASE_IDS), 18)

    def test_actual_combined_pdf_csv_results_match_independent_truth(self):
        for case_id, truth in TRUTH["cases"].items():
            with self.subTest(case=case_id):
                files = make_example(self.root / case_id, case_id)
                before = files["pdf"].read_bytes()
                spec = json.loads(files["spec"].read_text())
                scenario = json.loads(files["scenario"].read_text())
                facts = json.loads(files["facts"].read_text())
                call = lambda: review_regulatory_evidence(
                    files["pdf"], scenario, self.catalogue, facts, spec,
                    point_export=files["point_export"])
                if "expected_error" in truth:
                    with self.assertRaisesRegex(ValueError, re.escape(truth["expected_error"])):
                        call()
                    continue
                report = call()
                actual = {item["workbook_check_id"]: item["mechanical_status"]
                          for item in report["observations"]}
                expected = {qid: truth["overrides"].get(qid, TRUTH["default_observation_status"])
                            for qid in TRUTH["question_ids"]}
                self.assertEqual(actual, expected)
                self.assertEqual(report["source_sha256"], hashlib.sha256(before).hexdigest())
                self.assertEqual(files["pdf"].read_bytes(), before)
                self.assertEqual(report["overall_status"], "REVIEW_REQUIRED")
                self.assertTrue(all(item["source_status"] == "UNVERIFIED_CURRENT"
                                    and item["status"] == "REVIEW_REQUIRED"
                                    and item["residual_review"] for item in report["observations"]))
                export = report["point_export_comparison"]
                if truth["export_status"] is None:
                    self.assertIsNone(export)
                else:
                    self.assertEqual(export["mechanical_status"], truth["export_status"])
                    self.assertEqual(export["regulatory_status"], "REVIEW_REQUIRED")
                    self.assertEqual(export["source_sha256"],
                                     hashlib.sha256(files["point_export"].read_bytes()).hexdigest())
                    if truth.get("export_reason"):
                        self.assertIn(truth["export_reason"], [f["reason_code"] for f in export["findings"]])

    def test_full_offline_cli_replays_same_sources_and_keeps_authority_open(self):
        for case_id, truth in TRUTH["cases"].items():
            with self.subTest(case=case_id):
                files = make_example(self.root / case_id, case_id)
                output = files["pdf"].parent / "review.md"
                command = [sys.executable, str(SKILL / "engine/review_cli.py"), str(files["pdf"]),
                           "--scenario", str(files["scenario"]), "--clause-catalogue", str(self.catalogue_path),
                           "--clause-facts", str(files["facts"]), "--regulatory-evidence-spec", str(files["spec"]),
                           "--reference-cache", str(self.root / "empty-cache"), "--offline", "--output", str(output)]
                if files["point_export"] is not None:
                    command.extend(["--point-export", str(files["point_export"])])
                result = subprocess.run(command, cwd=self.root, capture_output=True, text=True, timeout=60)
                if "expected_error" in truth:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(truth["expected_error"], result.stderr)
                    self.assertFalse(output.exists())
                    continue
                self.assertEqual(result.returncode, 0, result.stderr)
                markdown = output.read_text()
                self.assertIn("Executed dated-clause evidence", markdown)
                self.assertIn("every regulatory verdict remains REVIEW_REQUIRED", markdown)
                for qid in TRUTH["question_ids"]:
                    status = truth["overrides"].get(qid, TRUTH["default_observation_status"])
                    pattern = (r"\| " + re.escape(qid) +
                               r" \| CANDIDATE_REVIEW \| (?:EXECUTED|BLOCKED) \| " + status + r" \|")
                    self.assertIsNotNone(re.search(pattern, markdown), f"{case_id}: missing {qid} {status} row")
                if truth["export_status"] is not None:
                    self.assertTrue("Mechanical result: " + truth["export_status"] in markdown,
                                    f"{case_id}: missing CSV {truth['export_status']} result")
                    self.assertIn("native DWG/SHP", markdown)
                self.assertIn("UNVERIFIED_CURRENT", markdown)
                self.assertIn("Download the current PLAR Table A2 PDF", markdown)

    def test_synthesis_has_stable_source_bytes_and_preserves_declared_input_fields(self):
        a = make_example(self.root / "one", "clean_exact_10km")
        b = make_example(self.root / "two", "clean_exact_10km")
        for key in ("pdf", "point_export", "spec", "scenario", "facts"):
            self.assertEqual(a[key].read_bytes(), b[key].read_bytes(), key)
        spec = json.loads(a["spec"].read_text())
        self.assertEqual(spec["hybrid_table"]["rows"][2]["easting"]["bbox_points"], [336, 413, 485, 429])
        self.assertEqual(spec["point_export"]["format"], "CSV_POINT_EXPORT")
        self.assertEqual(spec["point_export"]["coordinate_frame_id"],
                         spec["hybrid_table"]["coordinate_frame_id"])


if __name__ == "__main__":
    unittest.main()
