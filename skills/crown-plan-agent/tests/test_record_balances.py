"""Declared printed balances retain source, unit and scope boundaries."""
from copy import deepcopy
import sys
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / 'engine'))
from record_balances import review_record_balances, validate_balances


class RecordBalanceTests(unittest.TestCase):
    def setUp(self):
        self.sha = 'a' * 64
        self.result = {'fields': {}, 'sources': {'plan': self.source('PLAN', self.sha)}}
        self.field_specs = {}
        self.balance = {'id': 'total_area', 'kind': 'parts_total',
                        'scope_review': {'status': 'COMPLETE_FOR_DECLARED_EQUATION',
                                         'reviewer': 'Invented reviewer',
                                         'basis': 'Invented complete printed ledger'},
                        'subject_id': 'activity-A', 'measurement_scope': 'entire-activity',
                        'unit': 'ha', 'tolerance': '0.000',
                        'tolerance_basis': 'Exact printed amounts in invented example',
                        'terms': [{'field_id': 'part_a', 'component_id': 'component_a', 'role': 'component'},
                                  {'field_id': 'part_b', 'component_id': 'component_b', 'role': 'component'}],
                        'total_field_id': 'total', 'workbook_check_id': 'C_1_3_6_3_01'}
        self.add_field('part_a', '1.000 ha', 40)
        self.add_field('part_b', '2.000 ha', 80)
        self.add_field('total', '3.000 ha', 120)

    def source(self, kind, sha, status='CURRENT_FOR_REVIEW'):
        return {'source_sha256': sha, 'source_kind': kind, 'status': 'READY',
                'subject_id': 'activity-A', 'review': {'status': status,
                'reviewer': 'Invented reviewer', 'basis': 'Invented reviewed source'}}

    def add_field(self, fid, raw, y, *, unit_header=None, source_id='plan', sha=None,
                  semantic_role='area', pointer=None, source_kind=None):
        digest = sha or self.sha
        kind = source_kind or self.result['sources'].get(source_id, {}).get('source_kind', 'OTHER_RECORD')
        evidence = {'source_id': source_id, 'source_kind': kind, 'source_sha256': digest,
                    'page': 1, 'bbox_points': [10, y, 180, y + 20], 'text': raw,
                    'spans': [{'text': raw, 'bbox_points': [10, y, 180, y + 20]}]}
        if pointer is not None:
            evidence = {'source_id': source_id, 'source_kind': kind,
                        'source_sha256': digest, 'pointer': pointer, 'text': raw}
        unit_evidence = None
        if unit_header is not None:
            unit_evidence = {'source_id': source_id, 'source_kind': kind, 'source_sha256': digest,
                             'page': 1, 'bbox_points': [200, 10, 270, 30], 'text': unit_header,
                             'spans': [{'text': unit_header, 'bbox_points': [200, 10, 270, 30]}]}
        self.result['fields'][fid] = {
            'status': 'READY', 'raw_value': raw, 'unit_raw_value': unit_header,
            'semantic_role': semantic_role, 'subject_id': 'activity-A',
            'measurement_scope': 'entire-activity', 'source_id': source_id,
            'source_sha256': digest, 'evidence': evidence, 'unit_evidence': unit_evidence}
        self.field_specs[fid] = {
            'source_id': source_id, 'semantic_role': semantic_role,
            'subject_id': 'activity-A', 'measurement_scope': 'entire-activity',
            'selector': {'page': 1, 'bbox_points': [10, y, 180, y + 20], 'role': 'Invented amount'},
            'unit_selector': None}

    def review(self, balance=None, result=None):
        before = deepcopy((balance or self.balance, result or self.result))
        found = review_record_balances(result or self.result, [balance or self.balance])[0]
        self.assertEqual((balance or self.balance, result or self.result), before)
        self.assertEqual(found['status'], 'REVIEW_REQUIRED')
        self.assertEqual(found['spatial_partition_status'], 'REVIEW_REQUIRED')
        self.assertTrue(found['residual_review'])
        return found

    def test_exact_parts_balance_preserves_evidence(self):
        validate_balances([self.balance], self.field_specs)
        result = self.review()
        self.assertEqual(result['mechanical_status'], 'PASS')
        self.assertEqual(result['execution_status'], 'EXECUTED')
        self.assertEqual(result['expected'], '3.000')
        self.assertEqual(result['difference'], '0.000')
        self.assertEqual(len(result['evidence']), 3)

    def test_difference_and_inclusive_tolerance_use_decimal_values(self):
        self.result['fields']['total']['raw_value'] = '3.001 ha'
        self.balance['tolerance'] = '0.001'
        self.assertEqual(self.review()['mechanical_status'], 'PASS')
        self.balance['tolerance'] = '0.0009'
        result = self.review()
        self.assertEqual(result['mechanical_status'], 'FAIL')
        self.assertEqual(result['difference'], '0.001')

    def test_equal_values_from_independent_components_are_not_deduplicated(self):
        self.add_field('part_b', '1.000 ha', 80)
        self.add_field('total', '2.000 ha', 120)
        self.assertEqual(self.review()['expected'], '2.000')
        self.assertEqual(self.review()['mechanical_status'], 'PASS')

    def test_amendment_uses_one_approved_plus_additions_minus_deletions(self):
        self.add_field('approved', '10.000 ha', 160, source_id='old', sha='b' * 64, source_kind='APPROVED_RECORD')
        self.result['sources']['old'] = self.source('APPROVED_RECORD', 'b' * 64, 'HISTORICAL_BASIS')
        self.add_field('total', '9.000 ha', 120)
        balance = deepcopy(self.balance)
        balance.update(kind='amendment', workbook_check_id='C_3_3_3_1_05', terms=[
            {'field_id': 'approved', 'component_id': 'approved', 'role': 'approved'},
            {'field_id': 'part_a', 'component_id': 'added', 'role': 'addition'},
            {'field_id': 'part_b', 'component_id': 'deleted', 'role': 'deletion'}])
        validate_balances([balance], self.field_specs)
        self.assertEqual(self.review(balance)['mechanical_status'], 'PASS')
        balance['terms'][2]['role'] = 'addition'
        self.assertEqual(self.review(balance)['expected'], '13.000')
        self.assertEqual(self.review(balance)['mechanical_status'], 'FAIL')

    def test_gross_minus_exclusions_is_job_qa_without_regulatory_binding(self):
        balance = deepcopy(self.balance)
        balance.update(kind='gross_net', workbook_check_id=None, terms=[
            {'field_id': 'total', 'component_id': 'gross', 'role': 'gross'},
            {'field_id': 'part_a', 'component_id': 'exclusion', 'role': 'exclusion'}],
            total_field_id='part_b')
        validate_balances([balance], self.field_specs)
        result = self.review(balance)
        self.assertEqual(result['mechanical_status'], 'PASS')
        self.assertEqual(result['assessment_scope'], 'JOB_QA_ONLY')
        self.assertIsNone(result['workbook_check_id'])

    def test_negative_computed_total_fails_even_inside_a_large_tolerance(self):
        balance = deepcopy(self.balance)
        balance.update(kind='gross_net', workbook_check_id=None, tolerance='100', terms=[
            {'field_id': 'part_a', 'component_id': 'gross', 'role': 'gross'},
            {'field_id': 'part_b', 'component_id': 'exclusion', 'role': 'exclusion'}])
        result = self.review(balance)
        self.assertEqual(result['mechanical_status'], 'FAIL')
        self.assertEqual(result['expected'], '-1.000')

    def test_length_schedule_uses_length_fields_and_metres(self):
        for fid, raw, y in [('part_a', '100.00 m', 40), ('part_b', '250.00 m', 80), ('total', '350.00 m', 120)]:
            self.add_field(fid, raw, y, semantic_role='length')
        balance = {**self.balance, 'kind': 'length_schedule', 'unit': 'm', 'workbook_check_id': 'C_1_3_6_6_02'}
        validate_balances([balance], self.field_specs)
        self.assertEqual(self.review(balance)['mechanical_status'], 'PASS')

    def record_match(self, value='3.000 ha', *, kind='APPLICATION_FORM', review='CURRENT_FOR_REVIEW'):
        self.add_field('reference', value, 180, source_id='form', sha='b' * 64, source_kind=kind)
        self.result['sources']['form'] = self.source(kind, 'b' * 64, review)
        balance = deepcopy(self.balance)
        balance.update(kind='record_match', workbook_check_id=None, terms=[
            {'field_id': 'reference', 'component_id': 'record', 'role': 'reference'}])
        return balance

    def test_record_match_compares_actual_plan_and_reference_amounts(self):
        balance = self.record_match()
        validate_balances([balance], self.field_specs)
        result = self.review(balance)
        self.assertEqual(result['mechanical_status'], 'PASS')
        self.assertEqual(result['assessment_scope'], 'JOB_QA_ONLY')
        self.assertEqual(result['expected'], '3.000')
        self.result['fields']['reference']['raw_value'] = '3.001 ha'
        self.assertEqual(self.review(balance)['mechanical_status'], 'FAIL')
        self.assertEqual(self.review(balance)['difference'], '0.001')

    def test_historical_record_match_requires_approved_record_and_correct_scope(self):
        balance = self.record_match(kind='APPROVED_RECORD', review='HISTORICAL_BASIS')
        self.assertEqual(self.review(balance)['mechanical_status'], 'PASS')
        for mutation in ['wrong_kind', 'wrong_scope', 'unconfirmed']:
            result = deepcopy(self.result)
            if mutation == 'wrong_kind': result['sources']['form']['source_kind'] = 'APPLICATION_FORM'
            if mutation == 'wrong_scope': result['fields']['reference']['measurement_scope'] = 'added-area-only'
            if mutation == 'unconfirmed': result['sources']['form']['review']['status'] = 'UNCONFIRMED'
            with self.subTest(mutation=mutation):
                self.assertEqual(self.review(balance, result)['mechanical_status'], 'REVIEW_REQUIRED')

    def test_record_match_rejects_copy_alias_and_wrong_plan_record_roles(self):
        balance = self.record_match()
        for mutation in ['same_blob', 'plan_reference', 'record_total']:
            result = deepcopy(self.result)
            if mutation == 'same_blob':
                result['sources']['form']['source_sha256'] = self.sha
                result['fields']['reference']['source_sha256'] = self.sha
                result['fields']['reference']['evidence']['source_sha256'] = self.sha
            if mutation == 'plan_reference': result['sources']['form']['source_kind'] = 'PLAN'
            if mutation == 'record_total': result['sources']['plan']['source_kind'] = 'APPLICATION_FORM'
            with self.subTest(mutation=mutation):
                self.assertEqual(self.review(balance, result)['mechanical_status'], 'REVIEW_REQUIRED')

    def test_record_match_supports_length_without_implicit_conversion(self):
        balance = self.record_match('100.00 m')
        self.add_field('reference', '100.00 m', 180, source_id='form', sha='b' * 64, semantic_role='length')
        self.add_field('total', '100.00 m', 120, semantic_role='length')
        balance.update(unit='m')
        validate_balances([balance], self.field_specs)
        self.assertEqual(self.review(balance)['mechanical_status'], 'PASS')
        self.result['fields']['reference']['raw_value'] = '0.100 km'
        self.assertEqual(self.review(balance)['mechanical_status'], 'REVIEW_REQUIRED')

    def test_record_match_has_exactly_one_reference_and_no_clause_binding(self):
        balance = self.record_match()
        invalid = []
        candidate = deepcopy(balance)
        candidate['terms'].append({'field_id': 'part_a', 'component_id': 'second', 'role': 'reference'})
        invalid.append(candidate)
        candidate = deepcopy(balance); candidate['workbook_check_id'] = 'C_1_3_6_3_01'; invalid.append(candidate)
        for candidate in invalid:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                validate_balances([candidate], self.field_specs)

    def test_standalone_values_need_actual_matching_unit_headers(self):
        for fid, value, y in [('part_a', '1.000', 40), ('part_b', '2.000', 80), ('total', '3.000', 120)]:
            self.add_field(fid, value, y, unit_header='Area (ha)')
        self.assertEqual(self.review()['mechanical_status'], 'PASS')
        self.result['fields']['part_a']['unit_evidence'] = None
        self.assertEqual(self.review()['mechanical_status'], 'REVIEW_REQUIRED')

    def test_missing_wrong_competing_or_guessed_units_block_comparison(self):
        for header, value in [(None, '1.000'), ('Area (m2)', '1.000 ha'), ('ha / acres', '1.000'),
                              ('Area', '1.000'), ('ha', '1.000 m2')]:
            with self.subTest(header=header, value=value):
                self.add_field('part_a', value, 40, unit_header=header)
                self.assertEqual(self.review()['mechanical_status'], 'REVIEW_REQUIRED')

    def test_grouped_amounts_are_exact_and_malformed_values_remain_unresolved(self):
        self.add_field('part_a', '1,000.10 ha.', 40)
        self.add_field('part_b', '2 000.20 ha.', 80)
        self.add_field('total', '3,000.30 ha.', 120)
        self.assertEqual(self.review()['mechanical_status'], 'PASS')
        for raw in ['1,00.10 ha', '1e3 ha', '-1000 ha', '1000 ha APPROXIMATE', '1000 ha 1001 ha']:
            with self.subTest(raw=raw):
                self.add_field('part_a', raw, 40)
                self.assertEqual(self.review()['mechanical_status'], 'REVIEW_REQUIRED')

    def test_incomplete_scope_unreadable_field_or_different_subject_blocks(self):
        for change in ['scope', 'field', 'subject', 'measurement']:
            balance, result = deepcopy(self.balance), deepcopy(self.result)
            if change == 'scope': balance['scope_review']['status'] = 'UNCONFIRMED'
            if change == 'field': result['fields']['part_a']['status'] = 'REVIEW_REQUIRED'
            if change == 'subject': result['fields']['part_a']['subject_id'] = 'neighbouring-activity'
            if change == 'measurement': result['fields']['part_a']['measurement_scope'] = 'added-area-only'
            with self.subTest(change=change):
                found = self.review(balance, result)
                self.assertEqual(found['mechanical_status'], 'REVIEW_REQUIRED')
                self.assertEqual(found['execution_status'], 'BLOCKED')

    def test_historical_nonapproved_or_unconfirmed_sources_block(self):
        for status in ['HISTORICAL_BASIS', 'UNCONFIRMED', None]:
            with self.subTest(status=status):
                result = deepcopy(self.result)
                result['sources']['plan']['review']['status'] = status
                self.assertEqual(self.review(result=result)['mechanical_status'], 'REVIEW_REQUIRED')

    def test_mismatched_source_or_unbound_unit_evidence_blocks(self):
        for location in ['field', 'source', 'evidence', 'unit']:
            result = deepcopy(self.result)
            if location == 'field': result['fields']['part_a']['source_sha256'] = 'c' * 64
            if location == 'source': result['sources']['plan']['source_sha256'] = 'c' * 64
            if location == 'evidence': result['fields']['part_a']['evidence']['source_id'] = 'unrelated'
            if location == 'unit':
                self.add_field('part_a', '1.000', 40, unit_header='ha')
                result = deepcopy(self.result)
                result['fields']['part_a']['unit_evidence']['source_sha256'] = 'c' * 64
            with self.subTest(location=location):
                self.assertEqual(self.review(result=result)['mechanical_status'], 'REVIEW_REQUIRED')

    def test_reused_native_observations_are_not_independent_components(self):
        self.result['fields']['part_b']['evidence'] = deepcopy(self.result['fields']['part_a']['evidence'])
        self.result['fields']['part_b']['raw_value'] = '1.000 ha'
        self.add_field('total', '2.000 ha', 120)
        self.assertEqual(self.review()['mechanical_status'], 'REVIEW_REQUIRED')

    def test_same_snapshot_alias_and_json_pointer_cannot_duplicate_an_amount(self):
        self.add_field('part_a', '1.000 ha', 40, pointer='/area')
        self.add_field('part_b', '1.000 ha', 80, pointer='/area', source_id='alias', source_kind='PLAN')
        self.result['sources']['alias'] = deepcopy(self.result['sources']['plan'])
        self.add_field('total', '2.000 ha', 120, pointer='/total')
        self.assertEqual(self.review()['mechanical_status'], 'REVIEW_REQUIRED')

    def test_empty_balance_list_is_supported_and_inputs_are_strict(self):
        self.assertEqual(validate_balances([], {}), [])
        self.assertEqual(review_record_balances({'fields': {}, 'sources': {}}, []), [])
        invalid = []
        for key, value in [('kind', 'eval'), ('unit', 'ac'), ('tolerance', '-1'), ('workbook_check_id', 'C_1_3_5_2_02')]:
            candidate = deepcopy(self.balance); candidate[key] = value; invalid.append(candidate)
        for mutate in ['duplicate_field', 'duplicate_component', 'total_reused', 'extra', 'missing', 'unknown_field', 'wrong_dimension']:
            candidate = deepcopy(self.balance)
            if mutate == 'duplicate_field': candidate['terms'][1]['field_id'] = 'part_a'
            if mutate == 'duplicate_component': candidate['terms'][1]['component_id'] = 'component_a'
            if mutate == 'total_reused': candidate['total_field_id'] = 'part_a'
            if mutate == 'extra': candidate['expression'] = '1+2'
            if mutate == 'missing': candidate.pop('scope_review')
            if mutate == 'unknown_field': candidate['total_field_id'] = 'missing'
            if mutate == 'wrong_dimension': candidate.update(kind='length_schedule', unit='m', workbook_check_id=None)
            invalid.append(candidate)
        for candidate in invalid:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                validate_balances([candidate], self.field_specs)
        with self.assertRaises(ValueError): validate_balances([self.balance] * 51, self.field_specs)

    def test_fixed_role_constraints_and_bindings_are_enforced(self):
        candidates = []
        for kind in ['amendment', 'gross_net']:
            candidate = deepcopy(self.balance); candidate.update(kind=kind, workbook_check_id=None)
            candidates.append(candidate)
        candidate = deepcopy(self.balance); candidate['terms'][0]['role'] = 'addition'; candidates.append(candidate)
        candidate = deepcopy(self.balance); candidate['workbook_check_id'] = 'C_3_3_3_1_05'; candidates.append(candidate)
        for candidate in candidates:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                validate_balances([candidate], self.field_specs)

    def test_unknown_or_different_field_scope_is_valid_intent_but_blocked_evidence(self):
        for subject, scope in [(None, None), ('activity-B', 'entire-activity'), ('activity-A', 'added-only')]:
            field_specs, result = deepcopy(self.field_specs), deepcopy(self.result)
            field_specs['part_a'].update(subject_id=subject, measurement_scope=scope)
            result['fields']['part_a'].update(subject_id=subject, measurement_scope=scope)
            with self.subTest(subject=subject, scope=scope):
                validate_balances([self.balance], field_specs)
                self.assertEqual(self.review(result=result)['mechanical_status'], 'REVIEW_REQUIRED')

    def test_source_readiness_subject_review_basis_and_kind_are_required(self):
        for mutation in ['status', 'subject', 'reviewer', 'basis', 'kind']:
            result = deepcopy(self.result)
            source = result['sources']['plan']
            if mutation == 'status': source['status'] = 'REVIEW_REQUIRED'
            if mutation == 'subject': source['subject_id'] = 'activity-B'
            if mutation == 'reviewer': source['review']['reviewer'] = 'UNKNOWN'
            if mutation == 'basis': source['review']['basis'] = None
            if mutation == 'kind': result['fields']['part_a']['evidence']['source_kind'] = 'APPLICATION_FORM'
            with self.subTest(mutation=mutation):
                self.assertEqual(self.review(result=result)['mechanical_status'], 'REVIEW_REQUIRED')

    def test_matching_unknown_subject_scope_or_tolerance_basis_does_not_clear(self):
        for mutation in ['subject_id', 'measurement_scope', 'tolerance_basis']:
            balance, result = deepcopy(self.balance), deepcopy(self.result)
            if mutation == 'tolerance_basis':
                balance[mutation] = 'UNKNOWN'
            else:
                balance[mutation] = 'UNKNOWN'
                for field in result['fields'].values():field[mutation] = 'UNKNOWN'
                if mutation == 'subject_id': result['sources']['plan']['subject_id'] = 'UNKNOWN'
            with self.subTest(mutation=mutation):
                self.assertEqual(self.review(balance, result)['mechanical_status'], 'REVIEW_REQUIRED')


if __name__ == '__main__': unittest.main()
