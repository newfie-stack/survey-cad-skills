"""Synthetic source-catalogue audit tests."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from regulatory_catalog import load_candidate_catalog
from catalogue_audit import audit_catalogue


class CatalogueAuditTests(unittest.TestCase):
    def test_content_catalogue_has_citations_and_reviewable_applicability(self):
        path = Path(__file__).resolve().parents[1] / "engine" / "candidate_requirements.json"
        audit = audit_catalogue(load_candidate_catalog(path))
        self.assertEqual(audit["status"], "REVIEW_REQUIRED")
        self.assertEqual(audit["total"], 17)
        self.assertEqual(audit["incomplete_citations"], 0)
        self.assertEqual(audit["broad_applicability"], 17)

    def test_complete_citation_still_requires_review(self):
        entry = {"requirement_id": "SYNTH", "plan_types": ["sketch"],
                 "activities": ["PLA"], "stages": ["initial"],
                 "citation": {"publication_title": "Synthetic", "section": "1",
                              "version_date": "2024-01-01", "accessed_on": "2026-11-14",
                              "source_url": "https://open.alberta.ca/"}}
        audit = audit_catalogue([entry])
        self.assertEqual(audit["incomplete_citations"], 0)
        self.assertEqual(audit["findings"][0]["status"], "REVIEW_REQUIRED")

    def test_invalid_input(self):
        with self.assertRaises(TypeError):
            audit_catalogue(None)


if __name__ == "__main__":
    unittest.main()
