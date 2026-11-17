"""Invented source evidence for linked revision review; never compliance."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
from inventory_review import inventory_review
try:
    from revision_comparison import build_comparison
except ModuleNotFoundError as exc:
    if exc.name != 'revision_comparison':
        raise
    build_comparison = None


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':'), allow_nan=False).encode()).hexdigest()


class RevisionComparisonTests(unittest.TestCase):
    def setUp(self):
        self.scenario = {'company_name': 'Invented Company', 'purpose': 'Synthetic π'}
        self.rules = [{'requirement_id': 'TEST-SCALE', 'evidence_key': 'scale',
                       'summary': 'Confirm scale', 'check_method': 'numerical_scale',
                       'citation': {'publication_title': 'Invented reference',
                                    'version_date': '2026-01-01', 'page': 88,
                                    'section': 'S1', 'source_url': 'https://example.invalid'}}]
        self.basis = {'engine_version': '0.6.0', 'engine_sha256': 'a' * 64,
                      'scenario_sha256': digest(self.scenario), 'catalogue_sha256': 'b' * 64,
                      'references': [{'name': 'invented-table.json', 'sha256': 'c' * 64}]}
        self.basis['basis_sha256'] = digest(self.basis)
        self.before = self.inventory('baseline.pdf', '1', ['SCALE 1:5000'])
        self.after = self.inventory('revised.pdf', '2', ['SCALE 1:5000'])

    def inventory(self, name, digit, texts):
        return {'source_filename': name, 'source_sha256': digit * 64, 'pages': 2,
                'status': 'TEXT_INVENTORY_ONLY', 'spans': [
                    {'text': text, 'page': 1, 'bbox_points': [20, 30 + i * 30, 200, 45 + i * 30],
                     'page_size_points': [612, 792], 'text_angle_degrees': 0}
                    for i, text in enumerate(texts)]}

    def report(self, inventory, rules=None):
        report = inventory_review(inventory, self.scenario, rules or self.rules)
        report['source_filename'] = inventory['source_filename']
        report['pages'] = inventory['pages']
        report['review_summary'] = {'status': 'REVIEW_REQUIRED',
                                    'not_checked': ['Manual visual/geometry checks remain.']}
        return report

    def compare(self, before_report=None, after_report=None, basis=None):
        self.assertIsNotNone(build_comparison, 'Revision comparison is not implemented')
        return build_comparison(self.before, before_report or self.report(self.before),
                                self.after, after_report or self.report(self.after),
                                basis=self.basis if basis is None else basis)

    def state(self, **kwargs):
        return self.compare(**kwargs)['requirements'][0]['comparison_status']

    def test_same_unique_text_is_review_only_and_source_pages_are_distinct_from_citation(self):
        result = self.compare()
        row = result['requirements'][0]
        self.assertEqual(row['comparison_status'], 'SAME_OBSERVED_TEXT')
        self.assertEqual(row['baseline']['source_text'], 'SCALE 1:5000')
        self.assertEqual(row['baseline']['anchor']['page'], 1)
        self.assertEqual(row['citation']['page'], 88)
        self.assertFalse(row['location_changed'])
        self.assertEqual(result['overall_status'], 'REVIEW_REQUIRED')
        self.assertEqual(result['assessment_type'], 'REVISION_EVIDENCE_COMPARISON_NOT_COMPLIANCE')
        self.assertEqual(result['schema_version'], 1)
        self.assertEqual(result['comparison_type'], 'CROWN_PLAN_REVISION_TEXT_REVIEW')
        self.assertEqual(result['baseline']['pages'], 2)
        self.assertEqual(result['baseline_review_summary'], self.report(self.before)['review_summary'])
        self.assertEqual(sum(result['summary']['finding_counts'].values()), 1)
        self.assertEqual(len(result['summary']['finding_counts']), 6)
        self.assertFalse(result['identical_source_bytes'])
        self.assertTrue(any('automatically' in s for s in result['limitations']))

    def test_all_six_states(self):
        for before, after, expected in [
            (['SCALE 1:5000'], ['SCALE 1:2500'], 'OBSERVED_TEXT_CHANGED'),
            ([], ['SCALE 1:5000'], 'NEWLY_OBSERVED_TEXT'),
            (['SCALE 1:5000'], [], 'PREVIOUS_OBSERVATION_NOT_FOUND'),
            ([], [], 'NOT_COMPARED'),
            (['SCALE 1:5000'] * 2, ['SCALE 1:5000'] * 2, 'AMBIGUOUS')]:
            with self.subTest(expected=expected):
                self.before = self.inventory('baseline.pdf', '1', before)
                self.after = self.inventory('revised.pdf', '2', after)
                self.assertEqual(self.state(), expected)

    def test_repeated_second_match_edit_is_ambiguous_with_independent_literal_delta(self):
        self.before['spans'].append({**self.before['spans'][0], 'bbox_points': [20, 80, 200, 95]})
        self.after['spans'].append({**self.after['spans'][0], 'text': 'SCALE 1:2500',
                                    'bbox_points': [20, 80, 200, 95]})
        result = self.compare()
        self.assertEqual(result['requirements'][0]['comparison_status'], 'AMBIGUOUS')
        self.assertEqual({c['normalized_text'] for c in result['text_changes']},
                         {'SCALE 1:5000', 'SCALE 1:2500'})

    def test_expected_company_replacement_is_lost_match_and_literal_old_new(self):
        self.rules = [{'requirement_id': 'TEST-NAME', 'evidence_key': 'company_name',
                       'summary': 'Confirm company', 'check_method': 'scenario_text'}]
        self.before = self.inventory('baseline.pdf', '1', ['Company: Invented Company'])
        self.after = self.inventory('revised.pdf', '2', ['Company: Unexpected Company'])
        result = self.compare()
        self.assertEqual(result['requirements'][0]['comparison_status'], 'PREVIOUS_OBSERVATION_NOT_FOUND')
        self.assertEqual({c['normalized_text'] for c in result['text_changes']},
                         {'Company: Invented Company', 'Company: Unexpected Company'})

    def test_raw_table_cell_text_is_compared_separately_from_semantic_observation(self):
        self.before['spans'][0]['text'] = '0.020'
        self.after['spans'][0]['text'] = '0.030'
        left, right = self.report(self.before), self.report(self.after)
        for report, raw in [(left, '0.020'), (right, '0.030')]:
            row = report['requirements'][0]
            row.update(evidence_status='OBSERVED_CANDIDATE', candidate_count=1, page=1,
                       bbox_points=[20, 30, 200, 45], observation='Unchanged semantic label',
                       input_evidence={'source_filename': report['source_filename'], 'page': 1,
                                       'bbox_points': [20, 30, 200, 45], 'source_text': raw})
        row = self.compare(left, right)['requirements'][0]
        self.assertEqual(row['comparison_status'], 'OBSERVED_TEXT_CHANGED')
        self.assertEqual(row['baseline']['source_text'], '0.020')
        self.assertEqual(row['revised']['observation'], 'Unchanged semantic label')

    def test_whitespace_only_is_normalized_without_case_or_unicode_folding(self):
        self.after['spans'][0]['text'] = 'SCALE\t1:5000'
        self.assertEqual(self.state(), 'SAME_OBSERVED_TEXT')
        self.after['spans'][0]['text'] = 'scale 1:5000'
        self.assertEqual(self.state(), 'OBSERVED_TEXT_CHANGED')

    def test_location_only_move_size_and_orientation_remain_separate(self):
        self.after['spans'][0].update(page=2, bbox_points=[25, 40, 205, 55])
        row = self.compare()['requirements'][0]
        self.assertEqual(row['comparison_status'], 'SAME_OBSERVED_TEXT')
        self.assertTrue(row['location_changed'])
        self.assertEqual(self.compare()['text_changes'], [])
        self.after['spans'][0].update(page=1, bbox_points=[20, 30, 200, 45],
                                       page_size_points=[700, 800], text_angle_degrees=90)
        row = self.compare()['requirements'][0]
        self.assertTrue(row['location_changed'])
        self.assertEqual(row['revised']['text_angle_degrees'], 90)

    def test_visual_and_missing_text_do_not_close_observations(self):
        left, right = self.report(self.before), self.report(self.after)
        for report in (left, right):
            report['requirements'][0]['evidence_status'] = 'VISUAL_CHECK_REQUIRED'
        row = self.compare(left, right)['requirements'][0]
        self.assertEqual(row['comparison_status'], 'NOT_COMPARED')
        self.assertIsNone(row['location_changed'])
        self.after['spans'] = []
        self.assertEqual(self.state(), 'PREVIOUS_OBSERVATION_NOT_FOUND')

    def test_conflicting_unknown_observations_and_invalid_anchors_are_ambiguous(self):
        left, right = self.report(self.before), self.report(self.after)
        for report in (left, right):
            report['requirements'][0].update(evidence_status='UNKNOWN', candidate_count=None,
                observation='Conflicting total area values found. Confirm the activity total.')
        self.assertEqual(self.state(before_report=left, after_report=right), 'AMBIGUOUS')
        for mutation in ('bounds', 'duplicate', 'raw'):
            with self.subTest(mutation=mutation):
                left = self.report(self.before)
                if mutation == 'bounds': left['requirements'][0]['bbox_points'] = [1, 1, 1, 1]
                elif mutation == 'raw': left['requirements'][0]['input_evidence']['source_text'] = 'OTHER'
                else:
                    self.before['spans'].append(deepcopy(self.before['spans'][0]))
                self.assertEqual(self.state(before_report=left), 'AMBIGUOUS')

    def test_ids_not_sequence_or_row_order_are_identity(self):
        self.rules.append({**self.rules[0], 'requirement_id': 'AAAA'})
        left, right = self.report(self.before), self.report(self.after)
        right['requirements'].reverse()
        for report in (left, right):
            for i, row in enumerate(report['requirements']): row['note_id'] = 'R' + str(i)
        self.assertEqual([r['requirement_id'] for r in self.compare(left, right)['requirements']],
                         ['AAAA', 'TEST-SCALE'])

    def test_source_hash_name_count_and_assessment_binding_are_independent(self):
        for side in ('before', 'after'):
            for field, value in [('source_sha256', '3' * 64), ('source_sha256', 'F' * 64),
                                 ('source_filename', 'wrong.pdf'), ('pages', 99),
                                 ('overall_status', 'PASS'), ('assessment_type', 'COMPLIANCE')]:
                with self.subTest(side=side, field=field):
                    left, right = self.report(self.before), self.report(self.after)
                    (left if side == 'before' else right)[field] = value
                    with self.assertRaises(ValueError): self.compare(left, right)
        left = self.report(self.before); left['summary']['total'] = 2
        with self.assertRaises(ValueError): self.compare(before_report=left)
        right = self.report(self.after)
        right['requirements'][0]['input_evidence']['source_filename'] = 'baseline.pdf'
        with self.assertRaises(ValueError): self.compare(after_report=right)

    def test_changed_scenario_definitions_citations_and_requirement_sets_abort(self):
        for mutation in ('scenario', 'summary', 'instruction', 'citation', 'set', 'evidence_key'):
            with self.subTest(mutation=mutation):
                right = self.report(self.after)
                if mutation == 'scenario': right['scenario']['extra'] = ''
                elif mutation == 'summary': right['requirements'][0]['requirement_summary'] = 'Changed'
                elif mutation == 'instruction': right['requirements'][0]['review_instruction'] = 'Changed'
                elif mutation == 'citation': right['requirements'][0]['source_page'] = 89
                elif mutation == 'set': right['requirements'] = []; right['summary']['total'] = 0
                else: right['requirements'][0]['evidence_key'] = 'other'
                with self.assertRaises(ValueError): self.compare(after_report=right)

    def test_basis_requires_exact_schema_canonical_hashes_and_unique_hashed_references(self):
        for mutation in ('missing', 'extra', 'hash', 'uppercase', 'version', 'scenario', 'refhash', 'dupe'):
            with self.subTest(mutation=mutation):
                basis = deepcopy(self.basis)
                if mutation == 'missing': basis.pop('engine_sha256')
                elif mutation == 'extra': basis['unknown'] = ''
                elif mutation == 'hash': basis['basis_sha256'] = 'd' * 64
                elif mutation == 'uppercase': basis['catalogue_sha256'] = 'B' * 64
                elif mutation == 'version': basis['engine_version'] = '0.5.0'
                elif mutation == 'scenario': basis['scenario_sha256'] = 'd' * 64
                elif mutation == 'refhash': basis['references'][0]['sha256'] = 'x'
                else: basis['references'].append(deepcopy(basis['references'][0]))
                if mutation != 'hash':
                    basis['basis_sha256'] = digest({k: v for k, v in basis.items() if k != 'basis_sha256'})
                with self.assertRaises(ValueError): self.compare(basis=basis)

    def test_review_context_exposes_hash_bound_application_values_and_is_detached(self):
        self.scenario.update(stage='initial', regulator='AER',
                             details={'labels': ['Synthetic application']})
        self.basis['scenario_sha256'] = digest(self.scenario)
        self.basis['basis_sha256'] = digest({key: value for key, value in self.basis.items()
                                             if key != 'basis_sha256'})
        left, right = self.report(self.before), self.report(self.after)
        original = deepcopy((left, right, self.scenario))
        result = self.compare(left, right)
        self.assertEqual(result['review_context'], self.scenario)
        self.assertEqual(result['review_context']['stage'], 'initial')
        self.assertEqual(result['review_context']['regulator'], 'AER')
        self.assertEqual(digest(result['review_context']), result['basis']['scenario_sha256'])
        result['review_context']['details']['labels'].append('Changed output only')
        self.assertEqual((left, right, self.scenario), original)

    def test_identical_bytes_and_inputs_are_unchanged_and_outputs_detached(self):
        self.after['source_sha256'] = self.before['source_sha256']
        left, right = self.report(self.before), self.report(self.after)
        originals = deepcopy((self.before, left, self.after, right, self.basis))
        result = self.compare(left, right)
        self.assertTrue(result['identical_source_bytes'])
        self.assertEqual((self.before, left, self.after, right, self.basis), originals)
        result['basis']['references'][0]['name'] = 'mutated'
        result['baseline_review_summary']['not_checked'].append('mutated')
        self.assertEqual((self.before, left, self.after, right, self.basis), originals)

    def test_tuple_bounds_and_legacy_observation_fallback_use_validated_raw_span(self):
        for inventory in (self.before, self.after):
            inventory['spans'][0]['bbox_points'] = tuple(inventory['spans'][0]['bbox_points'])
        left, right = self.report(self.before), self.report(self.after)
        for report in (left, right):
            report['requirements'][0]['input_evidence'].pop('source_text')
        result = self.compare(left, right)
        self.assertEqual(result['requirements'][0]['comparison_status'], 'SAME_OBSERVED_TEXT')
        self.assertEqual(result['requirements'][0]['baseline']['source_text'], 'SCALE 1:5000')

    def test_unknown_coordinate_frames_and_invalid_orientation_cannot_claim_equal_observations(self):
        for mutation in ('inventory_frame', 'span_frame', 'angle'):
            with self.subTest(mutation=mutation):
                self.after = self.inventory('revised.pdf', '2', ['SCALE 1:5000'])
                if mutation == 'inventory_frame': self.after['coordinate_frame'] = 'OTHER'
                elif mutation == 'span_frame': self.after['spans'][0]['coordinate_frame'] = 'OTHER'
                else: self.after['spans'][0]['text_angle_degrees'] = float('nan')
                row = self.compare()['requirements'][0]
                self.assertEqual(row['comparison_status'], 'AMBIGUOUS')
                self.assertIsNone(row['revised']['anchor'])

    def test_definition_json_types_and_omitted_values_are_distinct(self):
        for omitted in (False, True):
            with self.subTest(omitted=omitted):
                left, right = self.report(self.before), self.report(self.after)
                left['requirements'][0]['expected_value'] = 1
                right['requirements'][0]['expected_value'] = True
                if omitted:
                    left['requirements'][0].pop('expected_value')
                    right['requirements'][0]['expected_value'] = None
                with self.assertRaises(ValueError): self.compare(left, right)

    def test_actual_conflicting_area_reports_stay_ambiguous(self):
        self.rules = [{'requirement_id': 'TEST-AREA', 'evidence_key': 'area',
                       'summary': 'Confirm total', 'check_method': 'total_area'}]
        self.before = self.inventory('baseline.pdf', '1', ['Total area 0.020 ha', 'Total area 0.030 ha'])
        self.after = self.inventory('revised.pdf', '2', ['Total area 0.020 ha', 'Total area 0.040 ha'])
        self.assertEqual(self.state(), 'AMBIGUOUS')

    def test_oversized_complete_json_is_rejected_instead_of_publishing_partial_rows(self):
        self.before = self.inventory('baseline.pdf', '1', ['X' * 8192] * 2600)
        self.after = self.inventory('revised.pdf', '2', [])
        with self.assertRaisesRegex(ValueError, '20 MiB'):
            self.compare()

    def test_nonfinite_scenario_and_aggregate_summary_overflow_are_rejected(self):
        left = self.report(self.before)
        left['scenario']['invalid'] = float('nan')
        with self.assertRaises(ValueError): self.compare(before_report=left)
        left = self.report(self.before)
        left['review_summary']['extra'] = ['x' * 8192] * 65
        with self.assertRaisesRegex(ValueError, 'aggregate limit'):
            self.compare(before_report=left)

    def test_unrelated_unlocated_span_does_not_break_a_unique_source_anchor(self):
        self.before['spans'].insert(0, {'text': 'Unrelated span', 'page': 1,
                                         'bbox_points': None, 'page_size_points': [612, 792]})
        self.assertEqual(self.state(), 'SAME_OBSERVED_TEXT')

    def test_inventory_text_is_bounded_before_note_planning_processes_spans(self):
        class OversizedText(str):
            def strip(self, *args): raise AssertionError('oversized span processed')
        left = self.report(self.before)
        self.before['spans'][0]['text'] = OversizedText('x' * 8193)
        with self.assertRaises(ValueError): self.compare(before_report=left)

    def test_retained_strings_and_summary_collections_are_explicitly_bounded(self):
        class OversizedText(str):
            def strip(self, *args): raise AssertionError('oversized input processed')
        for place in ('source', 'summary', 'scenario', 'count'):
            with self.subTest(place=place):
                left = self.report(self.before)
                huge = OversizedText('x' * 8193)
                if place == 'source': left['requirements'][0]['input_evidence']['source_text'] = huge
                elif place == 'summary': left['review_summary']['headline'] = huge
                elif place == 'scenario': left['scenario']['extra'] = huge
                else: left['review_summary']['not_checked'] = ['same'] * 201
                with self.assertRaises(ValueError): self.compare(before_report=left)


if __name__ == '__main__':
    unittest.main()
