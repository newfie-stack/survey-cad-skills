"""Replay frozen forward-trial accounting and saved first context requests.

This repeats deterministic preparation/checking, never the assisted reviewer or
semantic grader. All four issue detections were assisted manual findings.
"""
from collections import Counter
from copy import deepcopy
import hashlib
import html
import json
from pathlib import Path
import sys
import tempfile
import unittest

from assisted_trial_scoring import score_trial, validate_normalization


FIXTURES = Path(__file__).parent / "fixtures"
CASE_IDS = {"L38", "P72", "R46", "U91"}
SOURCE_COMMIT = "3a3e5697ccf4e48f75032054131131ed3a7f3ea9"
SCORE_TOTALS = {
    "known_defects": 4, "detected_defects": 4, "missed_defects": 0,
    "false_alarms": 0, "false_clearances": 0, "unsupported_claims": 0,
    "duplicate_findings": 0, "original_claims": 233, "atomic_claims": 246,
    "plans": 4, "clean_controls": 2, "oracle_review_claims": 0,
}
INTAKE_TOTALS = {
    "first_requested": 93, "first_ready": 56, "first_unresolved": 37,
    "executed_checks": 56, "context_retries": 0,
    "executed_counts": {"PASS": 54, "FAIL": 0, "REVIEW_REQUIRED": 2},
}


def normalization(grade):
    return grade["normalization_map"] if "normalization_map" in grade else grade["normalization"]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


