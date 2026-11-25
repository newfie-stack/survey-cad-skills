"""Static checks for the pre-checker's published safety and source contract.

These are synthetic documentation assertions, not review of any actual plans.
"""
from pathlib import Path
import unittest


SKILL_DIR = Path(__file__).resolve().parents[1]
ROOT = SKILL_DIR.parents[1]


class DocumentationContractTests(unittest.TestCase):
    def test_required_references_resolve(self):
        main = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        for ref in (
            "references/route-matrix.md",
            "references/review-checklist.md",
            "references/source-hierarchy.md",
            "references/official-checklist-coverage.md",
        ):
            with self.subTest(ref=ref):
                self.assertTrue((SKILL_DIR / ref).is_file())
                self.assertIn(ref, main)

    def test_both_source_checklists_tracked(self):
        doc = (SKILL_DIR / "references/official-checklist-coverage.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("https://www.myclss.ca/myclss/index/pc/", doc)
        self.assertIn("https://www.myclss.ca/myclss/index/iogc-pgic/", doc)
        self.assertIn("https://www.iogc-pgic.gc.ca/eng/1472575186371/1472575275357", doc)
        self.assertIn("Surface Permit sketch", doc)
        self.assertIn("REVIEW_REQUIRED", doc)

    def test_review_only_and_no_unverified_approval(self):
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        for label in (
            "pre-checking reviewer only",
            "must not create or reconstruct a production plan",
            "INSUFFICIENT EVIDENCE",
            "without editing the source plan",
            "No registration inference",
            "No provincial-rule leakage",
        ):
            with self.subTest(label=label):
                self.assertIn(label, skill)

    def test_skill_version_is_consistent(self):
        doc = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("version: 0.1.1", doc)
        self.assertIn("development preview v0.1.1", doc)
        self.assertNotIn("development preview v0.1.0", doc)

    def test_readme_separates_crown_and_canada_lands(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("- [Crown Plan Agent]", readme)
        self.assertIn("- [Canada Lands Plan Agent]", readme)
        self.assertNotIn(
            "Canada Lands Plan Agent](skills/canada-lands-plan-agent/SKILL.md) — new development-preview",
            readme,
        )


if __name__ == "__main__":
    unittest.main()
