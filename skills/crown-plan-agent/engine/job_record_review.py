"""Coordinate actual record comparisons and fixed balances under evidence gates."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from clause_schema import _bounded_data, load_clause_catalogue
from clause_workbook import prepare_clause_workbook
from finished_plan_spec import _fields
from job_record_checks import JOB_WORKBOOK_IDS, review_job_comparisons, validate_comparisons
from record_balances import BINDINGS, review_record_balances, validate_balances
from record_fields import preflight_record_sources, read_record_fields, validate_record_spec

ASSESSMENT_SCOPE = 'JOB_RECORD_AND_BALANCE_QA'
WORKBOOK_IDS = JOB_WORKBOOK_IDS | frozenset(BINDINGS.values())
RESIDUAL = ('Confirm the correct current job/subject and source roles, the complete question and '
            'remaining visual, field and authoritative evidence. A comparison does not establish '
            'legal identity, correct geometry or regulatory compliance.')


def validate_job_spec(spec: dict) -> dict:
    _bounded_data(spec)
    keys = {'schema_version', 'records', 'comparisons', 'balances'}
    _fields(spec, keys, keys, 'job-record review specification')
    if type(spec['schema_version']) is not int or spec['schema_version'] != 1:
        raise ValueError('Unsupported job-record schema_version')
    validate_record_spec(spec['records'])
    fields = spec['records']['fields']
    validate_comparisons(spec['comparisons'], fields)
    validate_balances(spec['balances'], fields)
    checks = [*spec['comparisons'], *spec['balances']]
    if not checks:
        raise ValueError('A job-record specification requires at least one comparison or balance')
    if len({q['id'] for q in checks}) != len(checks):
        raise ValueError('Comparison and balance IDs must be unique across this review')
    return deepcopy(spec)


def validate_job_inputs(spec: dict, *, scenario: dict | None = None,
                        clause_catalogue: dict | None = None, clause_facts: dict | None = None) -> dict | None:
    """Validate intent and applicability before native parsing or refresh."""
    validate_job_spec(spec)
    bound = any(q['workbook_check_id'] for q in [*spec['comparisons'], *spec['balances']])
    if clause_catalogue is None:
        if bound or clause_facts is not None:
            raise ValueError('Bound job-record questions/facts require the explicit dated clause catalogue')
        return None
    canonical = load_clause_catalogue(Path(__file__).with_name('dated_clause_catalogue.json'))
    if clause_catalogue != canonical:
        raise ValueError('Job-record question execution requires the exact shipped dated catalogue')
    if scenario is None:
        raise ValueError('Dated question execution requires application context')
    return prepare_clause_workbook(clause_catalogue, scenario, {} if clause_facts is None else clause_facts)


def _manifest(preflight: dict) -> dict:
    return {sid: (s['actual_sha256'], s['size_bytes'], s['filename'])
            for sid, s in preflight['sources'].items()}


def verify_job_review_sources(plan_pdf: str | Path, spec: dict, record_paths: dict[str, Path], report: dict) -> None:
    """Repeat the full source-snapshot guard immediately before artifact publication."""
    current = preflight_record_sources(plan_pdf, spec['records'], record_paths)
    if _manifest(current) != _manifest(report):
        raise ValueError('A job-record source changed before review publication')


def _selection(check: dict, questions: dict) -> dict:
    binding = check['workbook_check_id']
    if binding is None:
        return {'selection_status': 'JOB_QA_REQUESTED', 'blocking_fact_ids': [], 'override_reason_codes': []}
    question = questions[binding]
    return {key: deepcopy(question[key]) for key in
            ('selection_status', 'blocking_fact_ids', 'override_reason_codes')}


def review_job_records(plan_pdf: str | Path, spec: dict, record_paths: dict[str, Path], *,
                       scenario: dict | None = None, clause_catalogue: dict | None = None,
                       clause_facts: dict | None = None) -> dict:
    """Read supplied original records; never import a caller's claimed result."""
    spec = validate_job_spec(spec)
    workbook = validate_job_inputs(spec, scenario=scenario, clause_catalogue=clause_catalogue,
                                   clause_facts=clause_facts)
    before = preflight_record_sources(plan_pdf, spec['records'], record_paths)
    questions = {q['id']: q for c in workbook['clauses'] for q in c['checks']} if workbook else {}
    checks = [*spec['comparisons'], *spec['balances']]
    selected = {q['id']: _selection(q, questions) for q in checks}
    active = {cid for cid, state in selected.items()
              if state['selection_status'] in ('JOB_QA_REQUESTED', 'CANDIDATE_REVIEW')}
    fields_to_read = set()
    for q in checks:
        if q['id'] not in active:
            continue
        if 'plan_field_id' in q:
            fields_to_read.update((q['plan_field_id'], q['reference_field_id']))
        else:
            fields_to_read.update(t['field_id'] for t in q['terms'])
            fields_to_read.add(q['total_field_id'])
    records = {**deepcopy(before), 'fields': {}}
    executed = {}
    if fields_to_read:
        selected_spec = deepcopy(spec['records'])
        selected_spec['fields'] = {fid: field for fid, field in selected_spec['fields'].items() if fid in fields_to_read}
        source_ids = {'plan'} | {field['source_id'] for field in selected_spec['fields'].values()}
        selected_spec['sources'] = {sid: s for sid, s in selected_spec['sources'].items() if sid in source_ids}
        records = read_record_fields(plan_pdf, selected_spec,
                                     {sid: path for sid, path in record_paths.items() if sid in source_ids})
        results = [*review_job_comparisons(records, [q for q in spec['comparisons'] if q['id'] in active]),
                   *review_record_balances(records, [q for q in spec['balances'] if q['id'] in active])]
        executed = {finding['check_id']: finding for finding in results}
    findings = []
    for check in checks:
        cid = check['id']
        finding = executed.get(cid, {'check_id': cid, 'kind': check['kind'],
            'workbook_check_id': check['workbook_check_id'],
            'assessment_scope': 'DATED_CLAUSE_MECHANICAL_EVIDENCE',
            'execution_status': 'NOT_EXECUTED', 'mechanical_status': 'REVIEW_REQUIRED',
            'status': 'REVIEW_REQUIRED', 'evidence': [], 'observed': [],
            'reason': 'Workbook context, condition or override did not select this question.',
            'residual_review': RESIDUAL})
        finding.update(selected[cid])
        finding['source_status'] = 'UNVERIFIED_CURRENT' if check['workbook_check_id'] else 'JOB_EXPECTATION_NOT_REGULATORY_AUTHORITY'
        if check['workbook_check_id']:
            finding['citation'] = deepcopy(questions[check['workbook_check_id']]['citation'])
        findings.append(finding)
    after = preflight_record_sources(plan_pdf, spec['records'], record_paths)
    if _manifest(after) != _manifest(before):
        raise ValueError('A job-record source changed while preparing the review')
    counts = Counter(f['mechanical_status'] for f in findings if f['execution_status'] == 'EXECUTED')
    return {'schema_version': 1, 'assessment_scope': ASSESSMENT_SCOPE,
            'overall_status': 'REVIEW_REQUIRED', 'regulatory_status': 'NOT_ASSESSED',
            'plan_source_sha256': before['sources']['plan']['actual_sha256'],
            'prepared_by': spec['records']['prepared_by'], 'subject_id': spec['records']['subject_id'],
            'spec_sha256': sha256(json.dumps(spec, sort_keys=True, separators=(',', ':'),
                                            ensure_ascii=False, allow_nan=False).encode()).hexdigest(),
            'sources': {**deepcopy(before['sources']), **deepcopy(records['sources'])}, 'fields': records['fields'],
            'unread_field_ids': sorted(set(spec['records']['fields']) - fields_to_read),
            'source': deepcopy(workbook['source']) if workbook else None,
            'findings': findings,
            'counts': {'requested': len(checks), 'executed': sum(counts.values()),
                       'blocked': sum(f['execution_status'] == 'BLOCKED' for f in findings),
                       'not_executed': sum(f['execution_status'] == 'NOT_EXECUTED' for f in findings),
                       'requested_bound_questions': len({q['workbook_check_id'] for q in checks if q['workbook_check_id']}),
                       **{status: counts[status] for status in ('PASS', 'FAIL', 'REVIEW_REQUIRED')}}}


