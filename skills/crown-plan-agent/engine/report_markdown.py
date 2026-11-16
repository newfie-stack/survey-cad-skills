"""Render a review-only evidence ledger with traceable candidate findings."""
from __future__ import annotations

from html import escape

from review_summary import build_review_summary


def _cell(value: object) -> str:
    text = "" if value is None else str(value)
    return (escape(text, quote=False).replace("\\", "\\\\").replace("|", "\\|")
            .replace("[", "\\[").replace("]", "\\]")
            .replace("\r", " ").replace("\n", " "))


def render_review_markdown(report: dict) -> str:
    if report.get("assessment_type") != "CANDIDATE_EVIDENCE_REVIEW_NOT_COMPLIANCE":
        raise ValueError("Only review-only ledgers can be rendered")
    if report.get("overall_status") != "REVIEW_REQUIRED":
        raise ValueError("Unexpected overall compliance status")
    entries = report.get("requirements", [])
    if not isinstance(entries, list):
        raise ValueError("Invalid requirement list")
    if any(not isinstance(entry, dict) or entry.get("status") != "REVIEW_REQUIRED"
           for entry in entries):
        raise ValueError("Unverified requirements cannot be reported as passed")
    summary = build_review_summary(report)
    lines = [
        "# Crown Plan Agent — Evidence Review",
        "",
        "**Status: REVIEW_REQUIRED. This is not a regulatory compliance certificate.**",
        "",
        "## Review summary",
        "",
        _cell(summary["headline"]),
    ]
    for heading, key in (("What was checked", "checked"),
                         ("What needs attention", "needs_attention"),
                         ("What remains unchecked", "not_checked"),
                         ("Next steps", "next_steps")):
        lines += ["", "### " + heading, ""]
        lines.extend("- " + _cell(item) for item in (summary[key] or ["None recorded."]))
    if summary["context_question"]:
        lines += ["", "Information needed: " + _cell(summary["context_question"])]
    lines += [
        "",
        "## Detailed evidence",
        "",
        "| ID | Candidate requirement | Evidence | Page | Regulatory status |",
        "|---|---|---|---|---|",
    ]
    for entry in entries:
        lines.append("| " + " | ".join(_cell(value) for value in (
            entry.get("requirement_id"), entry.get("requirement_summary"),
            entry.get("evidence_status"), entry.get("page"), entry.get("status"),
        )) + " |")
    if report.get("source_filename"):
        lines += ["", "Input artifact: " + _cell(report["source_filename"])]
    if "plan_type_review" in report:
        review = report["plan_type_review"]
        if not isinstance(review, dict) or review.get("status") != "REVIEW_REQUIRED":
            raise ValueError("Invalid plan-type review")
        lines += ["", "## Plan type review",
                  "Jurisdiction scope: " + _cell(review.get("scope_status", "UNRESOLVED_SCOPE")),
                  "Declared land class: " + _cell(review.get("land_class") or "unresolved"),
                  "Plan classification: " + _cell(review.get("plan_type_status", "UNRESOLVED")),
                  "Missing or invalid base context: " + _cell(", ".join(review.get("missing_or_invalid_fields", [])) or "none recorded")]
        if summary["input_requests"]:
            lines.append("Additional review inputs requested: " + _cell(
                ", ".join(item["field"] for item in summary["input_requests"])))
        if review.get("review_scope"):
            lines.append("Review component: " + _cell(review["review_scope"]))
        if review.get("land_class") == "mixed" and review.get("scope_status") == "IN_SCOPE":
            lines.append("Scope is limited to the declared Alberta Crown component; whole-plan ownership is not inferred.")
        for note in review.get("notes", []):
            lines.append("- " + _cell(note))
        if "amendment_review" in review:
            amendment = review["amendment_review"]
            lines += ["", "### AER amendment plan review",
                      "Survey scope: " + _cell(amendment["route"]),
                      "Comparison: " + _cell(amendment["comparison"]),
                      "Source: " + _cell(amendment["source"]),
                      "Review: " + _cell(amendment["instruction"]),
                      "Compliance: NOT_ASSESSED"]
        renewal = review.get("renewal_review")
        if renewal is not None:
            lines += ["", "### AER renewal plan-of-record review",
                      "Source: " + _cell(renewal["source"]),
                      "Plan type on file: " + _cell(renewal["existing_plan_type"] or "unresolved"),
                      "Comparison: " + _cell(renewal["comparison"]),
                      "Confirm current requirements, site entry and any legacy variance separately.",
                      "Compliance: NOT_ASSESSED"]
        requirement = (renewal.get("requirement") if renewal is not None
                       else review.get("table_a2_requirement"))
        if requirement is not None:
            lines += ["", "### Table A2 plan-type comparison",
                      "Comparison: " + _cell(renewal["comparison"] if renewal is not None
                                              else review["table_a2_comparison"])]
            if renewal is None:
                lines.append("Proposed plan type: " + _cell(review["proposed_plan_type"] or "unresolved"))
            if "row" in requirement:
                lines += ["Source: " + _cell(requirement["source"]),
                          "Row: " + _cell(requirement["row"]),
                          "PDF page: " + _cell(requirement["page"]),
                          "Plan type: " + _cell(requirement["required_plan"]),
                          "Survey monuments: " + _cell(requirement["survey_monuments"]),
                          "Consultation: " + _cell(requirement["consultation"] or "unresolved").replace("*", "\\*"),
                          "Additional RTF approval option: " + _cell(requirement["rtf_approval"] or "unresolved"),
                          "Additional RTF authorization option: " + _cell(requirement["rtf_authorization"] or "unresolved")]
                lines.append("Verify consultation qualifiers and RTF options against Table A2 PDF page 18 and the applicable procedures.")
                if requirement["footnote"] is not None:
                    lines.append("Review row footnote " + _cell(requirement["footnote"]) + " on the cited PDF page.")
            else:
                matches = requirement["matches"]
                lines.append("Candidate rows: " + (", ".join(
                    f'{item["row"]} (PDF page {item["page"]})' for item in matches) or "none"))
            lines.append("Compliance: NOT_ASSESSED")
    if "applicability_decisions" in report:
        lines += ["", "## Candidate applicability",
                  "| Requirement | Selection | Unresolved context |",
                  "|---|---|---|"]
        for decision in report["applicability_decisions"]:
            if decision.get("status") != "REVIEW_REQUIRED":
                raise ValueError("Invalid applicability status")
            lines.append("| " + " | ".join(_cell(value) for value in (
                decision.get("requirement_id"), decision.get("applicability_status"),
                ", ".join(decision.get("missing_dimensions", [])
                          + decision.get("invalid_dimensions", [])),
            )) + " |")
    lines += ["", "## Evidence trace and source checks"]
    for entry in entries:
        lines += ["", "### " + _cell(entry.get("requirement_id")),
                  "- Observation: " + _cell(entry.get("observation") or "No text candidate recorded"),
                  "- Page: " + _cell(entry.get("page") or "unresolved"),
                  "- PDF bbox (points): " + _cell(entry.get("bbox_points") or "unresolved"),
                  "- Publication: " + _cell(entry.get("publication_title") or "unresolved"),
                  "- Section: " + _cell(entry.get("section") or "unresolved"),
                  "- Source status: " + _cell(entry.get("source_status"))]
        if entry.get("source_version"):
            lines.append("- Source edition: " + _cell(entry["source_version"]))
        if entry.get("source_page"):
            lines.append("- Source page: " + _cell(entry["source_page"]))
        if entry.get("source_url"):
            lines.append("- Source URL: " + _cell(entry["source_url"]))
        if entry.get("candidate_count", 0) and entry["candidate_count"] > 1:
            lines.append("- Text candidates: " + _cell(entry["candidate_count"]) + ". Confirm which belongs to the main plan.")
            if entry.get("candidate_pages"):
                lines.append("- Candidate pages: " + ", ".join(map(str, entry["candidate_pages"])))
        if entry.get("review_instruction"):
            lines.append("- Review: " + _cell(entry["review_instruction"]))
        source_review = entry.get("source_review")
        if source_review is not None:
            if source_review.get("source_status") != "REVIEW_REQUIRED":
                raise ValueError("Invalid source review status")
            lines.append("- Citation gaps: " + _cell(", ".join(source_review.get("missing_or_invalid", [])) or "none structurally detected"))
    if "geometry_handoff" in report:
        handoff = report["geometry_handoff"]
        if (not isinstance(handoff, dict) or handoff.get("status") != "REVIEW_REQUIRED"
                or handoff.get("execution_status") != "NOT_EXECUTED"):
            raise ValueError("Only unexecuted, review-only specialist proposals can be rendered")
        lines += ["", "## Geometry workflow",
                  "Specialist handoff: NOT_EXECUTED",
                  "Readiness: " + _cell(handoff.get("readiness"))]
        if "survey_geometry_review" not in report:
            lines.append("No supplied-coordinate geometry diagnostics were executed.")
        else:
            lines.append("Supplied-coordinate diagnostics below do not establish specialist reconstruction or acceptance.")
        requests = handoff.get("requested_skills", [])
        if requests:
            lines.append("Requested skills, in order; availability remains unverified:")
            for request in requests:
                lines.append("- " + _cell(request.get("name")) + ": " + _cell(request.get("purpose")))
        blockers = handoff.get("acceptance_blockers", [])
        if blockers:
            lines.append("Unresolved handoff inputs: " + _cell(", ".join(blockers)))
        lines.append("Return source/feature and observation registers, control evidence, reviewed CAD/preview and accepted coordinate JSON before treating reconstruction as completed.")
    if "survey_geometry_review" in report:
        geometry = report["survey_geometry_review"]
        if geometry.get("status") != "REVIEW_REQUIRED" or geometry.get("coordinate_source") != "EXPLICIT_SURVEY_COORDINATES":
            raise ValueError("Unverified or PDF-derived geometry is not reportable")
        traverse = geometry.get("traverse", {})
        lines += ["", "## Separate survey-coordinate geometry diagnostics",
                  "- Coordinate source: explicit survey coordinates (not PDF page points)",
                  "- CRS identifier: " + _cell(geometry.get("crs_identifier"))]
        if geometry.get("diagnostic_status") == "REPRESENTATION_UNRESOLVED":
            lines += ["- Diagnostic status: REPRESENTATION_UNRESOLVED",
                      "- Review: " + _cell(geometry.get("reason")),
                      "No boundary measurements or area comparison were computed for the unsupported subject representation."]
        else:
            lines.append("- CRS status: " + _cell(traverse.get("crs_status")))
        if traverse.get("crs_status") == "VERIFIED":
            lines += ["- Traverse misclosure (m): " + _cell(traverse.get("misclosure_m")),
                  "- Travelled distance (m): " + _cell(traverse.get("travelled_distance_m")),
                  "- Within user-supplied tolerance: " + _cell(traverse.get("within_supplied_tolerance"))]
        if "polygon" in geometry and traverse.get("crs_status") == "VERIFIED":
            lines += ["- Polygon area (m²): " + _cell(geometry["polygon"].get("area_m2")),
                      "- Polygon perimeter (m): " + _cell(geometry["polygon"].get("perimeter_m"))]
        lines.append("These diagnostics are not a survey adjustment or regulatory acceptance.")
        if "area_comparison" in geometry:
            area = geometry["area_comparison"]
            lines += ["", "### Selected plan area label",
                      "Comparison: " + _cell(area["comparison"]),
                      "PDF page: " + _cell(area["page"]),
                      "Supplied tolerance (ha): " + _cell(area["tolerance_ha"])]
            if area.get("source") == "table_total":
                lines.append("Selected evidence: Measurement table hectare total")
            if area.get("reason"):
                lines.append("Review: " + _cell(area["reason"]))
            if "observed_ha" in area:
                lines += ["Observed area (ha): " + _cell(area["observed_ha"]),
                          "PDF bbox (points): " + _cell(area["bbox_points"])]
            else:
                lines.append("Matching text spans: " + _cell(area["matching_spans"]))
                if area.get("source") == "table_total":
                    lines.append("Table candidates on selected page: " + _cell(area["candidate_count"]))
            if "calculated_ha" in area:
                lines += ["Calculated area (ha): " + _cell(area["calculated_ha"]),
                          "Absolute difference (ha): " + _cell(format(area["difference_ha"], ".12g"))]
            lines.append("Confirm the selected annotation and survey coordinates refer to the same boundary.")
    if "clause_workbook" in report:
        from clause_workbook_markdown import render_clause_workbook
        lines += ["", render_clause_workbook(report["clause_workbook"])]
    lines += ["", "## Required next steps", ""]
    lines.extend("- " + _cell(item) for item in summary["next_steps"])
    lines += ["",
              "No missing visual element or legal noncompliance is established by text extraction alone.",
              ""]
    return "\n".join(lines)
