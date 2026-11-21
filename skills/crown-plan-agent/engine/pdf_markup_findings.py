"""Adapt executed QA findings to bounded notes on the original plan only.

Reference records remain textual context. A report's selected rectangles are
never trusted as anchors: original native spans are matched independently with
the inspected plan inventory. Unsupported or multiple targets stay in the index.
"""
from __future__ import annotations

from copy import deepcopy
import json

from pdf_markup_plan import MAX_BODY, MAX_NOTES, _box, _citation, _locate, _text

_STATES = frozenset({"PASS", "FAIL", "REVIEW_REQUIRED"})
_EXECUTIONS = frozenset({"EXECUTED", "BLOCKED", "NOT_EXECUTED"})
_TITLES = {"applicant_name": "Applicant name", "legal_description": "Legal description",
           "disposition_id": "Disposition identifier", "parts_total": "Activity area total",
           "amendment": "Amendment area balance", "gross_net": "Gross and net area balance",
           "length_schedule": "Length schedule", "scale": "Numerical scale",
           "record_match": "Plan amount versus record",
           "point_export": "CAD/GIS point export",
           "required_text": "Required text candidate", "same_text": "Selected text agreement",
           "decimal_sum": "Printed amount total", "visual": "Visual evidence"}


def _collection(value: object, label: str) -> list:
    if not isinstance(value, list) or len(value) > MAX_NOTES:
        raise ValueError(label + " must be a bounded list")
    return value


def _state(value: object, label: str) -> str:
    if not isinstance(value, str) or value not in _STATES:
        raise ValueError("Invalid " + label)
    return value


def _bound_report(value: object, scope: str, digest: str, *, job=False) -> dict:
    if (not isinstance(value, dict) or value.get("assessment_scope") != scope
            or value.get("overall_status") != "REVIEW_REQUIRED"):
        raise ValueError("Only review-only expanded findings support markup")
    key = "plan_source_sha256" if job else "source_sha256"
    if value.get(key) != digest:
        raise ValueError("Expanded markup requires matching source SHA-256 bindings")
    return value


def _execution(finding: dict) -> None:
    if finding.get("execution_status") not in _EXECUTIONS:
        raise ValueError("Invalid expanded-finding execution status")


def _preview(value: object, limit=700) -> str:
    """Keep the correction note concise; full observations stay in Markdown."""
    if value is None:
        return "No unambiguous value recorded."
    if isinstance(value, str):
        text = value
    elif isinstance(value, (dict, list, int, float, bool)):
        try:
            text = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        except (ValueError, TypeError, RecursionError) as exc:
            raise ValueError("Expanded observation must be bounded JSON data") from exc
    else:
        raise ValueError("Unsupported expanded observation")
    if len(text) > limit:
        text = text[:limit] + " [remaining details are in Markdown]"
    return _text(text or "No unambiguous value recorded.", "Expanded observation")


def _inside(outer, inner) -> bool:
    return (outer[0] <= inner[0] and outer[1] <= inner[1]
            and outer[2] >= inner[2] and outer[3] >= inner[3])


def _direct_candidates(evidence: object, pages: int, spans: dict) -> tuple[list[dict], bool]:
    """Require complete, unique, independently found original native spans."""
    if not isinstance(evidence, dict):
        return [], True
    region = _box(evidence.get("bbox_points"))
    page = evidence.get("page")
    raw_spans = evidence.get("spans")
    if (type(page) is not int or not 1 <= page <= pages or region is None
            or not isinstance(raw_spans, list) or not 1 <= len(raw_spans) <= 5000):
        return [], True
    candidates, seen = [], set()
    for source in raw_spans:
        if not isinstance(source, dict) or "original_bbox_points" in source:
            return [], True
        box, text = _box(source.get("bbox_points")), source.get("text")
        if (box is None or not _inside(region, box) or not isinstance(text, str) or not text.strip()
                or source.get("page", page) != page):
            return [], True
        key = (page, box, text)
        if key in seen:
            return [], True
        seen.add(key)
        anchor, _, _, clipped = _locate({
            "page": page, "bbox_points": list(box), "evidence_status": "OBSERVED_CANDIDATE",
            "candidate_count": 1, "input_evidence": {
                "page": page, "bbox_points": list(box), "source_text": text}}, pages, spans)
        if anchor is None or clipped:
            return [], True
        candidates.append(anchor)
    return candidates, False


