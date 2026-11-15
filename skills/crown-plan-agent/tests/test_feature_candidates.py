"""Offline synthetic tests of annotation evidence hints."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from feature_candidates import review_candidates


def line(y):
    return {"page": 1, "type": "PDF_LINE", "role": "UNCLASSIFIED_GRAPHIC",
            "endpoints_points": [0, y, 100, y]}


class FeatureCandidateTests(unittest.TestCase):
    def test_right_of_way_hint_not_feature_identity(self):
        data = {"spans": [{"page": 1, "text": "15.00 P/L R/W", "bbox_points": [40, 40, 60, 50]}],
                "vectors": [line(55)]}
        result = review_candidates(data)[0]
        self.assertIn("RIGHT_OF_WAY_LABEL", result["semantic_hints"])
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["ambiguity"], "UNVERIFIED_ASSOCIATION")

    def test_two_close_lines_flagged_ambiguous(self):
        data = {"spans": [{"page": 1, "text": "C/L", "bbox_points": [40, 40, 60, 50]}],
                "vectors": [line(52), line(54)]}
        result = review_candidates(data)[0]
        self.assertIn("CENTRELINE_LABEL", result["semantic_hints"])
        self.assertEqual(result["ambiguity"], "MULTIPLE_NEARBY_LINES")

    def test_no_nearby_line(self):
        data = {"spans": [{"page": 1, "text": "TIE LINE", "bbox_points": [40, 40, 60, 50]}],
                "vectors": [line(500)]}
        self.assertEqual(review_candidates(data)[0]["ambiguity"], "NO_NEARBY_LINE")

    def test_no_hint_is_not_failure(self):
        data = {"spans": [{"page": 1, "text": "SYNTHETIC PLAN", "bbox_points": [40, 40, 60, 50]}],
                "vectors": []}
        self.assertEqual(review_candidates(data)[0]["semantic_hints"], [])


if __name__ == "__main__":
    unittest.main()
