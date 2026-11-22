"""Invented development documents; values are authored, never copied from work."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / 'engine'))
from runtime_security import load_pdf_runtime

SUBJECT = 'INVENTED-JOB-010'
NAME = 'PRAIRIE EXAMPLE ENERGY LTD.'
LEGAL = 'WITHIN SW 1/4 SEC 1 TWP 50 RGE 20 W4M'


def make_job_example(root: Path, *, plan_name=NAME, form_name=NAME, registry_name=NAME,
                     plan_legal=LEGAL, form_legal=LEGAL, plan_number='LOC001234',
                     form_number='LOC001234', crown='2.000 ha', private='1.100 ha',
                     amended='3.100 ha', deleted='0.100 ha') -> dict:
    root.mkdir(parents=True, exist_ok=False)
    runtime = load_pdf_runtime()
    selections = {}

    def pdf(source_id, items):
        path = root / (source_id + '.pdf')
        with runtime.open() as doc:
            page = doc.new_page(width=700, height=900)
            page.insert_text((40, 28), 'INVENTED RECORD - NOT A REAL JOB', fontsize=10)
            for index, (field_id, label, value) in enumerate(items):
                y = 60 + index * 30
                page.insert_text((40, y), label + ' ' + value, fontsize=10)
                selections[field_id] = {'region': {'page': 1, 'bbox_points': [30, y-16, 660, y+6],
                    'role': 'Reviewed invented ' + field_id, 'label': label}}
            doc.save(path)
        return path

    paths = {}
    paths['plan'] = pdf('plan', [
        ('p_app','Applicant:',plan_name), ('p_operator','Operator:','DECOY OPERATING LTD.'),
        ('p_number','Disposition:',plan_number), ('p_legal','Legal:',plan_legal),
        ('p_approved','Approved:','3.000 ha'), ('p_added','Added:','0.200 ha'),
        ('p_deleted','Deleted:',deleted), ('p_amended','Amended:',amended),
        ('p_crown','Crown area:',crown), ('p_private','Private area:',private),
        ('p_total','Activity total:','3.100 ha'), ('p_net','Net area:','2.900 ha'),
        ('p_excluded','Excluded:','0.200 ha')])
    paths['form'] = pdf('form', [('f_app','Applicant:',form_name),
        ('f_number','Disposition:',form_number),('f_legal','Legal:',form_legal),
        ('f_total','Activity area:','3.100 ha'), ('f_crown','Crown area:','2.000 ha'),
        ('f_private','Private area:','1.100 ha')])
    paths['registry'] = pdf('registry',[('r_app','Legal name:',registry_name)])
    paths['approved'] = pdf('approved',[('a_approved','Approved area:','3.000 ha')])
    paths['instructions'] = root/'instructions.json'
    paths['instructions'].write_text(json.dumps({'applicant':NAME,'confirmed_by':'Invented job owner',
        'basis':'Invented fixture expectation, not a real client instruction.'})+'\n')
    kinds = {'plan':'PLAN','form':'APPLICATION_FORM','registry':'CLIENT_REGISTRY',
             'approved':'APPROVED_RECORD','instructions':'JOB_INSTRUCTION'}
    sources = {sid: {'source_kind':kinds[sid], 'format':'JSON' if sid=='instructions' else 'PDF',
        'source_sha256':sha256(path.read_bytes()).hexdigest(),'subject_id':SUBJECT,
        'review':{'status':'HISTORICAL_BASIS' if sid=='approved' else 'CURRENT_FOR_REVIEW',
                  'reviewer':'Invented fixture author','basis':'Reviewed invented role and record version.'}}
        for sid,path in paths.items()}
    fields={}
    groups={'plan':['p_app','p_operator','p_number','p_legal','p_approved','p_added','p_deleted','p_amended',
                    'p_crown','p_private','p_total','p_net','p_excluded'],
            'form':['f_app','f_number','f_legal','f_total','f_crown','f_private'],
            'registry':['r_app'],'approved':['a_approved'],'instructions':['i_app']}
    for sid,ids in groups.items():
        for fid in ids:
            role=('applicant' if fid.endswith('_app') else 'operator' if fid.endswith('_operator') else
                  'disposition_id' if fid.endswith('_number') else 'legal_description' if fid.endswith('_legal') else 'area')
            fields[fid]={'source_id':sid,'semantic_role':role,'subject_id':SUBJECT,
                'measurement_scope':'same-invented-activity-ground-area' if role=='area' else None,
                'selector':{'pointer':'/applicant'} if sid=='instructions' else selections[fid], 'unit_selector':None}
    comparisons=[{'id':'applicant_form','kind':'applicant_name','plan_field_id':'p_app','reference_field_id':'f_app',
                  'workbook_check_id':'C_1_2_2_1_02'},
        {'id':'applicant_registry','kind':'applicant_name','plan_field_id':'p_app','reference_field_id':'r_app',
         'workbook_check_id':'C_1_2_2_1_01'},
        {'id':'legal_form','kind':'legal_description','plan_field_id':'p_legal','reference_field_id':'f_legal',
         'workbook_check_id':'C_1_2_1_4_01'},
        {'id':'number_form','kind':'disposition_id','plan_field_id':'p_number','reference_field_id':'f_number',
         'workbook_check_id':None},
        {'id':'applicant_confirmed','kind':'applicant_name','plan_field_id':'p_app','reference_field_id':'i_app',
         'workbook_check_id':None}]

    def balance(cid,kind,terms,total,binding=None):
        return {'id':cid,'kind':kind,'scope_review':{'status':'COMPLETE_FOR_DECLARED_EQUATION',
                'reviewer':'Invented fixture author','basis':'Complete invented balance for the stated activity.'},
            'subject_id':SUBJECT,'measurement_scope':'same-invented-activity-ground-area',
            'unit':'ha','tolerance':'0.000','tolerance_basis':'Exact invented displayed values.',
            'terms':[{'field_id':fid,'component_id':component,'role':role} for fid,component,role in terms],
            'total_field_id':total,'workbook_check_id':binding}
    balances=[balance('amendment_record','amendment',[
        ('a_approved','approved','approved'),('p_added','added','addition'),('p_deleted','deleted','deletion')],
        'p_amended','C_3_3_3_1_05'),
        balance('activity_parts','parts_total',[('p_crown','crown','component'),('p_private','private','component')],
                'p_total','C_1_3_6_3_01'),
        balance('form_area','record_match',[('f_total','activity','reference')],'p_total'),
        balance('crown_area','record_match',[('f_crown','crown','reference')],'p_crown'),
        balance('private_area','record_match',[('f_private','private','reference')],'p_private'),
        balance('approved_value','record_match',[('a_approved','approved','reference')],'p_approved'),
        balance('gross_net','gross_net',[('p_total','gross','gross'),('p_excluded','excluded','exclusion')],'p_net')]
    spec={'schema_version':1,'records':{'schema_version':1,'prepared_by':'Invented fixture author',
         'subject_id':SUBJECT,'sources':sources,'fields':fields},'comparisons':comparisons,'balances':balances}
    scenario={'land_class':'alberta_crown','regulator':'AER','disposition':'LOC','stage':'amendment',
              'plan_type':'survey_plan','existing_plan_type':'survey_plan','existing_length_m':1000,
              'affected_quarter_sections':1,'purpose':'Pipeline','subactivity':'Fresh Water'}
    facts={key:{'value':value,'provenance':{'source_id':'invented-brief','locator':'Invented amendment scenario'}}
           for key,value in [('uses_itemized_survey',True),('amendment_change_kind','add_and_delete')]}
    for name,value in [('job-spec.json',spec),('scenario.json',scenario),('facts.json',facts)]:
        (root/name).write_text(json.dumps(value,indent=2)+'\n')
    return {'pdf':paths.pop('plan'),'paths':paths,'spec':spec,'scenario':scenario,'facts':facts,
            'spec_path':root/'job-spec.json','scenario_path':root/'scenario.json','facts_path':root/'facts.json'}
