"""Synthetic conservative leader ranking checks."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from leader_review import rank_leader_candidates


def fixture(text, endpoints):
    return {"spans": [{"page": 1, "text": text, "bbox_points": [10,10,20,20]}],
            "vectors": [{"page": 1, "type": "PDF_LINE", "endpoints_points": endpoints}]}


class LeaderReviewTests(unittest.TestCase):
    def test_oblique_callout_elevated_not_verified(self):
        result = rank_leader_candidates(fixture("CAUTION", [20,15,80,65]))[0]
        self.assertEqual(result["review_priority"], "ELEVATED")
        self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_orthogonal_line_remains_unverified(self):
        result = rank_leader_candidates(fixture("C/L", [20,15,80,15]))[0]
        self.assertIn("ORTHOGONAL_SEGMENT_POSSIBLE_RULE_OR_DIMENSION", result["evidence_signals"])
        self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_layout_text_low_priority(self):
        result = rank_leader_candidates(fixture("LEGEND", [20,15,80,65]))[0]
        self.assertEqual(result["review_priority"], "LOW")

    def test_no_candidates(self):
        self.assertEqual(rank_leader_candidates(fixture("CAUTION", [300,300,350,350])), [])


if __name__ == "__main__":
    unittest.main()
