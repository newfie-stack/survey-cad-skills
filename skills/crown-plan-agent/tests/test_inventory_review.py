"""Synthetic PDF inventory to review ledger integration."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from inventory_review import inventory_review


class InventoryReviewTests(unittest.TestCase):
    def test_text_candidate_provenance(self):
        inventory = {"status": "TEXT_AND_VECTOR_INVENTORY_ONLY",
                     "spans": [{"page": 2, "text": "SCALE 1:5000",
                                "bbox_points": [20, 30, 90, 40]}]}
        rules = [{"requirement_id": "SYNTH-SCALE", "evidence_key": "scale",
                  "text_candidates": ["SCALE"]},
                 {"requirement_id": "SYNTH-NORTH", "evidence_key": "north",
                  "text_candidates": ["NORTH ARROW"]}]
        report = inventory_review(inventory, {"plan_type": "sketch"}, rules)
        self.assertEqual(report["requirements"][0]["page"], 2)
        self.assertEqual(report["requirements"][0]["evidence_status"], "OBSERVED_CANDIDATE")
        self.assertEqual(report["requirements"][1]["evidence_status"], "UNKNOWN")
        self.assertTrue(all(x["status"] == "REVIEW_REQUIRED" for x in report["requirements"]))

    def test_reject_invalid_inventory(self):
        with self.assertRaises(TypeError):
            inventory_review({}, {}, [])

    def test_reject_bad_candidates(self):
        with self.assertRaises(ValueError):
            inventory_review({"spans": []}, {}, [{"requirement_id": "X",
                            "evidence_key": "x", "text_candidates": [None]}])

    def test_plan_showing_heading_allows_a_description_after_the_type(self):
        rule = {"requirement_id": "SYNTH-HEADING", "evidence_key": "heading",
                "check_method": "plan_heading"}
        for kind, text in (
            ("sketch", "SKETCH PLAN SHOWING A FICTIONAL TEST CORRIDOR"),
            ("surveyor_sketch", "SURVEYOR SKETCH PLAN SHOWING: A FICTIONAL ACCESS SITE"),
            ("survey_plan", "PLAN OF SURVEY SHOWING: A FICTIONAL PARCEL"),
        ):
            with self.subTest(kind=kind):
                inventory = {"spans": [{"page": 1, "text": text,
                                         "bbox_points": [10, 10, 200, 20]}]}
                entry = inventory_review(inventory, {"plan_type": kind}, [rule])["requirements"][0]
                self.assertEqual(entry["evidence_status"], "OBSERVED_CANDIDATE")
                self.assertEqual(entry["observation"], text)
                self.assertEqual(entry["status"], "REVIEW_REQUIRED")


if __name__ == "__main__":
    unittest.main()
