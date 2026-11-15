"""Synthetic proximity association tests. No client plans."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from associations import associate_labels


class LabelAssociationTests(unittest.TestCase):
    def setUp(self):
        self.inventory = {
            "spans": [
                {"page": 1, "text": "SYNTHETIC R/W", "bbox_points": [45, 50, 55, 60]},
                {"page": 2, "text": "OTHER PAGE", "bbox_points": [45, 50, 55, 60]},
            ],
            "vectors": [
                {"page": 1, "type": "PDF_LINE", "role": "UNCLASSIFIED_GRAPHIC", "endpoints_points": [0, 65, 100, 65]},
                {"page": 2, "type": "PDF_LINE", "role": "UNCLASSIFIED_GRAPHIC", "endpoints_points": [0, 200, 100, 200]},
            ]
        }

    def test_nearest_same_page(self):
        results = associate_labels(self.inventory)
        self.assertEqual(results[0]["candidate_lines"][0]["vector_index"], 0)
        self.assertEqual(results[1]["candidate_lines"], [])
        self.assertEqual(results[0]["status"], "REVIEW_REQUIRED")

    def test_distance_gate(self):
        self.assertEqual(associate_labels(self.inventory, max_distance_points=5)[0]["candidate_lines"], [])

    def test_no_identity_inference(self):
        self.assertEqual(associate_labels(self.inventory)[0]["basis"], "NEAREST_PDF_PAGE_GEOMETRY_ONLY")

    def test_invalid_limits(self):
        for value in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                associate_labels(self.inventory, max_distance_points=value)
        with self.assertRaises(ValueError):
            associate_labels(self.inventory, max_candidates=0)


if __name__ == "__main__":
    unittest.main()
