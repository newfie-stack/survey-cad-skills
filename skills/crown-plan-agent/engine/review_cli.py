"""Offline Crown Plan Agent PDF-to-review command.

Never upload source plans or generated reports. Output is review-only.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
from pathlib import Path
from urllib.parse import quote

from artifact_publication import publish_artifacts
from clause_schema import load_bounded_json
from pdf_inspector import extract_pdf
from regulatory_catalog import load_candidate_catalog
from requirements import application_context
from review_pipeline import review_inventory
from table_a2_refresh import refresh_table_a2
from table_a2_rows import extract_a2_rows
from table_a2_lookup import disposition_code, verify_disposition


def preflight_review_paths(pdf: Path, output: Path,
                           annotated_pdf: Path | None = None) -> None:
    """Validate fresh artifact destinations before inspecting or refreshing."""
    if output.suffix.lower() != '.md':
        raise ValueError('Output must be a Markdown (.md) file')
    if output.resolve() == pdf.resolve():
        raise ValueError('Output must not overwrite the source')
    if annotated_pdf is not None:
        if annotated_pdf.suffix.lower() != '.pdf':
            raise ValueError('Marked-up output must be a PDF (.pdf) file')
        if annotated_pdf.resolve() == pdf.resolve():
            raise ValueError('Marked-up output must not overwrite the source')
        if not pdf.is_file() or pdf.suffix.lower() != '.pdf':
            raise ValueError('An existing source PDF is required for markup')
    destinations = [output] + ([annotated_pdf] if annotated_pdf is not None else [])
    resolved = [path.resolve() for path in destinations]
    if len(set(resolved)) != len(resolved):
        raise ValueError('Review output paths must be distinct')
    for path in destinations:
        if path.exists() or path.is_symlink():
            raise FileExistsError('Review output already exists')
        if not path.resolve().parent.is_dir():
            raise ValueError('Review output parent directory must already exist')
    if annotated_pdf is not None:
        skill_root = Path(__file__).resolve().parents[1]
        protected = [skill_root]
        for parent in skill_root.parents:
            if (parent / '.git').exists():
                protected.append(parent)
                break
        if any(path.is_relative_to(root) for path in resolved for root in protected):
            raise ValueError('Marked-up review outputs must stay outside the installed skill and code repository')


def markup_artifact_report(pdf_output: Path, markdown_output: Path,
                           manifest: dict, pdf_bytes: bytes) -> str:
    """Describe a prepared review copy without embedding external actions."""
    from report_markdown import _cell
    relative = os.path.relpath(pdf_output.resolve(), markdown_output.resolve().parent)
    destination = './' + quote(relative.replace(os.sep, '/'), safe='/')
    return ('\n## Marked-up PDF review copy\n\n'
            f'- Marked-up PDF: [{_cell(pdf_output.name)}]({destination})\n'
            '- Status: REVIEW_REQUIRED; evidence regions are review candidates.\n'
            f'- Source SHA-256: {manifest["source_sha256"]}\n'
            f'- Marked-up PDF SHA-256: {hashlib.sha256(pdf_bytes).hexdigest()}\n'
            f'- Original PDF pages: {manifest["original_page_count"]}\n'
            f'- Printable notes pages: {manifest["notes_page_count"]}\n'
            f'- Located notes: {manifest["located_count"]}\n'
            f'- Unlocated notes in the notes index: {manifest["unlocated_count"]}\n'
            '- Note IDs in the PDF identify the detailed finding or review limitation.\n'
            '- This copy reproduces the source plan and must remain private.\n')


def plar_source_instruction(context: dict) -> str:
    if context["scope_status"] == "OUT_OF_SCOPE":
        return ("Declared land class is outside the Alberta Crown review scope. "
                "No Crown plan requirements were selected.")
    if context["scope_status"] != "IN_SCOPE":
        return ("Confirm land_class and review_scope before selecting the applicable PLAR table; "
                "for mixed land, identify the Alberta Crown component as "
                "review_scope=alberta_crown_component.")
    regulator = context["regulator"]
    if regulator == "AER":
        return "Download the current PLAR Table A2 PDF and supply it with --table-a2-pdf."
    if regulator == "Alberta":
        return ("Review the current PLAR Table A1 manually for the exact disposition, purpose "
                "and activity; confirm current provincial authority requirements.")
    return "Confirm the regulator before selecting the applicable PLAR table."


def drawing_disposition_report(inventory: dict, code: str | None,
                               drawing_text: Path | None) -> str:
    heading = "\n## Drawing-text disposition evidence\n"
    if code is None:
        return heading + "Status: REVIEW_REQUIRED (supply an expected disposition code)\n"
    # CAD labels may end in a numeric identifier immediately after the code.
    # Do not match a code embedded in another word or identifier.
    pattern = re.compile(r"(?<!\w)" + re.escape(code) + r"(?:[0-9]+)?(?!\w)", re.IGNORECASE)
    if drawing_text is None:
        matches = sorted({span["page"] for span in inventory["spans"]
                          if pattern.search(span["text"])})
        location = "PDF page "
    else:
        with drawing_text.open(encoding="utf-8-sig") as export:
            matches = [number for number, line in enumerate(export, 1) if pattern.search(line)]
        location = "Export line "
    status = ("DISPOSITION_OBSERVED_IN_DRAWING_TEXT" if matches
              else "DISPOSITION_NOT_OBSERVED_IN_DRAWING_TEXT")
    evidence = ", ".join(location + str(number) for number in matches) or "none observed"
    return (heading + f"Status: {status}\nDisposition: {code}\nEvidence: {evidence}\n"
            "Review status: REVIEW_REQUIRED\n"
            "Text evidence establishes a mention only. Confirm the drawing context visually.\n")


def preflight_clause_inputs(scenario: dict, clause_catalogue: dict | None,
                            clause_facts: dict | None,
                            clause_inventory: dict | None) -> None:
    """Validate explicit workbook inputs before inspecting PDFs or refreshing sources."""
    if clause_catalogue is None:
        if clause_facts is not None or clause_inventory is not None:
            raise ValueError("Clause facts/inventory requires an explicit clause catalogue")
        return
    from clause_workbook import prepare_clause_workbook
    prepare_clause_workbook(clause_catalogue, scenario,
                            clause_facts if clause_facts is not None else {},
                            coverage_inventory=clause_inventory)


def run_review(pdf: Path, output: Path, scenario: dict, catalogue_path: Path,
               survey_geometry: dict | None = None,
               a2_pdf: Path | None = None,
               drawing_text: Path | None = None,
               a2_source_checked: bool = False, *,
               clause_catalogue: dict | None = None,
               clause_facts: dict | None = None,
               clause_inventory: dict | None = None,
               annotated_pdf: Path | None = None,
               finished_plan_spec: dict | None = None,
               finished_plan_contexts: dict | None = None) -> Path:
    preflight_review_paths(pdf, output, annotated_pdf)
    if finished_plan_spec is not None and finished_plan_contexts is not None:
        raise ValueError("Finished-plan spec and contexts are mutually exclusive; do not supply both")
    if finished_plan_contexts is not None:
        from finished_plan_spec import validate_spec
        from pdf_source import read_pdf_snapshot
        validate_spec(finished_plan_contexts)
        if read_pdf_snapshot(pdf)[1] != finished_plan_contexts["source_sha256"]:
            raise ValueError("Source SHA-256 digest does not match the finished-plan contexts")
    if not isinstance(scenario, dict):
        raise TypeError("Scenario must be a JSON object")
    preflight_clause_inputs(scenario, clause_catalogue, clause_facts, clause_inventory)
    context = application_context(scenario)
    regulator = context["regulator"]
    in_scope = context["scope_status"] == "IN_SCOPE"
    if (not in_scope or regulator != "AER") and (a2_pdf is not None or a2_source_checked):
        raise ValueError("Table A2 inputs require confirmed Alberta Crown scope and regulator AER; "
                         "confirm land_class, review_scope and regulator")
    disposition = scenario.get("disposition", scenario.get("activity"))
    code = disposition_code(disposition)
    if ("disposition" in scenario and "activity" in scenario
            and scenario["disposition"] != scenario["activity"]
            and (code is None or code != disposition_code(scenario["activity"]))):
        raise ValueError("Conflicting scenario disposition and legacy activity")
    if code is not None:
        scenario = {**scenario, "activity": code}
    catalogue = load_candidate_catalog(catalogue_path)
    inventory = extract_pdf(pdf, include_vectors=False)
    preparation = None
    if finished_plan_contexts is not None:
        from plan_intake import prepare_finished_plan
        preparation = prepare_finished_plan(pdf, finished_plan_contexts)
        if inventory["source_sha256"] != preparation["source_sha256"]:
            raise ValueError("Source PDF changed during plan intake")
        finished_plan_spec = preparation["spec"]
    finished_review = None
    if finished_plan_spec is not None:
        from finished_plan_review import review_finished_plan
        from pdf_source import read_pdf_snapshot
        finished_review = review_finished_plan(pdf, finished_plan_spec)
        if inventory["source_sha256"] != finished_review["source_sha256"]:
            raise ValueError("Source PDF changed during the combined review")
    rows = extract_a2_rows(a2_pdf) if a2_pdf is not None else None
    report = review_inventory(inventory, scenario, catalogue,
                              survey_geometry=survey_geometry, table_a2_rows=rows,
                              clause_catalogue=clause_catalogue, clause_facts=clause_facts,
                              clause_inventory=clause_inventory)
    if preparation is not None:
        report["plan_intake_preparation"] = preparation
    if finished_review is not None or preparation is not None:
        from report_markdown import render_review_markdown
        from review_summary import build_review_summary
        if finished_review is not None:
            report["finished_plan_review"] = finished_review
        report["review_summary"] = build_review_summary(report)
        report["report_markdown"] = render_review_markdown(report)
    report["report_markdown"] += drawing_disposition_report(inventory, code, drawing_text)
    if not in_scope:
        source_status = "OUT_OF_SCOPE" if context["scope_status"] == "OUT_OF_SCOPE" else "REVIEW_REQUIRED"
        report["report_markdown"] += (
            "\n## Crown review jurisdiction\nStatus: " + source_status + "\n"
            + plar_source_instruction(context) + "\n")
    elif rows is not None:
        verification = verify_disposition(rows, disposition)
        report["report_markdown"] += (
            "\n## PLAR Table A2 disposition verification\n"
            + "Status: " + verification["status"] + "\n"
            + "Source: PLAR Table A2, October 28, 2026\n"
            + "Source input: " + ("OFFICIAL_DOWNLOAD" if a2_source_checked
                                   else "LOCAL_PDF") + "\n"
            + "Source currency: UNVERIFIED\n"
            + "Disposition: " + verification.get("disposition", "unresolved") + "\n"
            + "Matching rows: " + ", ".join(
                str(item["row"]) + " (PDF page " + str(item["page"]) + ")"
                for item in verification["matched_rows"]) + "\n"
            + "Compliance: NOT_ASSESSED\n")
    elif regulator == "AER":
        report["report_markdown"] += (
            "\n## PLAR Table A2 disposition verification\nStatus: REVIEW_REQUIRED\n"
            + plar_source_instruction(context) + "\n")
    else:
        heading = "PLAR Table A1 manual review" if regulator == "Alberta" else "PLAR source selection"
        report["report_markdown"] += (
            "\n## " + heading + "\nStatus: REVIEW_REQUIRED\n"
            + plar_source_instruction(context)
            + "\nSource currency: UNVERIFIED\nCompliance: NOT_ASSESSED\n")
    if finished_review is not None:
        if read_pdf_snapshot(pdf)[1] != finished_review["source_sha256"]:
            raise ValueError("Source PDF changed during the combined review")
        report["report_markdown"] += finished_review["report_markdown"]
    if preparation is not None:
        from intake_reporting import render_intake_preparation
        if read_pdf_snapshot(pdf)[1] != preparation["source_sha256"]:
            raise ValueError("Source PDF changed during the prepared review")
        report["report_markdown"] += render_intake_preparation(preparation)
    if annotated_pdf is None:
        # Preserve the existing single-report workflow.
        with output.open("x", encoding="utf-8") as handle:
            handle.write(report["report_markdown"])
    else:
        from pdf_markup import build_annotated_pdf
        from pdf_source import read_pdf_snapshot
        pdf_bytes, manifest = build_annotated_pdf(pdf, report, inventory)
        if read_pdf_snapshot(pdf)[1] != manifest['source_sha256']:
            raise ValueError('Source PDF changed before review publication')
        report['report_markdown'] += markup_artifact_report(annotated_pdf, output, manifest, pdf_bytes)
        publish_artifacts({output: report['report_markdown'].encode('utf-8'),
                           annotated_pdf: pdf_bytes})
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline Crown plan evidence review (not compliance certification)")
    parser.add_argument("pdf", type=Path, help="Authorized local PDF")
    parser.add_argument("--scenario", required=True, type=Path, help="Local scenario JSON")
    parser.add_argument("--output", required=True, type=Path, help="New local Markdown report")
    parser.add_argument("--annotated-pdf", type=Path,
                        help="Optional new private PDF review copy with located comments and printable notes")
    parser.add_argument("--catalogue", type=Path, default=Path(__file__).with_name("candidate_requirements.json"))
    parser.add_argument("--clause-catalogue", type=Path,
                        help="Explicitly add a dated-source conditional clause workbook")
    parser.add_argument("--clause-facts", type=Path,
                        help="Typed fact/provenance JSON for the selected clause catalogue")
    parser.add_argument("--clause-inventory", type=Path,
                        help="Explicit matching inventory to assess dated clause-path coverage")
    finished = parser.add_mutually_exclusive_group()
    finished.add_argument("--finished-plan-spec", type=Path,
                        help="Opt-in source-bound drawing-QC checks in the Markdown report")
    finished.add_argument("--finished-plan-contexts", type=Path,
                        help="Prepare drawing-QC regions from source-bound reviewed contexts and literal labels")
    parser.add_argument("--survey-geometry", type=Path, help="Optional local JSON with explicitly sourced projected survey coordinates")
    parser.add_argument("--drawing-text", type=Path, help="Local UTF-8 DWG text export for the disposition check")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--table-a2-pdf", type=Path, help="User-supplied local Table A2 PDF for AER review")
    source.add_argument("--refresh-table-a2", action="store_true", help="Opt in to official Table A2 download for AER review")
    source.add_argument("--table-a2-url", help="Opt in to downloading an explicit official Table A2 PDF URL for AER review")
    parser.add_argument("--offline", action="store_true", help="Require offline mode (the default)")
    parser.add_argument("--reference-cache", type=Path, default=Path.home() / ".cache" / "crown-plan-agent" / "regulatory", help="Local directory for versioned regulatory PDFs")
    args = parser.parse_args(argv)
    if args.clause_catalogue is None and (args.clause_facts is not None or args.clause_inventory is not None):
        parser.error("--clause-facts/--clause-inventory requires --clause-catalogue")
    refresh_requested = args.refresh_table_a2 or args.table_a2_url is not None
    if args.offline and refresh_requested:
        parser.error("--offline cannot be combined with an official refresh")
    try:
        preflight_review_paths(args.pdf, args.output, args.annotated_pdf)
    except (OSError, RuntimeError, ValueError) as exc:
        if args.annotated_pdf is None:
            raise
        parser.error('Invalid review output: ' + str(exc))
    try:
        scenario = load_bounded_json(args.scenario)
        if not isinstance(scenario, dict):
            raise ValueError("Scenario must be a JSON object")
    except (OSError, TypeError, ValueError) as exc:
        parser.error("Invalid scenario JSON: " + str(exc))
    context = application_context(scenario)
    clause_catalogue = clause_facts = clause_inventory = None
    if args.clause_catalogue is not None:
        from clause_schema import load_clause_catalogue
        try:
            clause_catalogue = load_clause_catalogue(args.clause_catalogue)
            clause_facts = load_bounded_json(args.clause_facts) if args.clause_facts else {}
            clause_inventory = (load_bounded_json(args.clause_inventory)
                                if args.clause_inventory else None)
            # Validate the explicit local inputs before any opted-in refresh.
            preflight_clause_inputs(scenario, clause_catalogue, clause_facts, clause_inventory)
        except (OSError, TypeError, ValueError) as exc:
            parser.error("Invalid clause workbook inputs: " + str(exc))
    finished_plan_spec = None
    finished_plan_contexts = None
    finished_path = args.finished_plan_spec or args.finished_plan_contexts
    if finished_path is not None:
        from finished_plan_spec import load_spec
        from pdf_source import read_pdf_snapshot
        try:
            selected_spec = load_spec(finished_path)
            if read_pdf_snapshot(args.pdf)[1] != selected_spec["source_sha256"]:
                raise ValueError("Source SHA-256 digest does not match the specification")
            if args.finished_plan_contexts is not None:
                finished_plan_contexts = selected_spec
            else:
                finished_plan_spec = selected_spec
        except (OSError, TypeError, ValueError) as exc:
            parser.error("Invalid finished-plan inputs: " + str(exc))
    regulator = context["regulator"]
    in_scope = context["scope_status"] == "IN_SCOPE"
    if (not in_scope or regulator != "AER") and (args.table_a2_pdf is not None or refresh_requested):
        parser.error("Table A2 inputs require confirmed Alberta Crown scope and regulator AER; "
                     "confirm land_class, review_scope and regulator")
    survey_geometry = None
    if args.survey_geometry is not None:
        try:
            survey_geometry = load_bounded_json(args.survey_geometry)
            if not isinstance(survey_geometry, dict):
                raise ValueError("Survey geometry must be a JSON object")
        except (OSError, TypeError, ValueError) as exc:
            parser.error("Invalid survey geometry JSON: " + str(exc))
    if refresh_requested:
        refresh = refresh_table_a2(args.reference_cache, pinned_url=args.table_a2_url)
        if refresh["refresh_status"] != "CHECKED_OFFICIAL_SOURCE":
            parser.error("Official Table A2 refresh unresolved: " + refresh["reason"])
    # Offline reviews may use a previously cached reference, but never claim currency.
    cached_a2 = args.reference_cache / "plar_table_a2.pdf"
    a2_pdf = args.table_a2_pdf
    if in_scope and regulator == "AER" and a2_pdf is None and cached_a2.is_file():
        a2_pdf = cached_a2
    if refresh_requested and a2_pdf is None:
        parser.error("Official refresh reported success but cached Table A2 PDF is missing")
    try:
        run_review(args.pdf, args.output, scenario, args.catalogue,
                   survey_geometry=survey_geometry, a2_pdf=a2_pdf,
                   drawing_text=args.drawing_text, a2_source_checked=refresh_requested,
                   clause_catalogue=clause_catalogue, clause_facts=clause_facts,
                   clause_inventory=clause_inventory, annotated_pdf=args.annotated_pdf,
                   finished_plan_spec=finished_plan_spec,
                   finished_plan_contexts=finished_plan_contexts)
    except (OSError, RuntimeError, ValueError) as exc:
        if args.annotated_pdf is None:
            raise
        parser.error('Review could not be completed: ' + str(exc))
    if a2_pdf is None:
        print(plar_source_instruction(context))
    print("Review-only report created:", args.output)
    if args.annotated_pdf is not None:
        print('Private marked-up PDF created:', args.annotated_pdf)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
