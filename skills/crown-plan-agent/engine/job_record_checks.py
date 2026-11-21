"""Bounded job identity comparisons on actual, separately read source fields.

The caller must obtain fields from the shared source reader, not import claimed
findings. Review declarations establish comparison intent, not legal authenticity
or the correctness of either record. No majority vote selects a company name.
"""
from __future__ import annotations

from copy import deepcopy
from math import isfinite
import re
import unicodedata

from clause_schema import _bounded_data
from finished_plan_spec import _fields, _text

KIND_ROLES = {'applicant_name': 'applicant', 'legal_description': 'legal_description',
              'disposition_id': 'disposition_id'}
BINDINGS = {'C_1_2_1_4_01': ('legal_description', 'APPLICATION_FORM'),
            'C_1_2_2_1_01': ('applicant_name', 'CLIENT_REGISTRY'),
            'C_1_2_2_1_02': ('applicant_name', 'APPLICATION_FORM')}
JOB_WORKBOOK_IDS = frozenset(BINDINGS)
SOURCE_KINDS = frozenset({'PLAN', 'APPLICATION_FORM', 'CLIENT_REGISTRY', 'JOB_INSTRUCTION',
                          'APPROVED_RECORD', 'OTHER_RECORD'})
_COMPARISON_KEYS = {'id', 'kind', 'plan_field_id', 'reference_field_id', 'workbook_check_id'}
_FIELD_KEYS = {'source_id', 'semantic_role', 'subject_id', 'measurement_scope', 'selector', 'unit_selector'}
_IDENTIFIER = re.compile(r'[A-Za-z][A-Za-z0-9_.-]{0,63}\Z')
_SHA256 = re.compile(r'[0-9a-f]{64}\Z')
_DISPOSITION = re.compile(r'([A-Z]{3}) ?([0-9]{1,24})\Z')
_ASCII_UPPER = str.maketrans('abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')
_UNKNOWN = frozenset({'UNKNOWN', 'UNCONFIRMED', 'N/A', 'NIL', 'TBD', 'NOT PROVIDED'})
RESIDUAL_REVIEW = (
    'Confirm the authoritative current job record, complete subject and field roles. '
    'A literal field agreement or discrepancy does not establish legal identity, '
    'the complete clause, illustrated extents or regulatory compliance.')


def _comparison_shape(comparisons: object) -> list[dict]:
    _bounded_data(comparisons)
    if not isinstance(comparisons, list) or len(comparisons) > 50:
        raise ValueError('Job comparisons require a list of at most 50 checks')
    ids, pairs = set(), set()
    for comparison in comparisons:
        _fields(comparison, _COMPARISON_KEYS, _COMPARISON_KEYS, 'job comparison')
        cid = comparison['id']
        if not isinstance(cid, str) or _IDENTIFIER.fullmatch(cid) is None or cid in ids:
            raise ValueError('Job comparison IDs must be unique bounded identifiers')
        ids.add(cid)
        kind = comparison['kind']
        if not isinstance(kind, str) or kind not in KIND_ROLES:
            raise ValueError('Unsupported job comparison kind')
        for key in ('plan_field_id', 'reference_field_id'):
            _text(comparison[key], key, 128)
        if comparison['plan_field_id'] == comparison['reference_field_id']:
            raise ValueError('Independent document comparison needs separate fields')
        pair = (kind, comparison['plan_field_id'], comparison['reference_field_id'])
        if pair in pairs:
            raise ValueError('Duplicate job field-pair comparison')
        pairs.add(pair)
        binding = comparison['workbook_check_id']
        if binding is not None:
            if not isinstance(binding, str) or binding not in BINDINGS:
                raise ValueError('Unsupported job comparison workbook binding')
            if BINDINGS[binding][0] != kind:
                raise ValueError('Workbook question does not match the job comparison kind')
    return comparisons


