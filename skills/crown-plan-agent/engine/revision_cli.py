"""Offline comparison of two original plans under one shared review basis."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
from urllib.parse import quote

from artifact_publication import publish_artifacts
from clause_schema import (_bounded_data as validate_bounded_json_tree,
                           _invalid_constant, _unique_object)
from regulatory_catalog import validate_candidate_catalog
from requirements import application_context
from review_pipeline import review_inventory
from revision_comparison import build_comparison
from revision_markdown import render_comparison_markdown
from revision_sources import inspect_original_pdf, read_bounded_file
from table_a2_lookup import disposition_code
from table_a2_rows import extract_a2_rows

ENGINE_VERSION = '0.6.0'
MAX_JSON_INPUT = 2 * 1024 * 1024
MAX_PDF_INPUT = 100_000_000
MAX_ARTIFACT = 20 * 1024 * 1024


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def _parse_json_snapshot(raw: bytes) -> object:
    """Apply the established strict JSON checks to the retained input bytes."""
    if len(raw) > MAX_JSON_INPUT:
        raise ValueError('JSON file exceeds 2 MiB')
    try:
        result = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_object,
                            parse_constant=_invalid_constant)
    except (UnicodeError, RecursionError, ValueError) as exc:
        raise ValueError('Invalid bounded JSON: ' + str(exc)) from exc
    validate_bounded_json_tree(result)
    return result


def _engine_sha256() -> str:
    root = Path(__file__).resolve().parent
    files = sorted([*root.glob('*.py'), *root.glob('*.json')], key=lambda path: path.name)
    lines = [path.name + '\t' + sha256(path.read_bytes()).hexdigest() + '\n' for path in files]
    return sha256(''.join(lines).encode()).hexdigest()


def preflight_revision_paths(baseline_pdf: Path, revised_pdf: Path, output: Path,
                             json_output: Path, annotated_pdf: Path | None = None) -> None:
    """Require fresh private destinations before reading the source evidence."""
    if output.suffix.lower() != '.md' or json_output.suffix.lower() != '.json':
        raise ValueError('Comparison outputs must be Markdown (.md) and JSON (.json)')
    if annotated_pdf is not None and annotated_pdf.suffix.lower() != '.pdf':
        raise ValueError('The optional standard review copy must be a PDF (.pdf)')
    outputs = [output, json_output] + ([annotated_pdf] if annotated_pdf is not None else [])
    resolved = [path.resolve() for path in outputs]
    if len(set(resolved)) != len(resolved):
        raise ValueError('Comparison output paths must be distinct')
    sources = {baseline_pdf.resolve(), revised_pdf.resolve()}
    skill_root = Path(__file__).resolve().parents[1]
    protected = [skill_root]
    for parent in skill_root.parents:
        if (parent / '.git').exists():
            protected.append(parent)
            break
    for path, destination in zip(outputs, resolved):
        if destination in sources:
            raise ValueError('Comparison outputs must not overwrite either original')
        if any(destination.is_relative_to(root) for root in protected):
            raise ValueError('Comparison outputs must stay outside the installed skill and code repository')
        if path.exists() or path.is_symlink():
            raise FileExistsError('Comparison output already exists')
        if not destination.parent.is_dir():
            raise ValueError('Comparison output parent directory must already exist')


def _normal_scenario(scenario: dict) -> dict:
    if not isinstance(scenario, dict):
        raise TypeError('Scenario must be a JSON object')
    # The established CLI retains the supplied disposition and normalizes the
    # legacy activity alias only after checking that both agree.
    disposition = scenario.get('disposition', scenario.get('activity'))
    code = disposition_code(disposition)
    if ('disposition' in scenario and 'activity' in scenario
            and scenario['disposition'] != scenario['activity']
            and (code is None or code != disposition_code(scenario['activity']))):
        raise ValueError('Conflicting scenario disposition and legacy activity')
    return {**scenario, 'activity': code} if code is not None else dict(scenario)


def _json_bytes(value: dict) -> bytes:
    """Stop serialization at the budget instead of joining an oversized record."""
    chunks, used = [], 0
    encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
    for text in encoder.iterencode(value):
        chunk = text.encode('utf-8')
        used += len(chunk)
        if used + 1 > MAX_ARTIFACT:
            raise ValueError('Comparison JSON exceeds the 20 MiB artifact limit')
        chunks.append(chunk)
    return b''.join(chunks) + b'\n'


def run_comparison(baseline_pdf: Path, revised_pdf: Path, output: Path,
                   json_output: Path, scenario: dict, catalogue_path: Path, *,
                   a2_pdf: Path | None = None, annotated_pdf: Path | None = None,
                   _input_guards: tuple = ()) -> Path:
    """Prepare a complete private packet; never infer correction or approval."""
    baseline_pdf, revised_pdf, output, json_output, catalogue_path = map(
        Path, (baseline_pdf, revised_pdf, output, json_output, catalogue_path))
    a2_pdf = Path(a2_pdf) if a2_pdf is not None else None
    annotated_pdf = Path(annotated_pdf) if annotated_pdf is not None else None
    preflight_revision_paths(baseline_pdf, revised_pdf, output, json_output, annotated_pdf)
    validate_bounded_json_tree(scenario)
    scenario = _normal_scenario(scenario)
    context = application_context(scenario)
    if a2_pdf is not None and (context['scope_status'] != 'IN_SCOPE' or context['regulator'] != 'AER'):
        raise ValueError('Table A2 input requires confirmed Alberta Crown scope and regulator AER')
    # Strict structured-input validation precedes source PDF inspection. The
    # parsed context, not just its filename, participates in the common basis.
    _canonical(scenario)
    catalogue_bytes, catalogue_hash = read_bounded_file(catalogue_path, MAX_JSON_INPUT)
    catalogue = validate_candidate_catalog(_parse_json_snapshot(catalogue_bytes))
    guards = [(catalogue_path, catalogue_hash, MAX_JSON_INPUT), *_input_guards]
    references = [{'name': 'catalogue_input', 'sha256': catalogue_hash}]
    rows = None
    if a2_pdf is not None:
        reference_bytes, reference_hash = read_bounded_file(a2_pdf, MAX_PDF_INPUT)
        rows = extract_a2_rows(reference_bytes)
        guards.append((a2_pdf, reference_hash, MAX_PDF_INPUT))
        references.append({'name': 'table_a2', 'sha256': reference_hash})
    basis = {'engine_version': ENGINE_VERSION, 'engine_sha256': _engine_sha256(),
             'scenario_sha256': sha256(_canonical(scenario)).hexdigest(),
             'catalogue_sha256': sha256(_canonical(catalogue)).hexdigest(),
             'references': references}
    basis['basis_sha256'] = sha256(_canonical(basis)).hexdigest()
    inventories, reports = [], []
    for source in (baseline_pdf, revised_pdf):
        inventory = inspect_original_pdf(source)
        report = review_inventory(inventory, scenario, catalogue, table_a2_rows=rows)
        report['pages'] = inventory['pages']
        inventories.append(inventory)
        reports.append(report)
        guards.append((source, inventory['source_sha256'], MAX_PDF_INPUT))
    comparison = build_comparison(inventories[0], reports[0], inventories[1], reports[1], basis=basis)
    pdf_bytes = None
    if annotated_pdf is not None:
        from pdf_markup import build_annotated_pdf
        pdf_bytes, manifest = build_annotated_pdf(revised_pdf, reports[1], inventories[1])
        comparison['revised_review_copy'] = {
            'kind': 'STANDARD_REVISED_REVIEW_NOT_CHANGE_OVERLAY',
            'filename': annotated_pdf.name, 'source_sha256': manifest['source_sha256'],
            'sha256': sha256(pdf_bytes).hexdigest(),
            'finding_note_ids': {note['finding_id']: note['note_id'] for note in manifest['notes']
                                 if note['kind'] == 'REQUIREMENT'},
            'located_count': manifest['located_count'], 'unlocated_count': manifest['unlocated_count']}
    markdown = render_comparison_markdown(comparison)
    if annotated_pdf is not None:
        from report_markdown import _cell
        relative = os.path.relpath(annotated_pdf.resolve(), output.resolve().parent)
        destination = './' + quote(relative.replace(os.sep, '/'), safe='/')
        markdown += ('\n## Standard revised-plan review copy\n\n'
                     f'[{_cell(annotated_pdf.name)}]({destination})\n\n'
                     'This is the standard review of the revised original. The text-change list stays '
                     'in this comparison report; the PDF is not a visual change overlay. Keep it private.\n')
    markdown_bytes = markdown.encode('utf-8')
    if len(markdown_bytes) > MAX_ARTIFACT:
        raise ValueError('Comparison Markdown exceeds the 20 MiB artifact limit')
    record_bytes = _json_bytes(comparison)
    for source, expected, limit in guards:
        if read_bounded_file(source, limit)[1] != expected:
            raise ValueError('A source or shared review input changed before comparison publication')
    artifacts = {output: markdown_bytes, json_output: record_bytes}
    if annotated_pdf is not None:
        artifacts[annotated_pdf] = pdf_bytes
    publish_artifacts(artifacts)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Offline Crown plan revision evidence comparison')
    parser.add_argument('baseline_pdf', type=Path, help='Baseline original PDF')
    parser.add_argument('revised_pdf', type=Path, help='Revised original PDF')
    parser.add_argument('--scenario', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New comparison Markdown')
    parser.add_argument('--json-output', type=Path, required=True, help='New structured comparison record')
    parser.add_argument('--catalogue', type=Path, default=Path(__file__).with_name('candidate_requirements.json'))
    parser.add_argument('--table-a2-pdf', type=Path, help='Optional same locally supplied A2 source for both reviews')
    parser.add_argument('--annotated-pdf', type=Path, help='Optional standard revised-plan review copy')
    parser.add_argument('--offline', action='store_true', help='Offline mode (always enforced)')
    args = parser.parse_args(argv)
    try:
        preflight_revision_paths(args.baseline_pdf, args.revised_pdf, args.output,
                                 args.json_output, args.annotated_pdf)
        scenario_bytes, digest = read_bounded_file(args.scenario, MAX_JSON_INPUT)
        scenario = _parse_json_snapshot(scenario_bytes)
        run_comparison(args.baseline_pdf, args.revised_pdf, args.output, args.json_output,
                       scenario, args.catalogue, a2_pdf=args.table_a2_pdf,
                       annotated_pdf=args.annotated_pdf,
                       _input_guards=((args.scenario, digest, MAX_JSON_INPUT),))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    print('Review-only revision comparison created:', args.output)
    print('Structured comparison record:', args.json_output)
    if args.annotated_pdf is not None:
        print('Standard revised-plan review copy:', args.annotated_pdf)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
