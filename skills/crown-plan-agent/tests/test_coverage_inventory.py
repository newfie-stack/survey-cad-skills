"""Invented citation links test inventory gaps; no plans, PDF, or network input."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE))


def invented_inventory():
    """Three invented clauses deliberately include a direct gap and a reference."""
    def clause(ident, direct=(), references=()):
        return {"clause_id": ident, "pdf_page": 1,
                "summary": "Invented review item.", "requirement_status": "conditional_required",
                "review_scope": ["Invented activity only; human applicability review."],
                "exceptions": [], "review_notes": [],
                "candidate_requirement_ids": list(direct),
                "reference_only_requirement_ids": list(references)}
    return {"schema_version": 1, "source_status": "UNVERIFIED_CURRENT",
            "source": {"publication_title": "Invented Manual", "version_date": "2024-01-02",
                       "source_url": "https://example.org/invented-manual", "pdf_page_count": 3},
            "review_scope": "Citation-link inventory only; conditions do not select rules.",
            "clauses": [clause("1.1.1", ["SYN-DIRECT"]),
                        clause("2.1.1.1", references=["SYN-REF"]), clause("3.1.1.1")]}


def invented_candidates():
    return [{"requirement_id": "SYN-DIRECT",
             "citation": {"publication_title": "Invented Manual", "version_date": "2024-01-02",
                          "section": "1.1.1"}},
            {"requirement_id": "SYN-REF",
             "citation": {"publication_title": "Invented Manual", "version_date": "2024-01-02",
                          "section": "1.1.9"},
             "review_instruction": "Review the exception in section 2.1.1.1."}]


class CoverageInventoryTests(unittest.TestCase):
    def coverage(self):
        self.assertTrue((ENGINE / "coverage_inventory.py").exists(), "Coverage audit is not implemented")
        from coverage_inventory import audit_coverage
        return audit_coverage

    def load(self, data):
        from coverage_inventory import load_inventory
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "invented.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            return load_inventory(path)

    def test_three_clause_audit_counts_reference_only_as_a_direct_gap(self):
        inventory, candidates = invented_inventory(), invented_candidates()
        before = copy.deepcopy((inventory, candidates))
        audit = self.coverage()(candidates, inventory)
        self.assertEqual(audit["status"], "REVIEW_REQUIRED")
        self.assertEqual(audit["source_status"], "UNVERIFIED_CURRENT")
        self.assertEqual(audit["counts"], {"total_clauses": 3, "mapped_candidate_clauses": 1,
                         "reference_only_clauses": 1, "unmapped_clauses": 2,
                         "unreferenced_clauses": 1})
        self.assertEqual(audit["by_part"]["2"]["unmapped_clauses"], 1)
        self.assertEqual(audit["clauses"][1]["coverage_status"], "REFERENCE_ONLY")
        self.assertEqual(audit["clauses"][2]["coverage_status"], "UNMAPPED")
        self.assertEqual((inventory, candidates), before)

    def test_missing_and_duplicate_actual_candidate_ids_leave_gaps(self):
        for candidates in ([], invented_candidates() + [invented_candidates()[0]]):
            with self.subTest(candidates=candidates):
                audit = self.coverage()(candidates, invented_inventory())
                self.assertEqual(audit["counts"]["mapped_candidate_clauses"], 0)
                self.assertTrue(audit["clauses"][0]["invalid_declared_links"])

    def test_wrong_publication_version_or_section_cannot_claim_mapping(self):
        for field, bad in (("publication_title", "Other Manual"), ("version_date", "2024-01-03"),
                           ("section", "1.1.10"), ("section", "1.1.1, nonsense"),
                           ("section", 123)):
            with self.subTest(field=field, bad=bad):
                candidates = invented_candidates()
                candidates[0]["citation"][field] = bad
                audit = self.coverage()(candidates, invented_inventory())
                self.assertEqual(audit["counts"]["mapped_candidate_clauses"], 0)
                self.assertEqual(audit["clauses"][0]["coverage_status"], "UNMAPPED")

    def test_reference_requires_actual_instruction_and_matching_source(self):
        for mutate in (lambda c: c.pop("review_instruction"),
                       lambda c: c.update(review_instruction="See 2.1.1.10."),
                       lambda c: c["citation"].update(version_date="2020-01-01")):
            candidates = invented_candidates()
            mutate(candidates[1])
            audit = self.coverage()(candidates, invented_inventory())
            self.assertEqual(audit["counts"]["reference_only_clauses"], 0)
            self.assertEqual(audit["clauses"][1]["coverage_status"], "UNMAPPED")

    def test_reference_link_rejects_reversed_or_cross_prefix_primary_citation(self):
        for section in ("1.1.9–1.1.1", "1.1.1–1.2.2"):
            candidates = invented_candidates()
            candidates[1]["citation"]["section"] = section
            with self.subTest(section=section):
                self.assertEqual(self.coverage()(candidates, invented_inventory())["counts"]
                                 ["reference_only_clauses"], 0)

    def test_full_id_ranges_and_combined_citations_cover_only_valid_ids(self):
        for section in ("1.1.1–1.1.3", "1.1.1-1.1.3", "1.1.9, 1.1.1"):
            with self.subTest(section=section):
                candidates = invented_candidates()
                candidates[0]["citation"]["section"] = section
                self.assertEqual(self.coverage()(candidates, invented_inventory())["counts"]
                                 ["mapped_candidate_clauses"], 1)
        for section in ("1.1.3–1.1.1", "1.1.1–1.2.3", "1.1.1–3", "1.1", "1.1.10"):
            with self.subTest(section=section):
                candidates = invented_candidates()
                candidates[0]["citation"]["section"] = section
                self.assertEqual(self.coverage()(candidates, invented_inventory())["counts"]
                                 ["mapped_candidate_clauses"], 0)

    def test_undeclared_custom_id_does_not_inherit_declared_mapping(self):
        candidates = invented_candidates()
        candidates[0]["requirement_id"] = "CUSTOM-REPLACEMENT"
        self.assertEqual(self.coverage()(candidates, invented_inventory())["counts"]
                         ["mapped_candidate_clauses"], 0)

    def test_loader_rejects_duplicate_clauses_forged_status_and_wrong_types(self):
        mutations = [lambda d: d["clauses"].append(copy.deepcopy(d["clauses"][0])),
                     lambda d: d.update(source_status="VERIFIED_CURRENT"),
                     lambda d: d.update(current_authority_verified=True),
                     lambda d: d["source"].update(current_authority_verified=True),
                     lambda d: d.update(schema_version=True),
                     lambda d: d["source"].update(pdf_page_count=True),
                     lambda d: d["source"].update(version_date="2024-02-30"),
                     lambda d: d["source"].update(source_url="file:///invented"),
                     lambda d: d["clauses"][0].update(pdf_page=4),
                     lambda d: d["clauses"][0].update(pdf_page=True),
                     lambda d: d["clauses"][0].update(requirement_status="PASS"),
                     lambda d: d["clauses"][0].update(clause_id="5.1.1.1"),
                     lambda d: d["clauses"][0].update(candidate_requirement_ids="SYN-DIRECT"),
                     lambda d: d["clauses"][0].update(review_scope=[False]),
                     lambda d: d["clauses"][0].update(reference_only_requirement_ids=["SYN-DIRECT"])]
        for mutate in mutations:
            data = invented_inventory()
            mutate(data)
            with self.subTest(data=data), self.assertRaises(ValueError):
                self.load(data)
        self.assertEqual(self.load(invented_inventory()), invented_inventory())

    def test_audit_validates_inventory_even_without_loader(self):
        data = invented_inventory()
        data["source_status"] = "VERIFIED_CURRENT"
        with self.assertRaises(ValueError):
            self.coverage()(invented_candidates(), data)

    def test_default_public_inventory_has_144_clauses_and_115_primary_gaps(self):
        from coverage_inventory import load_inventory
        inventory = load_inventory()
        entries = json.loads((ENGINE / "candidate_requirements.json").read_text())["requirements"]
        audit = self.coverage()(entries, inventory)
        self.assertEqual(audit["counts"], {"total_clauses": 144, "mapped_candidate_clauses": 29,
                         "reference_only_clauses": 2, "unmapped_clauses": 115,
                         "unreferenced_clauses": 113})
        self.assertEqual({part: values["total_clauses"] for part, values in audit["by_part"].items()},
                         {"1": 48, "2": 8, "3": 52, "4": 36})
        self.assertEqual(sum(bool(x["invalid_declared_links"]) for x in audit["clauses"]), 0)
        text = json.dumps(inventory).lower()
        for forbidden in ("private-validation", "supplied_path", "sha256", "/workspace/", "file://"):
            self.assertNotIn(forbidden, text)

    def test_cli_outputs_audit_and_never_overwrites_existing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inventory, candidates, output = [root / name for name in
                                            ("inventory.json", "candidates.json", "audit.json")]
            inventory.write_text(json.dumps(invented_inventory()), encoding="utf-8")
            candidates.write_text(json.dumps({"schema_version": 1,
                                             "requirements": invented_candidates()}), encoding="utf-8")
            command = [sys.executable, str(ENGINE / "coverage_inventory.py"), "--inventory", str(inventory),
                       "--catalogue", str(candidates)]
            run = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(run.stdout)["counts"]["unmapped_clauses"], 2)
            output.write_text("keep me", encoding="utf-8")
            run = subprocess.run(command + ["--output", str(output)], text=True, capture_output=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertEqual(output.read_text(), "keep me")
            output.unlink()
            run = subprocess.run(command + ["--output", str(output)], text=True, capture_output=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(output.read_text())["status"], "REVIEW_REQUIRED")


if __name__ == "__main__":
    unittest.main()
