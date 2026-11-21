"""Read original, subject-bound PDF/JSON fields without inventing expectations.

Review/currentness/subject declarations are supplied evidence gates. This reader
does not independently establish legal identity, current authority or source
authenticity. It performs no OCR, semantic comparison or external access.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import re

from clause_schema import _bounded_data, _invalid_constant, _unique_object
from finished_plan_review import _contains, _intersects, _region_view
from finished_plan_spec import _fields, _text
from native_text_reading import reading_lines
from pdf_inspector import extract_pdf
from runtime_security import load_pdf_runtime

MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_PDF_BYTES = 100_000_000
MAX_TOTAL_BYTES = 200_000_000
MAX_VALUE_CHARS = 4096
MAX_EVIDENCE_SPANS = 32
ID = re.compile(r'[A-Za-z][A-Za-z0-9_.-]{0,63}\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')
SOURCE_KINDS = frozenset({'PLAN', 'APPLICATION_FORM', 'CLIENT_REGISTRY',
                          'JOB_INSTRUCTION', 'APPROVED_RECORD', 'OTHER_RECORD'})
ROLES = frozenset({'applicant', 'operator', 'landowner', 'surveyor',
                   'disposition_id', 'legal_description', 'area', 'length'})
REVIEW_STATUSES = frozenset({'CURRENT_FOR_REVIEW', 'HISTORICAL_BASIS', 'UNCONFIRMED'})
_ASCII_LOWER = str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')
_SOURCE_LABELS = {
    alias: (identity, role)
    for identity, role, aliases in (
        ('applicant', 'applicant', ('applicant', 'applicant name', 'applicant legal name',
                                    'legal name', 'registered legal name')),
        ('operator', 'operator', ('operator', 'operator name')),
        ('landowner', 'landowner', ('landowner', 'landowner name')),
        ('surveyor', 'surveyor', ('surveyor', 'surveyor name', 'survey firm')),
        ('disposition', 'disposition_id', ('disposition', 'disposition id', 'disposition number',
                                          'disposition no', 'disposition no.')),
        ('legal_description', 'legal_description', ('legal description', 'land description', 'legal')),
        ('area_total', 'area', ('area', 'total area', 'area required', 'activity area', 'activity total', 'entire activity area')),
        ('area_added', 'area', ('added area', 'area added', 'addition area', 'additional area', 'added')),
        ('area_deleted', 'area', ('deleted area', 'area deleted', 'deleted')),
        ('area_amended', 'area', ('amended area', 'area amended', 'amended')),
        ('area_excluded', 'area', ('excluded area', 'area excluded', 'exclusion area', 'excluded')),
        ('area_retained', 'area', ('retained area', 'area retained')),
        ('area_existing', 'area', ('existing area', 'area existing')),
        ('area_crown', 'area', ('crown area', 'crown land area')),
        ('area_private', 'area', ('private area', 'private land area')),
        ('area_gross', 'area', ('gross area', 'gross activity area')),
        ('area_approved', 'area', ('approved area', 'approved activity area', 'approved')),
        ('area_net', 'area', ('net area', 'net activity area')),
        ('length_total', 'length', ('length', 'total length', 'length required', 'activity length')),
        ('length_added', 'length', ('added length', 'length added', 'additional length')),
        ('length_excluded', 'length', ('excluded length', 'length excluded')),
        ('length_retained', 'length', ('retained length', 'length retained')),
        ('length_existing', 'length', ('existing length', 'length existing')),
    ) for alias in aliases
}
_SOURCE_LABEL = re.compile(r'([A-Za-z][A-Za-z .-]{0,63})\s*:\s*([^\r\n]+)\Z')
_QUANTITY = re.compile(
    r'(0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+|'
    r'[1-9][0-9]{0,2}(?: [0-9]{3})+)(\.[0-9]{1,12})? *'
    r'(ha|m2|m²|m\^2|m)\.?\Z', re.IGNORECASE | re.ASCII)
_UNIT_ROLES = {'ha': 'area', 'hectare': 'area', 'hectares': 'area', 'm2': 'area',
               'm²': 'area', 'm^2': 'area', 'square metres': 'area', 'square meters': 'area',
               'm': 'length', 'metre': 'length', 'metres': 'length', 'meter': 'length', 'meters': 'length'}


def _identifier(value, name):
    if not isinstance(value, str) or ID.fullmatch(value) is None:
        raise ValueError(name + ' must be a bounded ASCII identifier')


def _subject(value, name):
    if value is not None:
        _text(value, name, 200)


def _region(region):
    _fields(region, {'page', 'bbox_points', 'role', 'label'},
            {'page', 'bbox_points', 'role'}, 'record field region')
    if type(region['page']) is not int or region['page'] < 1:
        raise ValueError('Record field page must be a positive one-based integer')
    box = region['bbox_points']
    if not isinstance(box, list) or len(box) != 4:
        raise ValueError('Record field bbox_points requires four coordinates')
    for value in box:
        try:
            valid = type(value) in (int, float) and isfinite(value) and 0 <= value <= 1_000_000
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError('Record field coordinates must be bounded finite numbers')
    if box[0] >= box[2] or box[1] >= box[3]:
        raise ValueError('Record field region must have positive width and height')
    _text(region['role'], 'record region role', 200)
    if 'label' in region:
        _text(region['label'], 'record region label', 200)


def _selector(selector, fmt):
    key = 'region' if fmt == 'PDF' else 'pointer'
    _fields(selector, {key}, {key}, 'record field selector')
    if fmt == 'PDF':
        _region(selector[key])
    else:
        pointer = selector[key]
        _text(pointer, 'JSON pointer', 1000)
        if not pointer.startswith('/') or re.search(r'~(?![01])', pointer):
            raise ValueError('JSON selector requires a bounded absolute RFC6901 pointer')
        if len(pointer.split('/')) > 101:
            raise ValueError('JSON pointer nesting exceeds the limit')


def validate_record_spec(spec: dict) -> dict:
    """Validate the exact bounded base contract, returning an independent copy."""
    _bounded_data(spec)
    keys = {'schema_version', 'prepared_by', 'subject_id', 'sources', 'fields'}
    _fields(spec, keys, keys, 'record specification')
    if type(spec['schema_version']) is not int or spec['schema_version'] != 1:
        raise ValueError('Unsupported record schema_version')
    _text(spec['prepared_by'], 'record prepared_by', 200)
    _text(spec['subject_id'], 'record subject_id', 200)
    sources = spec['sources']
    if not isinstance(sources, dict) or not 1 <= len(sources) <= 10 or 'plan' not in sources:
        raise ValueError('Record sources require plan and at most ten source IDs')
    source_keys = {'source_kind', 'format', 'source_sha256', 'subject_id', 'review'}
    for ident, source in sources.items():
        _identifier(ident, 'source ID')
        _fields(source, source_keys, source_keys, 'record source')
        kind, fmt, digest = source['source_kind'], source['format'], source['source_sha256']
        if not isinstance(kind, str) or kind not in SOURCE_KINDS:
            raise ValueError('Unsupported source_kind')
        if (not isinstance(fmt, str) or fmt not in ('PDF', 'JSON')
                or (fmt == 'JSON' and kind != 'JOB_INSTRUCTION')
                or (ident == 'plan' and (kind != 'PLAN' or fmt != 'PDF'))
                or (ident != 'plan' and kind == 'PLAN')):
            raise ValueError('Source format/kind must preserve the original plan and record roles')
        if digest is not None and (not isinstance(digest, str) or SHA.fullmatch(digest) is None):
            raise ValueError('Record source hash must be lowercase SHA-256 or null for a missing source')
        _subject(source['subject_id'], 'source subject_id')
        review = source['review']
        _fields(review, {'status', 'reviewer', 'basis'}, {'status', 'reviewer', 'basis'}, 'source review')
        if not isinstance(review['status'], str) or review['status'] not in REVIEW_STATUSES:
            raise ValueError('Unsupported source review status')
        _text(review['reviewer'], 'source reviewer', 200)
        _text(review['basis'], 'source review basis', 1000)
    fields = spec['fields']
    if not isinstance(fields, dict) or not 1 <= len(fields) <= 100:
        raise ValueError('Record fields require one to one hundred selections')
    field_keys = {'source_id', 'semantic_role', 'subject_id', 'measurement_scope', 'selector', 'unit_selector'}
    for ident, field in fields.items():
        _identifier(ident, 'field ID')
        _fields(field, field_keys, field_keys, 'record field')
        source_id = field['source_id']
        if not isinstance(source_id, str) or source_id not in sources:
            raise ValueError('Field refers to an unknown source ID')
        if not isinstance(field['semantic_role'], str) or field['semantic_role'] not in ROLES:
            raise ValueError('Unsupported semantic field role')
        _subject(field['subject_id'], 'field subject_id')
        _subject(field['measurement_scope'], 'field measurement_scope')
        if field['selector'] is not None:
            _selector(field['selector'], sources[source_id]['format'])
        if field['unit_selector'] is not None:
            if field['semantic_role'] not in ('area', 'length'):
                raise ValueError('Only area and length fields may have a unit_selector')
            _selector(field['unit_selector'], sources[source_id]['format'])
    return deepcopy(spec)


def _paths(plan_pdf, spec, record_paths):
    if not isinstance(record_paths, dict) or any(
            not isinstance(ident, str) or ident == 'plan' or ident not in spec['sources']
            for ident in record_paths):
        raise ValueError('Record paths may only name declared non-plan sources')
    paths = {'plan': Path(plan_pdf)}
    for ident, path in record_paths.items():
        if not isinstance(path, (str, Path)):
            raise ValueError('Each supplied record path must identify one local file')
        paths[ident] = Path(path)
    return paths


def _snapshot(path, limit):
    if path.stat().st_size > limit:
        raise ValueError('Record source exceeds its file size limit')
    with path.open('rb') as handle:
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('Record source exceeds its file size limit')
    return raw, sha256(raw).hexdigest()


def _json(raw):
    try:
        data = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_unique_object,
                          parse_constant=_invalid_constant)
        _bounded_data(data)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError('Record JSON requires bounded valid UTF-8 data') from exc
    return data


def _preflight(plan_pdf, spec, record_paths):
    paths = _paths(plan_pdf, spec, record_paths)
    sources = {}
    total = 0
    for ident, definition in spec['sources'].items():
        path = paths.get(ident)
        source = {**deepcopy(definition), 'source_id': ident,
                  'filename': path.name if path is not None else None,
                  'actual_sha256': None, 'size_bytes': None, 'status': 'MISSING_SOURCE',
                  'reason': 'The declared source was not supplied as an available local file.'}
        if path is not None and path.is_file():
            if definition['source_sha256'] is None:
                raise ValueError('A supplied source requires an explicit SHA-256 binding')
            wanted_suffix = '.pdf' if definition['format'] == 'PDF' else '.json'
            if path.suffix.lower() != wanted_suffix:
                raise ValueError('Record file suffix must match its declared format')
            limit = MAX_PDF_BYTES if definition['format'] == 'PDF' else MAX_JSON_BYTES
            # Check the aggregate before allocating each source snapshot.
            if path.stat().st_size > MAX_TOTAL_BYTES - total:
                raise ValueError('Combined record sources exceed the aggregate size limit')
            raw, digest = _snapshot(path, min(limit, MAX_TOTAL_BYTES - total))
            total += len(raw)
            if digest != definition['source_sha256']:
                raise ValueError('Record source SHA-256 does not match the supplied source')
            if definition['format'] == 'JSON':
                _json(raw)
            source.update(actual_sha256=digest, size_bytes=len(raw), status='READY', reason='Source snapshot hash verified; field reading has not executed.')
            if definition['subject_id'] != spec['subject_id']:
                source.update(status='REVIEW_REQUIRED', reason='Source subject identity is missing or differs from the reviewed subject.')
            elif definition['review']['status'] == 'UNCONFIRMED':
                source.update(status='REVIEW_REQUIRED', reason='Source currentness and review basis are unconfirmed.')
        sources[ident] = source
    return {'schema_version': 1, 'subject_id': spec['subject_id'], 'prepared_by': spec['prepared_by'],
            'sources': sources}, paths


def preflight_record_sources(plan_pdf, spec: dict, record_paths: dict[str, Path]) -> dict:
    """Verify all supplied raw snapshots/JSON before any native parsing or download."""
    prepared = validate_record_spec(spec)
    return _preflight(plan_pdf, prepared, record_paths)[0]


def _raw_label(value, label):
    if label is None:
        return value.strip()
    prefix = label.strip()
    if not value.translate(_ASCII_LOWER).startswith(prefix.translate(_ASCII_LOWER)):
        return None
    if prefix[-1].isalnum() and len(value) > len(prefix) and value[len(prefix)].isalnum():
        return None
    return value[len(prefix):].strip()


def _pointer(data, pointer):
    for token in pointer.split('/')[1:]:
        token = token.replace('~1', '/').replace('~0', '~')
        if isinstance(data, dict):
            if token not in data:
                return None
            data = data[token]
        elif isinstance(data, list):
            if re.fullmatch(r'0|[1-9][0-9]{0,9}', token) is None or int(token) >= len(data):
                return None
            data = data[int(token)]
        else:
            return None
    return data


def _evidence(source, **detail):
    return {'source_id': source['source_id'], 'source_kind': source['source_kind'],
            'source_sha256': source['actual_sha256'], **detail}


def _json_field(source, data, selector):
    value = _pointer(data, selector['pointer'])
    evidence = _evidence(source, pointer=selector['pointer'], text=value if isinstance(value, str) else None,
                         evidence_type='JSON_SCALAR' if isinstance(value, str) else 'JSON_POINTER')
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_VALUE_CHARS:
        return None, evidence, 'JSON pointer does not identify one nonempty bounded string.'
    if any(ord(char) < 32 and char not in '\n\t\r' for char in value):
        return None, evidence, 'JSON field contains unsupported text control characters.'
    return value, evidence, ''


def _native_context(path, source, regions):
    # Check the reviewed runtime before any native parse, even for bad records.
    runtime = load_pdf_runtime()
    raw, digest = _snapshot(path, MAX_PDF_BYTES)
    if digest != source['actual_sha256']:
        raise ValueError('Record source changed before native reading')
    try:
        inventory = extract_pdf(path, include_vectors=False)
        if inventory['source_sha256'] != digest:
            raise ValueError('Record source changed during native extraction')
        by_page = defaultdict(list)
        for span in inventory['spans']:
            by_page[span['page']].append(span)
        page_info = {}
        with runtime.open(stream=raw, filetype='pdf') as document:
            if document.needs_pass:
                return None, 'Encrypted PDF fields require separate authorized reading.'
            for number in {region['page'] for region in regions}:
                if number > len(document):
                    continue
                page = document[number - 1]
                bounds = page.rect * page.derotation_matrix
                images = page.get_image_info()
                if len(images) > 20000:
                    return None, 'Page image count exceeds the field-reading limit.'
                page_info[number] = ([0, 0, bounds.width, bounds.height], [list(image['bbox']) for image in images])
        return (by_page, page_info), ''
    except (ValueError, RuntimeError) as exc:
        # Hash changes remain fatal; malformed/unreadable record contents do not
        # erase the review of other sources. Do not publish native error paths.
        if _snapshot(path, MAX_PDF_BYTES)[1] != source['actual_sha256']:
            raise ValueError('Record source changed during native reading') from exc
        return None, 'Original PDF fields could not be read within the supported limits.'


def _own_unit(candidate, unit_region):
    """A numeric field may separate only its own actual, recognized unit span.

    Other field declarations must never suppress identity continuations. Even
    this narrow exception does not accept a unit: its actual selector is read
    independently afterwards and can still block the numeric field.
    """
    if (unit_region is None or unit_region['page'] != candidate['page']
            or not _contains(unit_region['bbox_points'], candidate['bbox_points'])):
        return False
    if 'label' in unit_region:
        prefix, delimiter, payload = candidate['text'].partition(':')
        if (not delimiter or unit_region['label'].strip().translate(_ASCII_LOWER)
                != (prefix+':').translate(_ASCII_LOWER)):
            return False
        return _source_unit_role(candidate['text']) is not None
    return _plain_unit_role(candidate['text']) is not None or _source_unit_role(candidate['text']) is not None


def _plain_unit_role(text):
    token = text.strip().translate(_ASCII_LOWER)
    if token.endswith('.'):
        token = token[:-1]
    return _UNIT_ROLES.get(token)


def _source_unit_role(text):
    """Recognize an actual typed unit header without discarding numeric data."""
    match = _SOURCE_LABEL.fullmatch(text.strip())
    if match is None:
        return None
    label = ' '.join(match[1].translate(_ASCII_LOWER).split())
    role = _plain_unit_role(match[2])
    if role is None:
        return None
    known = _SOURCE_LABELS.get(label)
    if known is not None:
        return role if known[1] in ('area', 'length') and known[1] == role else None
    captions = {'unit': None, 'units': None, 'area units': 'area',
                'length units': 'length', 'distance units': 'length'}
    if label not in captions or (captions[label] is not None and captions[label] != role):
        return None
    return role


def _source_field(text):
    """Recognize only complete, explicit field labels printed in this source.

    This finite vocabulary is a reading boundary, not an acceptance of legal
    identity or field meaning. Caller-selected labels/values are not consulted.
    Aliases share an identity so repeated applicant names or totals compete.
    """
    match = _SOURCE_LABEL.fullmatch(text.strip())
    if match is None:
        return None
    label = ' '.join(match[1].translate(_ASCII_LOWER).split())
    payload = match[2].strip()
    if label not in _SOURCE_LABELS or not payload or payload.startswith(':'):
        return None
    identity, role = _SOURCE_LABELS[label]
    return identity, role, payload


def _whole_quantity(text):
    """Identify one original complete quantity token; never join source spans."""
    labelled = _source_field(text)
    value = labelled[2] if labelled is not None else text.strip()
    # NBSP is a supported printed grouping separator; other compatibility
    # numerals are not converted into ASCII by this reading-boundary grammar.
    match = _QUANTITY.fullmatch(value.replace('\u00a0', ' '))
    if match is None or len(match[1].replace(',', '').replace(' ', '')) > 18:
        return None
    unit = match[3].translate(_ASCII_LOWER)
    role = 'length' if unit == 'm' else 'area'
    if labelled is not None and labelled[1] != role:
        return None
    return role


def _possible_continuation(selected, spans, unit_region, semantic_role=None, measurement_scope=None):
    lines, issues = reading_lines([selected])
    if issues or len(lines) != 1:
        return True
    a = lines[0]['reading_box']
    direction = selected['text_direction']
    height = a[3] - a[1]
    selected_label = _source_field(selected['text'])
    if semantic_role is None and _source_unit_role(selected['text']) is not None:
        # The unit selector names a complete header, not a second amount with
        # the same caption as the nearby value that it qualifies.
        selected_label = None
    scoped_quantity = (semantic_role in ('area', 'length') and bool(measurement_scope)
                       and _whole_quantity(selected['text']) == semantic_role)
    original = selected['bbox_points']
    nearby = [original[0]-height*3, original[1]-height*3,
              original[2]+height*3, original[3]+height*3]
    for candidate in spans:
        if candidate is selected or not _intersects(nearby, candidate['bbox_points']) or _own_unit(candidate, unit_region):
            continue
        dx, dy = candidate['text_direction']
        if direction[0]*dx + direction[1]*dy <= 0 or abs(direction[0]*dy-direction[1]*dx) > 1e-4:
            continue
        other, problems = reading_lines([candidate])
        if problems or len(other) != 1:
            return True
        b = other[0]['reading_box']
        h = max(height, b[3]-b[1])
        same_line_tail = abs((a[1]+a[3]-b[1]-b[3])/2) <= h*0.3 and -0.5 <= b[0]-a[2] <= h*2.5
        next_line = (-h*0.3 <= b[1]-a[3] <= h*0.7 and b[1] > a[1]+h*0.3
                     and a[0]-h <= b[0] <= a[2]+h)
        previous_line = (-h*0.3 <= a[1]-b[3] <= h*0.7 and a[1] > b[1]+h*0.3
                         and b[0]-h <= a[0] <= b[2]+h)
        candidate_label = _source_field(candidate['text'])
        if (previous_line and selected_label is not None and candidate_label is not None
                and selected_label[0] == candidate_label[0]):
            return True
        if same_line_tail or next_line:
            if selected_label is not None and candidate_label is not None:
                if selected_label[0] == candidate_label[0]:
                    return True
                # Different actual labelled fields, with native geometry, have
                # their own reading boundaries regardless of other selectors.
                continue
            if (next_line and scoped_quantity and selected_label is None
                    and candidate_label is None and _whole_quantity(candidate['text']) is not None):
                # A complete numeral+unit on a separate row is not a numeric
                # continuation. Same-line tails remain competing evidence.
                continue
            return True
    return False


def _pdf_field(source, context, selector, unit_region=None, semantic_role=None, measurement_scope=None, unit_role=None):
    region = selector['region']
    by_page, page_info = context
    evidence = _evidence(source, page=region['page'], bbox_points=deepcopy(region['bbox_points']),
                         text=None, spans=[], evidence_type='SEARCH_REGION')
    if region['page'] not in page_info:
        return None, evidence, 'Selected PDF page does not exist.'
    bounds, images = page_info[region['page']]
    if not _contains(bounds, region['bbox_points']):
        return None, evidence, 'Selected field lies outside the visible unrotated PDF page.'
    spans = by_page[region['page']]
    try:
        view = _region_view(region, spans, images)
    except ValueError:
        return None, evidence, 'Selected field exceeds the bounded native-reading limits.'
    observed = view['evidence']
    evidence.update(text=observed['text'][:MAX_VALUE_CHARS],
                    spans=deepcopy(observed['spans'][:MAX_EVIDENCE_SPANS]), evidence_type=observed['evidence_type'])
    if len(observed['spans']) > MAX_EVIDENCE_SPANS or len(observed['text']) > MAX_VALUE_CHARS:
        evidence['truncated'] = True
    for span in evidence['spans']:
        if len(span['text']) > MAX_VALUE_CHARS:
            span['text'] = span['text'][:MAX_VALUE_CHARS]
            evidence['truncated'] = True
    if view['blockers']:
        return None, evidence, '; '.join(view['blockers'])
    selected = [span for span in spans if _intersects(region['bbox_points'], span['bbox_points'])]
    if len(selected) != 1:
        return None, evidence, 'Exactly one original native span is required; wrapped or split fields need independent reading.'
    span = selected[0]
    # Keep original extracted text rather than normalized _region_view values.
    evidence['text'] = span['text'][:MAX_VALUE_CHARS]
    labelled = _source_field(span['text'])
    if semantic_role is not None and labelled is not None and labelled[1] != semantic_role:
        return None, evidence, 'The actual printed field label identifies a different semantic role.'
    if unit_role is not None:
        actual_unit_role = _plain_unit_role(span['text']) or _source_unit_role(span['text'])
        if actual_unit_role is not None and actual_unit_role != unit_role:
            return None, evidence, 'The actual printed unit/header contradicts the numeric field role.'
    if 'label' in region:
        printed_label, delimiter, payload = span['text'].partition(':')
        if (not delimiter or not payload.strip()
                or region['label'].strip().translate(_ASCII_LOWER) != (printed_label + ':').translate(_ASCII_LOWER)):
            return None, evidence, 'The supplied label must end at the actual printed colon boundary without consuming any field value.'
        if semantic_role is not None and (labelled is None or labelled[1] != semantic_role):
            return None, evidence, 'Unknown printed prefixes cannot be used to strip a reviewed identity or quantity value.'
        if semantic_role is None and _source_unit_role(span['text']) is None:
            return None, evidence, 'A unit prefix must identify an actual recognized unit header, without erasing another quantity or field.'
    if _possible_continuation(span, spans, unit_region, semantic_role, measurement_scope):
        return None, evidence, 'A possible native field continuation requires separate visual association.'
    value = _raw_label(span['text'], region.get('label'))
    if value is None or not value.strip() or len(value) > MAX_VALUE_CHARS:
        return None, evidence, 'The literal label does not identify one nonempty bounded original field value.'
    return value, evidence, ''


def _verify_sources(paths, result):
    for ident, path in paths.items():
        source = result['sources'][ident]
        digest = source['actual_sha256']
        if digest is None:
            if path.is_file():
                raise ValueError('Record source availability changed during field reading')
            continue
        if not path.is_file():
            raise ValueError('Record source disappeared during field reading')
        limit = MAX_PDF_BYTES if source['format'] == 'PDF' else MAX_JSON_BYTES
        if _snapshot(path, limit)[1] != digest:
            raise ValueError('Record source changed during field reading')


def read_record_fields(plan_pdf, spec: dict, record_paths: dict[str, Path]) -> dict:
    """Read each reviewed field from current source bytes, preserving raw strings."""
    spec = validate_record_spec(spec)
    result, paths = _preflight(plan_pdf, spec, record_paths)
    fields = {}
    grouped = defaultdict(list)
    for ident, field in spec['fields'].items():
        source = result['sources'][field['source_id']]
        reason = source['reason'] if source['status'] != 'READY' else ''
        if field['subject_id'] != spec['subject_id'] or field['subject_id'] != source['subject_id']:
            reason = 'Field/source subject identity is missing or differs from the reviewed subject.'
        if field['selector'] is None:
            reason = '; '.join(filter(None, [reason, 'Source field has not been selected/reviewed.']))
        fields[ident] = {**{key: deepcopy(field[key]) for key in
                           ('source_id', 'semantic_role', 'subject_id', 'measurement_scope')},
                         'source_sha256': source['actual_sha256'],
                         'status': 'REVIEW_REQUIRED', 'raw_value': None, 'unit_raw_value': None,
                         'evidence': _evidence(source), 'unit_evidence': None, 'reason': reason}
        if not reason:
            grouped[field['source_id']].append(ident)
    for source_id, field_ids in grouped.items():
        source = result['sources'][source_id]
        path = paths[source_id]
        if source['format'] == 'JSON':
            raw, digest = _snapshot(path, MAX_JSON_BYTES)
            if digest != source['actual_sha256']:
                raise ValueError('Record JSON source changed before reading')
            data, context, error = _json(raw), None, ''
        else:
            regions = []
            for field_id in field_ids:
                field = spec['fields'][field_id]
                regions.append(field['selector']['region'])
                if field['unit_selector'] is not None:
                    regions.append(field['unit_selector']['region'])
            context, error = _native_context(path, source, regions)
            if error:
                source.update(status='REVIEW_REQUIRED', reason=error)
                for field_id in field_ids:
                    fields[field_id]['reason'] = error
                continue
        for field_id in field_ids:
            definition, field = spec['fields'][field_id], fields[field_id]
            def reader(selector, *, is_unit=False):
                if source['format'] == 'JSON':
                    return _json_field(source, data, selector)
                own_unit = (definition['unit_selector']['region'] if not is_unit
                            and definition['semantic_role'] in ('area', 'length')
                            and definition['unit_selector'] is not None else None)
                return _pdf_field(source, context, selector, own_unit,
                                  definition['semantic_role'] if not is_unit else None,
                                  definition['measurement_scope'] if not is_unit else None,
                                  definition['semantic_role'] if is_unit else None)
            value, evidence, reason = reader(definition['selector'])
            field.update(raw_value=value, evidence=evidence, reason=reason)
            if definition['unit_selector'] is not None:
                unit, unit_evidence, unit_reason = reader(definition['unit_selector'], is_unit=True)
                field.update(unit_raw_value=unit, unit_evidence=unit_evidence)
                if unit_reason:
                    field['reason'] = '; '.join(filter(None, [field['reason'], 'Unit field: ' + unit_reason]))
            if not field['reason']:
                field['status'] = 'READY'
    _verify_sources(paths, result)
    result['fields'] = fields
    return result
