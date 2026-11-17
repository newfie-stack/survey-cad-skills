"""Link source-bound review observations without making compliance decisions."""
from __future__ import annotations

from hashlib import sha256
import json
from math import isfinite
import re

from pdf_markup_plan import FRAME, build_markup_plan

STATES = ('SAME_OBSERVED_TEXT', 'OBSERVED_TEXT_CHANGED', 'NEWLY_OBSERVED_TEXT',
          'PREVIOUS_OBSERVATION_NOT_FOUND', 'AMBIGUOUS', 'NOT_COMPARED')
MAX_TEXT = 8192
MAX_ITEMS = 200
MAX_ARTIFACT_BYTES = 20 * 1024 * 1024
_SHA256 = re.compile(r'[0-9a-f]{64}')
_BASIS_KEYS = {'engine_version', 'engine_sha256', 'scenario_sha256',
               'catalogue_sha256', 'references', 'basis_sha256'}
# Definition fields only: observations, counts and source locations vary by PDF.
_DEFINITION_KEYS = ('authority', 'requirement_summary', 'publication_title',
                    'version_date', 'source_version', 'section', 'source_page',
                    'source_url', 'check_method', 'evidence_key', 'expected_value',
                    'severity', 'review_instruction', 'correction', 'regulator',
                    'land_class', 'review_scope', 'scope_status', 'activity', 'stage',
                    'plan_type', 'applicability', 'applicability_status')
_LIMITATIONS = [
    'All findings require independent review; no observation is automatically closed, fixed, approved or compliant.',
    'Only supported extracted text and candidate observations are compared; visual/manual checks, raster content, linework, symbols, signatures and geometry are not compared.',
    'Whitespace alone is normalized. Span fragmentation can create extracted-text inventory differences that require review, rather than semantic edits.',
    'Lost text matches or a lost text layer do not establish removal, correction or acceptance.',
    'Source hashes bind bytes, not current regulatory authority, applicability or professional acceptance; verify these independently.',
    'Location changes describe PDF text locations, page size and orientation; they do not prove that a surveyed feature moved.',
]