def _plan_candidates(evidence: list, mode: str, digest: str,
                     pages: int, spans: dict) -> tuple[list[dict], bool]:
    candidates, invalid = [], False
    if not isinstance(evidence, list) or len(evidence) > 5000:
        raise ValueError("Expanded finding evidence must be a bounded list")
    for item in evidence:
        if not isinstance(item, dict):
            invalid = True
            continue
        if mode == "job":
            inner = item.get("evidence")
            # Both layers must explicitly identify the current plan. Reference
            # PDFs can share page numbers and even coincident literal spans.
            if item.get("source_id") != "plan":
                continue
            if (item.get("source_sha256") != digest
                    or not isinstance(inner, dict) or inner.get("source_id") != "plan"
                    or inner.get("source_kind") != "PLAN" or inner.get("source_sha256") != digest):
                invalid = True
                continue
            found, problem = _direct_candidates(inner, pages, spans)
            candidates.extend(found)
            invalid = invalid or problem
        elif "source_locator" in item:
            locator = item["source_locator"]
            if (not isinstance(locator, dict) or locator.get("source_sha256") != digest
                    or not isinstance(locator.get("fields"), dict) or len(locator["fields"]) > 10):
                invalid = True
                continue
            for inner in locator["fields"].values():
                found, problem = _direct_candidates(inner, pages, spans)
                candidates.extend(found)
                invalid = invalid or problem
        else:
            found, problem = _direct_candidates(item, pages, spans)
            candidates.extend(found)
            invalid = invalid or problem
    return candidates, invalid


def _reference_context(evidence: list) -> str:
    references = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        source = item.get("source_id")
        inner = item.get("evidence")
        if not isinstance(inner, dict) or not isinstance(source, str):
            continue
        kind = inner.get("source_kind", "record")
        location = ("page " + str(inner["page"]) if type(inner.get("page")) is int else
                    "pointer " + str(inner.get("pointer", inner.get("json_pointer", "unlocated"))))
        text = source + " (" + str(kind) + ", " + location + ")"
        if text not in references:
            references.append(text)
    return _preview("; ".join(references), 600) if references else ""


def _source_citation(finding: dict, source: object) -> dict:
    citation = finding.get("citation")
    if not isinstance(citation, dict):
        return _citation({})
    source = source if isinstance(source, dict) else {}
    return _citation({"publication_title": citation.get("publication_title", source.get("title")),
                      "source_version": citation.get("version_date", source.get("version_date")),
                      "section": citation.get("section"), "source_page": citation.get("page"),
                      "source_url": citation.get("source_url", source.get("url"))})


def _record(identifier: str, finding: dict, state: str, mode: str, *, source=None) -> dict:
    kind = finding.get("kind", "review")
    _text(kind, "Expanded finding kind", limit=200)
    reason = _text(finding.get("reason"), "Expanded finding reason")
    residual = finding.get("residual_review", finding.get("correction"))
    if residual is not None:
        residual = _text(residual, "Expanded finding correction")
    evidence = finding.get("evidence", [])
    if not isinstance(evidence, list) or len(evidence) > 5000:
        raise ValueError("Expanded finding evidence must be a bounded list")
    description = finding.get("description")
    if description is None and isinstance(finding.get("drawing_finding"), dict):
        description = finding["drawing_finding"].get("description")
    title = (_text(description, "Expanded finding description", limit=400)
             if isinstance(description, str) and 0 < len(description) <= 400
             else _TITLES.get(kind, kind.replace("_", " ")))
    return {"finding_id": identifier, "kind": kind, "state": state,
            "title": title,
            "reason": reason, "residual": residual, "observed": finding.get("observed"),
            "mode": mode, "evidence": evidence, "links": [], "clause_results": [],
            "drawing_finding": None, "citation": _source_citation(finding, source),
            "details": {key: finding[key] for key in ("expected", "difference", "unit", "tolerance")
                        if key in finding}}


