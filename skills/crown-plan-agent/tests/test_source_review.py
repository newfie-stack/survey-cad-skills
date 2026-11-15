"""Public-source citation structural tests, not regulatory approval."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from source_review import review_source_record


class SourceReviewTests(unittest.TestCase):
    def setUp(self):
        self.record = {"publication_title": "Synthetic guidance", "section": "1.1",
                       "version_date": "2024-05-30", "accessed_on": "2026-11-14",
                       "source_url": "https://open.alberta.ca/"}

    def test_complete_citation_still_requires_review(self):
        result = review_source_record(self.record)
        self.assertTrue(result["citation_complete"])
        self.assertEqual(result["source_status"], "REVIEW_REQUIRED")

    def test_missing_section(self):
        record = {**self.record, "section": ""}
        self.assertIn("section", review_source_record(record)["missing_or_invalid"])

    def test_reject_nonofficial_host(self):
        record = {**self.record, "source_url": "https://open.alberta.ca.example.com/"}
        self.assertIn("official_https_source", review_source_record(record)["missing_or_invalid"])

    def test_reject_http(self):
        record = {**self.record, "source_url": "http://open.alberta.ca/"}
        self.assertFalse(review_source_record(record)["citation_complete"])

    def test_reject_bad_date(self):
        record = {**self.record, "version_date": "2024-99-99"}
        self.assertIn("version_date_valid_iso_date", review_source_record(record)["missing_or_invalid"])


if __name__ == "__main__":
    unittest.main()