def _text(value: object, label: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or len(value) > MAX_TEXT:
        raise ValueError(label + ' must be bounded text')
    return value


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError(label + ' requires a canonical SHA-256')
    return value


def _copy_bounded(value: object, label: str) -> object:
    """Validate incrementally before copying/encoding any caller-owned structure."""
    nodes = 0
    characters = 0

    def copy(item: object, depth: int) -> object:
        nonlocal nodes, characters
        nodes += 1
        if depth > 12 or nodes > 10000:
            raise ValueError(label + ' structure exceeds its limit')
        if isinstance(item, str):
            _text(item, label)
            characters += len(item)
            if characters > 512 * 1024:
                raise ValueError(label + ' text exceeds its aggregate limit')
            return str(item)
        if item is None or type(item) is bool or type(item) is int:
            if type(item) is int and item.bit_length() > 1024:
                raise ValueError(label + ' integer exceeds its limit')
            return item
        if type(item) is float:
            if not isfinite(item):
                raise ValueError(label + ' must contain finite JSON numbers')
            return item
        if isinstance(item, list):
            if len(item) > MAX_ITEMS:
                raise ValueError(label + ' item limit exceeded')
            return [copy(child, depth + 1) for child in item]
        if isinstance(item, dict):
            if len(item) > MAX_ITEMS:
                raise ValueError(label + ' item limit exceeded')
            result = {}
            for key, child in item.items():
                if not isinstance(key, str):
                    raise ValueError(label + ' requires string JSON keys')
                result[copy(key, depth + 1)] = copy(child, depth + 1)
            return result
        raise ValueError(label + ' must contain JSON values')

    return copy(value, 0)


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def _basis(value: dict) -> dict:
    if not isinstance(value, dict) or set(value) != _BASIS_KEYS:
        raise ValueError('Comparison basis requires its exact schema')
    result = _copy_bounded(value, 'Comparison basis')
    if result['engine_version'] != '0.6.0':
        raise ValueError('Comparison basis requires engine version 0.6.0')
    for key in ('engine_sha256', 'scenario_sha256', 'catalogue_sha256', 'basis_sha256'):
        _digest(result[key], key)
    references = result['references']
    if not isinstance(references, list):
        raise ValueError('Basis references must be a list')
    names = set()
    for record in references:
        if not isinstance(record, dict) or set(record) != {'name', 'sha256'}:
            raise ValueError('Reference entries require name and sha256')
        name = _text(record['name'], 'Reference name')
        if not name.strip() or name in names:
            raise ValueError('Reference names must be unique and nonempty')
        names.add(name)
        _digest(record['sha256'], 'Reference sha256')
    content = {key: val for key, val in result.items() if key != 'basis_sha256'}
    if sha256(_canonical(content)).hexdigest() != result['basis_sha256']:
        raise ValueError('Comparison basis SHA-256 does not match its canonical content')
    return result


def _prepare(inventory: dict, report: dict, basis: dict) -> tuple[dict, dict, dict]:
    if not isinstance(inventory, dict) or not isinstance(report, dict):
        raise TypeError('Source inventory and review report must be objects')
    source_hash = _digest(inventory.get('source_sha256'), 'Source inventory')
    if _digest(report.get('source_sha256'), 'Source report') != source_hash:
        raise ValueError('Report and inventory source hashes differ')
    filename = _text(inventory.get('source_filename'), 'Source filename')
    if not filename.strip() or report.get('source_filename') != filename:
        raise ValueError('Report and inventory source filenames differ')
    pages = inventory.get('pages')
    if (type(pages) is not int or not 1 <= pages <= 100
            or type(report.get('pages')) is not int or report['pages'] != pages):
        raise ValueError('Report and inventory source page counts differ or exceed limits')
    scenario = report.get('scenario')
    if not isinstance(scenario, dict):
        raise ValueError('Review scenario must be an object')
    scenario = _copy_bounded(scenario, 'Review scenario')
    if sha256(_canonical(scenario)).hexdigest() != basis['scenario_sha256']:
        raise ValueError('Report scenario differs from the shared basis')
    entries = report.get('requirements')
    summary = report.get('summary')
    if (not isinstance(entries, list) or len(entries) > MAX_ITEMS
            or not isinstance(summary, dict) or type(summary.get('total')) is not int
            or summary['total'] != len(entries)):
        raise ValueError('Review finding count is inconsistent or exceeds its limit')
    by_id = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError('Review findings must be objects')
        identifier = _text(entry.get('requirement_id'), 'Requirement ID')
        if not identifier.strip() or len(identifier) > 256 or identifier in by_id:
            raise ValueError('Requirement IDs must be unique and bounded')
        by_id[identifier] = entry
        # Bound values before note planning performs any text operations.
        for key in ('observation', 'evidence_status', 'source_status'):
            _text(entry.get(key), key, optional=True)
        evidence = entry.get('input_evidence')
        if evidence is not None:
            if not isinstance(evidence, dict):
                raise ValueError('Input evidence must be an object')
            _text(evidence.get('source_text'), 'Raw source text', optional=True)
            if evidence.get('source_filename') not in (None, filename):
                raise ValueError('Finding source filename differs from bound inventory')
        for key in ('review_instruction', 'correction'):
            _text(entry.get(key), key, optional=True)
        _copy_bounded(_definition(entry), 'Finding definition')
    review_summary = report.get('review_summary', {})
    if not isinstance(review_summary, dict):
        raise ValueError('Review summary must be an object')
    review_summary = _copy_bounded(review_summary, 'Review summary')
    plan = build_markup_plan(report, inventory, source_sha256=source_hash)
    notes = {note['finding_id']: note for note in plan['notes'] if note['kind'] == 'REQUIREMENT'}
    return by_id, notes, review_summary


def _definition(entry: dict) -> dict:
    return {key: entry[key] for key in _DEFINITION_KEYS if key in entry}


def _page_frames(inventory: dict) -> tuple[dict, str | None]:
    """Validate the bounded source register without inferring omitted PDF facts.

    Invalid registers are unavailable frame evidence, not reasons to discard a
    separately validated raw text anchor. Never retain unvalidated values.
    """
    frames = inventory.get('page_frames')
    if frames is None:
        return {}, 'SOURCE_PAGE_FRAMES_NOT_RECORDED'
    if not isinstance(frames, list) or len(frames) != inventory['pages']:
        return {}, 'INVALID_SOURCE_PAGE_FRAMES'
    result = {}
    keys = {'page', 'rotation', 'mediabox_points', 'cropbox_points', 'display_rect_points'}
    for frame in frames:
        if not isinstance(frame, dict) or set(frame) != keys:
            return {}, 'INVALID_SOURCE_PAGE_FRAMES'
        page, rotation = frame['page'], frame['rotation']
        if (type(page) is not int or not 1 <= page <= inventory['pages'] or page in result
                or type(rotation) is not int or rotation not in (0, 90, 180, 270)):
            return {}, 'INVALID_SOURCE_PAGE_FRAMES'
        record = {'page': page, 'rotation': rotation}
        for key in ('mediabox_points', 'cropbox_points', 'display_rect_points'):
            box = frame[key]
            try:
                valid = (isinstance(box, list) and len(box) == 4
                         and all(type(value) in (int, float) and isfinite(value) for value in box)
                         and box[0] < box[2] and box[1] < box[3])
            except OverflowError:
                valid = False
            if not valid:
                return {}, 'INVALID_SOURCE_PAGE_FRAMES'
            record[key] = list(box)
        result[page] = record
    return result, None


def _location_changed(left: dict, right: dict) -> bool | None:
    if left['anchor'] is None or right['anchor'] is None:
        return None
    # Compare known independent facts. Missing frame/orientation metadata is
    # never manufactured from the extractor's derotated dimensions.
    for key in ('anchor', 'page_size_points', 'text_angle_degrees', 'page_frame'):
        if left.get(key) is not None and right.get(key) is not None and left[key] != right[key]:
            return True
    if all(side.get(key) is not None for side in (left, right)
           for key in ('page_frame', 'text_angle_degrees')):
        return False
    return None


def _side(entry: dict, note: dict, inventory: dict, frames: dict, frame_reason: str | None) -> dict:
    evidence = entry.get('input_evidence') or {}
    count = entry.get('candidate_count')
    if count is not None and (type(count) is not int or not 0 <= count <= 200000):
        raise ValueError('Candidate count must be a bounded nonnegative integer or null')
    result = {key: entry.get(key) for key in ('observation', 'evidence_status', 'source_status')}
    result.update(source_text=evidence.get('source_text', entry.get('observation')), candidate_count=count,
                  anchor=note['anchor'], location_reason=note['location_reason'],
                  page_frame=None, frame_status='UNKNOWN',
                  frame_reason=frame_reason or 'NO_UNIQUE_SOURCE_ANCHOR')
    if note['anchor'] is not None:
        anchor = note['anchor']
        # build_markup_plan has already established exactly one raw source span.
        span = next(span for span in inventory['spans']
                    if type(span.get('page')) is int and span['page'] == anchor['page']
                    and span.get('text') == result['source_text']
                    and isinstance(span.get('bbox_points'), (list, tuple))
                    and all(type(v) in (int, float) for v in span['bbox_points'])
                    and tuple(span['bbox_points']) == tuple(anchor['bbox_points']))
        if (inventory.get('coordinate_frame', FRAME) != FRAME
                or span.get('coordinate_frame', FRAME) != FRAME):
            result.update(anchor=None, location_reason='UNKNOWN_COORDINATE_FRAME')
            return result
        angle = span.get('text_angle_degrees')
        try:
            valid_angle = angle is None or (type(angle) in (int, float) and isfinite(angle))
        except OverflowError:
            valid_angle = False
        if not valid_angle:
            result.update(anchor=None, location_reason='INVALID_SOURCE_ORIENTATION')
            return result
        result['page_size_points'] = list(span['page_size_points'])
        result['text_angle_degrees'] = angle
        frame = frames.get(anchor['page'])
        if frame is not None:
            result.update(page_frame=_copy_bounded(frame, 'Source page frame'),
                          frame_status='VALID', frame_reason=None)
    return result


def _ambiguous(side: dict) -> bool:
    count = side['candidate_count']
    status = side['evidence_status']
    return ((count is not None and count > 1)
            or (status == 'OBSERVED_CANDIDATE' and side['anchor'] is None)
            or (status == 'UNKNOWN' and bool(side['observation'])))


def _state(left: dict, right: dict, entry: dict) -> str:
    if _ambiguous(left) or _ambiguous(right):
        return 'AMBIGUOUS'
    if (entry.get('check_method') == 'visual'
            or 'VISUAL_CHECK_REQUIRED' in (left['evidence_status'], right['evidence_status'])):
        return 'NOT_COMPARED'
    before, after = left['anchor'] is not None, right['anchor'] is not None
    if before and after:
        return ('SAME_OBSERVED_TEXT' if ' '.join(left['source_text'].split())
                == ' '.join(right['source_text'].split()) else 'OBSERVED_TEXT_CHANGED')
    if after:
        return 'NEWLY_OBSERVED_TEXT'
    if before:
        return 'PREVIOUS_OBSERVATION_NOT_FOUND'
    return 'NOT_COMPARED'


def _check_artifact_size(value: dict) -> None:
    size = 0
    encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=True,
                               separators=(',', ':'), allow_nan=False)
    for chunk in encoder.iterencode(value):
        size += len(chunk.encode('utf-8'))
        if size > MAX_ARTIFACT_BYTES:
            raise ValueError('Comparison JSON exceeds the 20 MiB artifact limit')


