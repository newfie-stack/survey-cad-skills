"""Identity comparisons require independently bound, reviewed job records."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / 'engine'))
import job_record_checks


PLAN_HASH = 'a' * 64
FORM_HASH = 'b' * 64
REGISTRY_HASH = 'c' * 64


def field_spec(source_id, role='applicant', *, subject='invented-job', scope=None):
    return {'source_id': source_id, 'semantic_role': role, 'subject_id': subject,
            'measurement_scope': scope, 'selector': {'page': 1, 'bbox_points': [10, 10, 150, 25],
                'role': 'Reviewed ' + role}, 'unit_selector': None}


def source(kind, digest, *, subject='invented-job', status='CURRENT_FOR_REVIEW'):
    return {'source_kind': kind, 'source_sha256': digest, 'subject_id': subject,
            'review': {'status': status, 'reviewer': 'Invented reviewer',
                       'basis': 'Reviewed original for this invented job'}, 'status': 'READY'}


def field(source_id, kind, digest, value, *, role='applicant', subject='invented-job', scope=None):
    return {'status': 'READY', 'raw_value': value, 'unit_raw_value': None,
            'semantic_role': role, 'subject_id': subject, 'measurement_scope': scope,
            'source_id': source_id, 'source_sha256': digest,
            'evidence': {'source_id': source_id, 'source_kind': kind,
                         'source_sha256': digest, 'page': 1, 'bbox_points': [10, 10, 150, 25],
                         'text': value, 'spans': [{'text': value, 'bbox_points': [10, 10, 150, 25]}]},
            'unit_evidence': None, 'reason': 'One original native field'}


class JobRecordCheckTests(unittest.TestCase):
    def setUp(self):
        self.specs = {'plan_name': field_spec('plan'), 'form_name': field_spec('form'),
                      'registry_name': field_spec('registry')}
        self.result = {'sources': {'plan': source('PLAN', PLAN_HASH),
                                  'form': source('APPLICATION_FORM', FORM_HASH),
                                  'registry': source('CLIENT_REGISTRY', REGISTRY_HASH)},
                       'fields': {'plan_name': field('plan', 'PLAN', PLAN_HASH, 'Prairie Energy Ltd.'),
                                  'form_name': field('form', 'APPLICATION_FORM', FORM_HASH, 'Prairie Energy Ltd.'),
                                  'registry_name': field('registry', 'CLIENT_REGISTRY', REGISTRY_HASH, 'Prairie Energy Ltd.')}}
        self.comparison = {'id': 'applicant_form', 'kind': 'applicant_name',
                           'plan_field_id': 'plan_name', 'reference_field_id': 'form_name',
                           'workbook_check_id': 'C_1_2_2_1_02'}

    def compare(self, result=None, comparison=None):
        return job_record_checks.review_job_comparisons(
            self.result if result is None else result,
            [self.comparison if comparison is None else comparison])[0]

    def test_actual_bound_field_agreement_is_partial_evidence_not_compliance(self):
        before = deepcopy(self.result)
        self.assertEqual(job_record_checks.validate_comparisons([self.comparison], self.specs), [self.comparison])
        row = self.compare()
        self.assertEqual(row['mechanical_status'], 'PASS')
        self.assertEqual(row['execution_status'], 'EXECUTED')
        self.assertEqual(row['assessment_scope'], 'DATED_CLAUSE_MECHANICAL_EVIDENCE')
        self.assertEqual(row['status'], 'REVIEW_REQUIRED')
        self.assertTrue(row['residual_review'])
        self.assertEqual([f['source_sha256'] for f in row['evidence']], [PLAN_HASH, FORM_HASH])
        self.assertEqual(self.result, before)

    def test_each_registry_and_form_disagreement_is_preserved(self):
        comparisons = [self.comparison, {**self.comparison, 'id': 'applicant_registry',
                         'reference_field_id': 'registry_name', 'workbook_check_id': 'C_1_2_2_1_01'}]
        self.result['fields']['registry_name']['raw_value'] = 'Valley Energy Ltd.'
        rows = job_record_checks.review_job_comparisons(self.result, comparisons)
        self.assertEqual([r['mechanical_status'] for r in rows], ['PASS', 'FAIL'])
        self.assertEqual([r['workbook_check_id'] for r in rows], ['C_1_2_2_1_02', 'C_1_2_2_1_01'])

    def test_only_nfc_ascii_letter_case_and_whitespace_normalize(self):
        for value, expected in [('  prairie   ENERGY\tLtd. ', 'PASS'),
                                ('Prairie Energy Limited', 'FAIL'), ('Prairie Energy Ltd', 'FAIL'),
                                ('Prairie & Energy Ltd.', 'FAIL'), ('Ｐrairie Energy Ltd.', 'FAIL'),
                                ('Prаirie Energy Ltd.', 'FAIL')]:  # Cyrillic a remains distinct.
            with self.subTest(value=value):
                self.result['fields']['form_name']['raw_value'] = value
                self.assertEqual(self.compare()['mechanical_status'], expected)
        self.result['fields']['plan_name']['raw_value'] = 'Caf\u00e9 Energy Ltd.'
        self.result['fields']['form_name']['raw_value'] = 'Cafe\u0301 Energy Ltd.'
        self.assertEqual(self.compare()['mechanical_status'], 'PASS')

    def test_unconfirmed_unicode_case_equivalence_is_unresolved_not_a_mismatch_or_pass(self):
        for kind, role, question, plan, reference in [
            ('applicant_name', 'applicant', 'C_1_2_2_1_02', 'Société Énergie Ltd.', 'SOCIÉTÉ ÉNERGIE LTD.'),
            ('applicant_name', 'applicant', 'C_1_2_2_1_02', 'Straße Energy Ltd.', 'STRASSE ENERGY LTD.'),
            ('legal_description', 'legal_description', 'C_1_2_1_4_01', 'Lot é du plan 1', 'LOT É DU PLAN 1')]:
            with self.subTest(kind=kind, plan=plan, reference=reference):
                result = deepcopy(self.result)
                result['fields']['plan_name'].update(raw_value=plan, semantic_role=role)
                result['fields']['form_name'].update(raw_value=reference, semantic_role=role)
                comparison = {**self.comparison, 'kind': kind, 'workbook_check_id': question}
                row = self.compare(result, comparison)
                self.assertEqual(row['mechanical_status'], 'REVIEW_REQUIRED')
                self.assertEqual(row['execution_status'], 'BLOCKED')
                self.assertIn('Unicode', row['reason'])

    def test_placeholder_empty_control_and_ambiguous_values_cannot_agree(self):
        for value in (None, '', '  ', 'UNKNOWN', 'N/A', 'TBD', 'Prairie\u202eEnergy Ltd.'):
            with self.subTest(value=value):
                self.result['fields']['plan_name']['raw_value'] = value
                self.result['fields']['form_name']['raw_value'] = value
                row = self.compare()
                self.assertEqual(row['mechanical_status'], 'REVIEW_REQUIRED')
                self.assertEqual(row['execution_status'], 'BLOCKED')

    def test_job_instruction_is_unbound_job_qa_and_not_application_or_registry(self):
        self.result['sources']['form']['source_kind'] = 'JOB_INSTRUCTION'
        self.result['fields']['form_name']['evidence']['source_kind'] = 'JOB_INSTRUCTION'
        self.assertEqual(self.compare()['mechanical_status'], 'REVIEW_REQUIRED')
        unbound = {**self.comparison, 'workbook_check_id': None}
        row = self.compare(comparison=unbound)
        self.assertEqual(row['mechanical_status'], 'PASS')
        self.assertEqual(row['assessment_scope'], 'JOB_QA_ONLY')

    def test_wrong_role_field_cannot_be_promoted_to_applicant(self):
        for role in ('operator', 'landowner', 'surveyor', 'legal_description'):
            with self.subTest(role=role):
                specs = deepcopy(self.specs)
                specs['form_name']['semantic_role'] = role
                with self.assertRaises(ValueError):
                    job_record_checks.validate_comparisons([self.comparison], specs)
                result = deepcopy(self.result)
                result['fields']['form_name']['semantic_role'] = role
                self.assertEqual(self.compare(result=result)['mechanical_status'], 'REVIEW_REQUIRED')

    def test_historical_unknown_or_missing_reference_never_compares_as_current(self):
        for changed in ('historical', 'unconfirmed', 'missing_source', 'field_unready', 'missing_review', 'blank_basis'):
            with self.subTest(changed=changed):
                result = deepcopy(self.result)
                if changed == 'historical': result['sources']['form']['review']['status'] = 'HISTORICAL_BASIS'
                if changed == 'unconfirmed': result['sources']['form']['review']['status'] = 'UNCONFIRMED'
                if changed == 'missing_source': result['sources']['form']['status'] = 'MISSING_SOURCE'
                if changed == 'field_unready': result['fields']['form_name']['status'] = 'REVIEW_REQUIRED'
                if changed == 'missing_review': result['sources']['form']['review'] = None
                if changed == 'blank_basis': result['sources']['form']['review']['basis'] = ' '
                row = self.compare(result=result)
                self.assertEqual(row['mechanical_status'], 'REVIEW_REQUIRED')
                self.assertEqual(row['execution_status'], 'BLOCKED')

    def test_subject_and_scope_must_agree_through_field_and_source(self):
        for changed in ('source_subject', 'field_subject', 'blank_subject', 'scope_mismatch', 'one_scope'):
            with self.subTest(changed=changed):
                result = deepcopy(self.result)
                if changed == 'source_subject': result['sources']['form']['subject_id'] = 'neighboring-job'
                if changed == 'field_subject': result['fields']['form_name']['subject_id'] = 'neighboring-job'
                if changed == 'blank_subject': result['fields']['form_name']['subject_id'] = ''
                if changed == 'scope_mismatch':
                    result['fields']['plan_name']['measurement_scope'] = 'whole-disposition'
                    result['fields']['form_name']['measurement_scope'] = 'changed-land'
                if changed == 'one_scope': result['fields']['plan_name']['measurement_scope'] = 'whole-disposition'
                self.assertEqual(self.compare(result=result)['mechanical_status'], 'REVIEW_REQUIRED')

    def test_null_subject_is_valid_missing_evidence_and_blocks_only_comparison(self):
        specs = deepcopy(self.specs)
        specs['form_name']['subject_id'] = None
        self.assertEqual(job_record_checks.validate_comparisons([self.comparison], specs), [self.comparison])
        result = deepcopy(self.result)
        result['fields']['form_name']['subject_id'] = None
        row = self.compare(result=result)
        self.assertEqual(row['mechanical_status'], 'REVIEW_REQUIRED')
        self.assertEqual(row['execution_status'], 'BLOCKED')
        self.assertIn('identities', row['reason'])
        specs['form_name']['semantic_role'] = 'operator'
        with self.assertRaises(ValueError):
            job_record_checks.validate_comparisons([self.comparison], specs)

    def test_digest_and_original_source_evidence_must_bind(self):
        for changed in ('field_hash', 'evidence_hash', 'evidence_id', 'evidence_kind', 'same_blob', 'no_evidence'):
            with self.subTest(changed=changed):
                result = deepcopy(self.result)
                if changed == 'field_hash': result['fields']['form_name']['source_sha256'] = 'd' * 64
                if changed == 'evidence_hash': result['fields']['form_name']['evidence']['source_sha256'] = 'd' * 64
                if changed == 'evidence_id': result['fields']['form_name']['evidence']['source_id'] = 'plan'
                if changed == 'evidence_kind': result['fields']['form_name']['evidence']['source_kind'] = 'CLIENT_REGISTRY'
                if changed == 'same_blob':
                    result['sources']['form']['source_sha256'] = PLAN_HASH
                    result['fields']['form_name']['source_sha256'] = PLAN_HASH
                    result['fields']['form_name']['evidence']['source_sha256'] = PLAN_HASH
                if changed == 'no_evidence': result['fields']['form_name']['evidence'] = None
                self.assertEqual(self.compare(result=result)['mechanical_status'], 'REVIEW_REQUIRED')

    def test_legal_description_preserves_components_and_punctuation(self):
        result = deepcopy(self.result)
        for f in result['fields'].values(): f['semantic_role'] = 'legal_description'
        result['fields']['plan_name']['raw_value'] = 'NW 12-34-5 W4M'
        result['fields']['form_name']['raw_value'] = 'nw 12-34-5 w4m'
        comparison = {**self.comparison, 'kind': 'legal_description', 'workbook_check_id': 'C_1_2_1_4_01'}
        self.assertEqual(self.compare(result, comparison)['mechanical_status'], 'PASS')
        result['fields']['form_name']['raw_value'] = 'NW 12-34-6 W4M'
        self.assertEqual(self.compare(result, comparison)['mechanical_status'], 'FAIL')
        result['fields']['form_name']['raw_value'] = 'NW 12 34 5 W4M'
        self.assertEqual(self.compare(result, comparison)['mechanical_status'], 'FAIL')

    def test_disposition_compares_complete_identifiers_without_losing_zeros(self):
        result = deepcopy(self.result)
        for f in result['fields'].values(): f['semantic_role'] = 'disposition_id'
        result['fields']['plan_name']['raw_value'] = 'LOC 001234'
        comparison = {**self.comparison, 'kind': 'disposition_id', 'workbook_check_id': None}
        for value, expected in [('loc001234', 'PASS'), ('LOC 1234', 'FAIL'), ('DLO 001234', 'FAIL'),
                                ('LOC', 'REVIEW_REQUIRED'), ('LOC001234-A', 'REVIEW_REQUIRED'),
                                ('LOC001234 / LOC002345', 'REVIEW_REQUIRED'),
                                ('LOC 001 234', 'REVIEW_REQUIRED')]:
            with self.subTest(value=value):
                result['fields']['form_name']['raw_value'] = value
                row = self.compare(result, comparison)
                self.assertEqual(row['mechanical_status'], expected)
                self.assertEqual(row['assessment_scope'], 'JOB_QA_ONLY')

    def test_missing_runtime_fields_or_sources_remain_explicitly_blocked(self):
        for container, name in [('fields', 'form_name'), ('sources', 'form')]:
            result = deepcopy(self.result)
            result[container].pop(name)
            row = self.compare(result=result)
            self.assertEqual(row['execution_status'], 'BLOCKED')
            self.assertIn('missing', row['reason'].lower())

    def test_malformed_runtime_identity_containers_cannot_crash_or_pass(self):
        for key, value in [('source_id', {}), ('source_id', []), ('source_id', None)]:
            with self.subTest(key=key, value=value):
                result = deepcopy(self.result)
                result['fields']['form_name'][key] = value
                self.assertEqual(self.compare(result=result)['mechanical_status'], 'REVIEW_REQUIRED')
        for value in ({}, [], None):
            with self.subTest(kind=value):
                result = deepcopy(self.result)
                result['sources']['form']['source_kind'] = value
                result['fields']['form_name']['evidence']['source_kind'] = value
                self.assertEqual(self.compare(result=result)['mechanical_status'], 'REVIEW_REQUIRED')

    def test_a_source_hash_alone_does_not_locate_original_field_evidence(self):
        for mutation in ('no_locator', 'bad_page', 'bad_box', 'nonfinite_box'):
            with self.subTest(mutation=mutation):
                result = deepcopy(self.result)
                evidence = result['fields']['form_name']['evidence']
                if mutation == 'no_locator':
                    evidence.pop('page'); evidence.pop('bbox_points')
                if mutation == 'bad_page': evidence['page'] = 0
                if mutation == 'bad_box': evidence['bbox_points'] = [20, 10, 10, 25]
                if mutation == 'nonfinite_box': evidence['bbox_points'] = [10, 10, float('nan'), 25]
                self.assertEqual(self.compare(result=result)['mechanical_status'], 'REVIEW_REQUIRED')
        result = deepcopy(self.result)
        result['sources']['form']['source_kind'] = 'JOB_INSTRUCTION'
        result['fields']['form_name']['evidence'] = {
            'source_id': 'form', 'source_kind': 'JOB_INSTRUCTION', 'source_sha256': FORM_HASH,
            'pointer': '/applicant', 'text': 'Prairie Energy Ltd.', 'evidence_type': 'JSON_SCALAR'}
        unbound = {**self.comparison, 'workbook_check_id': None}
        self.assertEqual(self.compare(result, unbound)['mechanical_status'], 'PASS')
        result['fields']['form_name']['evidence']['pointer'] = '#/applicant'
        self.assertEqual(self.compare(result, unbound)['mechanical_status'], 'REVIEW_REQUIRED')

    def test_validation_rejects_unknown_shapes_kinds_and_bindings(self):
        mutations = [dict(extra=True), dict(id=''), dict(kind='area'), dict(kind='length'),
                     dict(kind='operator'), dict(plan_field_id='missing'),
                     dict(reference_field_id='plan_name'), dict(workbook_check_id='C_1_1_1_01'),
                     dict(kind='legal_description'), dict(workbook_check_id='C_1_2_1_4_01')]
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                job_record_checks.validate_comparisons([{**self.comparison, **mutation}], self.specs)
        self.assertEqual(job_record_checks.validate_comparisons([], self.specs), [])
        with self.assertRaises(ValueError): job_record_checks.validate_comparisons([self.comparison] * 2, self.specs)
        with self.assertRaises(ValueError):
            job_record_checks.validate_comparisons([self.comparison, {**self.comparison, 'id': 'duplicate_pair'}], self.specs)
        with self.assertRaises(ValueError):
            job_record_checks.validate_comparisons([{**self.comparison, 'id': f'check{i}'} for i in range(51)], self.specs)
        for value in (None, {}, 'not a list'):
            with self.assertRaises(ValueError): job_record_checks.validate_comparisons(value, self.specs)


if __name__ == '__main__': unittest.main()
