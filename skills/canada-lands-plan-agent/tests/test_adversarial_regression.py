"""Independent synthetic adversarial acceptance checks for bounded triage logic.

These fixtures are fictional data structures, not PDF/DWG visual inspection or
verification of binding IOGC standards. Unsupported checks must stay unresolved.
"""
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "engine" / "triage.py"
FIXTURES = Path(__file__).parent / "fixtures" / "synthetic_review_cases.json"
SPEC = importlib.util.spec_from_file_location("canada_lands_adversarial", SOURCE)
assert SPEC and SPEC.loader
triage_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(triage_module)


class TestAdversarialRegressions(unittest.TestCase):
    def test_seventeen_independent_scenarios(self):
        cases = json.loads(FIXTURES.read_text(encoding="utf-8"))
        self.assertEqual(len(cases), 17)
        self.assertEqual(len({c["id"] for c in cases}), len(cases))
        for case in cases:
            with self.subTest(case=case["id"]):
                actual = triage_module.triage(case["input"])
                self.assertEqual(actual["candidate_route"], case["expected_route"])
                self.assertEqual(actual["route_status"], case["expected_status"])
                self.assertEqual(actual["area_arithmetic"]["status"], case.get("expected_area", "REVIEW_REQUIRED"))
                self.assertEqual(actual["source_rule_verification"], "REVIEW_REQUIRED")
                self.assertEqual(actual["regulatory_acceptance"], "NOT_ASSESSED")
                self.assertEqual(actual["plan_visual_review"], case.get("expected_visual", "NOT_EXECUTED"))
                self.assertNotEqual(actual["iogc_incidental_activities_table_applicability"], "PASS")

    def test_deterministic_area_property_checks(self):
        rng = random.Random(20261124)
        for i in range(250):
            a = Decimal(rng.randrange(0, 100000)) / Decimal("10000")
            b = Decimal(rng.randrange(0, 100000)) / Decimal("10000")
            total = a + b
            good = triage_module.check_workspace_areas({
                "total_ha": str(total), "within_row_ha": str(a), "outside_row_ha": str(b),
            })
            with self.subTest(i=i, mode="consistent"):
                self.assertEqual(good["status"], "PASS")
                self.assertEqual(good["check_type"], "arithmetic_only")
            bad = triage_module.check_workspace_areas({
                "total_ha": str(total + Decimal("0.0002")),
                "within_row_ha": str(a), "outside_row_ha": str(b),
            })
            with self.subTest(i=i, mode="deliberate_mismatch"):
                self.assertEqual(bad["status"], "FAIL")
                self.assertEqual(bad["check_type"], "arithmetic_only")

    def test_defensive_numeric_inputs_do_not_crash(self):
        bad_values = ["1e999999999999", "NaN", "sNaN", "Infinity", "-0.5",
                      "1e100", None, True, [], {}, "0.0;DROP TABLE",
                      "1" * 10000]
        for value in bad_values:
            with self.subTest(value=str(value)[:28]):
                actual = triage_module.check_workspace_areas({
                    "total_ha": value, "within_row_ha": "0", "outside_row_ha": "0",
                })
                self.assertEqual(actual["status"], "REVIEW_REQUIRED")

    def test_missing_rule_proof_never_becomes_false_plan_pass(self):
        cases = json.loads(FIXTURES.read_text(encoding="utf-8"))
        gaps = [c for c in cases if "known_unverified_issue" in c]
        self.assertEqual(len(gaps), 4)
        for case in gaps:
            with self.subTest(gap=case["known_unverified_issue"]):
                actual = triage_module.triage(case["input"])
                self.assertEqual(actual["plan_visual_review"], "NOT_EXECUTED")
                self.assertNotEqual(actual["regulatory_acceptance"], "PASS")

    def test_no_document_type_automatically_qualifies_ia_table(self):
        for doc in ("application_survey_plan", "clsr_survey_plan",
                    "surface_permit_sketch", "asbuilt_exhibit", "unknown"):
            with self.subTest(doc=doc):
                result = triage_module.triage({
                    "land_class": "first_nation_reserve", "iogc_confirmed": True,
                    "purpose": "off_lease_remediation", "document_type": doc,
                })
                self.assertEqual(result["iogc_incidental_activities_table_applicability"], "REVIEW_REQUIRED")

    def test_cli_is_read_only_and_never_approves(self):
        case = {
            "land_class": "first_nation_reserve", "iogc_confirmed": True,
            "purpose": "off_lease_remediation", "workspace_area": {
                "total_ha": "0.48", "within_row_ha": "0.06", "outside_row_ha": "0.42",
            },
        }
        with tempfile.TemporaryDirectory() as root:
            input_file = Path(root) / "fictional-case.json"
            input_file.write_text(json.dumps(case), encoding="utf-8")
            before = input_file.read_bytes()
            process = subprocess.run([sys.executable, str(SOURCE), str(input_file)],
                                     capture_output=True, text=True, timeout=10)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(input_file.read_bytes(), before)
            response = json.loads(process.stdout)
            self.assertEqual(response["area_arithmetic"]["status"], "PASS")
            self.assertEqual(response["regulatory_acceptance"], "NOT_ASSESSED")
            self.assertEqual(sorted(p.name for p in Path(root).iterdir()), ["fictional-case.json"])

    def test_invalid_json_cli_fails_without_traceback(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "invalid-case.json"
            file.write_text("{broken", encoding="utf-8")
            process = subprocess.run([sys.executable, str(SOURCE), str(file)],
                                     capture_output=True, text=True, timeout=10)
            self.assertEqual(process.returncode, 2)
            self.assertIn("Invalid case input", process.stderr)
            self.assertNotIn("Traceback", process.stderr)


if __name__ == "__main__":
    unittest.main()