def validate_comparisons(comparisons: list, field_specs: dict) -> list:
    """Check bounded intent and roles before a caller opens reference artifacts."""
    comparisons = _comparison_shape(comparisons)
    if not isinstance(field_specs, dict):
        raise ValueError('Field specifications must be an object')
    for comparison in comparisons:
        selected = []
        for key in ('plan_field_id', 'reference_field_id'):
            fid = comparison[key]
            if fid not in field_specs:
                raise ValueError('Unknown field in job comparison: ' + fid)
            spec = field_specs[fid]
            _fields(spec, _FIELD_KEYS, _FIELD_KEYS, 'job comparison field')
            _text(spec['source_id'], 'Field source ID', 128)
            if spec['subject_id'] is not None:
                _text(spec['subject_id'], 'Field subject ID', 200)
            if spec['measurement_scope'] is not None:
                _text(spec['measurement_scope'], 'Field measurement scope', 300)
            if spec['semantic_role'] != KIND_ROLES[comparison['kind']]:
                raise ValueError('Field semantic role does not match the job comparison kind')
            selected.append(spec)
        if selected[0]['source_id'] == selected[1]['source_id']:
            raise ValueError('Independent job comparison requires different source records')
    return comparisons


def _normal(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip() or len(value) > 4096:
        return None
    if any(unicodedata.category(char).startswith('C') and char not in '\t\r\n' for char in value):
        return None
    # Preserve compatibility glyphs, punctuation, legal suffixes and homoglyphs.
    result = ' '.join(unicodedata.normalize('NFC', value).translate(_ASCII_UPPER).split())
    return None if result in _UNKNOWN else result


def _current_source(source: object) -> bool:
    if not isinstance(source, dict) or source.get('status') != 'READY':
        return False
    review = source.get('review')
    return (isinstance(review, dict) and review.get('status') == 'CURRENT_FOR_REVIEW'
            and _normal(review.get('reviewer')) is not None and _normal(review.get('basis')) is not None)


def _source_binding(field: dict, source: dict, source_id: str) -> bool:
    digest = source.get('source_sha256')
    kind = source.get('source_kind')
    evidence = field.get('evidence')
    return (isinstance(digest, str) and _SHA256.fullmatch(digest) is not None
            and isinstance(kind, str) and kind in SOURCE_KINDS
            and field.get('source_id') == source_id and field.get('source_sha256') == digest
            and isinstance(evidence, dict) and evidence.get('source_id') == source_id
            and evidence.get('source_kind') == kind and evidence.get('source_sha256') == digest
            and _located(evidence))


def _located(evidence: dict) -> bool:
    pointer = evidence.get('pointer')
    if pointer is not None:
        return (isinstance(pointer, str) and len(pointer) <= 4096
                and (pointer == '' or pointer.startswith('/'))
                and re.search(r'~(?![01])', pointer) is None)
    page, box = evidence.get('page'), evidence.get('bbox_points')
    if type(page) is not int or page < 1 or not isinstance(box, list) or len(box) != 4:
        return False
    try:
        return (all(type(value) in (int, float) and isfinite(value) and 0 <= value <= 1_000_000
                    for value in box) and box[0] < box[2] and box[1] < box[3])
    except OverflowError:
        return False


def _gate(comparison: dict, fields: list[dict | None], sources: list[dict | None]) -> str | None:
    if any(field is None for field in fields):
        return 'A requested source field is missing from the recorded read.'
    if any(source is None for source in sources):
        return 'A requested source record is missing from the recorded read.'
    if any(not isinstance(field, dict) or field.get('status') != 'READY' for field in fields):
        return 'Each original field must be completely and unambiguously readable.'
    if any(not _current_source(source) for source in sources):
        return 'Each source must be available and independently reviewed as current for this review; historical or unconfirmed records remain unresolved.'
    plan, reference = fields
    plan_source, reference_source = sources
    if plan_source.get('source_kind') != 'PLAN' or reference_source.get('source_kind') == 'PLAN':
        return 'The plan field and an independent job reference must have their separately reviewed source roles.'
    if any(field.get('semantic_role') != KIND_ROLES[comparison['kind']] for field in fields):
        return 'Field roles do not establish the requested subject; operator, landowner and surveyor fields are not applicant fields.'
    for field, source in zip(fields, sources):
        if not _source_binding(field, source, field.get('source_id')):
            return 'Field, evidence and source snapshot identities do not agree.'
    if plan_source['source_sha256'] == reference_source['source_sha256']:
        return 'The same underlying source bytes cannot count as an independent reference.'
    subjects = [field.get('subject_id') for field in fields] + [source.get('subject_id') for source in sources]
    if any(_normal(value) is None for value in subjects) or len(set(subjects)) != 1:
        return 'The reviewed job/subject identities are missing, unknown or inconsistent.'
    scopes = [field.get('measurement_scope') for field in fields]
    if scopes[0] != scopes[1] or any(scope is not None and _normal(scope) is None for scope in scopes):
        return 'The selected subject scopes differ or have not both been established.'
    question = comparison['workbook_check_id']
    if question is not None and reference_source['source_kind'] != BINDINGS[question][1]:
        return 'This clause requires an actual ' + BINDINGS[question][1] + '; another job reference cannot substitute for it.'
    return None


def review_job_comparisons(records_result: dict, comparisons: list) -> list:
    """Compare original reader outputs; retain each independent disagreement.

    This pure predicate layer does not read or authenticate files. The wrapping
    workflow must execute the shared source reader against the bound snapshots.
    Missing/unready records and mismatched identities remain explicit blockers.
    """
    comparisons = _comparison_shape(comparisons)
    if (not isinstance(records_result, dict) or not isinstance(records_result.get('fields'), dict)
            or not isinstance(records_result.get('sources'), dict)):
        raise ValueError('Job comparison execution requires recorded source and field objects')
    findings = []
    for comparison in comparisons:
        fields = [records_result['fields'].get(comparison[key]) for key in ('plan_field_id', 'reference_field_id')]
        sources = [records_result['sources'].get(field['source_id'])
                   if isinstance(field, dict) and isinstance(field.get('source_id'), str) else None
                   for field in fields]
        finding = {'check_id': comparison['id'], 'kind': comparison['kind'],
                   'workbook_check_id': comparison['workbook_check_id'],
                   'assessment_scope': ('DATED_CLAUSE_MECHANICAL_EVIDENCE'
                                        if comparison['workbook_check_id'] is not None else 'JOB_QA_ONLY'),
                   'mechanical_status': 'REVIEW_REQUIRED', 'execution_status': 'BLOCKED',
                   'reason': '', 'evidence': [deepcopy(field) for field in fields if isinstance(field, dict)],
                   'observed': [field.get('raw_value') if isinstance(field, dict) else None for field in fields],
                   'status': 'REVIEW_REQUIRED', 'residual_review': RESIDUAL_REVIEW}
        blocker = _gate(comparison, fields, sources)
        if blocker is not None:
            finding['reason'] = blocker
        else:
            values = [_normal(field.get('raw_value')) for field in fields]
            if any(value is None for value in values):
                finding['reason'] = 'Original values are empty, unknown or contain unsupported control characters.'
            else:
                if comparison['kind'] == 'disposition_id':
                    matches = [_DISPOSITION.fullmatch(value) for value in values]
                    values = [match.groups() if match else None for match in matches]
                if any(value is None for value in values):
                    finding['reason'] = ('A complete unambiguous disposition identifier requires three ASCII letters '
                                         'and its digit sequence; suffixes, missing numbers and competing identifiers remain unresolved.')
                elif (comparison['kind'] != 'disposition_id' and values[0] != values[1]
                      and values[0].casefold() == values[1].casefold()):
                    finding['reason'] = ('Unconfirmed Unicode case/equivalence may explain the different literal fields. '
                                         'Review the original spelling before accepting agreement or alleging a discrepancy.')
                else:
                    passed = values[0] == values[1]
                    finding.update(mechanical_status='PASS' if passed else 'FAIL', execution_status='EXECUTED',
                                   reason=('The selected literal subject fields agree.' if passed else
                                           'The selected literal subject fields disagree; confirm the authoritative record before correcting the plan.'))
                    finding['compared_values'] = deepcopy(values)
        findings.append(finding)
    return findings
