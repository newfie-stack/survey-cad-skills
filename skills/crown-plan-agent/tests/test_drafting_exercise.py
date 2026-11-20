from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pymupdf as fitz

from export_drafting_exercise import export_exercise


class DraftingExerciseTests(unittest.TestCase):
    def test_export_writes_blind_review_inputs_and_checksums(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "exercise"
            case_id = "msl_multiple_errors"
            manifest = export_exercise(output, case_id)

            self.assertEqual({path.name for path in output.iterdir()},
                             {"exercise-manifest.json", "review_inputs"})
            review_inputs = output / "review_inputs"
            self.assertEqual({path.name for path in review_inputs.iterdir()},
                             {"plan.pdf", "job-brief.md", "REVIEW.md"})
            with fitz.open(review_inputs / "plan.pdf") as document:
                self.assertEqual(len(document), 2)
                self.assertEqual(document.embfile_names(), [])
                plan_text = "\n".join(page.get_text() for page in document)
                plan_metadata = json.dumps(document.metadata)
            self.assertIn("MSL910842", plan_text)
            self.assertIn("MSL910842", (review_inputs / "job-brief.md").read_text(encoding="utf-8"))
            reviewer_text = "\n".join(
                (review_inputs / name).read_text(encoding="utf-8") for name in ("job-brief.md", "REVIEW.md")
            )
            for token in (case_id, "bbox_points", "coverage_review", "expected_denominator",
                          "known_defects", "REVIEW_REQUIRED", "grading.json", "truth.json", "checks.json"):
                self.assertNotIn(token, plan_text + plan_metadata + reviewer_text)

            expected_hashes = {
                name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                for name in ("review_inputs/plan.pdf", "review_inputs/job-brief.md", "review_inputs/REVIEW.md")
            }
            expected_manifest = {
                "schema_version": 1,
                "evidence_class": "WHOLLY_INVENTED_SYNTHETIC",
                "case_id": case_id,
                "files": expected_hashes,
            }
            manifest_file = output / "exercise-manifest.json"
            self.assertEqual(json.loads(manifest_file.read_text(encoding="utf-8")), expected_manifest)
            self.assertEqual(manifest, expected_manifest)

    def test_existing_output_directory_preserves_original_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "exercise"
            export_exercise(output, "loc_clean")
            pdf = output / "review_inputs" / "plan.pdf"
            original = pdf.read_bytes()

            with self.assertRaises(FileExistsError):
                export_exercise(output, "msl_rotated_clean")

            self.assertEqual(pdf.read_bytes(), original)

    def test_unknown_case_leaves_no_output_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "exercise"

            with self.assertRaises(ValueError):
                export_exercise(output, "unknown")

            self.assertFalse(output.exists())

    def test_cli_prints_only_manifest_location(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "exercise"
            script = Path(__file__).with_name("export_drafting_exercise.py")

            result = subprocess.run(
                [sys.executable, str(script), "--output", str(output), "--case", "loc_total_conflict"],
                capture_output=True, text=True, check=True,
            )

            manifest = output / "exercise-manifest.json"
            self.assertEqual(result.stdout.strip(), str(manifest))
            self.assertTrue(manifest.is_file())


if __name__ == "__main__":
    unittest.main()
