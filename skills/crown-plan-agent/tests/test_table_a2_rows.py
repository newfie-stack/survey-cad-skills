"""Optional private-document integration test; no official PDF committed to GitHub."""
import os
import json
import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from table_a2_rows import extract_a2_rows
from table_a2_lookup import verify_disposition, lookup_plan_requirement
from official_pdf_cache import _validate_table_a2


class TableA2RowsTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("CROWN_A2_TEST_PDF"), "Set CROWN_A2_TEST_PDF to local official PDF")
    def test_official_pdf_to_report_integration(self):
        """Exercise real Table A2 extraction with a synthetic plan."""
        import tempfile
        import fitz
        from review_cli import main
        source = Path(os.environ["CROWN_A2_TEST_PDF"])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = root / "synthetic-plan.pdf"
            document = fitz.open()
            document.new_page().insert_text((60, 60), "SCALE 1:5000 - PIL123456")
            document.save(str(plan))
            document.close()
            output = root / "review.md"
            scenario = {"land_class": "alberta_crown", "plan_type": "sketch", "disposition": "PIL",
                        "purpose": "Pipeline Installation",
                        "subactivity": "Header or Riser Site",
                        "stage": "initial", "regulator": "AER"}
            scenario_path = root / "scenario.json"
            scenario_path.write_text(json.dumps(scenario), encoding="utf-8")
            self.assertEqual(main([str(plan), "--scenario", str(scenario_path),
                                   "--table-a2-pdf", str(source), "--output", str(output)]), 0)
            report = output.read_text(encoding="utf-8")
            self.assertIn("DISPOSITION_FOUND", report)
            self.assertIn("DISPOSITION_OBSERVED_IN_DRAWING_TEXT", report)
            self.assertIn("Evidence: PDF page 1", report)
            self.assertIn("Source currency: UNVERIFIED", report)
            self.assertIn("Row: 64", report)
            self.assertIn("Plan type: Surveyor Sketch", report)
            self.assertIn("Comparison: DIFFERS_FROM_TABLE_A2", report)
            self.assertIn("Consultation: ", report)
            self.assertIn("Compliance: NOT_ASSESSED", report)

    def test_unrelated_pdf_rejected_as_table_a2(self):
        import fitz
        document = fitz.open()
        document.new_page()
        data = document.tobytes()
        document.close()
        with self.assertRaises(ValueError):
            _validate_table_a2(data)

    @unittest.skipUnless(os.environ.get("CROWN_A2_TEST_PDF"), "Set CROWN_A2_TEST_PDF to local official PDF")
    def test_official_october_2026_pdf(self):
        source = Path(os.environ["CROWN_A2_TEST_PDF"])
        _validate_table_a2(source.read_bytes())
        rows = extract_a2_rows(source)
        self.assertEqual(len(rows), 135)
        expected = {
            51: ("LOC", "Pipeline", "Fresh Water", "Sketch"),
            56: ("PLA", "Pipeline", "Above Ground", "Survey"),
            60: ("PLA", "Pipeline", "PNG/OS Pipeline", "Survey"),
            64: ("PIL", "Pipeline Installation", "Header or Riser Site", "Surveyor Sketch"),
        }
        for number, fields in expected.items():
            row = rows[number-1]
            self.assertEqual(tuple(row[key] for key in
                             ("disposition", "purpose", "activity", "required_plan")), fields)
        self.assertIn("maintenance, monitoring or emergency activities", rows[63]["definition"])
        self.assertEqual(rows[-1]["row"], 135)
        from collections import Counter
        self.assertEqual(Counter(row["required_plan"] for row in rows),
                         {"Sketch": 75, "Surveyor Sketch": 43, "Survey": 9, "N/A": 8})
        self.assertEqual(Counter(row["disposition"] for row in rows),
                         {"LOC": 29, "RTF": 26, "MSL": 24, "MLL": 22,
                          "PIL": 10, "PLA": 6, "": 4, "MME": 3,
                          "RML": 3, "RSC": 3, "RVC": 2,
                          "CEP": 1, "OSE": 1, "RME": 1})
        for code in ("PLA", "PIL", "LOC", "RTF", "MSL"):
            self.assertEqual(verify_disposition(rows, code)["status"],
                             "DISPOSITION_FOUND")
        self.assertEqual(lookup_plan_requirement(rows, disposition="LOC",
            purpose="Pipeline", activity="Fresh Water")["required_plan"], "Sketch")

        for key, expected_values in {
            "rtf_approval": {"Yes": 34, "No": 101},
            "rtf_authorization": {"Yes": 35, "No": 100},
            "consultation": {"PA": 99, "N/A": 24, "N/A*": 7, "PA*": 2,
                             "AA": 1, "AA*": 1, "P/A": 1},
        }.items():
            self.assertEqual(Counter(row[key] for row in rows), expected_values)
        self.assertEqual({r["row"]: r["footnote"] for r in rows if r["footnote"] is not None},
                         {11: 1, 93: 2, 135: 3})
        source_fields = {"rtf_approval", "rtf_authorization", "consultation", "footnote"}
        original_columns = [{k: v for k, v in row.items() if k not in source_fields} for row in rows]
        fingerprint = hashlib.sha256(json.dumps(original_columns, sort_keys=True,
            ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
        self.assertEqual(fingerprint,
            "dbd7ec4c84fb30a934d451e20bd131b64cc1eef096856ba4adaa4b987bfe73de")


if __name__ == "__main__":
    unittest.main()
