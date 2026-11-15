"""Synthetic PDF cache tests, no network or private documents."""
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from official_pdf_cache import refresh_official_pdf
import fitz

URL = "https://open.alberta.ca/dataset/synthetic/resource/synthetic/download/table.pdf"


class OfficialPDFCacheTests(unittest.TestCase):
    def setUp(self):
        validator = patch("official_pdf_cache._validate_table_a2")
        validator.start()
        self.addCleanup(validator.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        document = fitz.open()
        document.new_page()
        self.pdf = document.tobytes()
        document.close()

    def test_download_then_unchanged(self):
        first = refresh_official_pdf(URL, self.temp.name, fetch=lambda _: self.pdf)
        second = refresh_official_pdf(URL, self.temp.name, fetch=lambda _: self.pdf)
        self.assertEqual(first["status"], "UPDATED")
        self.assertEqual(second["status"], "UNCHANGED")
        self.assertEqual(first["currency"], "NOT_VERIFIED")

    def test_new_version_keeps_old(self):
        first = refresh_official_pdf(URL, self.temp.name, fetch=lambda _: self.pdf)
        document = fitz.open()
        document.new_page()
        document.new_page()
        newer = document.tobytes()
        document.close()
        second = refresh_official_pdf(URL, self.temp.name, fetch=lambda _: newer)
        self.assertNotEqual(first["sha256"], second["sha256"])
        self.assertEqual(len(list(Path(self.temp.name).glob("plar_table_a2_*.pdf"))), 2)
        self.assertTrue(json.loads((Path(self.temp.name)/"plar_table_a2.json").read_text())["review_required"])

    def test_reject_html_without_touching_active(self):
        refresh_official_pdf(URL, self.temp.name, fetch=lambda _: self.pdf)
        original = (Path(self.temp.name)/"plar_table_a2.pdf").read_bytes()
        with self.assertRaises(ValueError):
            refresh_official_pdf(URL, self.temp.name, fetch=lambda _: b"<html>error</html>")
        self.assertEqual((Path(self.temp.name)/"plar_table_a2.pdf").read_bytes(), original)

    def test_corrupt_active_cache_is_repaired(self):
        refresh_official_pdf(URL, self.temp.name, fetch=lambda _: self.pdf)
        active = Path(self.temp.name) / "plar_table_a2.pdf"
        active.write_bytes(b"corrupt")
        result = refresh_official_pdf(URL, self.temp.name, fetch=lambda _: self.pdf)
        self.assertEqual(result["status"], "UPDATED")
        self.assertEqual(active.read_bytes(), self.pdf)

    def test_corrupt_historical_version_blocks_refresh(self):
        result = refresh_official_pdf(URL, self.temp.name, fetch=lambda _: self.pdf)
        versions = list(Path(self.temp.name).glob("plar_table_a2_*.pdf"))
        self.assertEqual(len(versions), 1)
        versions[0].write_bytes(b"corrupt")
        with self.assertRaises(ValueError):
            refresh_official_pdf(URL, self.temp.name, fetch=lambda _: self.pdf)
        self.assertEqual((Path(self.temp.name) / "plar_table_a2.pdf").read_bytes(), self.pdf)

    def test_reject_nonofficial_url(self):
        with self.assertRaises(ValueError):
            refresh_official_pdf("https://open.alberta.ca.evil.example/table.pdf",
                                 self.temp.name, fetch=lambda _: self.pdf)


if __name__ == "__main__":
    unittest.main()
