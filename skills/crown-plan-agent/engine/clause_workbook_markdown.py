"""Validate and render the separate review-only dated-source clause workbook."""
from __future__ import annotations

from html import escape
import re

from clause_overrides import resolve_overrides
from clause_schema import ADAPTER_IDS, CONTEXT_FIELDS, validate_clause_catalogue
from clause_workbook import (ASSESSMENT_TYPE, SELECTIONS, STATE_FIELDS, _aggregate_fact_issues,
                             _aggregate_selection, _workbook_counts)
from requirements import application_context

TRUTHS = frozenset({"TRUE", "FALSE", "UNKNOWN"})
OPERATORS = frozenset({"const", "all", "any", "not", "eq", "in", "lt", "le", "gt", "ge"})
FACT_ISSUES = frozenset({"MISSING_FACT", "UNKNOWN_FACT", "INVALID_FACT_VALUE", "MISSING_PROVENANCE"})
EFFECTS = frozenset({"INACTIVE", "APPLIED", "UNRESOLVED", "POTENTIAL_OVERRIDE_CONFLICT", "CONFLICTING_OVERRIDES"})
REASONS = frozenset({"EXCLUDED_BY_OVERRIDE", "REPLACED_BY_OVERRIDE", "OVERRIDE_APPLICABILITY_UNRESOLVED",
                     "POTENTIAL_OVERRIDE_CONFLICT", "CONFLICTING_OVERRIDES", "CONDITION_FALSE"})
CLAUSE_FIELDS = {"id", "kind", "citation", "summary", "selection_status", "condition_trace",
                 "blocking_fact_ids", "fact_issues", "override_trace", "status", "source_status", "checks"}
CHECK_FIELDS = {"id", "kind", "citation", "selection_status", "condition_trace", "blocking_fact_ids",
                "fact_issues", "override_trace", "override_reason_codes", "questions", "review_requests",
                "pending_applicability_questions", "adapter_links", "observation_refs", "evidence_status",
                "status", "source_status"}


