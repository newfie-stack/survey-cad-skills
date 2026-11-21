"""Actual PDF observations stay subordinate to workbook applicability."""
import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

import fitz

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / 'engine'))
from clause_schema import load_clause_catalogue
import regulatory_evidence


class RegulatoryEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.pdf = Path(self.temp.name) / 'invented.pdf'
        with fitz.open() as doc:
            page = doc.new_page()
            page.insert_text((40, 60), 'MAIN SCALE 1:2500')
            page.insert_text((40, 100), 'UNSURVEYED TERRITORY')
            page.insert_text((40, 140), 'DETAIL A')
            page.insert_text((40, 180), 'DETAIL B')
            doc.save(self.pdf)
        self.sha = hashlib.sha256(self.pdf.read_bytes()).hexdigest()
        self.scenario = dict(land_class='alberta_crown', regulator='AER',
                             disposition='LOC', stage='initial', plan_type='sketch',
                             purpose='Pipeline', subactivity='Fresh Water')
        self.catalogue = load_clause_catalogue(SKILL / 'engine/dated_clause_catalogue.json')
        self.drawing = dict(schema_version=1, source_sha256=self.sha, prepared_by='Invented reviewer', checks=[
            dict(id='main_scale', kind='scale', description='Main scale label', basis='Dated clause1.2.2.3',
                 regions=[dict(page=1,bbox_points=[30,40,250,70],role='Reviewed main scale')]),
            dict(id='detail_refs', kind='same_text', description='Selected detail identity', basis='Dated clause1.3.7.1',
                 regions=[dict(page=1,bbox_points=[30,120,250,150],role='Detail identity'),
                          dict(page=1,bbox_points=[30,160,250,190],role='Main-view reference')])])
        self.spec = dict(schema_version=1, source_sha256=self.sha, prepared_by='Invented reviewer',
                         hybrid_table=None, point_export=None,
                         drawing=dict(spec=self.drawing,bindings=[
                             dict(workbook_check_id='C_1_2_2_3_01', drawing_check_id='main_scale'),
                             dict(workbook_check_id='C_1_3_7_1_02', drawing_check_id='detail_refs')]))

    def run_review(self, **kwargs):
        return regulatory_evidence.review_regulatory_evidence(
            self.pdf, kwargs.get('scenario',self.scenario), kwargs.get('catalogue',self.catalogue),
            kwargs.get('facts',{}), kwargs.get('spec',self.spec))

    def test_actual_pdf_comparisons_are_question_linked_and_not_compliance(self):
        result = self.run_review(facts={'has_details':{'value':True,'provenance':
            {'source_id':'invented-brief','locator':'Reviewed whole-sheet views'}}})
        by_id = {i['workbook_check_id']:i for i in result['observations']}
        self.assertEqual(by_id['C_1_2_2_3_01']['mechanical_status'],'PASS')
        self.assertEqual(by_id['C_1_3_7_1_02']['mechanical_status'],'FAIL')
        self.assertTrue(all(i['status']=='REVIEW_REQUIRED' and i['residual_review'] for i in result['observations']))
        self.assertEqual(result['counts']['supported_clause_paths'],9)
        self.assertEqual(result['source_sha256'],self.sha)

    def test_out_of_scope_and_unknown_applicability_do_not_execute(self):
        private = self.run_review(scenario={**self.scenario,'land_class':'private'})
        self.assertTrue(all(i['execution_status']=='NOT_EXECUTED' for i in private['observations']))
        self.assertEqual(private['counts']['executed_observations'],0)
        missing = self.run_review()
        row = next(i for i in missing['observations'] if i['workbook_check_id']=='C_1_3_7_1_02')
        self.assertEqual(row['selection_status'],'UNRESOLVED_APPLICABILITY')
        self.assertEqual(row['execution_status'],'NOT_EXECUTED')

    def test_binding_to_wrong_kind_or_unbound_check_is_rejected(self):
        for mutation in ('wrong_kind','unbound','unknown','duplicate'):
            spec=copy.deepcopy(self.spec)
            if mutation=='wrong_kind':spec['drawing']['bindings'][0]['workbook_check_id']='C_1_3_7_3_02'
            if mutation=='unbound':spec['drawing']['bindings'].pop()
            if mutation=='unknown':spec['drawing']['bindings'][0]['workbook_check_id']='C_1_1_1_06'
            if mutation=='duplicate':spec['drawing']['bindings'].append(copy.deepcopy(spec['drawing']['bindings'][0]))
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):self.run_review(spec=spec)

    def test_unbound_edition_or_mutated_conditions_are_rejected(self):
        catalogue=copy.deepcopy(self.catalogue)
        catalogue['clauses'][0]['summary']='Changed interpretation'
        with self.assertRaises(ValueError):self.run_review(catalogue=catalogue)
        for sha in ('0'*64,self.sha):
            spec=copy.deepcopy(self.spec)
            if sha!=self.sha:spec['source_sha256']=sha
            else:spec['drawing']['spec']['source_sha256']='0'*64
            with self.assertRaises(ValueError):self.run_review(spec=spec)

    def test_unsupported_or_unconfirmed_unsurveyed_fact_cannot_select_note(self):
        spec=copy.deepcopy(self.spec)
        spec['drawing']['spec']['checks']=[dict(id='territory',kind='required_text',description='Territory note',
            basis='Dated clause1.3.3.5',expected='UNSURVEYED TERRITORY',
            regions=[dict(page=1,bbox_points=[30,80,300,110],role='Reviewed plan body')])]
        spec['drawing']['bindings']=[dict(workbook_check_id='C_1_3_3_5_01',drawing_check_id='territory')]
        result=self.run_review(spec=spec)
        self.assertEqual(result['observations'][0]['execution_status'],'NOT_EXECUTED')
        spec['drawing']['spec']['checks'][0]['expected']='CROWN LAND'
        with self.assertRaises(ValueError):self.run_review(spec=spec)

    def test_no_exact_territory_wording_is_mandated_by_the_clause(self):
        spec=copy.deepcopy(self.spec)
        spec['drawing']['spec']['checks']=[dict(id='territory',kind='required_text',description='Territory note',
            basis='Dated clause1.3.3.5',expected='UNSURVEYED TERRITORY',regions=[
                dict(page=1,bbox_points=[30,120,250,150],role='Reviewed complete plan body',
                     coverage_review=dict(status='TEXT_COMPLETE',method='VISUAL_TO_TEXT_COMPARISON',
                         reviewer='Invented reviewer',statement='Invented complete context compared with image.'))])]
        spec['drawing']['bindings']=[dict(workbook_check_id='C_1_3_3_5_01',drawing_check_id='territory')]
        result=self.run_review(spec=spec,facts={'is_unsurveyed_territory':{'value':True,'provenance':
            {'source_id':'invented-brief','locator':'Invented cadastral context'}}})
        self.assertEqual(result['drawing_review']['findings'][0]['status'],'FAIL')
        self.assertEqual(result['observations'][0]['mechanical_status'],'REVIEW_REQUIRED')
        self.assertIn('wording',result['observations'][0]['reason'])


if __name__=='__main__':unittest.main()
