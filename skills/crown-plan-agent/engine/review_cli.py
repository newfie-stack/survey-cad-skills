"""Offline Crown Plan Agent PDF-to-review command.

Never upload source plans or generated reports. Output is review-only.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from clause_schema import load_bounded_json
from pdf_inspector import extract_pdf
from regulatory_catalog import load_candidate_catalog
from requirements import application_context
from review_pipeline import review_inventory
from table_a2_refresh import refresh_table_a2
from table_a2_rows import extract_a2_rows
from table_a2_lookup import disposition_code, verify_disposition


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
               clause_inventory: dict | None = None) -> Path:
    if output.suffix.lower() != ".md":
        raise ValueError("Output must be a Markdown (.md) file")
    if output.resolve() == pdf.resolve():
        raise ValueError("Output must not overwrite the source")
    if output.exists():
        raise FileExistsError("Review output already exists")
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
    rows = extract_a2_rows(a2_pdf) if a2_pdf is not None else None
    report = review_inventory(inventory, scenario, catalogue,
                              survey_geometry=survey_geometry, table_a2_rows=rows,
                              clause_catalogue=clause_catalogue, clause_facts=clause_facts,
                              clause_inventory=clause_inventory)
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
    # Exclusive creation prevents overwriting existing review records.
    with output.open("x", encoding="utf-8") as handle:
        handle.write(report["report_markdown"])
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline Crown plan evidence review (not compliance certification)")
    parser.add_argument("pdf", type=Path, help="Authorized local PDF")
    parser.add_argument("--scenario", required=True, type=Path, help="Local scenario JSON")
    parser.add_argument("--output", required=True, type=Path, help="New local Markdown report")
    parser.add_argument("--catalogue", type=Path, default=Path(__file__).with_name("candidate_requirements.json"))
    parser.add_argument("--clause-catalogue", type=Path,
                        help="Explicitly add a dated-source conditional clause workbook")
    parser.add_argument("--clause-facts", type=Path,
                        help="Typed fact/provenance JSON for the selected clause catalogue")
    parser.add_argument("--clause-inventory", type=Path,
                        help="Explicit matching inventory to assess dated clause-path coverage")
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
    run_review(args.pdf, args.output, scenario, args.catalogue,
               survey_geometry=survey_geometry, a2_pdf=a2_pdf,
               drawing_text=args.drawing_text, a2_source_checked=refresh_requested,
               clause_catalogue=clause_catalogue, clause_facts=clause_facts,
               clause_inventory=clause_inventory)
    if a2_pdf is None:
        print(plar_source_instruction(context))
    print("Review-only report created:", args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
