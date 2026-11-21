"""Actual source snapshots, reviewed field roles and original field strings."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pymupdf

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / 'engine'))
from record_fields import validate_record_spec, preflight_record_sources, read_record_fields


class RecordFieldTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plan = self.root / 'invented-plan.pdf'
        self.form = self.root / 'invented-form.pdf'
        self.note = self.root / 'invented-job.json'
        self.write_pdf(self.plan, 'Applicant: Prairie Energy Ltd.')
        self.write_pdf(self.form, 'Applicant: Prairie Energy Ltd.')
        self.note.write_text(json.dumps({'applicant': 'Prairie Energy Ltd.', 'unit': 'ha',
                                        'area': '1.00', 'nested/key': {'~name': 'Original'},
                                        'items': ['First']}), encoding='utf-8')
        self.spec = {'schema_version': 1, 'prepared_by': 'Invented reviewer', 'subject_id': 'invented_subject',
                     'sources': {'plan': self.source(self.plan, 'PLAN', 'PDF'),
                                 'form': self.source(self.form, 'APPLICATION_FORM', 'PDF'),
                                 'job': self.source(self.note, 'JOB_INSTRUCTION', 'JSON')},
                     'fields': {'plan_applicant': self.field('plan', {'region': self.region()}),
                                'form_applicant': self.field('form', {'region': self.region()}),
                                'job_applicant': self.field('job', {'pointer': '/applicant'})}}
        self.paths = {'form': self.form, 'job': self.note}

    def write_pdf(self, target, text, *, rotate=0, page_rotation=0, x=40, y=60):
        with pymupdf.open() as doc:
            page = doc.new_page(width=600, height=700)
            page.insert_text((x, y), text, fontsize=11, rotate=rotate)
            page.set_rotation(page_rotation)
            doc.save(target)

    def source(self, path, kind, fmt):
        return {'source_kind': kind, 'format': fmt, 'source_sha256': sha256(path.read_bytes()).hexdigest(),
                'subject_id': 'invented_subject', 'review': {'status': 'CURRENT_FOR_REVIEW',
                'reviewer': 'Invented reviewer', 'basis': 'Reviewed invented subject and current source.'}}

    @staticmethod
    def region():
        return {'page': 1, 'bbox_points': [30, 40, 300, 75], 'role': 'Reviewed applicant field', 'label': 'Applicant:'}

    @staticmethod
    def field(source, selector, *, role='applicant', unit_selector=None):
        return {'source_id': source, 'semantic_role': role, 'subject_id': 'invented_subject',
                'measurement_scope': None, 'selector': selector, 'unit_selector': unit_selector}

    def read(self, spec=None, paths=None):
        return read_record_fields(self.plan, spec or self.spec, self.paths if paths is None else paths)

    def test_reads_actual_original_pdf_and_json_strings_with_source_locations(self):
        result = self.read()
        self.assertEqual(result['fields']['plan_applicant']['raw_value'], 'Prairie Energy Ltd.')
        self.assertEqual(result['fields']['form_applicant']['raw_value'], 'Prairie Energy Ltd.')
        self.assertEqual(result['fields']['job_applicant']['raw_value'], 'Prairie Energy Ltd.')
        self.assertEqual(result['fields']['form_applicant']['evidence']['page'], 1)
        self.assertEqual(result['fields']['job_applicant']['evidence']['pointer'], '/applicant')
        self.assertEqual(result['sources']['form']['filename'], 'invented-form.pdf')
        self.assertNotIn(str(self.root), json.dumps(result))
        self.assertTrue(all(f['status'] == 'READY' for f in result['fields'].values()))

    def test_missing_reference_is_unresolved_without_losing_other_fields(self):
        result = self.read(paths={'job': self.note})
        self.assertEqual(result['sources']['form']['status'], 'MISSING_SOURCE')
        self.assertEqual(result['fields']['form_applicant']['status'], 'REVIEW_REQUIRED')
        self.assertIsNone(result['fields']['form_applicant']['raw_value'])
        self.assertEqual(result['fields']['plan_applicant']['status'], 'READY')
        missing = self.read(paths={**self.paths, 'form': self.root / 'missing.pdf'})
        self.assertEqual(missing['sources']['form']['status'], 'MISSING_SOURCE')

    def test_missing_hash_is_valid_only_for_an_unavailable_source(self):
        spec = deepcopy(self.spec)
        spec['sources']['form']['source_sha256'] = None
        self.assertEqual(self.read(spec, {'job': self.note})['sources']['form']['status'], 'MISSING_SOURCE')
        with self.assertRaises(ValueError): self.read(spec)

    def test_preflight_checks_every_hash_before_any_native_pdf_operation(self):
        spec = deepcopy(self.spec)
        spec['sources']['job']['source_sha256'] = '0' * 64
        with patch('record_fields.extract_pdf') as native:
            with self.assertRaises(ValueError): self.read(spec)
            native.assert_not_called()
        with patch('record_fields.extract_pdf') as native:
            preflight = preflight_record_sources(self.plan, self.spec, self.paths)
            self.assertEqual(preflight['sources']['plan']['status'], 'READY')
            native.assert_not_called()

    def test_subjects_and_unconfirmed_currentness_block_fields(self):
        for where, value in [('source_subject', 'other'), ('field_subject', 'other'),
                             ('source_subject', None), ('field_subject', None), ('review', 'UNCONFIRMED')]:
            spec = deepcopy(self.spec)
            if where == 'source_subject':spec['sources']['form']['subject_id'] = value
            if where == 'field_subject':spec['fields']['form_applicant']['subject_id'] = value
            if where == 'review':spec['sources']['form']['review']['status'] = value
            with self.subTest(where=where, value=value):
                self.assertEqual(self.read(spec)['fields']['form_applicant']['status'], 'REVIEW_REQUIRED')

    def test_historical_sources_remain_readable_with_their_status_for_predicate_gates(self):
        spec = deepcopy(self.spec)
        spec['sources']['form']['review']['status'] = 'HISTORICAL_BASIS'
        result = self.read(spec)
        self.assertEqual(result['fields']['form_applicant']['status'], 'READY')
        self.assertEqual(result['sources']['form']['review']['status'], 'HISTORICAL_BASIS')

    def test_json_pointer_escapes_and_array_indexes_are_resolved_literally(self):
        spec = deepcopy(self.spec)
        for pointer, wanted in [('/nested~1key/~0name', 'Original'), ('/items/0', 'First')]:
            spec['fields']['job_applicant']['selector']['pointer'] = pointer
            with self.subTest(pointer=pointer):
                self.assertEqual(self.read(spec)['fields']['job_applicant']['raw_value'], wanted)
        spec['fields']['job_applicant']['selector']['pointer'] = '/items/00'
        self.assertEqual(self.read(spec)['fields']['job_applicant']['status'], 'REVIEW_REQUIRED')

    def test_missing_null_nonstring_and_blank_json_values_are_unresolved(self):
        for data in ({}, {'applicant': None}, {'applicant': 123}, {'applicant': ['A']}, {'applicant': ' '}):
            self.note.write_text(json.dumps(data))
            spec = deepcopy(self.spec)
            spec['sources']['job']['source_sha256'] = sha256(self.note.read_bytes()).hexdigest()
            with self.subTest(data=data):
                field = self.read(spec)['fields']['job_applicant']
                self.assertEqual(field['status'], 'REVIEW_REQUIRED')
                self.assertIsNone(field['raw_value'])

    def test_json_values_preserve_compatibility_characters_case_and_punctuation(self):
        value = 'Ｐrairie & Energy, Ltd. 001'
        self.note.write_text(json.dumps({'applicant': value}), encoding='utf-8')
        spec = deepcopy(self.spec)
        spec['sources']['job']['source_sha256'] = sha256(self.note.read_bytes()).hexdigest()
        self.assertEqual(self.read(spec)['fields']['job_applicant']['raw_value'], value)

    def test_unit_field_is_read_from_actual_source_separately(self):
        spec = deepcopy(self.spec)
        spec['fields']['job_area'] = self.field('job', {'pointer': '/area'}, role='area', unit_selector={'pointer': '/unit'})
        spec['fields']['job_area']['measurement_scope'] = 'whole_activity'
        result = self.read(spec)['fields']['job_area']
        self.assertEqual((result['raw_value'], result['unit_raw_value']), ('1.00', 'ha'))
        self.assertEqual(result['unit_evidence']['pointer'], '/unit')

    def test_original_label_stripping_is_ascii_case_insensitive_and_prefix_bounded(self):
        spec = deepcopy(self.spec)
        spec['fields']['plan_applicant']['selector']['region']['label'] = 'aPpLiCaNt:'
        self.assertEqual(self.read(spec)['fields']['plan_applicant']['raw_value'], 'Prairie Energy Ltd.')
        spec['fields']['plan_applicant']['selector']['region']['label'] = 'App'
        self.assertEqual(self.read(spec)['fields']['plan_applicant']['status'], 'REVIEW_REQUIRED')

    def test_clipped_or_multiple_native_spans_are_not_manufactured_into_a_field(self):
        spec = deepcopy(self.spec)
        spec['fields']['plan_applicant']['selector']['region']['bbox_points'][2] = 100
        self.assertEqual(self.read(spec)['fields']['plan_applicant']['status'], 'REVIEW_REQUIRED')
        other = self.root / 'multispan.pdf'
        with pymupdf.open() as doc:
            page = doc.new_page()
            page.insert_text((40, 60), 'Prairie', fontsize=11)
            page.insert_text((85, 60), 'Energy Ltd.', fontsize=12)
            doc.save(other)
        spec = deepcopy(self.spec)
        spec['sources']['plan']['source_sha256'] = sha256(other.read_bytes()).hexdigest()
        spec['fields']['plan_applicant']['selector']['region'].pop('label')
        result = read_record_fields(other, spec, self.paths)
        self.assertEqual(result['fields']['plan_applicant']['status'], 'REVIEW_REQUIRED')

    def test_wrapped_continuation_outside_selected_box_stays_unresolved(self):
        other = self.root / 'wrapped.pdf'
        with pymupdf.open() as doc:
            page = doc.new_page()
            page.insert_text((40, 60), 'Applicant: Prairie', fontsize=11)
            page.insert_text((90, 76), 'Energy Ltd.', fontsize=11)
            doc.save(other)
        spec = deepcopy(self.spec)
        spec['sources']['plan']['source_sha256'] = sha256(other.read_bytes()).hexdigest()
        spec['fields']['plan_applicant']['selector']['region']['bbox_points'] = [30, 40, 180, 64]
        result = read_record_fields(other, spec, self.paths)
        self.assertEqual(result['fields']['plan_applicant']['status'], 'REVIEW_REQUIRED')

    def test_rotated_native_field_and_rotated_sheet_preserve_raw_value(self):
        for angle, rotation, box, x, y in [(90,0,[230,100,260,470],250,450),
                                          (180,90,[30,440,360,470],350,450),
                                          (270,180,[240,40,270,410],250,50)]:
            other=self.root/f'rotated-{angle}.pdf'
            self.write_pdf(other,'Applicant: Prairie Energy Ltd.',rotate=angle,page_rotation=rotation,x=x,y=y)
            spec=deepcopy(self.spec)
            spec['sources']['plan']['source_sha256']=sha256(other.read_bytes()).hexdigest()
            spec['fields']['plan_applicant']['selector']['region']['bbox_points']=box
            with self.subTest(angle=angle):
                result=read_record_fields(other,spec,self.paths)
                self.assertEqual(result['fields']['plan_applicant']['raw_value'],'Prairie Energy Ltd.')
                self.assertEqual(result['fields']['plan_applicant']['status'],'READY')

    def test_raster_overlap_is_unresolved(self):
        other=self.root/'raster.pdf'
        with pymupdf.open() as doc:
            page=doc.new_page()
            page.insert_text((40,60),'Applicant: Prairie Energy Ltd.',fontsize=11)
            pix=pymupdf.Pixmap(pymupdf.csRGB,pymupdf.IRect(0,0,2,2),False)
            pix.clear_with(255)
            page.insert_image(pymupdf.Rect(30,40,300,75),pixmap=pix)
            doc.save(other)
        spec=deepcopy(self.spec)
        spec['sources']['plan']['source_sha256']=sha256(other.read_bytes()).hexdigest()
        self.assertEqual(read_record_fields(other,spec,self.paths)['fields']['plan_applicant']['status'],'REVIEW_REQUIRED')

    def test_json_duplicate_keys_constants_and_non_utf8_fail_before_native(self):
        for raw in [b'{"applicant":"A","applicant":"B"}',b'{"applicant":NaN}',b'{"applicant":"\xff"}']:
            self.note.write_bytes(raw)
            spec=deepcopy(self.spec)
            spec['sources']['job']['source_sha256']=sha256(raw).hexdigest()
            with self.subTest(raw=raw),patch('record_fields.extract_pdf') as native:
                with self.assertRaises(ValueError):self.read(spec)
                native.assert_not_called()

    def test_unknown_paths_and_malformed_schema_are_rejected(self):
        with self.assertRaises(ValueError):self.read(paths={**self.paths,'surprise':self.note})
        mutations=[lambda s:s.update(extra=True),lambda s:s['sources'].pop('plan'),
            lambda s:s['sources']['form'].update(format='JSON'),
            lambda s:s['fields']['form_applicant'].update(semantic_role='owner_guess'),
            lambda s:s['fields']['job_applicant']['selector'].update(pointer='#/applicant'),
            lambda s:s['fields']['job_applicant']['selector'].update(pointer='/bad~2escape'),
            lambda s:s['fields']['plan_applicant']['selector']['region'].update(coverage_review={})]
        for mutate in mutations:
            spec=deepcopy(self.spec);mutate(spec)
            with self.subTest(spec=spec),self.assertRaises(ValueError):validate_record_spec(spec)

    def test_per_file_and_aggregate_bounds_apply_before_native(self):
        with patch('record_fields.MAX_JSON_BYTES',4),patch('record_fields.extract_pdf') as native:
            with self.assertRaises(ValueError):self.read()
            native.assert_not_called()
        with patch('record_fields.MAX_TOTAL_BYTES',100),patch('record_fields.extract_pdf') as native:
            with self.assertRaises(ValueError):self.read()
            native.assert_not_called()

    def test_native_compatibility_glyphs_are_preserved_without_nfkc_conversion(self):
        other = self.root / 'original-glyphs.pdf'
        with pymupdf.open() as doc:
            page = doc.new_page()
            page.insert_text((40, 60), 'Applicant: Ｐrairie Energy Ltd.', fontname='china-s', fontsize=11)
            doc.save(other)
        spec = deepcopy(self.spec)
        spec['sources']['plan']['source_sha256'] = sha256(other.read_bytes()).hexdigest()
        spec['fields']['plan_applicant']['selector']['region']['bbox_points'] = [30, 40, 500, 75]
        result = read_record_fields(other, spec, self.paths)['fields']['plan_applicant']
        self.assertEqual(result['status'], 'READY')
        self.assertEqual(result['raw_value'], 'Ｐrairie Energy Ltd.')
        self.assertIn('Ｐrairie', result['evidence']['text'])

    def test_unreadable_reference_does_not_abort_other_source_fields(self):
        self.form.write_bytes(b'%PDF-1.7\nThis is an invented broken PDF.')
        spec = deepcopy(self.spec)
        spec['sources']['form']['source_sha256'] = sha256(self.form.read_bytes()).hexdigest()
        result = self.read(spec)
        self.assertEqual(result['sources']['form']['status'], 'REVIEW_REQUIRED')
        self.assertEqual(result['fields']['form_applicant']['status'], 'REVIEW_REQUIRED')
        self.assertEqual(result['fields']['plan_applicant']['status'], 'READY')
        self.assertEqual(result['fields']['job_applicant']['status'], 'READY')

    def test_changed_source_during_another_native_read_is_rejected(self):
        import record_fields
        original = record_fields.extract_pdf
        changed = False
        def change_after_real_read(*args, **kwargs):
            nonlocal changed
            result = original(*args, **kwargs)
            if not changed:
                changed = True
                self.note.write_text('{"applicant":"Changed company"}')
            return result
        with patch('record_fields.extract_pdf', side_effect=change_after_real_read):
            with self.assertRaisesRegex(ValueError, 'changed'):
                self.read()

    def test_missing_unit_retains_raw_number_and_stays_unresolved(self):
        spec = deepcopy(self.spec)
        spec['fields']['job_area'] = self.field('job', {'pointer': '/area'}, role='area',
                                               unit_selector={'pointer': '/missing_unit'})
        field = self.read(spec)['fields']['job_area']
        self.assertEqual(field['raw_value'], '1.00')
        self.assertEqual(field['status'], 'REVIEW_REQUIRED')
        self.assertIsNone(field['unit_raw_value'])

    def test_reader_preserves_inputs_and_source_bytes(self):
        before = deepcopy(self.spec)
        contents = {path: path.read_bytes() for path in (self.plan, self.form, self.note)}
        self.read()
        self.assertEqual(self.spec, before)
        self.assertEqual(contents, {path: path.read_bytes() for path in contents})

    def test_unit_selectors_are_only_allowed_on_area_and_length_fields(self):
        for role in ('applicant', 'operator', 'landowner', 'surveyor', 'disposition_id', 'legal_description'):
            spec = deepcopy(self.spec)
            spec['fields']['plan_applicant']['semantic_role'] = role
            spec['fields']['plan_applicant']['unit_selector'] = {'region': self.region()}
            with self.subTest(role=role), self.assertRaises(ValueError):
                validate_record_spec(spec)

    def test_unrelated_fields_cannot_hide_an_applicant_name_continuation(self):
        other = self.root / 'wrapped-auxiliary.pdf'
        with pymupdf.open() as doc:
            page = doc.new_page()
            page.insert_text((40, 60), 'Applicant: Prairie Energy', fontsize=11)
            page.insert_text((40, 78), 'Alpha Ltd.', fontsize=11)
            page.insert_text((40, 200), 'Area: 1.00', fontsize=11)
            doc.save(other)
        for auxiliary in ('none', 'area_unit', 'label'):
            spec = deepcopy(self.spec)
            spec['sources']['plan']['source_sha256'] = sha256(other.read_bytes()).hexdigest()
            spec['fields']['plan_applicant']['selector']['region']['bbox_points'] = [30, 45, 400, 64]
            suffix = {'page': 1, 'bbox_points': [30, 65, 400, 84], 'role': 'Invented auxiliary field'}
            if auxiliary == 'area_unit':
                spec['fields']['auxiliary_area'] = self.field('plan', {'region': {
                    'page': 1, 'bbox_points': [30, 180, 400, 210], 'role': 'Area field', 'label': 'Area:'}},
                    role='area', unit_selector={'region': suffix})
                spec['fields']['auxiliary_area']['measurement_scope'] = 'whole_activity'
            elif auxiliary == 'label':
                spec['fields']['auxiliary_label'] = self.field('plan', {'region': {**suffix, 'label': 'Alpha'}}, role='operator')
            with self.subTest(auxiliary=auxiliary):
                result = read_record_fields(other, spec, self.paths)
                self.assertEqual(result['fields']['plan_applicant']['status'], 'REVIEW_REQUIRED')
                self.assertIsNone(result['fields']['plan_applicant']['raw_value'])

    def test_numeric_field_can_read_its_own_original_recognized_unit(self):
        other = self.root / 'numeric-unit.pdf'
        with pymupdf.open() as doc:
            page = doc.new_page()
            page.insert_text((40, 60), 'Area: 1.00', fontsize=11)
            page.insert_text((100, 60), 'ha', fontsize=11)
            doc.save(other)
        spec = deepcopy(self.spec)
        spec['sources']['plan']['source_sha256'] = sha256(other.read_bytes()).hexdigest()
        spec['fields'] = {'plan_area': self.field('plan', {'region': {
            'page': 1, 'bbox_points': [30, 40, 95, 70], 'role': 'Area value', 'label': 'Area:'}},
            role='area', unit_selector={'region': {'page': 1, 'bbox_points': [98, 40, 130, 70], 'role': 'Area unit'}})}
        spec['fields']['plan_area']['measurement_scope'] = 'whole_activity'
        result = read_record_fields(other, spec, self.paths)['fields']['plan_area']
        self.assertEqual(result['status'], 'READY')
        self.assertEqual((result['raw_value'], result['unit_raw_value']), ('1.00', 'ha'))

    def test_missing_record_can_have_an_explicitly_unselected_field(self):
        spec = deepcopy(self.spec)
        spec['sources']['form']['source_sha256'] = None
        spec['fields']['form_applicant']['selector'] = None
        result = self.read(spec, {'job': self.note})
        self.assertEqual(result['sources']['form']['status'], 'MISSING_SOURCE')
        field = result['fields']['form_applicant']
        self.assertEqual(field['status'], 'REVIEW_REQUIRED')
        self.assertIsNone(field['raw_value'])
        self.assertNotIn('bbox_points', field['evidence'])
        self.assertNotIn('page', field['evidence'])
        self.assertIn('not been selected', field['reason'])
        self.assertEqual(result['fields']['plan_applicant']['status'], 'READY')

    def test_supplied_source_with_unselected_field_does_not_invent_a_locator(self):
        spec = deepcopy(self.spec)
        spec['fields']['form_applicant']['selector'] = None
        result = self.read(spec)
        field = result['fields']['form_applicant']
        self.assertEqual(result['sources']['form']['status'], 'READY')
        self.assertEqual(field['status'], 'REVIEW_REQUIRED')
        self.assertIsNone(field['raw_value'])
        self.assertEqual(field['evidence']['source_sha256'], spec['sources']['form']['source_sha256'])
        self.assertNotIn('bbox_points', field['evidence'])
        self.assertNotIn('page', field['evidence'])
        self.assertIn('not been selected', field['reason'])
        self.assertEqual(result['fields']['job_applicant']['status'], 'READY')


if __name__=='__main__':unittest.main()
