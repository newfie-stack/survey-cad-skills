"""Resolve cited clause exclusions/replacements before evidence review."""
from __future__ import annotations

from copy import deepcopy

from clause_conditions import ISSUE_CODES, RESULTS
from clause_schema import CONTEXT_FIELDS, validate_clause_catalogue

OPERATORS = frozenset({"const", "all", "any", "not", "eq", "in", "lt", "le", "gt", "ge"})
EFFECT_RANK = {"INACTIVE": 0, "APPLIED": 1, "UNRESOLVED": 2,
               "POTENTIAL_OVERRIDE_CONFLICT": 3, "CONFLICTING_OVERRIDES": 4}
SELECTION = {"TRUE": "CANDIDATE_REVIEW", "FALSE": "NOT_SELECTED_FOR_REVIEW",
             "UNKNOWN": "UNRESOLVED_APPLICABILITY"}


def _fact_id(ident: object, facts: set[str]) -> bool:
    return (isinstance(ident, str) and (ident in facts
            or ident.startswith("context:") and ident[8:] in CONTEXT_FIELDS))


def _validate_trace(trace: object, facts: set[str], *, max_nodes: int, max_depth: int) -> None:
    if (not isinstance(trace, dict) or set(trace) != {
            "result", "nodes", "blocking_fact_ids", "fact_issues"}
            or not isinstance(trace["result"], str) or trace["result"] not in RESULTS):
        raise ValueError("A pre-override condition trace must have a three-valued result")
    nodes = trace["nodes"]
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= max_nodes:
        raise ValueError("Invalid bounded condition nodes")
    paths = set()
    for node in nodes:
        if not isinstance(node, dict) or set(node) != {"path", "operator", "result", "operand"}:
            raise ValueError("Invalid condition node shape")
        path, operator, result, operand = (node[key] for key in ("path", "operator", "result", "operand"))
        if (not isinstance(path, str) or not path or len(path) > 4096 or path in paths
                or not isinstance(operator, str) or operator not in OPERATORS
                or not isinstance(result, str) or result not in RESULTS):
            raise ValueError("Invalid condition node")
        paths.add(path)
        if operator in {"const", "all", "any", "not"}:
            if operand is not None or operator == "const" and result == "UNKNOWN":
                raise ValueError("Invalid logical condition node")
        elif (not isinstance(operand, dict) or set(operand) != {"origin", "id"}
              or not isinstance(operand["origin"], str) or operand["origin"] not in {"fact", "context"}
              or not isinstance(operand["id"], str)
              or operand["id"] not in (facts if operand["origin"] == "fact" else CONTEXT_FIELDS)):
            raise ValueError("Invalid condition operand")
    if nodes[0]["path"] != "$" or nodes[0]["result"] != trace["result"]:
        raise ValueError("Root node and trace result disagree")
    # Check only the retained logical tree. Comparison results remain declared
    # assertions; original predicates, literals and fact values are not replayed.
    cursor = 0
    unknown_operands, knownness = set(), {}

    def visit(path: str, depth: int) -> tuple[str, set[str]]:
        nonlocal cursor
        if depth > max_depth or cursor >= len(nodes) or nodes[cursor]["path"] != path:
            raise ValueError("Condition paths do not form the bounded preorder tree")
        node = nodes[cursor]
        cursor += 1
        operator, result = node["operator"], node["result"]
        if operator == "not":
            child, blockers = visit(path + ".not", depth + 1)
            expected = {"TRUE": "FALSE", "FALSE": "TRUE", "UNKNOWN": "UNKNOWN"}[child]
        elif operator in {"all", "any"}:
            children = []
            while cursor < len(nodes) and nodes[cursor]["path"] == f"{path}.{operator}[{len(children)}]":
                children.append(visit(f"{path}.{operator}[{len(children)}]", depth + 1))
            if not children:
                raise ValueError("Logical trace nodes require nonempty sequential children")
            states = [value for value, _ in children]
            if operator == "all":
                expected = "FALSE" if "FALSE" in states else "UNKNOWN" if "UNKNOWN" in states else "TRUE"
            else:
                expected = "TRUE" if "TRUE" in states else "UNKNOWN" if "UNKNOWN" in states else "FALSE"
            blockers = ({ident for state, ids in children if state == "UNKNOWN" for ident in ids}
                        if expected == "UNKNOWN" else set())
        else:
            expected, blockers = result, set()
            if operator != "const":
                operand = node["operand"]
                ident = ("context:" if operand["origin"] == "context" else "") + operand["id"]
                known = result != "UNKNOWN"
                if ident in knownness and knownness[ident] != known:
                    raise ValueError("An operand cannot be both known and unknown in one trace")
                knownness[ident] = known
                if not known:
                    unknown_operands.add(ident)
                    blockers.add(ident)
        if result != expected:
            raise ValueError("Logical trace result disagrees with its retained children")
        return expected, blockers

    _, derived_blockers = visit("$", 1)
    if cursor != len(nodes):
        raise ValueError("Condition trace contains orphan nodes")
    blockers = trace["blocking_fact_ids"]
    if (not isinstance(blockers, list) or not all(_fact_id(ident, facts) for ident in blockers)
            or blockers != sorted(set(blockers))):
        raise ValueError("Invalid blocking fact IDs")
    if trace["result"] != "UNKNOWN" and blockers:
        raise ValueError("Known conditions cannot have blocking facts")
    if trace["result"] == "UNKNOWN" and not blockers:
        raise ValueError("Unknown pre-override conditions require unresolved operands")
    if set(blockers) != derived_blockers:
        raise ValueError("Trace blockers do not follow its unknown operands")
    issues = trace["fact_issues"]
    if not isinstance(issues, list):
        raise ValueError("Invalid fact issue list")
    seen = set()
    for issue in issues:
        if (not isinstance(issue, dict) or set(issue) != {"fact_id", "code", "blocking"}
                or not _fact_id(issue["fact_id"], facts) or issue["fact_id"] in seen
                or not isinstance(issue["code"], str) or issue["code"] not in ISSUE_CODES
                or type(issue["blocking"]) is not bool
                or issue["blocking"] != (issue["fact_id"] in blockers)):
            raise ValueError("Invalid condition fact issue")
        seen.add(issue["fact_id"])
    if not set(blockers) <= seen:
        raise ValueError("Every blocker requires a fact issue")
    if seen != unknown_operands:
        raise ValueError("Fact issues must describe every unknown comparison operand")


