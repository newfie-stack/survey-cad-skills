"""Synthetic projected traverse closure tests."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from traverse import traverse_closure


class TraverseTests(unittest.TestCase):
    def test_closed_utm_traverse(self):
        x, y = 500000.0, 5600000.0
        result = traverse_closure([(x,y),(x+100,y),(x+100,y+20),
                                   (x,y+20),(x,y)], crs_verified=True)
        self.assertAlmostEqual(result["misclosure_m"], 0)
        self.assertAlmostEqual(result["travelled_distance_m"], 240)
        self.assertIsNone(result["closure_ratio_denominator"])
        self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_open_traverse_tolerance_is_only_diagnostic(self):
        result = traverse_closure([(0,0),(100,0),(100,20),(0,20),(0.03,0)],
                                  tolerance_m=0.02)
        self.assertAlmostEqual(result["misclosure_m"], 0.03)
        self.assertFalse(result["within_supplied_tolerance"])
        self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_no_implicit_tolerance(self):
        result = traverse_closure([(0,0),(10,0),(0,1)])
        self.assertIsNone(result["within_supplied_tolerance"])

    def test_decimal_tolerance_boundary_is_translation_invariant(self):
        # Decimal endpoint differences are exactly 0.2 m in both locations.
        for vertices in (
            [(0,0),(10,0),(0,0.2)],
            [(500000,6000000),(500010,6000000),(500000,6000000.2)],
        ):
            for tolerance in (None, 0.2):
                with self.subTest(vertices=vertices, tolerance=tolerance):
                    result = traverse_closure(vertices, crs_verified=True,
                                              tolerance_m=tolerance)
                    self.assertEqual(result["delta_easting_m"], 0)
                    self.assertEqual(result["delta_northing_m"], 0.2)
                    self.assertEqual(result["misclosure_m"], 0.2)
                    self.assertIs(result["within_supplied_tolerance"],
                                  None if tolerance is None else True)
                    self.assertEqual(result["status"], "REVIEW_REQUIRED")

    def test_vector_tolerance_boundary_at_projected_offset(self):
        # A 0.3 m by 0.4 m closure vector has length exactly 0.5 m.
        for tolerance in (None, 0.5):
            with self.subTest(tolerance=tolerance):
                result = traverse_closure(
                    [(500000,6000000),(500010,6000000),(500000.3,6000000.4)],
                    tolerance_m=tolerance)
                self.assertEqual(result["delta_easting_m"], 0.3)
                self.assertEqual(result["delta_northing_m"], 0.4)
                self.assertEqual(result["misclosure_m"], 0.5)
                self.assertIs(result["within_supplied_tolerance"],
                              None if tolerance is None else True)

    def test_just_outside_tolerance_is_rejected_without_rounding_slack(self):
        for vertices, tolerance in (
            ([(500000,6000000),(500010,6000000),(500000,6000000.200000001)], 0.2),
            # hypot rounds these vector lengths to 0.5, despite their excess.
            ([(0,0),(10,0),(0.30000000000000004,0.4)], 0.5),
            ([(0,0),(10,0),(0.3,0.4000000000000001)], 0.5),
        ):
            with self.subTest(vertices=vertices):
                result = traverse_closure(vertices, tolerance_m=tolerance)
                self.assertFalse(result["within_supplied_tolerance"])

    def test_zero_tolerance_requires_exact_closure_after_translation(self):
        for vertices, expected in (
            ([(0,0),(10,0),(0,0)], True),
            ([(500000,6000000),(500010,6000000),(500000,6000000)], True),
            ([(0,0),(10,0),(0.0000000001,0)], False),
            ([(500000,6000000),(500010,6000000),(500000.0000000001,6000000)], False),
        ):
            with self.subTest(vertices=vertices):
                result = traverse_closure(vertices, tolerance_m=0)
                self.assertIs(result["within_supplied_tolerance"], expected)

    def test_reject_invalid_tolerance(self):
        for tolerance in (float("nan"), float("inf"), -float("inf"), -1, True, "0.2"):
            with self.subTest(tolerance=tolerance), self.assertRaises(ValueError):
                traverse_closure([(0,0),(10,0),(0,1)], tolerance_m=tolerance)

    def test_reject_nonfinite_coordinates(self):
        for coordinate in (float("nan"), float("inf"), -float("inf")):
            for index in range(3):
                for axis in range(2):
                    vertices = [[0,0],[10,0],[0,1]]
                    vertices[index][axis] = coordinate
                    with self.subTest(coordinate=coordinate, index=index, axis=axis):
                        with self.assertRaises(ValueError):
                            traverse_closure(vertices, tolerance_m=0.2)

    def test_reject_zero_leg(self):
        with self.assertRaises(ValueError):
            traverse_closure([(0,0),(0,0),(1,1)])

    def test_reject_unverified_crs_flag_type(self):
        with self.assertRaises(ValueError):
            traverse_closure([(0,0),(10,0),(0,1)], crs_verified="yes")


if __name__ == "__main__":
    unittest.main()
