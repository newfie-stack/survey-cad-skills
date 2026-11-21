"""Replay known synthetic claims; this does not rerun the assisted review.

These tests catch lost claims, broken source binding and incomplete grading in
the preserved experiment. Expectations come from its frozen November 21 result.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from assisted_trial_scoring import score_trial, validate_normalization


FIXTURES = Path(__file__).parent / "fixtures"
CASE_IDS = {"B76", "D31", "F58", "H90", "K27", "M84", "N24", "Q19", "S63", "T67", "V42", "X95"}
EXPECTED_TOTALS = {
    "known_defects": 12, "detected_defects": 12, "missed_defects": 0,
    "false_alarms": 0, "duplicate_findings": 1, "false_clearances": 0,
    "unsupported_claims": 0, "plans": 12, "clean_controls": 6,
    "clean_control_false_alarms": 0, "oracle_review_claims": 0,
    "atomic_claims": 647,
}


class WholePlanTrialEvidenceTests(unittest.TestCase):
    def load_trial(self):
        paths = [FIXTURES / f"whole_plan_trial_{name}.json" for name in ("truth", "evidence")]
        for path in paths:
            self.assertTrue(path.is_file(), f"Missing preserved whole-plan trial fixture: {path.name}")
        return tuple(json.loads(path.read_text(encoding="utf-8")) for path in paths)

    def test_all_twelve_frozen_cases_replay_the_recorded_result(self):
        truth, evidence = self.load_trial()
        cases = {case["case_id"]: case for case in truth["cases"]}
        self.assertEqual(set(cases), CASE_IDS)
        self.assertEqual({case["case_id"] for case in evidence["cases"]}, CASE_IDS)
        totals = dict.fromkeys(EXPECTED_TOTALS, 0)
        parents = 0
        for record in evidence["cases"]:
            with self.subTest(case=record["case_id"]):
                case = cases[record["case_id"]]
                original = record["original_review"]["content"]
                normalized = record["normalized_review"]["content"]
                grade = record["adjudication"]["content"]
                source = case["source_sha256"]
                self.assertEqual(original["source_sha256"], source)
                self.assertEqual(grade["source_sha256"], source)
                self.assertEqual(record["source"]["source_sha256"], source)
                self.assertEqual(record["source"]["brief_sha256"], case["brief_sha256"])
                self.assertEqual(original["overall_status"], "REVIEW_REQUIRED")
                self.assertEqual(original["regulatory_status"], "NOT_ASSESSED")
                self.assertTrue(grade["markdown_claim_coverage_checked"])
                atoms = validate_normalization(original, normalized, grade["normalization"])
                result = score_trial([issue["id"] for issue in case["defects"]], normalized,
                                     grade["adjudications"], source_sha256=source)
                saved = record["score"]
                self.assertEqual(saved, {"case_id": case["case_id"], "is_clean": case["is_clean"],
                                         "claims": atoms, **result})
                for key in ("known_defects", "detected_defects", "missed_defects", "false_alarms",
                            "duplicate_findings", "false_clearances", "unsupported_claims"):
                    totals[key] += result[key]
                totals["plans"] += 1
                totals["clean_controls"] += case["is_clean"]
                totals["clean_control_false_alarms"] += result["false_alarms"] if case["is_clean"] else 0
                totals["oracle_review_claims"] += len(result["oracle_review_claim_ids"])
                totals["atomic_claims"] += atoms
                parents += len(original["claims"])
        self.assertEqual(parents, 378)
        self.assertEqual(totals, EXPECTED_TOTALS)
        self.assertEqual(evidence["artifacts"]["scorecard.json"]["content"]["totals"], EXPECTED_TOTALS)

    def test_embedded_artifacts_retain_frozen_hash_links_and_portable_content_hashes(self):
        truth, evidence = self.load_trial()
        self.assertEqual(evidence["provenance"]["truth_fixture_sha256"], hashlib.sha256(
            (FIXTURES / "whole_plan_trial_truth.json").read_bytes()).hexdigest())
        artifacts = dict(evidence["artifacts"])
        artifacts.update({oracle["artifact"]["path"]: oracle["artifact"] for oracle in truth["oracles"]})
        for case in evidence["cases"]:
            for name in ("original_review", "normalized_review", "adjudication", "markdown_report", "review_freeze", "job_brief"):
                artifact = case[name]
                artifacts[artifact["path"]] = artifact
            if "grader_report" in case:
                artifact = case["grader_report"]
                artifacts[artifact["path"]] = artifact
        for path, artifact in artifacts.items():
            with self.subTest(artifact=path):
                content = artifact["content"]
                portable = (json.dumps(content, ensure_ascii=False, sort_keys=True,
                                       separators=(",", ":")) if artifact["format"] == "json" else content).encode("utf-8")
                self.assertEqual(hashlib.sha256(portable).hexdigest(), artifact["portable_content_sha256"])
                self.assertEqual(len(portable), artifact["portable_content_bytes"])
                self.assertNotIn("/workspace/", portable.decode("utf-8"))
                self.assertEqual(len(artifact["original_sha256"]), 64)
        inputs = artifacts["input-freeze.json"]["content"]
        reviews = artifacts["review-freeze.json"]["content"]
        final = artifacts["final-results-freeze.json"]["content"]
        materials = artifacts["experiment-materials-freeze.json"]["content"]
        for manifest in (inputs, final, materials):
            for path, frozen_hash in manifest["files"].items():
                if path in artifacts:
                    with self.subTest(frozen_artifact=path):
                        self.assertEqual(artifacts[path]["original_sha256"], frozen_hash)
        for oracle in truth["oracles"]:
            self.assertEqual(oracle["artifact"]["original_sha256"], inputs["files"][oracle["artifact"]["path"]])
            for case in oracle["artifact"]["content"]["cases"]:
                combined = next(row for row in truth["cases"] if row["case_id"] == case["case_id"])
                self.assertEqual(combined, {"author": oracle["author"],
                                            "original_truth_artifact": oracle["artifact"]["path"], **case})
        for record in evidence["cases"]:
            case_id = record["case_id"]
            for name in ("original_review", "markdown_report"):
                artifact = record[name]
                self.assertEqual(artifact["original_sha256"], reviews["cases"][case_id][Path(artifact["path"]).name])
            for name in ("normalized_review", "adjudication"):
                artifact = record[name]
                self.assertEqual(artifact["original_sha256"], final["files"][artifact["path"]])
            source = record["source"]
            self.assertEqual(inputs["files"][source["pdf_path"]], source["source_sha256"])
            self.assertEqual(inputs["files"][source["brief_path"]], source["brief_sha256"])
            self.assertEqual(record["job_brief"]["original_sha256"], source["brief_sha256"])
        source_freeze = artifacts["source-freeze.json"]["content"]
        self.assertEqual(source_freeze["source_commit"], "ea800aedfcf2d922f13a997776f7ee9366252fe1")
        self.assertEqual(source_freeze["reviewer_prompt_sha256"], artifacts["REVIEWER_PROMPT.txt"]["original_sha256"])
        self.assertEqual(source_freeze["protocol_sha256"], artifacts["PROTOCOL.md"]["original_sha256"])
        self.assertEqual(artifacts["grader-prompt-freeze.sha256"]["content"].split()[0],
                         artifacts["GRADER_PROMPT.txt"]["original_sha256"])

    def test_losing_an_original_claim_mapping_fails_real_normalization(self):
        _, evidence = self.load_trial()
        for record in evidence["cases"]:
            with self.subTest(case=record["case_id"]), self.assertRaises(ValueError):
                validate_normalization(record["original_review"]["content"],
                                       record["normalized_review"]["content"],
                                       record["adjudication"]["content"]["normalization"][1:])

    def test_losing_an_atomic_claim_fails_real_normalization(self):
        _, evidence = self.load_trial()
        for record in evidence["cases"]:
            normalized = deepcopy(record["normalized_review"]["content"])
            normalized["claims"].pop()
            with self.subTest(case=record["case_id"]), self.assertRaises(ValueError):
                validate_normalization(record["original_review"]["content"], normalized,
                                       record["adjudication"]["content"]["normalization"])

    def test_wrong_source_fails_real_normalization_and_scoring(self):
        truth, evidence = self.load_trial()
        cases = {case["case_id"]: case for case in truth["cases"]}
        for record in evidence["cases"]:
            normalized = deepcopy(record["normalized_review"]["content"])
            normalized["source_sha256"] = "0" * 64
            grade = record["adjudication"]["content"]
            with self.subTest(case=record["case_id"]):
                with self.assertRaises(ValueError):
                    validate_normalization(record["original_review"]["content"], normalized, grade["normalization"])
                case = cases[record["case_id"]]
                with self.assertRaises(ValueError):
                    score_trial([issue["id"] for issue in case["defects"]], normalized,
                                grade["adjudications"], source_sha256=case["source_sha256"])

    def test_missing_adjudication_fails_real_scoring(self):
        truth, evidence = self.load_trial()
        cases = {case["case_id"]: case for case in truth["cases"]}
        for record in evidence["cases"]:
            case = cases[record["case_id"]]
            with self.subTest(case=case["case_id"]), self.assertRaises(ValueError):
                score_trial([issue["id"] for issue in case["defects"]],
                            record["normalized_review"]["content"],
                            record["adjudication"]["content"]["adjudications"][1:],
                            source_sha256=case["source_sha256"])


if __name__ == "__main__":
    unittest.main()
