"""Actual offline command, record preflight and private correction copy."""
import copy
from contextlib import redirect_stderr,redirect_stdout
from hashlib import sha256
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SKILL=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SKILL/'engine'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from job_record_examples import make_job_example
from review_cli import main
from runtime_security import load_pdf_runtime


class JobRecordCLITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def args(self,case,output):
        args=[str(case['pdf']),'--scenario',str(case['scenario_path']),'--output',str(output),'--offline',
              '--reference-cache',str(self.root/'empty-cache'),'--clause-catalogue',str(SKILL/'engine/dated_clause_catalogue.json'),
              '--clause-facts',str(case['facts_path']),'--job-record-spec',str(case['spec_path'])]
        for sid,path in case['paths'].items():args.extend(['--job-record-file',sid+'='+str(path)])
        return args

    def test_complete_cli_and_reopened_pdf_include_actual_name_disagreement(self):
        case=make_job_example(self.root/'mismatch',form_name='OTHER INVENTED ENERGY LTD.')
        original=case['pdf'].read_bytes()
        output=self.root/'review.md'
        marked=self.root/'review-copy.pdf'
        with redirect_stdout(io.StringIO()),patch('review_cli.refresh_table_a2') as network:
            self.assertEqual(main([*self.args(case,output),'--annotated-pdf',str(marked)]),0)
        network.assert_not_called()
        text=output.read_text()
        self.assertIn('Plan and job-record comparisons',text)
        self.assertIn('applicant_form',text)
        self.assertIn('Compared 12 requested job-record checks',text)
        self.assertIn('FAIL=1',text)
        runtime=load_pdf_runtime()
        with runtime.open(marked) as doc:
            rendered='\n'.join(page.get_text() for page in doc)
            self.assertIn('applicant_form',rendered)
            self.assertTrue(any('applicant_form' in a.info.get('content','')
                                for page in doc for a in page.annots() or []))
        self.assertEqual(case['pdf'].read_bytes(),original)
        with self.assertRaises(FileExistsError):main(self.args(case,output))

    def test_stale_record_blocks_native_work_and_opted_in_source_refresh(self):
        case=make_job_example(self.root/'stale')
        case['paths']['registry'].write_bytes(case['paths']['registry'].read_bytes()+b'\n')
        args=[a for a in self.args(case,self.root/'review.md') if a!='--offline']
        with redirect_stderr(io.StringIO()),patch('review_cli.extract_pdf') as native,patch('review_cli.refresh_table_a2') as network:
            with self.assertRaises(SystemExit):main([*args,'--refresh-table-a2'])
        native.assert_not_called();network.assert_not_called()

    def test_duplicate_source_argument_and_orphan_record_flag_are_rejected(self):
        case=make_job_example(self.root/'arguments')
        for args in ([*self.args(case,self.root/'review.md'),'--job-record-file','form='+str(case['paths']['form'])],
                     [str(case['pdf']),'--scenario',str(case['scenario_path']),'--output',str(self.root/'review.md'),
                      '--job-record-file','form='+str(case['paths']['form'])]):
            with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):main(args)

    def test_confirmed_instruction_is_usable_without_form_or_regulatory_catalogue(self):
        case=make_job_example(self.root/'confirmed')
        spec=copy.deepcopy(case['spec'])
        spec['comparisons']=[q for q in spec['comparisons'] if q['id']=='applicant_confirmed']
        spec['balances']=[]
        case['spec_path'].write_text(json.dumps(spec))
        args=[str(case['pdf']),'--scenario',str(case['scenario_path']),'--output',str(self.root/'review.md'),
              '--offline','--reference-cache',str(self.root/'empty-cache'),
              '--job-record-spec',str(case['spec_path']),
              '--job-record-file','instructions='+str(case['paths']['instructions'])]
        with redirect_stdout(io.StringIO()):self.assertEqual(main(args),0)
        self.assertIn('JOB_QA_ONLY',(self.root/'review.md').read_text())

    def test_record_changed_after_actual_pdf_generation_prevents_both_outputs(self):
        from pdf_markup import build_annotated_pdf
        case=make_job_example(self.root/'export-race',form_name='OTHER INVENTED ENERGY LTD.')
        output,marked=self.root/'review.md',self.root/'review-copy.pdf'
        def change_after_build(*args,**kwargs):
            result=build_annotated_pdf(*args,**kwargs)
            reference=case['paths']['registry']
            reference.write_bytes(reference.read_bytes()+b'\n')
            return result
        with redirect_stdout(io.StringIO()),redirect_stderr(io.StringIO()), \
                patch('pdf_markup.build_annotated_pdf',side_effect=change_after_build):
            with self.assertRaises(SystemExit):
                main([*self.args(case,output),'--annotated-pdf',str(marked)])
        self.assertFalse(output.exists())
        self.assertFalse(marked.exists())


if __name__=='__main__':unittest.main()
