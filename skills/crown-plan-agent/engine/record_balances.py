"""Compare fixed printed-record balances; no spatial or regulatory acceptance.

Field outputs must come from the source-bound record reader. Scope, currentness
and role declarations are review evidence, not facts inferred by this module.
No arithmetic expression, unit conversion or geometry reconstruction is accepted.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from decimal import Decimal, localcontext
from math import isfinite
import re
import unicodedata

from clause_schema import _bounded_data
from finished_plan_spec import _fields, _text, decimal_value
from printed_numbers import parse_printed_amount

MAX_BALANCES = 50
MAX_TERMS = 100
IDENTIFIER = re.compile(r'[A-Za-z][A-Za-z0-9_.-]{0,63}\Z')
DIGEST = re.compile(r'[0-9a-f]{64}\Z')
SOURCE_KINDS = frozenset({'PLAN', 'APPLICATION_FORM', 'CLIENT_REGISTRY', 'JOB_INSTRUCTION',
                          'APPROVED_RECORD', 'OTHER_RECORD'})
KINDS = frozenset({'parts_total', 'amendment', 'gross_net', 'length_schedule', 'record_match'})
BINDINGS = {'parts_total': 'C_1_3_6_3_01', 'amendment': 'C_3_3_3_1_05',
            'length_schedule': 'C_1_3_6_6_02'}
ROLES = {'parts_total': {'component'}, 'length_schedule': {'component'},
         'amendment': {'approved', 'addition', 'deletion'},
         'gross_net': {'gross', 'exclusion'}, 'record_match': {'reference'}}
FIELDS = {'id', 'kind', 'scope_review', 'subject_id', 'measurement_scope', 'unit',
          'tolerance', 'tolerance_basis', 'terms', 'total_field_id', 'workbook_check_id'}
RESIDUAL = ('This compares the declared printed balance only. Verify current application-specific '
            'authority, complete component identities, record truth and remaining source/visual '
            'obligations. Spatial partition, overlap, road exclusions and boundary areas remain '
            'unverified; no geometry or accepted regulatory result is established.')


def _identifier(value: object, label: str) -> None:
    if not isinstance(value, str) or IDENTIFIER.fullmatch(value) is None:
        raise ValueError(label + ' must be a bounded identifier')


def _validate_shape(balances: object) -> None:
    _bounded_data(balances)
    if not isinstance(balances, list) or len(balances) > MAX_BALANCES:
        raise ValueError('balances must contain 0..50 entries')
    identifiers = set()
    for balance in balances:
        _fields(balance, FIELDS, FIELDS, 'balance')
        _identifier(balance['id'], 'Balance ID')
        if balance['id'] in identifiers:
            raise ValueError('Balance IDs must be unique')
        identifiers.add(balance['id'])
        kind = balance['kind']
        if not isinstance(kind, str) or kind not in KINDS:
            raise ValueError('Unsupported balance kind')
        _text(balance['subject_id'], 'Balance subject_id', 200)
        _text(balance['measurement_scope'], 'Balance measurement_scope', 200)
        units = {'m'} if kind == 'length_schedule' else {'ha', 'm2', 'm'} if kind == 'record_match' else {'ha', 'm2'}
        if balance['unit'] not in units:
            raise ValueError('Balance unit is incompatible with its dimension')
        decimal_value(balance['tolerance'])
        _text(balance['tolerance_basis'], 'Balance tolerance_basis')
        review = balance['scope_review']
        keys = {'status', 'reviewer', 'basis'}
        _fields(review, keys, keys, 'Balance scope_review')
        if review['status'] not in ('COMPLETE_FOR_DECLARED_EQUATION', 'UNCONFIRMED'):
            raise ValueError('Unsupported balance scope review status')
        _text(review['reviewer'], 'Balance scope reviewer', 200)
        _text(review['basis'], 'Balance scope basis')
        binding = balance['workbook_check_id']
        if binding is not None and binding != BINDINGS.get(kind):
            raise ValueError('Balance workbook binding is unsupported for its kind')
        _identifier(balance['total_field_id'], 'Balance total_field_id')
        terms = balance['terms']
        if not isinstance(terms, list) or not 1 <= len(terms) <= MAX_TERMS:
            raise ValueError('Balance terms must contain 1..100 entries')
        fields, components, roles = set(), set(), Counter()
        for term in terms:
            keys = {'field_id', 'component_id', 'role'}
            _fields(term, keys, keys, 'Balance term')
            _identifier(term['field_id'], 'Balance field ID')
            _identifier(term['component_id'], 'Balance component ID')
            if not isinstance(term['role'], str) or term['role'] not in ROLES[kind]:
                raise ValueError('Unsupported role for balance kind')
            if term['field_id'] in fields or term['component_id'] in components:
                raise ValueError('Balance fields and component identities must be unique')
            fields.add(term['field_id'])
            components.add(term['component_id'])
            roles[term['role']] += 1
        if balance['total_field_id'] in fields:
            raise ValueError('Balance total cannot reuse a component field')
        if kind == 'amendment' and (roles['approved'] != 1 or not roles['addition'] + roles['deletion']):
            raise ValueError('Amendment balance needs one approved amount and a change')
        if kind == 'gross_net' and (roles['gross'] != 1 or not roles['exclusion']):
            raise ValueError('Gross/net balance needs one gross amount and exclusions')
        if kind == 'record_match' and len(terms) != 1:
            raise ValueError('A record match needs exactly one reference amount')


def validate_balances(balances: list, field_specs: dict) -> list:
    """Validate bounded review intent against the caller's validated field map."""
    _validate_shape(balances)
    if not isinstance(field_specs, dict):
        raise ValueError('Balance field specifications must be an ID-keyed object')
    for balance in balances:
        dimension = 'length' if balance['unit'] == 'm' else 'area'
        refs = [term['field_id'] for term in balance['terms']] + [balance['total_field_id']]
        for ident in refs:
            field = field_specs.get(ident)
            if not isinstance(field, dict):
                raise ValueError('Balance references an unknown field')
            if field.get('semantic_role') != dimension:
                raise ValueError('Balance field semantic role does not match its dimension')
            for name in ('subject_id', 'measurement_scope'):
                if field.get(name) is not None:
                    _text(field[name], 'Balance field ' + name, 300)
    return deepcopy(balances)