class IntakeForwardEvidenceTests(unittest.TestCase):
    def load_trial(self):
        evidence_path = FIXTURES / "intake_forward_evidence.json"
        truth_path = FIXTURES / "intake_forward_truth.json"
        self.assertTrue(evidence_path.is_file(), "Missing preserved intake forward-trial evidence")
        self.assertTrue(truth_path.is_file(), "Missing preserved intake forward-trial truth")
        self.evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        truth = json.loads(truth_path.read_text(encoding="utf-8"))
        self.truth = {case["case_id"]: case for case in truth["original_oracle"]["content"]["cases"]}
        self.records = {case["case_id"]: case for case in self.evidence["cases"]}
        return self.evidence

    def artifact(self, record, name):
        return self.evidence["artifacts"][record["artifacts"][name]]

    def content(self, record, name):
        return self.artifact(record, name)["content"]

    def test_four_cases_replay_all_claims_and_manual_detections(self):
        evidence = self.load_trial()
        self.assertEqual(set(self.records), CASE_IDS)
        self.assertEqual(set(self.truth), CASE_IDS)
        scorecard = evidence["artifacts"]["scorecard.json"]["content"]
        saved = {case["case_id"]: case for case in scorecard["cases"]}
        totals = dict.fromkeys(SCORE_TOTALS, 0)
        methods = []
        for case_id, record in self.records.items():
            with self.subTest(case=case_id):
                truth = self.truth[case_id]
                original = self.content(record, "original_review")
                normalized = self.content(record, "normalized_review")
                grade = self.content(record, "adjudication")
                self.assertEqual(original["source_sha256"], truth["source_sha256"])
                self.assertEqual(grade["source_sha256"], truth["source_sha256"])
                self.assertEqual(original["overall_status"], "REVIEW_REQUIRED")
                self.assertEqual(original["regulatory_status"], "NOT_ASSESSED")
                self.assertTrue(grade["markdown_claim_coverage_checked"])
                atoms = validate_normalization(original, normalized, normalization(grade))
                result = score_trial([issue["id"] for issue in truth["defects"]], normalized,
                                     grade["adjudications"], source_sha256=truth["source_sha256"])
                self.assertEqual({key: saved[case_id][key] for key in result}, result)
                self.assertEqual(saved[case_id]["original_claims"], len(original["claims"]))
                self.assertEqual(saved[case_id]["atomic_claims"], atoms)
                for key in ("known_defects", "detected_defects", "missed_defects", "false_alarms",
                            "false_clearances", "unsupported_claims", "duplicate_findings"):
                    totals[key] += result[key]
                totals["original_claims"] += len(original["claims"])
                totals["atomic_claims"] += atoms
                totals["plans"] += 1
                totals["clean_controls"] += truth["is_clean"]
                totals["oracle_review_claims"] += len(result["oracle_review_claim_ids"])
                by_claim = {claim["id"]: claim for claim in normalized["claims"]}
                methods += [by_claim[row["claim_id"]]["method"] for row in grade["adjudications"]
                            if row["verdict"] == "FOUND"]
        self.assertEqual(totals, SCORE_TOTALS)
        self.assertEqual(scorecard["totals"], SCORE_TOTALS)
        self.assertEqual(len(methods), 4)
        self.assertTrue(all(method.startswith("MANUAL_") for method in methods))

    def test_first_request_metrics_keep_every_unresolved_request_and_actual_cli_result(self):
        evidence = self.load_trial()
        totals = {key: 0 for key in INTAKE_TOTALS if key != "executed_counts"}
        counts = Counter({"PASS": 0, "FAIL": 0, "REVIEW_REQUIRED": 0})
        for case_id, record in self.records.items():
            with self.subTest(case=case_id):
                original = self.content(record, "original_review")
                contexts = self.content(record, "first_contexts")
                prep = self.content(record, "first_preparation")
                ready = self.content(record, "first_ready_spec")
                verified = self.content(record, "adjudication")["intake_verified"]
                source = self.truth[case_id]["source_sha256"]
                for saved in (contexts, prep, ready, prep["intake"]):
                    self.assertEqual(saved["source_sha256"], source)
                self.assertEqual(prep["context_spec_sha256"],
                                 self.artifact(record, "first_contexts")["original_canonical_json_sha256"])
                requested = {check["id"]: check for check in contexts["checks"]}
                resolutions = {row["check_id"]: row for row in prep["resolutions"]}
                self.assertEqual(len(resolutions), len(prep["resolutions"]))
                self.assertEqual(set(resolutions), set(requested))
                for check_id, row in resolutions.items():
                    self.assertEqual(row["request"], requested[check_id])
                ready_ids = {row["check_id"] for row in prep["resolutions"] if row["status"] == "READY"}
                unresolved = set(requested) - ready_ids
                self.assertEqual(ready, prep["spec"])
                self.assertEqual({check["id"] for check in ready["checks"]}, ready_ids)
                followups = {task["check_id"] for task in prep["visual_tasks"] if "check_id" in task}
                self.assertEqual(followups, unresolved)
                self.assertEqual(len(original["intake_attempts"]), 1)
                self.assertTrue(original["intake_attempts"][0]["is_first_attempt"])
                self.assertEqual(verified["attempts"], 1)
                self.assertEqual(verified["context_retries"], 0)
                report = self.content(record, "first_cli_report")
                section = report.split("## Finished-plan drawing QC\n", 1)[1].split("\n## ", 1)[0]
                actual_counts = {status: section.count(f"Status: **{status}**")
                                 for status in counts}
                self.assertEqual(actual_counts, verified["executed_counts"])
                self.assertEqual(sum(actual_counts.values()), len(ready_ids))
                self.assertIn(f"Source SHA-256: {source}", section)
                self.assertIn("Specification SHA-256: " +
                              self.artifact(record, "first_ready_spec")["original_canonical_json_sha256"], section)
                preparation_section = html.unescape(report.split("## Plan intake and check preparation\n", 1)[1])
                for check_id in unresolved:
                    self.assertIn(check_id, preparation_section)
                for key, actual in (("first_requested", len(requested)), ("first_ready", len(ready_ids)),
                                    ("first_unresolved", len(unresolved)), ("executed_checks", len(ready_ids))):
                    self.assertEqual(verified[key], actual)
                    totals[key] += actual
                counts.update(actual_counts)
        totals["executed_counts"] = dict(counts)
        self.assertEqual(totals, INTAKE_TOTALS)
        self.assertEqual(evidence["artifacts"]["scorecard.json"]["content"]["intake_totals"], INTAKE_TOTALS)

    def test_saved_first_contexts_reproduce_preparation_and_mechanical_outcomes(self):
        self.load_trial()
        import intake_forward_layouts
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
        from finished_plan_review import render_finished_plan, review_finished_plan
        from plan_intake import prepare_finished_plan
        with tempfile.TemporaryDirectory() as temporary:
            for case_id, record in self.records.items():
                with self.subTest(case=case_id):
                    folder = Path(temporary) / case_id
                    intake_forward_layouts.write_case(folder, case_id)
                    source = folder / "plan.pdf"
                    if hashlib.sha256(source.read_bytes()).hexdigest() != self.truth[case_id]["source_sha256"]:
                        self.skipTest("Frozen preparation replay requires the recorded PDF byte identity/runtime")
                    prepared = prepare_finished_plan(source, self.content(record, "first_contexts"))
                    self.assertEqual(prepared, self.content(record, "first_preparation"))
                    actual = review_finished_plan(source, prepared["spec"])
                    self.assertEqual(actual["summary"], self.content(record, "adjudication")["intake_verified"]["executed_counts"])
                    self.assertIn(render_finished_plan(actual), self.content(record, "first_cli_report"))
                    if "mechanical_result" in record["artifacts"]:
                        self.assertEqual(actual, self.content(record, "mechanical_result"))

    def test_portable_hashes_and_freezes_bind_prompts_inputs_and_complete_reviews(self):
        evidence = self.load_trial()
        self.assertEqual(evidence["provenance"]["source_commit"], SOURCE_COMMIT)
        self.assertEqual(evidence["provenance"]["truth_fixture_sha256"], hashlib.sha256(
            (FIXTURES / "intake_forward_truth.json").read_bytes()).hexdigest())
        for path, artifact in evidence["artifacts"].items():
            with self.subTest(artifact=path):
                portable = canonical(artifact["content"]) if artifact["format"] == "json" else artifact["content"].encode("utf-8")
                self.assertEqual(hashlib.sha256(portable).hexdigest(), artifact["portable_content_sha256"])
                self.assertEqual(len(portable), artifact["portable_content_bytes"])
                self.assertNotIn("/workspace/", portable.decode("utf-8"))
        artifacts = evidence["artifacts"]
        frozen = artifacts["trial-freeze.json"]["content"]
        reviews = artifacts["review-freeze.json"]["content"]
        self.assertEqual(frozen["source_commit"], SOURCE_COMMIT)
        self.assertEqual(len(frozen["source_files"]), 76)
        self.assertEqual(frozen["reviewer_prompt_sha256"], artifacts["REVIEWER_PROMPT.txt"]["original_sha256"])
        self.assertEqual(reviews["grader_prompt_sha256"], artifacts["GRADER_PROMPT.txt"]["original_sha256"])
        for case_id, record in self.records.items():
            truth = self.truth[case_id]
            self.assertEqual(frozen["inputs"][f"review_inputs/{case_id}/plan.pdf"], truth["source_sha256"])
            self.assertEqual(frozen["inputs"][f"review_inputs/{case_id}/job-brief.md"], truth["brief_sha256"])
            for name, digest in reviews["cases"][case_id].items():
                path = f"reviews/{case_id}/{name}"
                if path in artifacts:
                    self.assertEqual(artifacts[path]["original_sha256"], digest)
            self.assertEqual(self.artifact(record, "job_brief")["original_sha256"], truth["brief_sha256"])

    def test_lost_parent_mapping_is_rejected_by_real_normalization(self):
        self.load_trial()
        for case_id, record in self.records.items():
            with self.subTest(case=case_id), self.assertRaises(ValueError):
                validate_normalization(self.content(record, "original_review"), self.content(record, "normalized_review"),
                                       normalization(self.content(record, "adjudication"))[1:])

    def test_lost_atom_is_rejected_by_real_normalization(self):
        self.load_trial()
        for case_id, record in self.records.items():
            normalized = deepcopy(self.content(record, "normalized_review"))
            normalized["claims"].pop()
            with self.subTest(case=case_id), self.assertRaises(ValueError):
                validate_normalization(self.content(record, "original_review"), normalized,
                                       normalization(self.content(record, "adjudication")))

    def test_wrong_source_is_rejected_by_real_normalization_and_scoring(self):
        self.load_trial()
        for case_id, record in self.records.items():
            normalized = deepcopy(self.content(record, "normalized_review"))
            normalized["source_sha256"] = "0" * 64
            grade = self.content(record, "adjudication")
            truth = self.truth[case_id]
            with self.subTest(case=case_id):
                with self.assertRaises(ValueError):
                    validate_normalization(self.content(record, "original_review"), normalized, normalization(grade))
                with self.assertRaises(ValueError):
                    score_trial([issue["id"] for issue in truth["defects"]], normalized,
                                grade["adjudications"], source_sha256=truth["source_sha256"])

    def test_missing_adjudication_is_rejected_by_real_scoring(self):
        self.load_trial()
        for case_id, record in self.records.items():
            truth = self.truth[case_id]
            with self.subTest(case=case_id), self.assertRaises(ValueError):
                score_trial([issue["id"] for issue in truth["defects"]], self.content(record, "normalized_review"),
                            self.content(record, "adjudication")["adjudications"][1:],
                            source_sha256=truth["source_sha256"])


if __name__ == "__main__":
    unittest.main()
