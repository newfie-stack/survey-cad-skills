"""Exercise the supported evidence pass in the actual offline review workflow."""
import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import fitz
SKILL=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SKILL/'engine'))
from review_cli import main,run_review
from clause_schema import load_clause_catalogue


class EvidenceCLIIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.pdf=self.root/'invented.pdf'
        with fitz.open() as doc:
            doc.new_page().insert_text((40,60),'SCALE 1:2500')
            doc.save(self.pdf)
        sha=hashlib.sha256(self.pdf.read_bytes()).hexdigest()
        self.scenario=dict(land_class='alberta_crown',regulator='AER',disposition='LOC',stage='initial',
                           plan_type='sketch',purpose='Pipeline',subactivity='Fresh Water')
        self.spec=dict(schema_version=1,source_sha256=sha,prepared_by='Invented reviewer',hybrid_table=None,point_export=None,
            drawing=dict(spec=dict(schema_version=1,source_sha256=sha,prepared_by='Invented reviewer',checks=[
                dict(id='scale',kind='scale',description='Numerical scale',basis='Dated1.2.2.3',
                     regions=[dict(page=1,bbox_points=[30,40,250,70],role='Reviewed main scale')])]),
                bindings=[dict(workbook_check_id='C_1_2_2_3_01',drawing_check_id='scale')]))
        self.scenario_path=self.root/'scenario.json'
        self.scenario_path.write_text(json.dumps(self.scenario))
        self.spec_path=self.root/'evidence.json'
        self.spec_path.write_text(json.dumps(self.spec))

    def test_offline_cli_includes_execution_and_summary_without_network(self):
        output=self.root/'review.md'
        with redirect_stdout(io.StringIO()),patch('review_cli.refresh_table_a2') as download:
            result=main([str(self.pdf),'--scenario',str(self.scenario_path),'--output',str(output),'--offline',
                '--reference-cache',str(self.root/'empty-cache'),
                '--clause-catalogue',str(SKILL/'engine/dated_clause_catalogue.json'),
                '--regulatory-evidence-spec',str(self.spec_path)])
        self.assertEqual(result,0)
        download.assert_not_called()
        text=output.read_text()
        self.assertIn('Executed dated-clause evidence',text)
        self.assertIn('C_1_2_2_3_01',text)
        self.assertIn('Executed 1 clause-linked mechanical observation',text)
        self.assertIn('Mechanical PASS=1; FAIL=0; REVIEW_REQUIRED=0',text)
        self.assertIn('not close',text)
        self.assertIn('UNVERIFIED_CURRENT',text)

    def test_missing_catalogue_is_rejected_before_reading_source(self):
        with redirect_stderr(io.StringIO()),patch('review_cli.extract_pdf') as read:
            with self.assertRaises(SystemExit):
                main([str(self.pdf),'--scenario',str(self.scenario_path),'--output',str(self.root/'review.md'),
                      '--regulatory-evidence-spec',str(self.spec_path)])
            read.assert_not_called()

    def test_invalid_evidence_spec_blocks_pdf_and_opted_in_download(self):
        spec={**self.spec,'unexpected':'invalid'}
        self.spec_path.write_text(json.dumps(spec))
        with redirect_stderr(io.StringIO()),patch('review_cli.extract_pdf') as read,patch('review_cli.refresh_table_a2') as download:
            with self.assertRaises(SystemExit):
                main([str(self.pdf),'--scenario',str(self.scenario_path),'--output',str(self.root/'review.md'),
                    '--clause-catalogue',str(SKILL/'engine/dated_clause_catalogue.json'),
                    '--regulatory-evidence-spec',str(self.spec_path),'--refresh-table-a2'])
            read.assert_not_called()
            download.assert_not_called()

    def test_direct_api_requires_matching_catalogue_and_export_pair(self):
        for kwargs in ({'regulatory_evidence_spec':self.spec},
                       {'point_export':self.root/'points.csv'}):
            with self.subTest(kwargs=kwargs),patch('review_cli.extract_pdf') as read:
                with self.assertRaises(ValueError):
                    run_review(self.pdf,self.root/'review.md',self.scenario,SKILL/'engine/candidate_requirements.json',**kwargs)
                read.assert_not_called()

    def test_stale_evidence_stops_before_native_extraction_or_download(self):
        spec={**self.spec,'source_sha256':'0'*64}
        spec['drawing']=json.loads(json.dumps(spec['drawing']))
        spec['drawing']['spec']['source_sha256']='0'*64
        self.spec_path.write_text(json.dumps(spec))
        with redirect_stderr(io.StringIO()),patch('review_cli.extract_pdf') as read,patch('review_cli.refresh_table_a2') as download:
            with self.assertRaises(SystemExit):
                main([str(self.pdf),'--scenario',str(self.scenario_path),'--output',str(self.root/'review.md'),
                    '--clause-catalogue',str(SKILL/'engine/dated_clause_catalogue.json'),
                    '--regulatory-evidence-spec',str(self.spec_path),'--refresh-table-a2'])
            read.assert_not_called()
            download.assert_not_called()


if __name__=='__main__':unittest.main()