def _point_export_records(export: object, digest: str) -> list[dict]:
    if not isinstance(export, dict) or export.get("regulatory_status") != "REVIEW_REQUIRED":
        raise ValueError("Only review-only point-export comparisons support markup")
    state = _state(export.get("mechanical_status"), "point-export mechanical status")
    if export.get("execution_status") not in _EXECUTIONS:
        raise ValueError("Invalid point-export execution status")
    actual_hash = export.get("plan_source_sha256")
    if actual_hash != digest and (actual_hash is not None or export["execution_status"] == "EXECUTED"):
        raise ValueError("Point-export markup requires the matching plan source SHA-256")
    findings = _collection(export.get("findings", []), "Point-export findings")
    comparisons = export.get("comparisons", [])
    if not isinstance(comparisons, list) or len(comparisons) > 10000:
        raise ValueError("Point-export comparisons exceed the bounded contract")
    point_rows, duplicate_rows = {}, set()
    for comparison in comparisons:
        if not isinstance(comparison, dict) or not isinstance(comparison.get("point_id"), str):
            raise ValueError("Point-export comparison requires a point identity")
        identity = comparison["point_id"]
        if identity in point_rows:
            duplicate_rows.add(identity)
        point_rows[identity] = comparison.get("table")
    if not findings and state != "PASS":
        findings = [{"reason_code": "POINT_EXPORT_UNRESOLVED", "status": state,
                     "reason": export.get("reason", "The supplied point-export comparison remains unresolved.")}]
    records = []
    for ordinal, finding in enumerate(findings, 1):
        if not isinstance(finding, dict):
            raise ValueError("Invalid point-export finding")
        status = _state(finding.get("status"), "point-export finding status")
        reason_code = _text(finding.get("reason_code"), "Point-export reason code", limit=128)
        identity = finding.get("point_id")
        if identity is not None and not isinstance(identity, str):
            raise ValueError("Point-export finding identity must preserve its original string")
        table = finding.get("table", point_rows.get(identity))
        evidence = []
        if isinstance(table, dict) and table.get("point_id") == identity and identity not in duplicate_rows:
            locator = table.get("source_locator")
            fields = locator.get("fields") if isinstance(locator, dict) else None
            point = fields.get("point_id") if isinstance(fields, dict) else None
            # A point's own literal ID cell is a comparison location, without
            # choosing either artifact's coordinates as authoritative.
            if (isinstance(identity, str) and isinstance(locator, dict)
                    and locator.get("source_sha256") == digest and isinstance(point, dict)
                    and isinstance(point.get("text"), str) and point["text"].strip() == identity):
                evidence = [{"source_locator": {"source_sha256": digest, "fields": {"point_id": point}}}]
        reason = (("Point " + _preview(identity, 100) + ": ") if identity is not None else "") + reason_code
        if finding.get("reason"):
            reason += "; " + _text(finding["reason"], "Point-export reason")
        item = {"kind": "point_export", "reason": reason, "observed": finding, "evidence": evidence,
                "residual_review": "Confirm the supplied export and reviewed table; this does not inspect native CAD/GIS or establish survey control."}
        record = _record(f"POINT-{ordinal:03}-" + reason_code, item, status, "clause")
        record["links"].append(reason_code)
        records.append(record)
    return records


