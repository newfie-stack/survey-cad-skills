"""Synthetic leader heuristics tests, not client plan examples."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from leaders import leader_candidates


class LeaderCandidatesTests(unittest.TestCase):
    def setUp(self):
        self.inventory = {
            "spans": [{"page": 1, "text": "SYNTHETIC CALLOUT", "bbox_points": [10, 10, 20, 20]}],
            "vectors": [{"page": 1, "type": "PDF_LINE", "endpoints_points": [20, 15, 100, 75]}],
        }

    def test_endpoint_near_text(self):
        result = leader_candidates(self.inventory)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["status"], "REVIEW_REQUIRED")
        self.assertEqual(result[0]["interpretation"], "POSSIBLE_LEADER_NOT_VERIFIED")

    def test_other_page_not_linked(self):
        self.inventory["vectors"][0]["page"] = 2
        self.assertEqual(leader_candidates(self.inventory), [])

    def test_length_gate(self):
        self.assertEqual(leader_candidates(self.inventory, max_length_points=20), [])

    def test_far_endpoint_not_linked(self):
        self.inventory["vectors"][0]["endpoints_points"] = [100, 100, 150, 150]
        self.assertEqual(leader_candidates(self.inventory), [])

    def test_invalid_limits(self):
        with self.assertRaises(ValueError):
            leader_candidates(self.inventory, endpoint_radius_points=0)


if __name__ == "__main__":
    unittest.main()
