"""Actual invented records verify the coordinator, not caller-supplied answers."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SKILL=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SKILL/'engine'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from clause_schema import load_clause_catalogue
from job_record_examples import make_job_example,NAME
import job_record_review


class JobRecordReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.catalogue=load_clause_catalogue(SKILL/'engine/dated_clause_catalogue.json')

    def run_case(self,case,**overrides):
        return job_record_review.review_job_records(case['pdf'],overrides.get('spec',case['spec']),
            overrides.get('paths',case['paths']),scenario=overrides.get('scenario',case['scenario']),
            clause_catalogue=overrides.get('catalogue',self.catalogue),clause_facts=case['facts'])

    def test_clean_actual_records_and_all_printed_balances_execute(self):
        case=make_job_example(self.root/'clean')
        before={str(p):p.read_bytes() for p in [case['pdf'],*case['paths'].values()]}
        result=self.run_case(case)
        self.assertEqual(len(result['findings']),12)
        self.assertTrue(all(f['mechanical_status']=='PASS' for f in result['findings']))
        self.assertEqual(result['counts']['executed'],12)
        self.assertEqual(result['overall_status'],'REVIEW_REQUIRED')
        self.assertEqual(result['plan_source_sha256'],hashlib.sha256(case['pdf'].read_bytes()).hexdigest())
        self.assertTrue(all(Path(p).read_bytes()==raw for p,raw in before.items()))

    def test_conflicting_form_registry_and_confirmed_instruction_are_all_reported(self):
        case=make_job_example(self.root/'conflict',form_name='ANOTHER EXAMPLE ENERGY LTD.')
        rows={f['check_id']:f for f in self.run_case(case)['findings']}
        self.assertEqual(rows['applicant_form']['mechanical_status'],'FAIL')
        self.assertEqual(rows['applicant_registry']['mechanical_status'],'PASS')
        self.assertEqual(rows['applicant_confirmed']['mechanical_status'],'PASS')
        self.assertTrue(all(r['status']=='REVIEW_REQUIRED' for r in rows.values()))

    def test_shifted_categories_fail_even_when_grand_total_is_unchanged(self):
        case=make_job_example(self.root/'categories',crown='2.100 ha',private='1.000 ha')
        rows={f['check_id']:f for f in self.run_case(case)['findings']}
        self.assertEqual(rows['activity_parts']['mechanical_status'],'PASS')
        self.assertEqual(rows['form_area']['mechanical_status'],'PASS')
        self.assertEqual(rows['crown_area']['mechanical_status'],'FAIL')
        self.assertEqual(rows['private_area']['mechanical_status'],'FAIL')

    def test_missing_record_and_wrong_job_association_never_clear_name(self):
        case=make_job_example(self.root/'missing')
        paths={k:p for k,p in case['paths'].items() if k!='registry'}
        rows={f['check_id']:f for f in self.run_case(case,paths=paths)['findings']}
        self.assertEqual(rows['applicant_registry']['mechanical_status'],'REVIEW_REQUIRED')
        spec=copy.deepcopy(case['spec'])
        spec['records']['sources']['form']['subject_id']='ANOTHER-JOB'
        rows={f['check_id']:f for f in self.run_case(case,spec=spec)['findings']}
        self.assertEqual(rows['applicant_form']['mechanical_status'],'REVIEW_REQUIRED')

    def test_bound_questions_stop_at_scope_gate_while_job_qa_stays_separate(self):
        case=make_job_example(self.root/'scope')
        result=self.run_case(case,scenario={**case['scenario'],'land_class':'private'})
        for row in result['findings']:
            if row['workbook_check_id']:
                self.assertEqual(row['execution_status'],'NOT_EXECUTED')
                self.assertEqual(row['mechanical_status'],'REVIEW_REQUIRED')
            else:self.assertEqual(row['assessment_scope'],'JOB_QA_ONLY')

    def test_all_gated_questions_do_not_invoke_the_native_record_reader(self):
        case=make_job_example(self.root/'gated')
        spec=copy.deepcopy(case['spec'])
        spec['comparisons']=[q for q in spec['comparisons'] if q['workbook_check_id']]
        spec['balances']=[]
        with patch('job_record_review.read_record_fields') as reader:
            result=self.run_case(case,spec=spec,scenario={**case['scenario'],'regulator':'Unknown'})
        reader.assert_not_called()
        self.assertEqual(result['counts']['executed'],0)
        self.assertEqual(result['counts']['not_executed'],3)

    def test_same_record_bytes_cannot_be_relabelled_as_independent_registry(self):
        case=make_job_example(self.root/'duplicate')
        spec=copy.deepcopy(case['spec'])
        spec['records']['sources']['registry']['source_sha256']=spec['records']['sources']['plan']['source_sha256']
        spec['records']['fields']['r_app']['selector']=copy.deepcopy(spec['records']['fields']['p_app']['selector'])
        rows={f['check_id']:f for f in self.run_case(case,spec=spec,paths={**case['paths'],'registry':case['pdf']})['findings']}
        self.assertEqual(rows['applicant_registry']['mechanical_status'],'REVIEW_REQUIRED')

    def test_stale_auxiliary_document_fails_before_any_native_read(self):
        case=make_job_example(self.root/'stale')
        case['paths']['registry'].write_bytes(case['paths']['registry'].read_bytes()+b'\n')
        with patch('job_record_review.read_record_fields') as reader,self.assertRaises(ValueError):
            self.run_case(case)
        reader.assert_not_called()

    def test_unbound_job_instruction_comparison_does_not_require_a_catalogue(self):
        case=make_job_example(self.root/'confirmed')
        spec=copy.deepcopy(case['spec'])
        spec['comparisons']=[q for q in spec['comparisons'] if q['id']=='applicant_confirmed']
        spec['balances']=[]
        result=job_record_review.review_job_records(case['pdf'],spec,case['paths'])
        self.assertEqual(result['findings'][0]['mechanical_status'],'PASS')
        self.assertEqual(result['findings'][0]['assessment_scope'],'JOB_QA_ONLY')

    def test_malformed_record_readiness_is_not_replaced_by_hash_only_preflight(self):
        case=make_job_example(self.root/'malformed')
        case['paths']['registry'].write_bytes(b'This is an invented invalid PDF.')
        case['spec']['records']['sources']['registry']['source_sha256']=hashlib.sha256(case['paths']['registry'].read_bytes()).hexdigest()
        result=self.run_case(case)
        self.assertEqual(result['sources']['registry']['status'],'REVIEW_REQUIRED')
        rows={f['check_id']:f for f in result['findings']}
        self.assertEqual(rows['applicant_registry']['mechanical_status'],'REVIEW_REQUIRED')
        self.assertEqual(rows['applicant_form']['mechanical_status'],'PASS')


if __name__=='__main__':unittest.main()