def build_comparison(baseline_inventory: dict, baseline_report: dict,
                     revised_inventory: dict, revised_report: dict, *, basis: dict) -> dict:
    """Compare regenerated reviews under one exact basis and independent PDF hashes.

    The caller must supply immutable inventories regenerated from the actual
    originals. This pure model validates bindings and locations; hashes do not
    authenticate sources or establish regulatory acceptance.
    """
    from revision_text import compare_text_inventories

    shared = _basis(basis)
    # Validate literal span bounds before note planning indexes raw source text.
    changes = compare_text_inventories(baseline_inventory, revised_inventory)
    before, before_notes, before_summary = _prepare(baseline_inventory, baseline_report, shared)
    after, after_notes, after_summary = _prepare(revised_inventory, revised_report, shared)
    if set(before) != set(after):
        raise ValueError('Requirement definitions differ between reviews')
    before_frames, before_frame_reason = _page_frames(baseline_inventory)
    after_frames, after_frame_reason = _page_frames(revised_inventory)
    rows, counts = [], dict.fromkeys(STATES, 0)
    for identifier in sorted(before):
        left_entry, right_entry = before[identifier], after[identifier]
        if (_canonical(_definition(left_entry)) != _canonical(_definition(right_entry))
                or before_notes[identifier]['citation'] != after_notes[identifier]['citation']):
            raise ValueError('Requirement definition or citation differs between reviews')
        left = _side(left_entry, before_notes[identifier], baseline_inventory,
                     before_frames, before_frame_reason)
        right = _side(right_entry, after_notes[identifier], revised_inventory,
                      after_frames, after_frame_reason)
        status = _state(left, right, left_entry)
        location = _location_changed(left, right)
        correction = left_entry.get('correction') or 'Independently inspect the drawing evidence.'
        instruction = left_entry.get('review_instruction') or correction
        rows.append({'requirement_id': identifier,
                     'requirement_summary': left_entry.get('requirement_summary'),
                     'review_instruction': instruction, 'correction': correction,
                     'comparison_status': status, 'baseline': left, 'revised': right,
                     'location_changed': location, 'citation': dict(before_notes[identifier]['citation'])})
        counts[status] += 1
    result = {'schema_version': 1, 'comparison_type': 'CROWN_PLAN_REVISION_TEXT_REVIEW',
              'overall_status': 'REVIEW_REQUIRED',
              'assessment_type': 'REVISION_EVIDENCE_COMPARISON_NOT_COMPLIANCE',
              'basis': shared,
              'review_context': _copy_bounded(baseline_report['scenario'], 'Review context'),
              'requirements': rows, 'text_changes': changes,
              'identical_source_bytes': baseline_inventory['source_sha256'] == revised_inventory['source_sha256'],
              'summary': {'finding_counts': counts, 'changed_text_groups': len(changes)},
              'baseline_review_summary': before_summary, 'revised_review_summary': after_summary,
              'limitations': list(_LIMITATIONS)}
    for label, inventory in (('baseline', baseline_inventory), ('revised', revised_inventory)):
        result[label] = {key: inventory[key] for key in ('source_filename', 'source_sha256', 'pages')}
    _check_artifact_size(result)
    return result
