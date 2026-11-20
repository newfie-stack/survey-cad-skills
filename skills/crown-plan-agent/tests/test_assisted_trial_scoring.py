"""A count of model claims is not evidence that the planted issues were found."""
import importlib.util
import unittest


SOURCE = "1" * 64


def claim(cid, kind="finding"):
    return {"id": cid, "kind": kind, "claim": "An atomic drawing observation",
            "location": "Sheet 1, selected frame", "evidence": ["Invented printed evidence"]}


def grade(cid, verdict, defects=(), **extra):
    return {"claim_id": cid, "verdict": verdict, "defect_ids": list(defects),
            "rationale": "Independent semantic adjudication of the saved claim", **extra}


class AssistedTrialScoringTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("assisted_trial_scoring"),
                             "Source-bound assisted-trial scorer is not implemented")
        from assisted_trial_scoring import score_trial
        self.score = score_trial

    def run_case(self, defects, claims, grades, source=SOURCE):
        return self.score(defects, {"source_sha256": source, "claims": claims}, grades,
                          source_sha256=SOURCE)

    def test_true_finding_and_false_alarm_are_not_two_detections(self):
        row = self.run_case(["D1", "D2"], [claim("F1"), claim("F2")],
                            [grade("F1", "FOUND", ["D1"]), grade("F2", "FALSE_ALARM")])
        self.assertEqual(row["detected_defects"], 1)
        self.assertEqual(row["missed_defect_ids"], ["D2"])
        self.assertEqual(row["false_alarm_claim_ids"], ["F2"])
        self.assertFalse(row["all_planted_defects_found"])

    def test_paraphrased_findings_get_one_detection_and_a_duplicate(self):
        row = self.run_case(["D1"], [claim("F1"), claim("F2")],
                            [grade("F1", "FOUND", ["D1"]),
                             grade("F2", "DUPLICATE", duplicate_of="F1")])
        self.assertEqual(row["detected_defects"], 1)
        self.assertEqual(row["duplicate_claim_ids"], ["F2"])
        self.assertEqual(row["false_alarms"], 0)

    def test_unmarked_repeat_of_one_truth_issue_still_cannot_inflate_recall(self):
        row = self.run_case(["D1"], [claim("F1"), claim("F2")],
                            [grade("F1", "FOUND", ["D1"]), grade("F2", "FOUND", ["D1"])])
        self.assertEqual(row["detected_defects"], 1)
        self.assertEqual(row["duplicate_claim_ids"], ["F2"])

    def test_blanket_false_clearance_retains_every_affected_issue_and_contradiction(self):
        row = self.run_case(["D1", "D2"], [claim("F1"), claim("C1", "clearance")],
                            [grade("F1", "FOUND", ["D1"]),
                             grade("C1", "FALSE_CLEARANCE", ["D1", "D2"])])
        self.assertEqual(row["false_clearances"], 1)
        self.assertEqual(row["falsely_cleared_defect_ids"], ["D1", "D2"])
        self.assertEqual(row["contradicted_defect_ids"], ["D1"])
        self.assertFalse(row["no_contradicted_or_unsupported_claims"])

    def test_one_unsplit_finding_cannot_receive_credit_for_two_truth_issues(self):
        with self.assertRaises(ValueError):
            self.run_case(["D1", "D2"], [claim("F1")],
                          [grade("F1", "FOUND", ["D1", "D2"])])

    def test_clearance_claim_count_is_separate_from_unique_falsely_cleared_issues(self):
        row = self.run_case(["D1"], [claim("C1", "clearance"), claim("C2", "clearance")],
                            [grade("C1", "FALSE_CLEARANCE", ["D1"]),
                             grade("C2", "FALSE_CLEARANCE", ["D1"])])
        self.assertEqual(row["false_clearance_claims"], 2)
        self.assertEqual(row["falsely_cleared_defects"], 1)

    def test_unresolved_and_manual_referral_are_not_detection_credit(self):
        row = self.run_case(["D1"], [claim("U1", "unresolved"), claim("M1", "manual")],
                            [grade("U1", "UNRESOLVED", ["D1"]), grade("M1", "MANUAL")])
        self.assertEqual(row["detected_defects"], 0)
        self.assertEqual(row["missed_defect_ids"], ["D1"])
        self.assertEqual(row["unresolved_claim_ids"], ["U1"])
        self.assertEqual(row["manual_claim_ids"], ["M1"])

    def test_clean_control_can_have_no_assertions_without_inventing_a_pass(self):
        row = self.run_case([], [], [])
        self.assertEqual(row["known_defects"], 0)
        self.assertEqual(row["false_alarms"], 0)
        self.assertTrue(row["all_planted_defects_found"])
        self.assertNotIn("plan_approved", row)

    def test_unsupported_and_outside_oracle_claims_are_visible_without_credit(self):
        row = self.run_case([], [claim("F1"), claim("F2")],
                            [grade("F1", "UNSUPPORTED"), grade("F2", "ORACLE_REVIEW")])
        self.assertEqual(row["detected_defects"], 0)
        self.assertEqual(row["unsupported_claim_ids"], ["F1"])
        self.assertEqual(row["oracle_review_claim_ids"], ["F2"])
        self.assertFalse(row["measurement_complete"])

    def test_every_saved_claim_needs_exactly_one_adjudication(self):
        for rows in ([], [grade("extra", "FALSE_ALARM")],
                     [grade("F1", "FALSE_ALARM"), grade("F1", "FALSE_ALARM")]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.run_case([], [claim("F1")], rows)

    def test_wrong_source_unknown_truth_ids_and_wrong_claim_kinds_are_rejected(self):
        with self.assertRaises(ValueError):
            self.run_case([], [], [], source="2" * 64)
        with self.assertRaises(ValueError):
            self.run_case(["D1"], [claim("F1")], [grade("F1", "FOUND", ["D2"])])
        with self.assertRaises(ValueError):
            self.run_case(["D1"], [claim("U1", "unresolved")], [grade("U1", "FOUND", ["D1"])])

    def test_duplicate_cycles_or_unknown_targets_are_rejected(self):
        for target in ("F1", "missing"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                self.run_case([], [claim("F1")], [grade("F1", "DUPLICATE", duplicate_of=target)])
        with self.assertRaises(ValueError):
            self.run_case([], [claim("F1"), claim("F2")],
                          [grade("F1", "DUPLICATE", duplicate_of="F2"),
                           grade("F2", "DUPLICATE", duplicate_of="F1")])

    def test_atomic_normalization_preserves_both_original_claims(self):
        from assisted_trial_scoring import validate_normalization
        raw = {"source_sha256": SOURCE, "claims": [claim("C1"), claim("C2", "clearance")]}
        normalized = {"source_sha256": SOURCE, "claims": [
            {**claim("C1.a"), "parent_id": "C1"}, {**claim("C1.b"), "parent_id": "C1"},
            {**claim("C2", "clearance"), "parent_id": "C2"}]}
        mappings = [{"parent_id": "C1", "normalized_ids": ["C1.a", "C1.b"], "rationale": "Split compound assertion"},
                    {"parent_id": "C2", "normalized_ids": ["C2"], "rationale": "Already atomic"}]
        self.assertEqual(validate_normalization(raw, normalized, mappings), 3)
        with self.assertRaises(ValueError):
            validate_normalization(raw, normalized, mappings[:1])

    def test_normalization_cannot_reassign_a_claim_or_change_source(self):
        from assisted_trial_scoring import validate_normalization
        raw = {"source_sha256": SOURCE, "claims": [claim("C1")]}
        mapping = [{"parent_id": "C1", "normalized_ids": ["N1"], "rationale": "Atomic copy"}]
        for source, parent in ((SOURCE, "other"), ("2" * 64, "C1")):
            with self.subTest(source=source, parent=parent), self.assertRaises(ValueError):
                validate_normalization(raw, {"source_sha256": source, "claims": [
                    {**claim("N1"), "parent_id": parent}]}, mapping)


if __name__ == "__main__":
    unittest.main()