def render_job_record_review(report: dict) -> str:
    from report_markdown import _cell
    if report.get('assessment_scope') != ASSESSMENT_SCOPE or report.get('overall_status') != 'REVIEW_REQUIRED':
        raise ValueError('Only review-only job-record results can be rendered')
    counts = report['counts']
    lines = ['', '## Plan and job-record comparisons', '',
             'Results describe selected literal fields and printed balances. Regulatory compliance is not established.',
             'Plan SHA-256: ' + _cell(report['plan_source_sha256']),
             f"Requested {counts['requested']}; executed {counts['executed']}; blocked {counts['blocked']}; not executed {counts['not_executed']}.",
             f"Mechanical PASS={counts['PASS']}; FAIL={counts['FAIL']}; REVIEW_REQUIRED={counts['REVIEW_REQUIRED']}.",
             '', '| Check | Scope/question | Selection | Execution | Mechanical result | Finding |', '|---|---|---|---|---|---|']
    for f in report['findings']:
        lines.append('| ' + ' | '.join(_cell(v) for v in (f['check_id'], f['workbook_check_id'] or 'JOB_QA_ONLY',
            f['selection_status'], f['execution_status'], f['mechanical_status'], f['reason'])) + ' |')
    lines.extend(['', '### Reference source snapshots', '',
                  '| Source | Kind | File | Subject | Reviewed version basis | Readiness | SHA-256 |', '|---|---|---|---|---|---|---|'])
    for sid, source in report['sources'].items():
        lines.append('| ' + ' | '.join(_cell(v) for v in (sid, source['source_kind'], source['filename'],
            source['subject_id'], source['review']['status'] + ': ' + source['review']['basis'],
            source['status'], source['actual_sha256'])) + ' |')
    lines.extend(['', 'Source roles, subject associations and currentness are supplied review declarations; a verified byte hash does not authenticate a record.',
                  '', '### Original selected fields', '', '| Field | Source | Semantic role | Original value | Unit header | Source location | Readiness |', '|---|---|---|---|---|---|---|'])
    for fid, field in report['fields'].items():
        evidence = field['evidence']
        location = ('page ' + str(evidence['page']) + ', box ' + str(evidence.get('bbox_points'))
                    if 'page' in evidence else 'JSON pointer ' + str(evidence.get('pointer', 'unlocated')))
        lines.append('| ' + ' | '.join(_cell(v) for v in (fid, field['source_id'], field['semantic_role'],
            field['raw_value'], field['unit_raw_value'], location, field['status'])) + ' |')
    for f in report['findings']:
        if f['kind'] in ('record_match', 'parts_total', 'amendment', 'gross_net', 'length_schedule'):
            lines.extend(['', 'Balance details: ' + _cell(f['check_id'])])
            for key in ('observed', 'expected', 'difference', 'unit', 'tolerance', 'tolerance_basis'):
                if key in f:
                    lines.append('- ' + key + ': ' + _cell(json.dumps(f[key], ensure_ascii=False)))
    lines.extend(['', RESIDUAL, 'Spatial partition/overlap and accepted boundary geometry remain separate evidence requirements.', ''])
    return '\n'.join(lines)