def _keys(value: object, keys: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(label + " has missing or unsupported fields")


def _text(value: object, label: str, limit: int = 4096) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(label + " must be bounded nonempty text")


def _enum(value: object, choices: frozenset | set, label: str) -> None:
    if not isinstance(value, str) or value not in choices:
        raise ValueError("Invalid " + label)


def _strings(value: object, label: str, *, unique: bool = True, limit: int = 4096) -> None:
    if not isinstance(value, list):
        raise ValueError(label + " must be a list")
    for item in value:
        _text(item, label, limit)
    if unique and len(value) != len(set(value)):
        raise ValueError(label + " must not contain duplicates")


def _issues(value: object, blockers: list[str]) -> None:
    if not isinstance(value, list):
        raise ValueError("Fact issues must be a list")
    seen = set()
    for issue in value:
        _keys(issue, {"fact_id", "code", "blocking"}, "Fact issue")
        _text(issue["fact_id"], "Fact issue ID", 128)
        _enum(issue["code"], FACT_ISSUES, "fact issue code")
        if type(issue["blocking"]) is not bool:
            raise ValueError("Invalid fact issue code or blocking flag")
        pair = (issue["fact_id"], issue["code"])
        if pair in seen:
            raise ValueError("Duplicate fact issue")
        seen.add(pair)
    if set(blockers) != {i["fact_id"] for i in value if i["blocking"]}:
        raise ValueError("Blocking fact IDs and issue flags disagree")


def _trace(value: object, max_nodes: int) -> set[str]:
    _keys(value, {"result", "nodes", "blocking_fact_ids", "fact_issues"}, "Condition trace")
    _strings(value["blocking_fact_ids"], "Trace blockers", limit=128)
    _issues(value["fact_issues"], value["blocking_fact_ids"])
    _enum(value["result"], TRUTHS | {"NOT_EVALUATED"}, "condition trace result")
    if not isinstance(value["nodes"], list) or len(value["nodes"]) > max_nodes:
        raise ValueError("Condition trace nodes exceed the contract")
    if value["result"] == "NOT_EVALUATED":
        if value["nodes"] or value["blocking_fact_ids"] or value["fact_issues"]:
            raise ValueError("Unevaluated trace must be empty")
        return set()
    if value["result"] not in TRUTHS or not value["nodes"]:
        raise ValueError("Invalid condition trace result")
    if value["result"] != "UNKNOWN" and value["blocking_fact_ids"]:
        raise ValueError("Known condition results cannot have blockers")
    if value["result"] == "UNKNOWN" and not value["blocking_fact_ids"]:
        raise ValueError("Unknown condition requires an unresolved operand")
    paths, references = set(), set()
    for node in value["nodes"]:
        _keys(node, {"path", "operator", "result", "operand"}, "Condition node")
        _text(node["path"], "Condition path")
        _enum(node["operator"], OPERATORS, "condition operator")
        _enum(node["result"], TRUTHS, "condition node result")
        if node["path"] in paths:
            raise ValueError("Invalid condition node path, operator or result")
        paths.add(node["path"])
        if node["operator"] in {"const", "all", "any", "not"}:
            if node["operand"] is not None:
                raise ValueError("Logical condition nodes cannot claim an operand")
        else:
            operand = node["operand"]
            _keys(operand, {"origin", "id"}, "Condition operand")
            _text(operand["id"], "Condition operand ID", 128)
            if operand["origin"] == "context":
                if operand["id"] not in CONTEXT_FIELDS:
                    raise ValueError("Unknown context operand")
                references.add("context:" + operand["id"])
            elif operand["origin"] == "fact":
                references.add(operand["id"])
            else:
                raise ValueError("Unknown condition operand origin")
    if value["nodes"][0]["path"] != "$" or value["nodes"][0]["result"] != value["result"]:
        raise ValueError("Condition root and trace result disagree")
    if any(issue["fact_id"] not in references for issue in value["fact_issues"]):
        raise ValueError("Fact issue has no referenced condition operand")
    return references


def _override_list(value: object, clauses: dict, checks: dict) -> None:
    if not isinstance(value, list) or len(value) > 5000:
        raise ValueError("Override trace must be a bounded list")
    for event in value:
        _keys(event, {"by_clause_id", "citation", "action", "targets", "condition_result", "effect"}, "Override event")
        _text(event["by_clause_id"], "Override controller ID", 128)
        if event["by_clause_id"] not in clauses:
            raise ValueError("Unknown override controller")
        controller = clauses[event["by_clause_id"]]
        if event["citation"] != controller["citation"]:
            raise ValueError("Override citation does not match its controller")
        _strings(event["targets"], "Override targets", limit=128)
        if not event["targets"] or any(target not in checks for target in event["targets"]):
            raise ValueError("Unknown or absent override target")
        _enum(event["action"], {"exclude", "replace"}, "override action")
        _enum(event["condition_result"], TRUTHS, "override condition")
        _enum(event["effect"], EFFECTS, "override effect")
        if event["condition_result"] != controller["condition_trace"]["result"]:
            raise ValueError("Override truth does not match its clause condition")
        if event["condition_result"] == "FALSE" and event["effect"] != "INACTIVE":
            raise ValueError("False override cannot execute")


def _event_identity(event: dict) -> tuple:
    return (event["by_clause_id"], event["action"], tuple(event["targets"]), event["condition_result"])


def _validate_workbook(workbook: object) -> None:
    _keys(workbook, {"assessment_type", "catalogue_id", "source", "context", "context_issues", "clauses",
                     "counts", "coverage", "overall_status", "source_status"}, "Workbook")
    if (workbook["assessment_type"] != ASSESSMENT_TYPE or workbook["overall_status"] != "REVIEW_REQUIRED"
            or workbook["source_status"] != "UNVERIFIED_CURRENT"):
        raise ValueError("Only unverified review-only workbooks can be rendered")
    _text(workbook["catalogue_id"], "Catalogue ID", 128)
    context = workbook["context"]
    _keys(context, set(CONTEXT_FIELDS), "Context")
    for name, value in context.items():
        if value is not None:
            _text(value, "Context " + name)
    _enum(context["scope_status"], {"IN_SCOPE", "OUT_OF_SCOPE", "UNRESOLVED_SCOPE"}, "declared scope")
    _strings(workbook["context_issues"], "Context issues")
    allowed_fields = CONTEXT_FIELDS - {"scope_status"}
    for issue in workbook["context_issues"]:
        prefix, separator, field = issue.partition(":")
        if not separator or prefix not in {"MISSING_CONTEXT", "INVALID_CONTEXT", "OUT_OF_SCOPE"} or field not in allowed_fields:
            raise ValueError("Invalid context issue")
    normalized = application_context(context)
    if normalized["scope_status"] != context["scope_status"]:
        raise ValueError("Declared scope and context disagree")
    if context["scope_status"] == "OUT_OF_SCOPE":
        gate = "OUT_OF_SCOPE"
        if workbook["context_issues"] != ["OUT_OF_SCOPE:land_class"]:
            raise ValueError("Outside scope must be recorded explicitly")
    elif workbook["context_issues"] or context["scope_status"] != "IN_SCOPE":
        gate = "UNRESOLVED_APPLICABILITY"
        if not workbook["context_issues"] or any(i.startswith("OUT_OF_SCOPE:") for i in workbook["context_issues"]):
            raise ValueError("Unresolved context needs its own issue record")
        unresolved_fields = set(normalized["missing_dimensions"] + normalized["invalid_dimensions"])
        if {issue.partition(":")[2] for issue in workbook["context_issues"]} != unresolved_fields:
            raise ValueError("Context issues must identify the genuinely unresolved fields")
    else:
        gate = None
        if normalized["missing_dimensions"] or normalized["invalid_dimensions"]:
            raise ValueError("Missing context cannot activate review paths")
    clauses_list = workbook["clauses"]
    if not isinstance(clauses_list, list) or len(clauses_list) > 500:
        raise ValueError("Clause records must be a bounded list")
    clauses, checks, references = {}, {}, set()
    for clause in clauses_list:
        _keys(clause, CLAUSE_FIELDS, "Clause")
        _text(clause["id"], "Clause ID", 128)
        if clause["id"] in clauses:
            raise ValueError("Duplicate clause ID")
        clauses[clause["id"]] = clause
        if not isinstance(clause["checks"], list) or not clause["checks"]:
            raise ValueError("A clause must retain its atomic checks")
        references.update(_trace(clause["condition_trace"], 256))
        for check in clause["checks"]:
            _keys(check, CHECK_FIELDS, "Check")
            _text(check["id"], "Check ID", 128)
            if check["id"] in checks or len(checks) >= 5000:
                raise ValueError("Duplicate or excessive check IDs")
            checks[check["id"]] = check
            if check["citation"] != clause["citation"]:
                raise ValueError("Check citation must identify its owning clause")
            references.update(_trace(check["condition_trace"], 513))
    # Reuse input-schema validation for source metadata, IDs, kinds, citations,
    # question types, adapter registry, bounds and the override reference graph.
    shell = {"schema_version": 1, "catalogue_id": workbook["catalogue_id"],
             "source_status": "UNVERIFIED_CURRENT", "source": workbook["source"], "facts": [], "clauses": []}
    # Placeholder definitions establish only the trace's identifier namespace.
    # No original facts or predicates are reconstructed or evaluated here.
    fact_ids = {node["operand"]["id"] for item in [*clauses_list, *checks.values()]
                for node in item["condition_trace"]["nodes"]
                if node["operand"] and node["operand"]["origin"] == "fact"}
    shell["facts"] = [{"id": ident, "type": "boolean", "unit": None, "minimum": None,
                       "maximum": None, "allowed_values": None, "provenance_required": False,
                       "purpose": "applicability"} for ident in sorted(fact_ids)]
    identities = set()
    for clause in clauses_list:
        _override_list(clause["override_trace"], clauses, checks)
        for event in clause["override_trace"]:
            identity = _event_identity(event)
            if event["by_clause_id"] != clause["id"] or identity in identities:
                raise ValueError("Controller decisions must be unique and owned by their clause")
            identities.add(identity)
        shell["clauses"].append({"id": clause["id"], "kind": clause["kind"], "citation": clause["citation"],
                                  "summary": clause["summary"], "when": {"const": True},
                                  "checks": [{"id": c["id"], "kind": c["kind"], "when": {"const": True},
                                              "questions": c["questions"], "adapter_links": c["adapter_links"]} for c in clause["checks"]],
                                  "overrides": [{"action": e["action"], "targets": e["targets"]} for e in clause["override_trace"]]})
    validate_clause_catalogue(shell)
    if gate is None:
        replayed = resolve_overrides(shell, {i: c["condition_trace"] for i, c in clauses.items()},
                                     {i: c["condition_trace"] for i, c in checks.items()})
        decisions = [event for clause in clauses_list for event in clause["override_trace"]]
        if decisions != replayed["override_decisions"]:
            raise ValueError("Controller decisions disagree with retained conditions")
        for ident, check in checks.items():
            if any(check[key] != replayed["checks"][ident][key] for key in STATE_FIELDS):
                raise ValueError("Check selection or override trace disagrees with its conditions")
    for clause in clauses_list:
        for item in [clause, *clause["checks"]]:
            if item["status"] != "REVIEW_REQUIRED" or item["source_status"] != "UNVERIFIED_CURRENT":
                raise ValueError("Nested status must remain unverified and review-only")
            _enum(item["selection_status"], SELECTIONS, "selection status")
            _strings(item["blocking_fact_ids"], "Blocking facts", limit=128)
            _issues(item["fact_issues"], item["blocking_fact_ids"])
            if any(issue["fact_id"] not in references for issue in item["fact_issues"]):
                raise ValueError("Unknown fact issue reference")
            if item["selection_status"] != "UNRESOLVED_APPLICABILITY" and item["blocking_fact_ids"]:
                raise ValueError("Known selection has no unresolved blockers")
            if gate is not None:
                if (item["selection_status"] != gate or item["condition_trace"]["result"] != "NOT_EVALUATED"
                        or item["override_trace"] or item["blocking_fact_ids"] or item["fact_issues"]):
                    raise ValueError("Context gate cannot evaluate or activate nested paths")
            elif item["selection_status"] == "OUT_OF_SCOPE" or item["condition_trace"]["result"] == "NOT_EVALUATED":
                raise ValueError("In-scope paths require evaluated conditions")
        if gate is None and clause["selection_status"] != _aggregate_selection(clause["checks"]):
            raise ValueError("Clause and child selection disagree")
        blockers = sorted({i for c in clause["checks"] if c["selection_status"] == "UNRESOLVED_APPLICABILITY" for i in c["blocking_fact_ids"]})
        if clause["blocking_fact_ids"] != blockers:
            raise ValueError("Clause blockers must aggregate unresolved child checks")
        if clause["fact_issues"] != _aggregate_fact_issues(clause["checks"], blockers):
            raise ValueError("Clause fact issues must aggregate child checks")
        for check in clause["checks"]:
            selected = check["selection_status"] == "CANDIDATE_REVIEW"
            pending = check["selection_status"] == "UNRESOLVED_APPLICABILITY"
            _strings(check["review_requests"], "Review requests", unique=False)
            _strings(check["pending_applicability_questions"], "Pending questions", unique=False)
            if (check["review_requests"] != (check["questions"] if selected else [])
                    or check["pending_applicability_questions"] != (check["questions"] if pending else [])):
                raise ValueError("Questions must remain separated from active review requests")
            _strings(check["observation_refs"], "Observation references", limit=128)
            if any(i not in ADAPTER_IDS or i not in check["adapter_links"] for i in check["observation_refs"]):
                raise ValueError("Observation references require declared known adapter links")
            evidence = ("OBSERVATION_CANDIDATE_AVAILABLE" if check["observation_refs"] else
                        "MANUAL_REVIEW_REQUIRED" if selected else "NOT_EVALUATED")
            if check["evidence_status"] != evidence or (not selected and check["observation_refs"]):
                raise ValueError("Observation availability cannot activate or satisfy a check")
            _strings(check["override_reason_codes"], "Override reasons")
            if any(reason not in REASONS for reason in check["override_reason_codes"]):
                raise ValueError("Unknown override reason")
            _override_list(check["override_trace"], clauses, checks)
            if any(_event_identity(e) not in identities for e in check["override_trace"]):
                raise ValueError("Check override trace lacks a controller decision")
            if gate is not None and check["override_reason_codes"]:
                raise ValueError("Context gate cannot resolve overrides")
            if selected and check["condition_trace"]["result"] != "TRUE":
                raise ValueError("Only a true effective condition can select a review request")
            if (gate is None and pending and check["condition_trace"]["result"] != "UNKNOWN"
                    and not check["override_reason_codes"]):
                raise ValueError("Unresolved selection requires a condition or override reason")
    _keys(workbook["counts"], set(_workbook_counts(clauses_list)), "Counts")
    if any(type(value) is not int or value < 0 for value in workbook["counts"].values()):
        raise ValueError("Counts must be nonnegative integers")
    if workbook["counts"] != _workbook_counts(clauses_list):
        raise ValueError("Workbook counts disagree with its clause/check records")
    coverage = workbook["coverage"]
    _keys(coverage, {"universe_status", "expected_clause_count", "unmapped_clause_ids", "atomic_obligation_completeness"}, "Coverage")
    if coverage["atomic_obligation_completeness"] != "NOT_ASSESSED":
        raise ValueError("Clause paths do not establish atomic completeness")
    if coverage["universe_status"] == "NOT_SUPPLIED":
        if coverage["expected_clause_count"] is not None or coverage["unmapped_clause_ids"] is not None:
            raise ValueError("An absent inventory cannot establish a universe")
    elif coverage["universe_status"] == "MATCHED":
        _strings(coverage["unmapped_clause_ids"], "Unmapped clauses", limit=128)
        if (type(coverage["expected_clause_count"]) is not int
                or coverage["expected_clause_count"] != len(clauses) + len(coverage["unmapped_clause_ids"])
                or any(not re.fullmatch(r"[0-9]+(?:\.[0-9]+)+", i) or i in clauses for i in coverage["unmapped_clause_ids"])):
            raise ValueError("Explicit inventory counts or unmapped IDs disagree")
    else:
        raise ValueError("Unknown source-universe status")


def _safe(value: object) -> str:
    text = escape(str(value), quote=False).replace("\r", " ").replace("\n", " ")
    for char in "\\`*_{}[]|#":
        text = text.replace(char, "\\" + char)
    return text


def _condition_lines(record: dict) -> list[str]:
    lines = ["Condition result: " + record["condition_trace"]["result"]]
    operands = [node for node in record["condition_trace"]["nodes"] if node["operand"]]
    if operands:
        lines.append("")
    for node in operands:
        operand = node["operand"]
        lines.append("- " + _safe(operand["origin"] + ":" + operand["id"]) + " "
                     + node["operator"] + " → " + node["result"])
    if record["blocking_fact_ids"]:
        lines += ["", "Blocking facts: " + ", ".join(_safe(i) for i in record["blocking_fact_ids"])]
    if record["fact_issues"]:
        lines.append("")
    for issue in record["fact_issues"]:
        lines.append("- Fact issue: " + _safe(issue["fact_id"]) + " — " + issue["code"]
                     + (" (blocking)" if issue["blocking"] else " (nonblocking)"))
    return lines


def render_clause_workbook(workbook: dict) -> str:
    """Render only structurally consistent, unverified review workbooks."""
    _validate_workbook(workbook)
    source = workbook["source"]
    lines = ["## Dated-source clause workbook", "",
             "**Status: REVIEW_REQUIRED. Source status: UNVERIFIED_CURRENT. This is not a compliance determination.**", "",
             "Catalogue: " + _safe(workbook["catalogue_id"]),
             "Selected source: " + _safe(source["title"]) + " — " + _safe(source["version_date"]),
             "Source classification: " + source["classification"], "Source URL: " + _safe(source["url"]),
             "Scope: " + workbook["context"]["scope_status"],
             "Only this explicitly selected publication/edition is represented. Current authority and atomic obligation completeness remain unverified.",
             "No adapters were executed by this workbook. Caller-declared observation references are assertions, not execution or satisfaction evidence.", ""]
    lines += ["### Declared review context", "", "| Field | Declared value |", "| --- | --- |"]
    lines.extend("| " + field + " | " + _safe(value if value is not None else "not declared") + " |"
                 for field, value in workbook["context"].items())
    lines.append("")
    if workbook["context_issues"]:
        lines += ["Context issues: " + ", ".join(_safe(i) for i in workbook["context_issues"]), ""]
    lines += ["### Workbook counts", "", "| Count | Value |", "| --- | ---: |"]
    lines.extend("| " + name + " | " + str(value) + " |" for name, value in workbook["counts"].items())
    coverage = workbook["coverage"]
    lines += ["", "Universe: " + coverage["universe_status"],
              "Expected clauses: " + (str(coverage["expected_clause_count"]) if coverage["expected_clause_count"] is not None else "unknown"),
              "Unmapped clause IDs: " + (", ".join(_safe(i) for i in coverage["unmapped_clause_ids"]) or "none" if coverage["unmapped_clause_ids"] is not None else "unknown"),
              "Atomic obligation completeness: NOT_ASSESSED", ""]
    for clause in workbook["clauses"]:
        lines += ["", "### Clause " + _safe(clause["id"]) + " — " + _safe(clause["summary"]), "",
                  "Selection: " + clause["selection_status"] + "; kind: " + clause["kind"],
                  "Citation: section " + _safe(clause["citation"]["section"]) + ", PDF page " + str(clause["citation"]["page"])]
        lines += _condition_lines(clause)
        if clause["override_trace"]:
            lines += ["", "Controller decisions:", ""]
        for event in clause["override_trace"]:
            lines.append("- Override " + event["action"] + " → " + ", ".join(_safe(i) for i in event["targets"])
                         + ": " + event["condition_result"] + " / " + event["effect"])
        for check in clause["checks"]:
            lines += ["", "#### Check " + _safe(check["id"]), "",
                      "Selection: " + check["selection_status"] + "; kind: " + check["kind"],
                      "Evidence: " + check["evidence_status"]]
            lines += _condition_lines(check)
            if check["override_reason_codes"]:
                lines += ["", "Override reasons: " + ", ".join(check["override_reason_codes"])]
            if check["override_trace"]:
                lines.append("")
            for event in check["override_trace"]:
                lines.append("- Override source: clause " + _safe(event["by_clause_id"]) + ", section "
                             + _safe(event["citation"]["section"]) + ", PDF page " + str(event["citation"]["page"])
                             + " — " + event["action"] + " / " + event["effect"])
            if check["review_requests"]:
                label = ("Guidance review (absence is not a missing mandatory element)" if check["kind"] in {"optional", "permission"}
                         else "Exemption control review" if check["kind"] == "exemption" else "Manual review requests")
                lines += ["", label + ":", ""]
                lines.extend("- " + _safe(q) for q in check["review_requests"])
            elif check["pending_applicability_questions"]:
                lines += ["", "Questions pending applicability (not active review requests):", ""]
                lines.extend("- " + _safe(q) for q in check["pending_applicability_questions"])
            else:
                lines += ["", "Reference questions (not requested):", ""]
                lines.extend("- " + _safe(q) for q in check["questions"])
            if check["observation_refs"]:
                lines += ["", "Caller-declared observation references: " + ", ".join(_safe(i) for i in check["observation_refs"])]
    return "\n".join(lines) + "\n"
