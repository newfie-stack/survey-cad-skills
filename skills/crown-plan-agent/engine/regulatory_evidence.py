"""Execute bounded observations for selected dated questions, never compliance."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from clause_schema import _bounded_data, load_clause_catalogue
from clause_workbook import prepare_clause_workbook
from finished_plan_spec import _fields, _text, validate_spec
from pdf_source import read_pdf_snapshot

HYBRID_IDS = ('C_3_5_2_1_01', 'C_3_5_2_1_02', 'C_3_5_2_2_01',
              'C_3_5_2_2_02', 'C_3_5_2_3_01', 'C_3_5_6_2_01', 'C_3_5_6_3_01')
DRAWING_KINDS = {'C_1_2_2_3_01': 'scale', 'C_1_3_3_5_01': 'required_text',
                 'C_1_3_7_1_02': 'same_text', 'C_1_3_7_3_02': 'same_text'}
SUPPORTED_IDS = frozenset(HYBRID_IDS) | DRAWING_KINDS.keys()
ASSESSMENT_SCOPE = 'DATED_CLAUSE_MECHANICAL_EVIDENCE'
RESIDUAL = ('Confirm the complete clause, current application-specific authority, source/subject '
            'identity and remaining visual or field evidence. This bounded observation does not close the question.')


def validate_evidence_spec(spec: dict) -> dict:
    """Validate review intent before native PDF work, downloads or CSV reads."""
    _bounded_data(spec)
    keys = {'schema_version', 'source_sha256', 'prepared_by', 'hybrid_table', 'drawing', 'point_export'}
    _fields(spec, keys, keys, 'regulatory evidence spec')
    # Reuse the exact digest, version and preparer contract without accepting a finding.
    validate_spec({'schema_version': spec['schema_version'], 'source_sha256': spec['source_sha256'],
                   'prepared_by': spec['prepared_by'], 'checks': [{
                       'id': 'validate_source', 'kind': 'visual', 'description': 'Validate envelope',
                       'basis': 'Envelope validation', 'regions': [
                           {'page': 1, 'bbox_points': [0, 0, 1, 1], 'role': 'Envelope only'}]}]})
    hybrid, drawing, export = spec['hybrid_table'], spec['drawing'], spec['point_export']
    if hybrid is None and drawing is None:
        raise ValueError('Evidence spec requires hybrid_table or drawing requests')
    if hybrid is not None:
        from hybrid_table_review import validate_hybrid_spec
        validate_hybrid_spec(hybrid)
        if hybrid['source_sha256'] != spec['source_sha256']:
            raise ValueError('Hybrid table and evidence source SHA-256 must match')
    if export is not None:
        from cad_gis_points import validate_point_export_spec
        validate_point_export_spec(export)
        if hybrid is None:
            raise ValueError('A point export requires the source-bound hybrid table')
    if drawing is not None:
        _fields(drawing, {'spec', 'bindings'}, {'spec', 'bindings'}, 'drawing')
        validate_spec(drawing['spec'])
        if drawing['spec']['source_sha256'] != spec['source_sha256']:
            raise ValueError('Drawing and evidence source SHA-256 must match')
        bindings = drawing['bindings']
        checks = {c['id']: c for c in drawing['spec']['checks']}
        if not isinstance(bindings, list) or not 1 <= len(bindings) <= len(DRAWING_KINDS):
            raise ValueError('Drawing bindings require a bounded nonempty list')
        used_checks, used_questions = set(), set()
        for binding in bindings:
            _fields(binding, {'workbook_check_id', 'drawing_check_id'},
                    {'workbook_check_id', 'drawing_check_id'}, 'drawing binding')
            question, cid = binding['workbook_check_id'], binding['drawing_check_id']
            _text(question, 'workbook check ID', 128)
            _text(cid, 'drawing check ID', 64)
            if question not in DRAWING_KINDS or cid not in checks:
                raise ValueError('Unknown or unsupported drawing binding')
            if question in used_questions or cid in used_checks:
                raise ValueError('Duplicate drawing question or observation binding')
            used_questions.add(question)
            used_checks.add(cid)
            check = checks[cid]
            if check['kind'] != DRAWING_KINDS[question]:
                raise ValueError('Drawing kind does not match the supported question')
            if question == 'C_1_3_3_5_01' and check['expected'] != 'UNSURVEYED TERRITORY':
                raise ValueError('Territory observation requires the source-specific territory phrase')
        if used_checks != set(checks):
            raise ValueError('Every drawing check needs exactly one supported question binding')
    return spec


def validate_execution_inputs(scenario: dict, catalogue: dict, facts: dict, spec: dict) -> dict:
    """Only this shipped dated interpretation may select this adapter mapping."""
    validate_evidence_spec(spec)
    canonical = load_clause_catalogue(Path(__file__).with_name('dated_clause_catalogue.json'))
    if catalogue != canonical:
        raise ValueError('Evidence execution requires the exact shipped dated clause catalogue')
    return prepare_clause_workbook(catalogue, scenario, facts)


def review_regulatory_evidence(pdf: str | Path, scenario: dict, catalogue: dict,
                               facts: dict, spec: dict, *, point_export: Path | None = None) -> dict:
    """Read original evidence only for selected questions; preserve all blockers."""
    workbook = validate_execution_inputs(scenario, catalogue, facts, spec)
    if (point_export is not None) != (spec['point_export'] is not None):
        raise ValueError('Point-export file and specification must be supplied together')
    source = Path(pdf)
    digest = read_pdf_snapshot(source)[1]
    if digest != spec['source_sha256']:
        raise ValueError('Source SHA-256 does not match regulatory evidence specification')
    questions = {q['id']: (c, q) for c in workbook['clauses'] for q in c['checks']}
    requested = list(HYBRID_IDS) if spec['hybrid_table'] is not None else []
    bindings = spec['drawing']['bindings'] if spec['drawing'] is not None else []
    requested.extend(b['workbook_check_id'] for b in bindings)
    selected = {ident for ident in requested if questions[ident][1]['selection_status'] == 'CANDIDATE_REVIEW'}
    executed = {}
    hybrid_report = None
    if selected.intersection(HYBRID_IDS):
        from hybrid_table_review import review_hybrid_table
        hybrid_report = review_hybrid_table(source, spec['hybrid_table'])
        for finding in hybrid_report['findings']:
            ident = finding['workbook_check_id']
            if ident in selected:
                executed[ident] = finding
    selected_bindings = [b for b in bindings if b['workbook_check_id'] in selected]
    drawing_report = None
    if selected_bindings:
        from finished_plan_review import review_finished_plan
        drawing_spec = deepcopy(spec['drawing']['spec'])
        ids = {b['drawing_check_id'] for b in selected_bindings}
        drawing_spec['checks'] = [c for c in drawing_spec['checks'] if c['id'] in ids]
        drawing_report = review_finished_plan(source, drawing_spec)
        by_id = {f['check_id']: f for f in drawing_report['findings']}
        for binding in selected_bindings:
            f = by_id[binding['drawing_check_id']]
            observation = {
                'mechanical_status': f['status'], 'execution_status': 'EXECUTED',
                'reason': f['reason'], 'evidence': deepcopy(f['evidence']), 'drawing_finding': deepcopy(f)}
            if binding['workbook_check_id'] == 'C_1_3_3_5_01' and f['status'] == 'FAIL':
                observation.update(mechanical_status='REVIEW_REQUIRED', reason=(
                    'The selected territory phrase was not observed; clause1.3.3.5 does not prescribe '
                    'exact wording. Inspect alternative wording and the full source before alleging an omission.'))
            executed[binding['workbook_check_id']] = observation
    observations = []
    for ident in requested:
        clause, question = questions[ident]
        observation = {'workbook_check_id': ident, 'clause_id': clause['id'],
                       'citation': deepcopy(question['citation']),
                       'selection_status': question['selection_status'],
                       'execution_status': 'NOT_EXECUTED', 'mechanical_status': 'REVIEW_REQUIRED',
                       'reason': 'Workbook applicability/override gate did not select this question.',
                       'evidence': [], 'source_status': 'UNVERIFIED_CURRENT',
                       'status': 'REVIEW_REQUIRED', 'residual_review': RESIDUAL}
        if ident in executed:
            finding = executed[ident]
            observation.update(deepcopy(finding))
            # An adapter can report a diagnostic only, never overwrite the authority verdict.
            observation.update(workbook_check_id=ident, clause_id=clause['id'],
                               status='REVIEW_REQUIRED', source_status='UNVERIFIED_CURRENT',
                               residual_review=RESIDUAL)
        observations.append(observation)
    export_report = None
    if point_export is not None:
        if hybrid_report is not None:
            from cad_gis_points import compare_point_export
            export_report = compare_point_export(point_export, spec['point_export'], hybrid_report['table'])
        else:
            export_report = {'execution_status': 'NOT_EXECUTED', 'mechanical_status': 'REVIEW_REQUIRED',
                             'regulatory_status': 'REVIEW_REQUIRED',
                             'reason': 'No hybrid question passed the workbook selection gate; export was not read.'}
    if read_pdf_snapshot(source)[1] != digest:
        raise ValueError('Source PDF changed during clause evidence execution')
    counts = Counter(o['mechanical_status'] for o in observations if o['execution_status'] == 'EXECUTED')
    selected_questions = [q for c in workbook['clauses'] for q in c['checks'] if q['selection_status'] == 'CANDIDATE_REVIEW']
    report = {'schema_version': 1, 'assessment_scope': ASSESSMENT_SCOPE,
              'source_sha256': digest, 'prepared_by': spec['prepared_by'],
              'spec_sha256': hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(',', ':'),
                                                       ensure_ascii=False, allow_nan=False).encode()).hexdigest(),
              'catalogue_id': workbook['catalogue_id'], 'source': deepcopy(workbook['source']),
              'overall_status': 'REVIEW_REQUIRED', 'source_status': 'UNVERIFIED_CURRENT',
              'observations': observations, 'hybrid_table_review': hybrid_report,
              'drawing_review': drawing_report, 'point_export_comparison': export_report,
              'counts': {'supported_question_paths': len(SUPPORTED_IDS), 'supported_clause_paths': 9,
                         'requested_observations': len(observations),
                         'executed_observations': sum(counts.values()),
                         'not_executed_observations': len(observations) - sum(counts.values()),
                         'selected_manual_questions': len(selected_questions),
                         'selected_questions_without_requested_observation': sum(q['id'] not in requested for q in selected_questions),
                         **{status: counts[status] for status in ('PASS', 'FAIL', 'REVIEW_REQUIRED')}}}
    return report


def render_regulatory_evidence(report: dict) -> str:
    from report_markdown import _cell
    if report.get('assessment_scope') != ASSESSMENT_SCOPE or report.get('overall_status') != 'REVIEW_REQUIRED':
        raise ValueError('Only review-only clause evidence can be rendered')
    counts = report['counts']
    lines = ['', '## Executed dated-clause evidence', '',
             'Mechanical observations are partial evidence; every regulatory verdict remains REVIEW_REQUIRED.',
             'Source SHA-256: ' + _cell(report['source_sha256']),
             f"Requested {counts['requested_observations']}; executed {counts['executed_observations']}; not executed {counts['not_executed_observations']}.",
             f"Mechanical PASS={counts['PASS']}; FAIL={counts['FAIL']}; REVIEW_REQUIRED={counts['REVIEW_REQUIRED']}.",
             f"Selected workbook questions without a requested observation: {counts['selected_questions_without_requested_observation']}.",
             '', '| Question | Selection | Execution | Mechanical result | Reason |', '|---|---|---|---|---|']
    for row in report['observations']:
        lines.append('| ' + ' | '.join(_cell(row.get(k)) for k in
                     ('workbook_check_id', 'selection_status', 'execution_status', 'mechanical_status', 'reason')) + ' |')
    hybrid = report.get('hybrid_table_review')
    if hybrid is not None:
        lines.extend(['', '### Coordinate-table source trace', '',
                      '| Physical row | Field | Page | PDF box | Original text |', '|---|---|---|---|---|'])
        for row in hybrid['field_evidence']:
            for field, evidence in row['source_locator']['fields'].items():
                lines.append('| ' + ' | '.join(_cell(v) for v in (
                    row['row_index'], field, evidence['page'], evidence['bbox_points'], evidence['text'])) + ' |')
        lines.extend(['', 'Table completeness, CRS, frame and role acceptance are supplied review declarations; the reader does not independently establish them.'])
    drawing = report.get('drawing_review')
    if drawing is not None:
        lines.extend(['', '### Drawing source trace', '', '| Observation | Page | PDF box | Selected role | Original text |', '|---|---|---|---|---|'])
        for finding in drawing['findings']:
            for evidence in finding['evidence']:
                lines.append('| ' + ' | '.join(_cell(v) for v in (
                    finding['check_id'], evidence['page'], evidence['bbox_points'], evidence['role'], evidence['text'])) + ' |')
    export = report.get('point_export_comparison')
    if export is not None:
        lines.extend(['', '### CAD/GIS point-export comparison', '',
                      'Execution: ' + _cell(export.get('comparison_execution_status', export['execution_status'])),
                      'Mechanical result: ' + _cell(export['mechanical_status']),
                      'Export source SHA-256: ' + _cell(export.get('source_sha256', 'not read')),
                      'Coordinate frame: ' + _cell(export.get('coordinate_frame_id', 'unresolved')),
                      'This reads an exported point file; native DWG/SHP, survey control and transformations are not inspected.'])
        if export.get('reason'):
            lines.append(_cell(export['reason']))
        for finding in export.get('findings', []):
            lines.append('- ' + _cell(finding['reason_code']) + ': ' + _cell(json.dumps(finding, ensure_ascii=False)))
        comparisons = export.get('comparisons', [])
        if comparisons:
            lines.extend(['', '| Point | CSV line | Easting difference | Northing difference | Comparison |', '|---|---|---|---|---|'])
            for point in comparisons:
                lines.append('| ' + ' | '.join(_cell(v) for v in (
                    point['point_id'], point['export']['export_line'], point['delta_easting'], point['delta_northing'], point['status'])) + ' |')
    lines.extend(['', RESIDUAL, ''])
    return '\n'.join(lines)
