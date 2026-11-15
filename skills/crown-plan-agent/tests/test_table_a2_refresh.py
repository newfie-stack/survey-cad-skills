"""Synthetic pre-review refresh orchestration tests."""
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from table_a2_refresh import refresh_table_a2
import fitz

PAGE = "https://www.alberta.ca/public-lands-administration-regulation"
PDF = "https://open.alberta.ca/dataset/synthetic/resource/test/download/plar-a2.pdf"


class RefreshTests(unittest.TestCase):
    def setUp(self):
        validator = patch("official_pdf_cache._validate_table_a2")
        validator.start()
        self.addCleanup(validator.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        doc = fitz.open()
        doc.new_page()
        self.data = doc.tobytes()
        doc.close()

    def test_refresh_from_unique_link(self):
        result = refresh_table_a2(self.temp.name,
            fetch_html=lambda _: '<a href="' + PDF + '">PLAR Table A2</a>',
            fetch_pdf=lambda _: self.data)
        self.assertEqual(result["refresh_status"], "CHECKED_OFFICIAL_SOURCE")
        self.assertEqual(result["regulatory_currency"], "NOT_VERIFIED")
        self.assertTrue((Path(self.temp.name) / "plar_table_a2.pdf").exists())

    def test_intermediate_page_fails_closed(self):
        result = refresh_table_a2(self.temp.name,
            fetch_html=lambda _: '<a href="https://open.alberta.ca/publications/a2">PLAR Table A2</a>')
        self.assertEqual(result["refresh_status"], "UNRESOLVED_SOURCE")
        self.assertFalse(result["cached_pdf_available"])

    def test_two_hop_official_publication(self):
        publication = "https://open.alberta.ca/publications/public-lands-administration-regulation-plar-table-a2-alberta-energy-regulator-aer"
        listing = '<a href="' + publication + '">PLAR Table A2</a>'
        detail = '<a href="' + PDF + '">Download PDF</a>'
        result = refresh_table_a2(
            self.temp.name,
            fetch_html=lambda url: listing if url == PAGE else detail,
            fetch_pdf=lambda _: self.data)
        self.assertEqual(result["refresh_status"], "CHECKED_OFFICIAL_SOURCE")

    def test_two_hop_multiple_pdfs_fails_closed(self):
        publication = "https://open.alberta.ca/publications/public-lands-administration-regulation-plar-table-a2-alberta-energy-regulator-aer"
        listing = '<a href="' + publication + '">PLAR Table A2</a>'
        detail = ('<a href="' + PDF + '">PDF</a>'
                  '<a href="https://open.alberta.ca/dataset/x/resource/y/download/other.pdf">Other</a>')
        result = refresh_table_a2(
            self.temp.name,
            fetch_html=lambda url: listing if url == PAGE else detail,
            fetch_pdf=lambda _: self.data)
        self.assertEqual(result["refresh_status"], "UNRESOLVED_SOURCE")

    def test_ambiguous_direct_links_do_not_fallback_to_publication(self):
        publication = "https://open.alberta.ca/publications/a2"
        listing = ('<a href="' + PDF + '">PLAR Table A2</a>'
                   '<a href="https://open.alberta.ca/dataset/other/resource/other/download/a2.pdf">PLAR Table A2</a>'
                   '<a href="' + publication + '">PLAR Table A2</a>')
        result = refresh_table_a2(self.temp.name,
                                  fetch_html=lambda _: listing,
                                  fetch_pdf=lambda _: self.data)
        self.assertEqual(result["refresh_status"], "UNRESOLVED_SOURCE")
        self.assertFalse((Path(self.temp.name) / "plar_table_a2.pdf").exists())

    def test_pinned_official_url_bypasses_blocked_listing(self):
        result = refresh_table_a2(
            self.temp.name, pinned_url=PDF,
            fetch_html=lambda _: (_ for _ in ()).throw(OSError("403")),
            fetch_pdf=lambda _: self.data)
        self.assertEqual(result["refresh_status"], "CHECKED_OFFICIAL_SOURCE")
        self.assertEqual(result["regulatory_currency"], "NOT_VERIFIED")

    def test_pinned_lookalike_url_is_rejected(self):
        result = refresh_table_a2(
            self.temp.name,
            pinned_url="https://open.alberta.ca.evil.example/a2.pdf",
            fetch_pdf=lambda _: self.data)
        self.assertEqual(result["refresh_status"], "UNRESOLVED_SOURCE")

    def test_stale_cache_is_flagged(self):
        refresh_table_a2(self.temp.name,
            fetch_html=lambda _: '<a href="' + PDF + '">PLAR Table A2</a>',
            fetch_pdf=lambda _: self.data)
        result = refresh_table_a2(self.temp.name, fetch_html=lambda _: "")
        self.assertTrue(result["cached_pdf_available"])
        self.assertEqual(result["regulatory_currency"], "NOT_VERIFIED")


if __name__ == "__main__":
    unittest.main()