def _issues(records: list[dict], blockers: set[str]) -> list[dict]:
    merged = {}
    for record in records:
        for issue in record["fact_issues"]:
            ident = issue["fact_id"]
            if ident in merged and merged[ident] != issue["code"]:
                raise ValueError("Contradictory primary issues for the same fact")
            merged[ident] = issue["code"]
    return [{"fact_id": ident, "code": merged[ident], "blocking": ident in blockers}
            for ident in sorted(merged)]


def resolve_overrides(catalogue: dict, clause_results: dict, check_results: dict) -> dict:
    """Return review selection and cited traces without changing input records.

    Scope/context gates precede this API. Controllers use clause.when alone;
    missing replacement observations or child conditions never restore old paths.
    """
    validate_clause_catalogue(catalogue)
    if not isinstance(clause_results, dict) or not isinstance(check_results, dict):
        raise TypeError("Condition results must be objects")
    clauses = catalogue["clauses"]
    facts = {fact["id"] for fact in catalogue["facts"]}
    expected_clauses = {clause["id"] for clause in clauses}
    expected_checks = {check["id"] for clause in clauses for check in clause["checks"]}
    if set(clause_results) != expected_clauses or set(check_results) != expected_checks:
        raise ValueError("Condition result IDs must match the selected catalogue exactly")
    for trace in clause_results.values():
        _validate_trace(trace, facts, max_nodes=256, max_depth=16)
    for trace in check_results.values():
        _validate_trace(trace, facts, max_nodes=513, max_depth=17)
    # The same declared fact cannot acquire a different primary issue by branch.
    _issues([*clause_results.values(), *check_results.values()], set())
    checks = {ident: {"selection_status": SELECTION[trace["result"]],
                      "condition_trace": deepcopy(trace),
                      "blocking_fact_ids": list(trace["blocking_fact_ids"]),
                      "fact_issues": deepcopy(trace["fact_issues"]),
                      "override_trace": [], "override_reason_codes": []}
              for ident, trace in check_results.items()}
    controllers, incoming = [], {}
    for clause in clauses:
        for override in clause["overrides"]:
            truth = clause_results[clause["id"]]["result"]
            effect = {"TRUE": "APPLIED", "FALSE": "INACTIVE", "UNKNOWN": "UNRESOLVED"}[truth]
            controller = {"record": {"by_clause_id": clause["id"],
                                     "citation": deepcopy(clause["citation"]),
                                     "action": override["action"],
                                     "targets": list(override["targets"]),
                                     "condition_result": truth, "effect": effect},
                          "trace": clause_results[clause["id"]],
                          "providers": [check["id"] for check in clause["checks"]]
                                       if override["action"] == "replace" else []}
            index = len(controllers)
            controllers.append(controller)
            for ident in override["targets"]:
                incoming.setdefault(ident, []).append(index)
    trace_effects = {ident: {} for ident in checks}

    def attach(ident: str, indexes: list[int], effects: dict[int, str]) -> None:
        for index in indexes:
            effect = effects[index]
            previous = trace_effects[ident].get(index, "INACTIVE")
            if EFFECT_RANK[effect] >= EFFECT_RANK[previous]:
                trace_effects[ident][index] = effect
            record = controllers[index]["record"]
            if EFFECT_RANK[effect] > EFFECT_RANK[record["effect"]]:
                record["effect"] = effect

    def update(ident: str, status: str, reason: str, indexes: list[int]) -> None:
        item = checks[ident]
        records = [item, *(controllers[index]["trace"] for index in indexes)]
        blockers = ({fact for record in records for fact in record["blocking_fact_ids"]}
                    if status == "UNRESOLVED_APPLICABILITY" else set())
        item["selection_status"] = status
        item["blocking_fact_ids"] = sorted(blockers)
        item["fact_issues"] = _issues(records, blockers)
        item["override_reason_codes"] = sorted(set(item["override_reason_codes"]) | {reason})

    for ident, indexes in incoming.items():
        active = [index for index in indexes
                  if controllers[index]["record"]["condition_result"] != "FALSE"]
        replacements = [index for index in active if controllers[index]["record"]["action"] == "replace"]
        exclusions = [index for index in active if controllers[index]["record"]["action"] == "exclude"]
        true_replacements = [index for index in replacements
                             if controllers[index]["record"]["condition_result"] == "TRUE"]
        true_exclusions = [index for index in exclusions
                           if controllers[index]["record"]["condition_result"] == "TRUE"]
        conflict = len(replacements) > 1 or bool(replacements and exclusions)
        if conflict:
            confirmed = len(true_replacements) > 1 or bool(true_replacements and true_exclusions)
            reason = "CONFLICTING_OVERRIDES" if confirmed else "POTENTIAL_OVERRIDE_CONFLICT"
            effects = {index: reason if index in active else "INACTIVE" for index in indexes}
            if check_results[ident]["result"] != "FALSE":
                update(ident, "UNRESOLVED_APPLICABILITY", reason, active)
            else:
                update(ident, "NOT_SELECTED_FOR_REVIEW", "CONDITION_FALSE", active)
            # Every replacement provider is pending while competing source paths
            # remain possible, even when the old target is independently false.
            for index in replacements:
                for provider in controllers[index]["providers"]:
                    update(provider, "UNRESOLVED_APPLICABILITY", reason, active)
                    attach(provider, active, effects)
        else:
            effects = {index: ({"TRUE": "APPLIED", "FALSE": "INACTIVE", "UNKNOWN": "UNRESOLVED"}[
                controllers[index]["record"]["condition_result"]]) for index in indexes}
            if active and check_results[ident]["result"] == "FALSE":
                update(ident, "NOT_SELECTED_FOR_REVIEW", "CONDITION_FALSE", active)
            elif true_exclusions:
                update(ident, "NOT_SELECTED_FOR_REVIEW", "EXCLUDED_BY_OVERRIDE", active)
            elif true_replacements:
                update(ident, "NOT_SELECTED_FOR_REVIEW", "REPLACED_BY_OVERRIDE", active)
            elif active:
                update(ident, "UNRESOLVED_APPLICABILITY", "OVERRIDE_APPLICABILITY_UNRESOLVED", active)
        attach(ident, indexes, effects)
    for ident, item in checks.items():
        for index in sorted(trace_effects[ident]):
            record = deepcopy(controllers[index]["record"])
            record["effect"] = trace_effects[ident][index]
            item["override_trace"].append(record)
    return {"checks": checks, "override_decisions": [deepcopy(controller["record"])
                                                     for controller in controllers]}
