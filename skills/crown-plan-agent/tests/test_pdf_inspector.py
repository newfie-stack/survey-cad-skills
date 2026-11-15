"""Synthetic-only tests for the PDF position adapter; no client plans."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from pdf_inspector import normalize_span


class PdfInspectorTests(unittest.TestCase):
    def test_bbox_and_page_provenance(self):
        result = normalize_span({"text": "SCALE 1:5000", "bbox": [20, 30, 90, 40]}, 1, 612, 792)
        self.assertEqual(result["page"], 2)
        self.assertEqual(result["bbox_points"], [20, 30, 90, 40])
        self.assertEqual(result["page_size_points"], [612.0, 792.0])

    def test_rotated_text_direction(self):
        result = normalize_span({"text": "SYNTHETIC R/W", "bbox": [10, 20, 40, 70]},
                                0, 612, 792, (0, -1))
        self.assertEqual(result["text_angle_degrees"], -90.0)
        self.assertEqual(result["text_direction"], [0.0, -1.0])

    def test_invalid_direction(self):
        with self.assertRaises(ValueError):
            normalize_span({"text": "X", "bbox": [1, 2, 3, 4]},
                           0, 612, 792, (0, 0))

    def test_clip_partial_bbox_and_preserve_original_coordinates(self):
        for box, clipped in (([-1, 1, 5, 10], [0, 1, 5, 10]),
                             ([1, -2, 5, 10], [1, 0, 5, 10]),
                             ([610, 1, 614, 10], [610, 1, 612, 10]),
                             ([1, 790, 5, 795], [1, 790, 5, 792])):
            with self.subTest(box=box):
                result = normalize_span({"text": "SYNTHETIC EDGE", "bbox": box},
                                        0, 612, 792)
                self.assertEqual(result["bbox_points"], clipped)
                self.assertEqual(result["original_bbox_points"], box)

    def test_reject_wholly_out_of_page(self):
        with self.assertRaises(ValueError):
            normalize_span({"text": "X", "bbox": [-5, 1, -1, 10]}, 0, 612, 792)

    def test_reject_malformed_bbox(self):
        for box in ([5, 1, 1, 10], [1, 10, 5, 1],
                    [float("nan"), 1, 5, 10], [1, 1, float("inf"), 10]):
            with self.subTest(box=box), self.assertRaises(ValueError):
                normalize_span({"text": "X", "bbox": box}, 0, 612, 792)

    def test_reject_invalid_page_size(self):
        for width, height in ((0, 792), (612, -1), (float("inf"), 792),
                              (612, float("nan"))):
            with self.subTest(width=width, height=height), self.assertRaises(ValueError):
                normalize_span({"text": "X", "bbox": [1, 1, 5, 10]},
                               0, width, height)

    def test_reject_empty(self):
        with self.assertRaises(ValueError):
            normalize_span({"text": " ", "bbox": [1, 1, 2, 2]}, 0, 612, 792)


if __name__ == "__main__":
    unittest.main()
