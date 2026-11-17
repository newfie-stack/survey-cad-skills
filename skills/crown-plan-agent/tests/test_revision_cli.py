"""Invented two-source comparison packets; all PDFs remain temporary."""
from contextlib import redirect_stderr, redirect_stdout
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

ENGINE = Path(__file__).resolve().parents[1] / 'engine'
sys.path.insert(0, str(ENGINE))
try:
    import revision_cli
except ModuleNotFoundError as exc:
    if exc.name != 'revision_cli':
        raise
    revision_cli = None
try:
    import fitz
except ImportError:
    fitz = None


@unittest.skipUnless(fitz is not None, 'PyMuPDF unavailable')
class RevisionCLITests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.old, self.new = self.root/'old.pdf', self.root/'new.pdf'
        self.make_pdf(self.old)
        self.make_pdf(self.new, scale='1:2500', applicant='EXAMPLE SOUTH LTD')
        self.scenario = {'land_class':'alberta_crown', 'regulator':'AER',
            'disposition':'LOC', 'stage':'initial', 'plan_type':'sketch',
            'purpose':'Invented purpose', 'subactivity':'', 'applicant_name':'EXAMPLE NORTH LTD'}
        self.scenario_path = self.root/'scenario.json'
        self.scenario_path.write_text(json.dumps(self.scenario))
        self.catalogue = self.root/'catalogue.json'
        shutil.copyfile(ENGINE/'candidate_requirements.json', self.catalogue)
        self.md, self.record, self.marked = [self.root/name for name in
                                           ('comparison.md','comparison.json','revised-review.pdf')]
        self.originals = {p: p.read_bytes() for p in (self.old,self.new)}

    def make_pdf(self, path, *, scale='1:5000', applicant='EXAMPLE NORTH LTD', graphics=False):
        with fitz.open() as doc:
            page=doc.new_page(width=500,height=700)
            if not graphics:
                for y,text in ((55,'SKETCH PLAN SHOWING INVENTED LAND'), (85,'SCALE '+scale),
                               (115,'Applicant: '+applicant), (145,'TOTAL AREA: 0.200 ha')):
                    page.insert_text((40,y),text)
            page.draw_rect(fitz.Rect(40,180,220 if scale=='1:5000' else 250,350))
            doc.save(path)

    def run_api(self, **kwargs):
        self.assertIsNotNone(revision_cli,'Revision Comparison CLI is not implemented')
        return revision_cli.run_comparison(self.old,self.new,self.md,self.record,
                                          self.scenario,self.catalogue,**kwargs)

    def invoke(self, extras=()):
        self.assertIsNotNone(revision_cli,'Revision Comparison CLI is not implemented')
        args=[str(self.old),str(self.new),'--scenario',str(self.scenario_path),
              '--catalogue',str(self.catalogue),'--output',str(self.md),
              '--json-output',str(self.record),'--offline',*extras]
        out,err=io.StringIO(),io.StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            try: code=revision_cli.main(args)
            except SystemExit as exc: code=exc.code
        return code,out.getvalue(),err.getvalue()

    def test_changed_scale_and_replacement_name_form_one_bound_private_packet(self):
        self.assertEqual(self.run_api(),self.md)
        result=json.loads(self.record.read_text())
        rows={row['requirement_id']:row for row in result['requirements']}
        self.assertEqual(rows['CANDIDATE-PLAN-SCALE']['comparison_status'],'OBSERVED_TEXT_CHANGED')
        self.assertEqual(rows['CANDIDATE-APPLICANT']['comparison_status'],'PREVIOUS_OBSERVATION_NOT_FOUND')
        changed={row['normalized_text'] for row in result['text_changes']}
        self.assertIn('Applicant: EXAMPLE NORTH LTD',changed)
        self.assertIn('Applicant: EXAMPLE SOUTH LTD',changed)
        for role,path in (('baseline',self.old),('revised',self.new)):
            self.assertEqual(result[role]['source_sha256'],sha256(self.originals[path]).hexdigest())
            self.assertEqual(path.read_bytes(),self.originals[path])
        self.assertEqual(result['overall_status'],'REVIEW_REQUIRED')
        self.assertEqual(result['basis']['engine_version'],'0.6.0')
        for path in (self.md,self.record):
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
        self.assertFalse(list(self.root.glob('.cpa-review-*')))

    def test_cli_runs_offline_and_does_not_open_network_connections(self):
        with patch('socket.create_connection',side_effect=AssertionError('network forbidden')) as connect:
            code,_,error=self.invoke()
        self.assertEqual(code,0,error)
        connect.assert_not_called()
        self.assertTrue(self.md.is_file());self.assertTrue(self.record.is_file())

    def test_same_source_reports_byte_equality_without_closing_review(self):
        self.new.write_bytes(self.old.read_bytes())
        self.run_api()
        result=json.loads(self.record.read_text())
        self.assertTrue(result['identical_source_bytes'])
        self.assertEqual(result['text_changes'],[])
        self.assertEqual(result['overall_status'],'REVIEW_REQUIRED')

    def test_scanned_revision_does_not_close_previous_observations(self):
        self.new.unlink();self.make_pdf(self.new,graphics=True)
        self.run_api()
        result=json.loads(self.record.read_text())
        scale=next(row for row in result['requirements'] if row['requirement_id']=='CANDIDATE-PLAN-SCALE')
        self.assertEqual(scale['comparison_status'],'PREVIOUS_OBSERVATION_NOT_FOUND')
        self.assertEqual(result['overall_status'],'REVIEW_REQUIRED')

    def test_linework_only_difference_is_outside_the_supported_text_result(self):
        with fitz.open(self.old) as doc:
            doc[0].draw_line((300,180),(350,350))
            self.new.write_bytes(doc.tobytes())
        self.run_api()
        result=json.loads(self.record.read_text())
        self.assertFalse(result['identical_source_bytes'])
        self.assertEqual(result['text_changes'],[])
        self.assertIn('linework',self.md.read_text().lower())

    def test_optional_pdf_is_standard_revised_review_with_preserved_source(self):
        self.run_api(annotated_pdf=self.marked)
        with fitz.open(self.new) as source,fitz.open(self.marked) as output:
            self.assertGreater(output.page_count,source.page_count)
            self.assertEqual(output[0].get_text(),source[0].get_text())
            self.assertEqual(output[0].rect,source[0].rect)
            self.assertEqual(output[0].get_pixmap(annots=False).samples,
                             source[0].get_pixmap(annots=False).samples)
        self.assertIn('standard',self.md.read_text().lower())
        self.assertEqual(self.new.read_bytes(),self.originals[self.new])

    def test_existing_destination_rejected_before_source_inspection(self):
        self.assertIsNotNone(revision_cli)
        self.record.write_text('Existing private record')
        with patch.object(revision_cli,'inspect_original_pdf') as inspect:
            with self.assertRaises(FileExistsError):self.run_api()
        inspect.assert_not_called();self.assertFalse(self.md.exists())
        self.assertEqual(self.record.read_text(),'Existing private record')

    def test_dangling_symlink_and_missing_parent_are_rejected_before_inspection(self):
        self.assertIsNotNone(revision_cli)
        for mode in ('symlink','missing_parent'):
            with self.subTest(mode=mode):
                old_record=self.record
                if mode=='symlink':self.record.symlink_to(self.root/'not-created.json')
                else:self.record=self.root/'missing'/'comparison.json'
                with patch.object(revision_cli,'inspect_original_pdf') as inspect:
                    with self.assertRaises((ValueError,OSError)):self.run_api()
                inspect.assert_not_called();self.assertFalse(self.md.exists())
                if mode=='symlink':self.record.unlink()
                self.record=old_record

    def test_outputs_inside_installed_skill_are_rejected(self):
        self.assertIsNotNone(revision_cli)
        self.md=ENGINE.parent/('never-created-'+uuid4().hex+'.md')
        with patch.object(revision_cli,'inspect_original_pdf') as inspect:
            with self.assertRaises(ValueError):self.run_api()
        inspect.assert_not_called();self.assertFalse(self.md.exists())

    def test_source_change_after_comparison_cancels_the_whole_packet(self):
        self.assertIsNotNone(revision_cli)
        real=revision_cli.build_comparison
        replacement=b'Externally replaced source'
        def changed(*args,**kwargs):
            value=real(*args,**kwargs);self.old.write_bytes(replacement);return value
        with patch.object(revision_cli,'build_comparison',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'changed'):self.run_api()
        self.assertFalse(self.md.exists());self.assertFalse(self.record.exists())
        self.assertEqual(self.old.read_bytes(),replacement)

    def test_shared_catalogue_change_cancels_the_whole_packet(self):
        self.assertIsNotNone(revision_cli)
        real=revision_cli.build_comparison
        def changed(*args,**kwargs):
            value=real(*args,**kwargs);self.catalogue.write_text('{}');return value
        with patch.object(revision_cli,'build_comparison',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'changed'):self.run_api()
        self.assertFalse(self.md.exists());self.assertFalse(self.record.exists())

    def test_failure_publishing_second_artifact_leaves_no_partial_packet(self):
        self.assertIsNotNone(revision_cli)
        real=os.link
        def fail_second(stage,dest,*args,**kwargs):
            if Path(dest)==self.record:raise OSError('Injected second-output failure')
            return real(stage,dest,*args,**kwargs)
        with patch('artifact_publication.os.link',side_effect=fail_second):
            with self.assertRaisesRegex(OSError,'Injected'):self.run_api()
        self.assertFalse(self.md.exists());self.assertFalse(self.record.exists())
        self.assertFalse(list(self.root.glob('.cpa-review-*')))
        for path,data in self.originals.items():self.assertEqual(path.read_bytes(),data)

    def test_duplicate_scenario_json_is_rejected_without_outputs(self):
        self.scenario_path.write_text('{"regulator":"AER","regulator":"Alberta"}')
        code,_,error=self.invoke()
        self.assertEqual(code,2);self.assertIn('Duplicate',error)
        self.assertFalse(self.md.exists());self.assertFalse(self.record.exists())

    def test_conflicting_disposition_alias_is_rejected(self):
        self.scenario['activity']='MSL'
        with self.assertRaisesRegex(ValueError,'Conflicting'):self.run_api()
        self.assertFalse(self.md.exists());self.assertFalse(self.record.exists())

    def test_scenario_file_change_after_comparison_cancels_cli_publication(self):
        self.assertIsNotNone(revision_cli)
        real=revision_cli.build_comparison
        def changed(*args,**kwargs):
            value=real(*args,**kwargs);self.scenario_path.write_text('{}');return value
        with patch.object(revision_cli,'build_comparison',side_effect=changed):
            code,_,error=self.invoke()
        self.assertEqual(code,2);self.assertIn('changed',error)
        self.assertFalse(self.md.exists());self.assertFalse(self.record.exists())

    def test_shared_reference_file_change_after_parsing_cancels_publication(self):
        self.assertIsNotNone(revision_cli)
        reference=self.root/'invented-reference.pdf'
        reference.write_bytes(b'Invented parser-boundary input; not a regulatory source')
        real=revision_cli.build_comparison
        def changed(*args,**kwargs):
            value=real(*args,**kwargs);reference.write_bytes(b'Changed external reference');return value
        # Existing Table A2 parser has its own structural tests. Here the fault
        # boundary supplies an empty unresolved row set to exercise input binding.
        with patch.object(revision_cli,'extract_a2_rows',return_value=[]), \
             patch.object(revision_cli,'build_comparison',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'changed'):self.run_api(a2_pdf=reference)
        self.assertFalse(self.md.exists());self.assertFalse(self.record.exists())

    def test_artifact_budget_failure_does_not_publish_an_incomplete_packet(self):
        self.assertIsNotNone(revision_cli)
        with patch.object(revision_cli,'MAX_ARTIFACT',200):
            with self.assertRaisesRegex(ValueError,'20 MiB'):self.run_api()
        self.assertFalse(self.md.exists());self.assertFalse(self.record.exists())

    def test_table_a2_input_outside_aer_scope_fails_before_source_inspection(self):
        self.assertIsNotNone(revision_cli)
        self.scenario['regulator']='Alberta'
        with patch.object(revision_cli,'inspect_original_pdf') as inspect:
            with self.assertRaisesRegex(ValueError,'regulator AER'):
                self.run_api(a2_pdf=self.root/'unread-reference.pdf')
        inspect.assert_not_called()


if __name__=='__main__':unittest.main()
