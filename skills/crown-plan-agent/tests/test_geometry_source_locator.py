"""Source metadata stays compact even for handcrafted inventory inputs."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from geometry_handoff import prepare_geometry_handoff


class GeometrySourceLocatorTests(unittest.TestCase):
    def test_page_count_does_not_expand_unobserved_page_locators(self):
        result = prepare_geometry_handoff({"pages": 10000,
                                           "spans": [{"page": 7}, {"page": 7}],
                                           "vectors": [{"page": 4}]}, {})
        self.assertEqual(result["source"]["page_count"], 10000)
        self.assertEqual(result["source"]["pages"], [4, 7])

    def test_document_with_no_observations_preserves_only_count(self):
        result = prepare_geometry_handoff({"pages": 5, "spans": []}, {})
        self.assertEqual(result["source"]["page_count"], 5)
        self.assertEqual(result["source"]["pages"], [])


if __name__ == "__main__":
    unittest.main()
