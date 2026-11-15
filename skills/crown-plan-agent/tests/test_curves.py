"""Synthetic PDF cubic path tests; no private plan inputs."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from curves import curve_candidates

try:
    import fitz
except ImportError:
    fitz = None


@unittest.skipUnless(fitz is not None, "PyMuPDF unavailable")
class CurveTests(unittest.TestCase):
    def test_cubic_path_is_unclassified(self):
        doc = fitz.open()
        try:
            page = doc.new_page()
            shape = page.new_shape()
            shape.draw_bezier(fitz.Point(20,20), fitz.Point(40,20),
                              fitz.Point(60,80), fitz.Point(80,80))
            shape.finish()
            shape.commit()
            found = curve_candidates(page, 1)
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]["type"], "PDF_CUBIC_BEZIER")
            self.assertEqual(found[0]["status"], "REVIEW_REQUIRED")
            self.assertEqual(len(found[0]["control_points_points"]), 8)
        finally:
            doc.close()

    def test_no_curve_for_straight_line(self):
        doc = fitz.open()
        try:
            page = doc.new_page()
            page.draw_line((10, 10), (50, 50))
            self.assertEqual(curve_candidates(page, 1), [])
        finally:
            doc.close()

    def test_curve_limit(self):
        doc = fitz.open()
        try:
            page = doc.new_page()
            for shift in (0, 100):
                shape = page.new_shape()
                shape.draw_bezier(fitz.Point(10+shift,10), fitz.Point(20+shift,10),
                                  fitz.Point(30+shift,50), fitz.Point(40+shift,50))
                shape.finish()
                shape.commit()
            with self.assertRaises(ValueError):
                curve_candidates(page, 1, max_curves=1)
        finally:
            doc.close()


if __name__ == "__main__":
    unittest.main()
