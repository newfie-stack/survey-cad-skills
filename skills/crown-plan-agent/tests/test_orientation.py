"""Synthetic orientation matching checks."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from orientation import orientation_candidates


def fixture(angle, vectors):
    return {"spans": [{"page": 1, "text": "SYNTHETIC R/W", "bbox_points": [45,45,55,55],
                       **({"text_angle_degrees": angle} if angle is not None else {})}],
            "vectors": [{"page": 1, "type": "PDF_LINE", "role": "UNCLASSIFIED_GRAPHIC",
                         "endpoints_points": v} for v in vectors]}


class OrientationTests(unittest.TestCase):
    def test_parallel_priority(self):
        results = orientation_candidates(fixture(0, [[50,40,50,60],[0,60,100,60]]))
        self.assertEqual(results[0]["candidates"][0]["vector_index"], 1)
        self.assertEqual(results[0]["candidates"][0]["orientation_signal"], "PARALLEL_LIKE")
        self.assertEqual(results[0]["status"], "REVIEW_REQUIRED")

    def test_rotated_parallel(self):
        results = orientation_candidates(fixture(-90, [[60,0,60,100]]))
        self.assertEqual(results[0]["candidates"][0]["orientation_signal"], "PARALLEL_LIKE")

    def test_missing_direction_stays_unknown(self):
        results = orientation_candidates(fixture(None, [[0,60,100,60]]))
        self.assertEqual(results[0]["candidates"][0]["orientation_signal"], "UNKNOWN_TEXT_DIRECTION")

    def test_invalid_tolerance(self):
        with self.assertRaises(ValueError):
            orientation_candidates(fixture(0, []), parallel_tolerance_degrees=100)


if __name__ == "__main__":
    unittest.main()
