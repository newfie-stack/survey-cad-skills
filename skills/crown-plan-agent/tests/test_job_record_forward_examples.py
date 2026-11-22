"""Preserve invented source bundles and replay their reviewed preparation.

These published cases are regressions. The original model-review grade and its
executed/assisted attribution are immutable historical evidence, not a score for
the current reader. No model calls or work inputs are used by these tests.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys
import tempfile
import unittest
from unittest.mock import patch

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / 'engine'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime_security import load_pdf_runtime
from job_record_review import review_job_records
from job_record_forward_examples import (
    CASE_IDS, make_forward_example, load_forward_truth, rebind_recorded_preparation,
)

PDF = load_pdf_runtime()
RECORDED_RUNTIME = (sys.version_info[:3] == (3, 12, 16)
                    and platform.system() == 'Linux'
                    and platform.machine() in ('x86_64', 'AMD64')
                    and getattr(PDF, 'VersionBind', None) == '2.1'
                    and getattr(PDF, 'VersionFitz', None) == '1.28.6')


class JobRecordForwardExamplesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.truth = load_forward_truth()

    def test_original_phase_accounting_and_attribution_are_preserved(self):
        self.assertEqual(set(CASE_IDS), set(self.truth['cases']))
        phase = self.truth['phases']['initial']
        totals = phase['grade_totals']
        self.assertEqual(totals['planted_defects'], 4)
        self.assertEqual(totals['detected_defects'], 4)
        self.assertEqual(totals['executed_defect_detections'], 1)
        self.assertEqual(totals['assisted_only_defect_detections'], 3)
        self.assertEqual(totals['expected_unresolved'], 1)
        self.assertEqual(totals['correct_unresolved'], 1)
        for key in ('missed_defects', 'false_alarms', 'false_clearances',
                    'unsupported_claims', 'duplicate_finding_claims'):
            self.assertEqual(totals[key], 0)
        initial_cases = [c for c in self.truth['cases'].values() if c['phase'] == 'initial']
        summed = {k: sum(c['original_grade_counts'][k] for c in initial_cases)
                  for k in totals}
        self.assertEqual(summed, totals)
        engine = phase['engine_totals']
        self.assertEqual((engine['requested'], engine['executed'], engine['blocked']), (88, 21, 67))
        self.assertEqual(engine['PASS'], 20)
        self.assertEqual(engine['FAIL'], 1)
        replay = phase['known_preparation_replay']
        self.assertEqual(replay['classification'], 'KNOWN_PREPARATION_REPLAY_NOT_FORWARD_VALIDATION')
        self.assertEqual(replay['source_commit'], 'b5624579add28116bd2e0152781140a763249e01')
        self.assertEqual(replay['original_counts'], engine)
        self.assertEqual(replay['replay_counts'], engine)
        self.assertTrue(all(value == 0 for value in replay['count_differences'].values()))
        self.assertFalse(replay['historical_grade_attribution_changed'])

    def test_portable_oracle_is_bound_separately_from_its_original_utf8_hash(self):
        phase = self.truth['phases']['initial']
        canonical = json.dumps(phase['author_oracle'], sort_keys=True, separators=(',', ':'),
                               ensure_ascii=False, allow_nan=False).encode()
        self.assertEqual(sha256(canonical).hexdigest(), phase['portable_oracle_canonical_sha256'])
        self.assertEqual(phase['original_author_oracle_sha256'],
                         'ad07c57e2d679a8d5c5decafa0f5e172c54f4c40423c1ca79687a1640094e289')
        self.assertEqual(phase['author_oracle']['cases']['H4P7']['classification'], 'clean_control')
        self.assertEqual(len(phase['author_oracle']['cases']['Q6T9']['expected']), 2)
        self.assertEqual(len(phase['author_oracle']['cases']['Z2C8']['unresolved']), 1)

    @unittest.skipUnless(RECORDED_RUNTIME, 'Original bytes recorded on Linux x86_64, Python3.12.16/PyMuPDF2.1/MuPDF1.28.6')
    def test_all_original_input_bytes_match_the_frozen_forward_study(self):
        checked = 0
        for case_id in CASE_IDS:
            paths = make_forward_example(self.root / case_id, case_id)
            expected = self.truth['cases'][case_id]['original_inputs']
            actual = {p.name: p for p in paths.values() if p is not None}
            self.assertEqual(set(actual), set(expected))
            for filename, entry in expected.items():
                with self.subTest(case=case_id, file=filename):
                    raw = actual[filename].read_bytes()
                    self.assertEqual(len(raw), entry['bytes'])
                    self.assertEqual(sha256(raw).hexdigest(), entry['sha256'])
                    checked += 1
        self.assertEqual(checked, 35)

    def test_every_regenerated_pdf_is_native_and_keeps_the_invented_marker(self):
        for case_id in CASE_IDS:
            paths = make_forward_example(self.root / case_id, case_id)
            for key, path in paths.items():
                if path is None or path.suffix != '.pdf':
                    continue
                with self.subTest(case=case_id, source=key), PDF.open(path) as document:
                    self.assertEqual(len(document), 1)
                    self.assertEqual(document[0].get_image_info(), [])
                    text = document[0].get_text()
                    self.assertIn('INVENTED EVALUATION MATERIAL', text)
                    self.assertIn('NO ACTUAL LAND OR COMPANY', text)

    def test_static_category_and_role_oracle_is_visible_in_actual_sources(self):
        paths = make_forward_example(self.root / 'categories', 'Q6T9')
        with PDF.open(paths['plan']) as plan, PDF.open(paths['application']) as form:
            plan_text, form_text = plan[0].get_text(), form[0].get_text()
            self.assertIn('1.160', plan_text)
            self.assertIn('0.440', plan_text)
            self.assertIn('1.240', form_text)
            self.assertIn('0.360', form_text)
            self.assertIn('1.600', plan_text)
            self.assertIn('1.600', form_text)
        paths = make_forward_example(self.root / 'roles', 'V3K5')
        spec, files = rebind_recorded_preparation('V3K5', paths)
        review = review_job_records(paths['plan'], spec, files)
        finding = next(f for f in review['findings'] if f['check_id'] == 'applicant_form')
        self.assertEqual(finding['mechanical_status'], 'FAIL')
        self.assertEqual(finding['observed'], ['Stoneglen Way Energy Ltd.', 'Twinfallow Crossing Ltd.'])
        self.assertEqual(finding['status'], 'REVIEW_REQUIRED')

    def test_saved_preparations_read_actual_regenerated_sources_without_promoting_regulatory_results(self):
        for case_id in CASE_IDS:
            paths = make_forward_example(self.root / case_id, case_id)
            spec, files = rebind_recorded_preparation(case_id, paths)
            before = deepcopy(spec)
            report = review_job_records(paths['plan'], spec, files)
            self.assertEqual(spec, before)
            self.assertEqual(report['plan_source_sha256'], sha256(paths['plan'].read_bytes()).hexdigest())
            self.assertEqual(report['counts']['requested'],
                             self.truth['cases'][case_id]['original_mechanical_counts']['requested'])
            self.assertEqual(report['overall_status'], 'REVIEW_REQUIRED')
            self.assertEqual(report['regulatory_status'], 'NOT_ASSESSED')
            self.assertTrue(all(f['status'] == 'REVIEW_REQUIRED' for f in report['findings']))
            self.assertTrue(all(f['assessment_scope'] == 'JOB_QA_ONLY' for f in report['findings']))
            # These are captured mechanical regressions, not a fresh accuracy
            # score and not a rewrite of the earlier assisted-review grade.
            recorded = self.truth['cases'][case_id]
            expected_counts = recorded.get('known_replay_counts', recorded['original_mechanical_counts'])
            self.assertEqual(report['counts'], expected_counts)
            current = {f['check_id']: {k: f[k] for k in ('mechanical_status', 'execution_status')}
                       for f in report['findings']}
            expected_results = recorded.get('known_replay_results', recorded['original_mechanical_results'])
            self.assertEqual(current, expected_results)
            for field in report['fields'].values():
                if field['status'] == 'READY':
                    self.assertEqual(field['source_sha256'], report['sources'][field['source_id']]['actual_sha256'])
                    self.assertEqual(field['evidence']['source_sha256'], field['source_sha256'])

    def test_missing_current_baseline_is_not_replaced_with_superseded_supplied_area(self):
        paths = make_forward_example(self.root / 'baseline', 'Z2C8')
        spec, files = rebind_recorded_preparation('Z2C8', paths)
        self.assertIsNone(spec['records']['sources']['governing']['source_sha256'])
        self.assertNotIn('governing', files)
        report = review_job_records(paths['plan'], spec, files)
        finding = next(f for f in report['findings'] if f['check_id'] == 'existing_vs_approved')
        self.assertEqual(finding['mechanical_status'], 'REVIEW_REQUIRED')
        self.assertEqual(finding['execution_status'], 'BLOCKED')
        with PDF.open(paths['approved']) as old:
            self.assertIn('SUPERSEDED RECORD', old[0].get_text())
            self.assertIn('2.900 ha', old[0].get_text())

    def test_dense_phase_remains_a_separate_frozen_trial_with_its_own_oracle(self):
        phase = self.truth['phases']['dense_forward']
        self.assertEqual(phase['source_commit'], 'b5624579add28116bd2e0152781140a763249e01')
        self.assertEqual(phase['original_author_oracle_sha256'],
                         '1f948c8c11c0e497da40eb1fe4b50565ea2ac86d1a2215e713b112ff532c0188')
        self.assertEqual(phase['author_oracle']['cases']['B5J8']['classification'], 'clean_control')
        self.assertEqual(phase['author_oracle']['cases']['R8D1']['classification'], 'problem_unresolved_evidence')
        self.assertEqual(sum(len(case['expected_findings']) for case in phase['author_oracle']['cases'].values()), 0)
        self.assertEqual(len(phase['author_oracle']['cases']['R8D1']['expected_unresolved']), 1)
        canonical = json.dumps(phase['author_oracle'], sort_keys=True, separators=(',', ':'),
                               ensure_ascii=False, allow_nan=False).encode()
        self.assertEqual(sha256(canonical).hexdigest(), phase['portable_oracle_canonical_sha256'])
        self.assertEqual(phase['engine_totals']['requested'], 22)
        self.assertEqual(phase['engine_totals']['executed'], 10)
        self.assertEqual(phase['engine_totals']['blocked'], 12)
        self.assertEqual(phase['grading_status'], 'INDEPENDENT_GRADES_FROZEN')
        totals = phase['grade_totals']
        dense_cases = [c for c in self.truth['cases'].values() if c['phase'] == 'dense_forward']
        self.assertEqual({k: sum(c['original_grade_counts'][k] for c in dense_cases)
                          for k in totals}, totals)
        self.assertEqual(totals['planted_defects'], 0)
        self.assertEqual(totals['expected_unresolved'], 1)
        self.assertEqual(totals['correct_unresolved'], 1)
        self.assertEqual(totals['executed_unresolved_detections'], 0)
        self.assertEqual(totals['assisted_only_unresolved_detections'], 1)
        for key in ('false_alarms', 'false_clearances', 'unsupported_claims',
                    'duplicate_finding_claims'):
            self.assertEqual(totals[key], 0)
        limitations = phase['execution_limitations']
        self.assertEqual(limitations['source_resolvable_identity_checks_blocked'], 11)
        self.assertEqual(limitations['genuine_current_record_dependency_checks'], 1)
        self.assertFalse(limitations['engine_blockers_counted_as_detections'])
        self.assertFalse(limitations['assisted_results_promoted_to_engine_results'])
        self.assertNotIn('combined_accuracy', self.truth)

    def test_complete_quantities_execute_but_two_unlabelled_registry_names_stay_open(self):
        for case_id in ('B5J8', 'R8D1'):
            paths = make_forward_example(self.root / case_id, case_id)
            spec, files = rebind_recorded_preparation(case_id, paths)
            report = review_job_records(paths['plan'], spec, files)
            amounts = [f for f in report['findings'] if f['kind'] in ('parts_total', 'record_match')]
            self.assertEqual(len(amounts), 5)
            self.assertTrue(all(f['execution_status'] == 'EXECUTED' and f['mechanical_status'] == 'PASS'
                                for f in amounts))
            self.assertTrue(all(f['status'] == 'REVIEW_REQUIRED' for f in amounts))
            if case_id == 'R8D1':
                applicant = next(f for f in report['findings'] if f['check_id'] == 'applicant_vs_registry')
                self.assertEqual(applicant['mechanical_status'], 'REVIEW_REQUIRED')
                self.assertEqual(applicant['execution_status'], 'BLOCKED')
                field = report['fields']['registry_applicant']
                self.assertIsNone(field['raw_value'])
                originals = [s['text'] for s in field['evidence']['spans']]
                self.assertIn('Cresswake Route Ltd.', originals)
                self.assertIn('Cresswake Passage Ltd.', originals)

    def test_changed_original_reference_fails_before_any_native_record_read(self):
        paths = make_forward_example(self.root / 'changed', 'H4P7')
        spec, files = rebind_recorded_preparation('H4P7', paths)
        reference = paths['registry']
        reference.write_bytes(reference.read_bytes() + b'\n')
        with patch('job_record_review.read_record_fields') as reader:
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                review_job_records(paths['plan'], spec, files)
        reader.assert_not_called()

    def test_corrupted_truth_is_rejected_instead_of_becoming_a_new_oracle(self):
        path = self.root / 'changed-truth.json'
        altered = deepcopy(self.truth)
        altered['phases']['initial']['grade_totals']['executed_defect_detections'] = 4
        path.write_text(json.dumps(altered))
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            load_forward_truth(path)

    def test_generator_cannot_overwrite_existing_or_protected_directories(self):
        existing = self.root / 'exists'
        existing.mkdir()
        marker = existing / 'keep.txt'
        marker.write_text('unchanged')
        with self.assertRaises(FileExistsError):
            make_forward_example(existing, 'H4P7')
        self.assertEqual(marker.read_text(), 'unchanged')
        with self.assertRaises(ValueError):
            make_forward_example(SKILL / 'generated-forward-inputs', 'H4P7')


if __name__ == '__main__':
    unittest.main()