def expanded_markup_notes(report: dict, *, digest: str, pages: int,
                          spans: dict, remaining: int) -> list[dict]:
    """Return new actionable notes, preserving complete finding-ID accounting."""
    records, finished = [], {}
    drawing = report.get("finished_plan_review")
    if drawing is not None:
        drawing = _bound_report(drawing, "DRAWING_QC_ONLY", digest)
        for finding in _collection(drawing.get("findings"), "Finished-plan findings"):
            if not isinstance(finding, dict):
                raise ValueError("Invalid finished-plan finding")
            cid = _text(finding.get("check_id"), "Drawing finding ID", limit=128)
            if cid in finished:
                raise ValueError("Duplicate drawing finding ID")
            state = _state(finding.get("status"), "drawing mechanical status")
            record = _record("DRAWING-" + cid, finding, state, "drawing")
            record["drawing_finding"] = finding
            record["links"].append(cid)
            records.append(record)
            finished[cid] = record
    regulatory = report.get("regulatory_evidence_review")
    if regulatory is not None:
        regulatory = _bound_report(regulatory, "DATED_CLAUSE_MECHANICAL_EVIDENCE", digest)
        seen = set()
        for finding in _collection(regulatory.get("observations"), "Clause observations"):
            if not isinstance(finding, dict) or finding.get("status") != "REVIEW_REQUIRED":
                raise ValueError("Only review-required clause observations support markup")
            cid = _text(finding.get("workbook_check_id"), "Clause observation ID", limit=128)
            if cid in seen:
                raise ValueError("Duplicate clause observation ID")
            seen.add(cid)
            state = _state(finding.get("mechanical_status"), "clause mechanical status")
            _execution(finding)
            alias = finding.get("drawing_finding")
            candidate = finished.get(alias.get("check_id")) if isinstance(alias, dict) else None
            if candidate is not None and candidate["drawing_finding"] == alias:
                record = candidate
                record["links"].append(cid)
                record["clause_results"].append((cid, state, _text(finding.get("reason"), "Clause reason")))
                record["citation"] = _source_citation(finding, regulatory.get("source"))
            else:
                record = _record("CLAUSE-" + cid, finding, state, "clause", source=regulatory.get("source"))
                record["links"].append(cid)
                record["clause_results"].append((cid, state, record["reason"]))
                records.append(record)
        if regulatory.get("point_export_comparison") is not None:
            records.extend(_point_export_records(regulatory["point_export_comparison"], digest))
    job = report.get("job_record_review")
    if job is not None:
        job = _bound_report(job, "JOB_RECORD_AND_BALANCE_QA", digest, job=True)
        seen = set()
        for finding in _collection(job.get("findings"), "Job-record findings"):
            if not isinstance(finding, dict) or finding.get("status") != "REVIEW_REQUIRED":
                raise ValueError("Only review-required job findings support markup")
            cid = _text(finding.get("check_id"), "Job finding ID", limit=128)
            if cid in seen:
                raise ValueError("Duplicate job finding ID")
            seen.add(cid)
            state = _state(finding.get("mechanical_status"), "job mechanical status")
            _execution(finding)
            record = _record("JOB-" + cid, finding, state, "job", source=job.get("source"))
            record["links"].append(cid)
            question = finding.get("workbook_check_id")
            if question is not None:
                question = _text(question, "Job question ID", limit=128)
                record["links"].append(question)
                record["clause_results"].append((question, state, record["reason"]))
            records.append(record)
    actionable = [r for r in records if r["state"] != "PASS"
                  or any(state != "PASS" for _, state, _ in r["clause_results"])]
    if len(actionable) > remaining:
        raise ValueError("Markup note limit exceeded")
    notes = []
    for record in sorted(actionable, key=lambda r: r["finding_id"]):
        candidates, invalid = _plan_candidates(record["evidence"], record["mode"], digest, pages, spans)
        unique = {(a["page"], tuple(a["bbox_points"])): a for a in candidates}
        anchor = next(iter(unique.values())) if len(unique) == 1 and not invalid else None
        # A repeated underlying field is not independent source evidence.
        if len(unique) != len(candidates):
            anchor = None
        body = ("Mechanical result: " + record["state"] + " (bounded QA, not regulatory noncompliance).\n"
                "Finding: " + record["reason"] + "\n"
                "Observed: " + _preview(record["observed"]) + "\n"
                "Linked finding IDs: " + ", ".join(record["links"]))
        for label, value in record["details"].items():
            body += "\n" + label.title() + ": " + _preview(value, 300)
        for cid, state, reason in record["clause_results"]:
            body += "\nClause observation: " + state + " [" + cid + "]; " + reason
        context = _reference_context(record["evidence"])
        if context:
            body += "\nSource context: " + context + "; record page locations are not plan markers."
        if record["residual"]:
            body += "\nReview: " + record["residual"]
        else:
            body += "\nReview: Confirm the selected evidence, job scope and remaining visual or record obligations."
        notes.append({"finding_id": record["finding_id"], "kind": "QA_COMPARISON",
                      "title": "QA comparison: " + record["title"],
                      "body": _text(body, "Expanded note body", limit=MAX_BODY),
                      "citation": record["citation"],
                      "status": "REVIEW_REQUIRED", "source_status": "UNVERIFIED_CURRENT",
                      "anchor": deepcopy(anchor), "evidence_page": anchor["page"] if anchor else None,
                      "location_reason": "UNIQUE_SOURCE_SPAN" if anchor else "NO_SOURCE_LOCATION",
                      "linked_finding_ids": list(record["links"]), "mechanical_status": record["state"]})
    return notes
