"""Synthetic official source discovery tests."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from table_a2_discovery import discover_a2_pdf

PAGE = "https://www.alberta.ca/public-lands-administration-regulation"
PDF = "https://open.alberta.ca/dataset/synthetic/resource/test/download/plar-a2.pdf"


class DiscoveryTests(unittest.TestCase):
    def test_unique_official_pdf(self):
        html = '<a href="' + PDF + '">PLAR Table A2</a>'
        self.assertEqual(discover_a2_pdf(PAGE, html), PDF)

    def test_intermediate_page_requires_review(self):
        html = '<a href="https://open.alberta.ca/publications/a2">PLAR Table A2</a>'
        with self.assertRaises(ValueError):
            discover_a2_pdf(PAGE, html)

    def test_reject_lookalike_host(self):
        html = '<a href="https://open.alberta.ca.evil.example/table.pdf">PLAR Table A2</a>'
        with self.assertRaises(ValueError):
            discover_a2_pdf(PAGE, html)

    def test_ambiguous_official_pdf_requires_review(self):
        html = ('<a href="' + PDF + '">PLAR Table A2</a>'
                '<a href="https://open.alberta.ca/other.pdf">PLAR Table A2</a>')
        with self.assertRaises(ValueError):
            discover_a2_pdf(PAGE, html)


if __name__ == "__main__":
    unittest.main()
