"""Synthetic geometry checks; no real plan data."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from geometry import check_polygon

class GeometryTests(unittest.TestCase):
    def test_rectangle(self):
        result = check_polygon([(0,0),(100,0),(100,15),(0,15),(0,0)], crs_verified=True)
        self.assertAlmostEqual(result["area_m2"], 1500)
        self.assertAlmostEqual(result["area_ha"], 0.15)
        self.assertAlmostEqual(result["perimeter_m"], 230)
        self.assertEqual(result["compliance_status"], "REVIEW_REQUIRED")

    def test_utm_offset_rectangle_area(self):
        x, y = 532000.0, 5589000.0
        vertices = [(x,y),(x+100,y),(x+100,y+15),(x,y+15),(x,y)]
        result = check_polygon(vertices, crs_verified=True)
        self.assertAlmostEqual(result["area_m2"], 1500)
        self.assertAlmostEqual(result["perimeter_m"], 230)

    def test_large_offset_small_parcel(self):
        x, y = 1_000_000.0, 10_000_000.0
        vertices = [(x,y),(x+0.25,y),(x+0.25,y+0.5),
                    (x,y+0.5),(x,y)]
        result = check_polygon(vertices, crs_verified=True)
        self.assertAlmostEqual(result["area_m2"], 0.125)

    def test_translation_invariance(self):
        ring = [(0,0),(100,0),(120,20),(0,20),(0,0)]
        shifted = [(x+600000, y+6000000) for x,y in ring]
        self.assertAlmostEqual(check_polygon(ring)["area_m2"],
                               check_polygon(shifted)["area_m2"])

    def test_unknown_crs(self):
        self.assertEqual(check_polygon([(0,0),(1,0),(0,1),(0,0)])["crs_status"], "REVIEW_REQUIRED")

    def test_open_ring(self):
        with self.assertRaises(ValueError):
            check_polygon([(0,0),(1,0),(0,1)])

    def test_crossing(self):
        with self.assertRaises(ValueError):
            check_polygon([(0,0),(2,2),(0,2),(2,0),(0,0)])

    def test_collinear_overlap(self):
        with self.assertRaises(ValueError):
            check_polygon([(0,0),(4,0),(2,0),(4,3),(0,3),(0,0)])

    def test_nonadjacent_vertex_touch(self):
        with self.assertRaises(ValueError):
            check_polygon([(0,0),(4,0),(4,4),(2,2),(0,4),(2,2),(0,0)])

    def test_nonfinite(self):
        with self.assertRaises(ValueError):
            check_polygon([(0,0),(float("nan"),0),(0,1),(0,0)])

if __name__ == "__main__":
    unittest.main()