def _normal(value: str) -> str:
    return ' '.join(unicodedata.normalize('NFKC', value).split()).upper()


def _known_text(value: object) -> bool:
    return (isinstance(value, str) and bool(value.strip()) and len(value) <= 4096
            and _normal(value) not in {'UNKNOWN', 'UNCONFIRMED', 'N/A', 'NIL', 'TBD', 'NOT PROVIDED'})


def _box(value: object) -> bool:
    if not isinstance(value, list) or len(value) != 4:
        return False
    try:
        return (all(type(number) in (int, float) and isfinite(number) and 0 <= number <= 1_000_000
                    for number in value) and value[0] < value[2] and value[1] < value[3])
    except OverflowError:
        return False


def _header_unit(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip() or len(value) > 300:
        return None
    text = _normal(value)
    if text.endswith('.'):
        text = text[:-1]
    aliases = {'ha': ('HA', 'HECTARE', 'HECTARES'),
               'm': ('M', 'METRE', 'METRES', 'METER', 'METERS'),
               'm2': ('M2', 'M^2', 'SQUARE METRES', 'SQUARE METERS')}
    prefixes = ('AREA', 'TOTAL AREA', 'AREA REQUIRED', 'APPROVED AREA', 'ADDED AREA',
                'DELETED AREA', 'RETAINED AREA', 'GROSS AREA', 'NET AREA', 'LENGTH',
                'TOTAL LENGTH', 'TOTAL')
    for unit, names in aliases.items():
        for name in names:
            if text in (name, '(' + name + ')', '[' + name + ']'):
                return unit
            for prefix in prefixes:
                if text in (prefix + ' (' + name + ')', prefix + '(' + name + ')',
                            prefix + ' [' + name + ']', prefix + ': ' + name,
                            prefix + ' ' + name):
                    return unit
    return None


def _evidence_tokens(evidence: object, field: dict) -> tuple[set[tuple], str | None]:
    """Identify native observations, not arbitrary field aliases or container IDs."""
    if not isinstance(evidence, dict):
        return set(), 'Source-located amount evidence is missing.'
    digest, source_id = field.get('source_sha256'), field.get('source_id')
    if (evidence.get('source_sha256') != digest or evidence.get('source_id') != source_id
            or evidence.get('source_kind') != field.get('source_kind')
            or field.get('source_kind') not in SOURCE_KINDS
            or not isinstance(digest, str) or DIGEST.fullmatch(digest) is None):
        return set(), 'Amount evidence is not bound to its declared source snapshot.'
    pointers = [evidence[key] for key in ('pointer', 'json_pointer') if key in evidence]
    if pointers:
        if (not all(isinstance(pointer, str) and len(pointer) <= 4096
                    and (pointer == '' or pointer.startswith('/'))
                    and re.search(r'~(?![01])', pointer) is None for pointer in pointers)
                or len(set(pointers)) != 1):
            return set(), 'JSON amount evidence needs one explicit source pointer.'
        return {(digest, 'JSON', pointers[0])}, None
    page, box = evidence.get('page'), evidence.get('bbox_points')
    if type(page) is not int or page < 1 or not _box(box):
        return set(), 'PDF amount evidence needs a page and source box.'
    spans = evidence.get('spans')
    if spans:
        tokens = set()
        if not isinstance(spans, list) or len(spans) > 5000:
            return set(), 'PDF amount span evidence is malformed or unbounded.'
        for span in spans:
            if (not isinstance(span, dict) or not _box(span.get('bbox_points'))
                    or not isinstance(span.get('text'), str)):
                return set(), 'PDF amount span evidence is malformed.'
            try:
                tokens.add((digest, 'PDF', page, tuple(span['bbox_points']), span['text']))
            except TypeError:
                return set(), 'PDF amount span evidence is malformed.'
        return tokens, None
    if not isinstance(evidence.get('text'), str):
        return set(), 'PDF amount evidence needs its original text.'
    try:
        return {(digest, 'PDF', page, tuple(box), evidence['text'])}, None
    except TypeError:
        return set(), 'PDF amount evidence is malformed.'


def _read_amount(field: dict, balance: dict) -> tuple[Decimal | None, str | None]:
    raw = field.get('raw_value')
    if not isinstance(raw, str) or len(raw) > 1000:
        return None, 'An amount must retain one bounded original string.'
    unit = balance['unit']
    header = field.get('unit_raw_value')
    if header is not None:
        if _header_unit(header) != unit:
            return None, 'The actual unit header is unsupported, conflicting or different from the declared unit.'
        _, issue = _evidence_tokens(field.get('unit_evidence'), field)
        if issue:
            return None, 'Unit-header evidence is not source bound: ' + issue
    value = parse_printed_amount(raw, unit)
    if value is None and header is not None:
        value = parse_printed_amount(raw + ' ' + unit, unit)
    if value is None:
        return None, 'Amount formatting or units are unsupported; a bare number needs an actual matching unit header.'
    return value, None


def review_record_balances(record_result: dict, balances: list) -> list:
    """Execute fixed balances on actual reader outputs; retain all residual work."""
    _validate_shape(balances)
    if not isinstance(record_result, dict):
        raise ValueError('Record result must be an object')
    fields, sources = record_result.get('fields'), record_result.get('sources')
    if not isinstance(fields, dict) or not isinstance(sources, dict):
        raise ValueError('Record result requires ID-keyed fields and sources')
    findings = []
    for balance in balances:
        finding = {'check_id': balance['id'], 'kind': balance['kind'],
                   'workbook_check_id': balance['workbook_check_id'],
                   'assessment_scope': ('JOB_QA_ONLY' if balance['workbook_check_id'] is None
                                        else 'DATED_CLAUSE_MECHANICAL_EVIDENCE'),
                   'mechanical_status': 'REVIEW_REQUIRED', 'execution_status': 'BLOCKED',
                   'reason': '', 'evidence': [], 'observed': [], 'expected': None,
                   'difference': None, 'unit': balance['unit'], 'tolerance': balance['tolerance'],
                   'tolerance_basis': balance['tolerance_basis'], 'status': 'REVIEW_REQUIRED',
                   'spatial_partition_status': 'REVIEW_REQUIRED', 'residual_review': RESIDUAL}
        issues, seen, amounts = [], set(), []
        if balance['scope_review']['status'] != 'COMPLETE_FOR_DECLARED_EQUATION':
            issues.append('Complete component scope for the declared equation has not been reviewed.')
        if not all(_known_text(balance['scope_review'][name]) for name in ('reviewer', 'basis')):
            issues.append('The declared component scope needs an identified reviewer and review basis.')
        if not all(_known_text(balance[name]) for name in ('subject_id', 'measurement_scope', 'tolerance_basis')):
            issues.append('The activity identity, measurement scope and tolerance basis must be known for this balance.')
        dimension = 'length' if balance['unit'] == 'm' else 'area'
        refs = [*balance['terms'], {'field_id': balance['total_field_id'], 'component_id': None, 'role': 'total'}]
        for term in refs:
            ident, role = term['field_id'], term['role']
            field = fields.get(ident)
            if not isinstance(field, dict):
                issues.append('Missing source field: ' + ident)
                amounts.append(None)
                continue
            finding['evidence'].append(deepcopy(field))
            item = {'field_id': ident, 'component_id': term['component_id'], 'role': role,
                    'raw_value': field.get('raw_value'), 'unit_raw_value': field.get('unit_raw_value'), 'value': None}
            finding['observed'].append(item)
            if field.get('status') != 'READY':
                issues.append('Field remains unreadable or unresolved: ' + ident)
            if (field.get('semantic_role') != dimension or field.get('subject_id') != balance['subject_id']
                    or field.get('measurement_scope') != balance['measurement_scope']):
                issues.append('Field role, subject or measurement scope differs: ' + ident)
            source = sources.get(field.get('source_id')) if isinstance(field.get('source_id'), str) else None
            source_kind = source.get('source_kind') if isinstance(source, dict) else None
            bound_field = {**field, 'source_kind': source_kind}
            if not isinstance(source, dict) or source.get('source_sha256') != field.get('source_sha256'):
                issues.append('Field source snapshot is not registered: ' + ident)
            else:
                review = source.get('review')
                status = review.get('status') if isinstance(review, dict) else None
                allowed = {'CURRENT_FOR_REVIEW'}
                if role == 'approved' or (balance['kind'] == 'record_match' and role == 'reference'
                                           and source_kind == 'APPROVED_RECORD'):
                    allowed.add('HISTORICAL_BASIS')
                if status not in allowed:
                    issues.append('Source currentness is not resolved for this amount role: ' + ident)
                if (source.get('status') != 'READY' or source.get('subject_id') != balance['subject_id']
                        or source_kind not in SOURCE_KINDS
                        or not isinstance(review, dict)
                        or not all(_known_text(review.get(name)) for name in ('reviewer', 'basis'))):
                    issues.append('Source readiness, subject, kind or review provenance is unresolved: ' + ident)
            tokens, issue = _evidence_tokens(field.get('evidence'), bound_field)
            if issue:
                issues.append(ident + ': ' + issue)
            if seen.intersection(tokens):
                issues.append('Underlying amount observations are reused; fields are not independent: ' + ident)
            seen.update(tokens)
            value, issue = _read_amount(bound_field, balance)
            if issue:
                issues.append(ident + ': ' + issue)
            item['value'] = None if value is None else str(value)
            amounts.append(value)
        if balance['kind'] == 'record_match':
            reference = fields.get(balance['terms'][0]['field_id'])
            total = fields.get(balance['total_field_id'])
            reference = reference if isinstance(reference, dict) else {}
            total = total if isinstance(total, dict) else {}
            reference_source = sources.get(reference.get('source_id')) if isinstance(reference.get('source_id'), str) else None
            total_source = sources.get(total.get('source_id')) if isinstance(total.get('source_id'), str) else None
            reference_source = reference_source if isinstance(reference_source, dict) else {}
            total_source = total_source if isinstance(total_source, dict) else {}
            if total_source.get('source_kind') != 'PLAN':
                issues.append('A record match must identify its compared total as a plan amount.')
            if reference_source.get('source_kind') not in SOURCE_KINDS - {'PLAN'}:
                issues.append('A record match needs a separately classified reference record.')
            if reference.get('source_sha256') == total.get('source_sha256'):
                issues.append('A plan and reference record cannot be aliases of the same source snapshot.')
        if issues:
            finding['reason'] = '; '.join(dict.fromkeys(issues))
        else:
            with localcontext() as context:
                context.prec = 60
                expected = sum(((-value if term['role'] in {'deletion', 'exclusion'} else value)
                                for term, value in zip(balance['terms'], amounts[:-1])), Decimal(0))
                difference = abs(expected - amounts[-1])
                passed = expected >= 0 and difference <= decimal_value(balance['tolerance'])
            finding.update(mechanical_status='PASS' if passed else 'FAIL', execution_status='EXECUTED',
                           expected=str(expected), difference=str(difference),
                           reason=('Declared printed balance produces a negative total.' if expected < 0 else
                                   'Compared the actual plan amount with the separately identified record amount using the explicit inclusive tolerance.'
                                   if balance['kind'] == 'record_match' else
                                   'Compared the declared printed balance with its actual total using the explicit inclusive tolerance.'))
        findings.append(finding)
    return findings
