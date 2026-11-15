"""Offline, synthetic-only regression test for Crown Plan Agent evidence gates.

This verifies fixture expectations and conservative classification, not current
regulatory compliance, visual PDF inspection or a deployed AI agent.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

FIXTURE = Path(__file__).with_name("synthetic_plan_test2.json")
VALID = {"PASS", "FAIL", "REVIEW_REQUIRED", "NOT_APPLICABLE"}


def classify(fixture: dict) -> dict[str, str]:
    obs = fixture["observations"]
    sources = fixture["source_verification"]
    artifacts = fixture["artifacts"]
    if not fixture.get("synthetic") or not artifacts.get("plan_pdf_present"):
        raise ValueError("Synthetic fixture and declared plan evidence required")
    # A FAIL here means the synthetic fixture intentionally omits an observable
    # item. It is not a legal finding until its current requirement is verified.
    result = {
        "legal_description": "FAIL" if obs.get("legal_description_present") is False else "REVIEW_REQUIRED",
        "north_arrow": "FAIL" if obs.get("north_arrow_present") is False else "REVIEW_REQUIRED",
        "monument_evidence": "REVIEW_REQUIRED",
        "area": "REVIEW_REQUIRED" if obs.get("geometry_area_ha") is None else "PASS",
        "als_declaration": "REVIEW_REQUIRED",
        "gis_schema": "REVIEW_REQUIRED" if not artifacts.get("shapefile_present") else "PASS",
        "current_plan_type": "REVIEW_REQUIRED" if not all(sources.values()) else "PASS",
    }
    return result


class TestSyntheticPlan(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_expected_findings(self) -> None:
        observed = classify(self.fixture)
        expected = {x["id"]: x["status"] for x in self.fixture["expected"]}
        self.assertEqual(expected, observed)
        self.assertTrue(set(observed.values()).issubset(VALID))

    def test_no_private_data_or_source_plan(self) -> None:
        raw = FIXTURE.read_text(encoding="utf-8").lower()
        for marker in ("client_name", "private_plan"):
            self.assertNotIn(marker, raw)

    def test_missing_plan_is_not_accepted(self) -> None:
        case = json.loads(json.dumps(self.fixture))
        case["artifacts"]["plan_pdf_present"] = False
        with self.assertRaises(ValueError):
            classify(case)

    def test_missing_current_regulatory_source_stays_unresolved(self) -> None:
        result = classify(self.fixture)
        self.assertEqual(result["current_plan_type"], "REVIEW_REQUIRED")
        self.assertEqual(result["als_declaration"], "REVIEW_REQUIRED")


if __name__ == "__main__":
    unittest.main()
