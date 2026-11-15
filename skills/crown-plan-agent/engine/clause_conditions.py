"""Typed three-valued conditions for a selected dated-source workbook.

These helpers evaluate declared facts, not plan compliance or source currency.
No condition executes adapters, interprets prose or discovers external evidence.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

from clause_schema import (is_valid_fact_value, validate_clause_catalogue, validate_fact_definitions,
                           validate_predicate)

RESULTS = frozenset({"TRUE", "FALSE", "UNKNOWN"})
ISSUE_CODES = frozenset({"MISSING_FACT", "UNKNOWN_FACT", "INVALID_FACT_VALUE",
                         "MISSING_PROVENANCE"})


def prepare_fact_values(definitions: list[dict], facts: dict) -> dict:
    """Validate record shapes and retain one primary issue per unknown fact.

    Prepared values are internal typed records. Decimal input strings become
    Decimal values; neither their values nor provenance are copied into traces.
    """
    if not isinstance(definitions, list) or not isinstance(facts, dict):
        raise TypeError("Fact definitions must be a list and facts an object")
    by_id = {}
    for definition in definitions:
        if not isinstance(definition, dict) or not isinstance(definition.get("id"), str):
            raise ValueError("Fact definitions require string IDs")
        ident = definition["id"]
        if ident in by_id:
            raise ValueError("Fact definition IDs must be unique")
        by_id[ident] = definition
    validate_fact_definitions(by_id)
    if any(ident not in by_id for ident in facts):
        raise ValueError("Undeclared fact ID")
    for record in facts.values():
        if not isinstance(record, dict) or set(record) != {"value", "provenance"}:
            raise ValueError("Fact records require exactly value and provenance")
        provenance = record["provenance"]
        if provenance is not None:
            if not isinstance(provenance, dict) or set(provenance) != {"source_id", "locator"}:
                raise ValueError("Invalid fact provenance shape")
            if any(not isinstance(value, str) or not value.strip() or len(value) > 4096
                   for value in provenance.values()):
                raise ValueError("Provenance requires bounded nonempty source_id and locator")
    prepared = {}
    for ident, definition in by_id.items():
        issue = None
        if ident not in facts:
            issue = "MISSING_FACT"
        elif facts[ident]["value"] is None:
            issue = "UNKNOWN_FACT"
        elif not is_valid_fact_value(definition, facts[ident]["value"]):
            issue = "INVALID_FACT_VALUE"
        elif definition["provenance_required"] and facts[ident]["provenance"] is None:
            issue = "MISSING_PROVENANCE"
        value = None if issue else facts[ident]["value"]
        if issue is None and definition["type"] == "decimal":
            value = Decimal(value)
        prepared[ident] = {"known": issue is None, "value": value,
                           "issue": {"fact_id": ident, "code": issue} if issue else None,
                           "definition": deepcopy(definition)}
    return prepared


def _validate_prepared(prepared: dict) -> dict:
    if not isinstance(prepared, dict):
        raise TypeError("Prepared facts must be an object")
    definitions = {}
    for ident, record in prepared.items():
        if not isinstance(record, dict) or set(record) != {"known", "value", "issue", "definition"}:
            raise ValueError("Invalid prepared fact shape")
        if type(record["known"]) is not bool:
            raise ValueError("Prepared known must be an explicit boolean")
        definitions[ident] = record["definition"]
    validate_fact_definitions(definitions)
    for ident, record in prepared.items():
        definition = definitions[ident]
        if record["known"] is True:
            value = record["value"]
            if definition["type"] == "decimal":
                if (not isinstance(value, Decimal) or not value.is_finite()
                        or len(value.as_tuple().digits) > 50
                        or abs(value.as_tuple().exponent) > 50):
                    raise ValueError("Invalid prepared decimal")
                value = format(value, "f")
            if record["issue"] is not None or not is_valid_fact_value(definition, value):
                raise ValueError("Invalid known prepared fact")
        else:
            issue = record["issue"]
            if (record["value"] is not None or not isinstance(issue, dict)
                    or set(issue) != {"fact_id", "code"} or issue["fact_id"] != ident
                    or not isinstance(issue["code"], str) or issue["code"] not in ISSUE_CODES):
                raise ValueError("Unknown prepared fact requires one valid issue")
    return definitions


def _trace(result: str, nodes: list[dict], issues: dict[str, dict], blockers: set[str]) -> dict:
    return {"result": result, "nodes": nodes, "blocking_fact_ids": sorted(blockers),
            "fact_issues": [{**issues[ident], "blocking": ident in blockers}
                            for ident in sorted(issues)]}


def _combine(operator: str, children: list[dict], path: str) -> dict:
    states = [child["result"] for child in children]
    if operator == "all":
        result = "FALSE" if "FALSE" in states else "UNKNOWN" if "UNKNOWN" in states else "TRUE"
    else:
        result = "TRUE" if "TRUE" in states else "UNKNOWN" if "UNKNOWN" in states else "FALSE"
    issues = {issue["fact_id"]: {"fact_id": issue["fact_id"], "code": issue["code"]}
              for child in children for issue in child["fact_issues"]}
    blockers = ({ident for child in children if child["result"] == "UNKNOWN"
                 for ident in child["blocking_fact_ids"]} if result == "UNKNOWN" else set())
    nodes = [{"path": path, "operator": operator, "result": result, "operand": None}]
    nodes.extend(node for child in children for node in child["nodes"])
    return _trace(result, nodes, issues, blockers)


def _evaluate(predicate: dict, context: dict, prepared: dict, path: str) -> dict:
    operator, body = next(iter(predicate.items()))
    if operator == "const":
        result = "TRUE" if body is True else "FALSE"
        return _trace(result, [{"path": path, "operator": operator,
                               "result": result, "operand": None}], {}, set())
    if operator in {"all", "any"}:
        children = [_evaluate(child, context, prepared, f"{path}.{operator}[{index}]")
                    for index, child in enumerate(body)]
        return _combine(operator, children, path)
    if operator == "not":
        child = _evaluate(body, context, prepared, path + ".not")
        result = {"TRUE": "FALSE", "FALSE": "TRUE", "UNKNOWN": "UNKNOWN"}[child["result"]]
        return {**child, "result": result, "nodes": [
            {"path": path, "operator": "not", "result": result, "operand": None},
            *child["nodes"]]}
    origin = "fact" if "fact" in body else "context"
    ident = body[origin]
    issue = None
    if origin == "fact":
        record = prepared[ident]
        value = record["value"]
        issue = record["issue"]
        kind = record["definition"]["type"]
    else:
        value = context.get(ident)
        kind = "enum"
        code = ("MISSING_FACT" if ident not in context else "UNKNOWN_FACT" if value is None
                else "INVALID_FACT_VALUE" if not isinstance(value, str) or not value.strip() else None)
        if code:
            issue = {"fact_id": "context:" + ident, "code": code}
    if issue is not None:
        result = "UNKNOWN"
        issues, blockers = {issue["fact_id"]: issue}, {issue["fact_id"]}
    else:
        literal = body["values"] if operator == "in" else body["value"]
        if kind == "decimal":
            literal = [Decimal(item) for item in literal] if operator == "in" else Decimal(literal)
        if operator == "eq":
            matched = value == literal
        elif operator == "in":
            matched = value in literal
        elif operator == "lt":
            matched = value < literal
        elif operator == "le":
            matched = value <= literal
        elif operator == "gt":
            matched = value > literal
        else:  # The strict predicate validator permits only ge here.
            matched = value >= literal
        result = "TRUE" if matched is True else "FALSE"
        issues, blockers = {}, set()
    return _trace(result, [{"path": path, "operator": operator, "result": result,
                           "operand": {"origin": origin, "id": ident}}], issues, blockers)


def evaluate_predicate(predicate: dict, context: dict, prepared_facts: dict) -> dict:
    """Return a bounded deterministic trace; invalid expressions are errors."""
    if not isinstance(context, dict):
        raise TypeError("Normalized application context must be an object")
    definitions = _validate_prepared(prepared_facts)
    validate_predicate(predicate, definitions)
    return _evaluate(predicate, context, prepared_facts, "$")


def evaluate_clause_conditions(catalogue: dict, context: dict, facts: dict) -> dict:
    """Evaluate each clause and its inherited atomic check conditions.

    The workbook owns the preceding core-context stop gate. This function never
    infers scope, current authority or a conventional plan variant.
    """
    validate_clause_catalogue(catalogue)
    if not isinstance(context, dict):
        raise TypeError("Normalized application context must be an object")
    prepared = prepare_fact_values(catalogue["facts"], facts)
    clause_results, check_results = {}, {}
    for clause in catalogue["clauses"]:
        clause_results[clause["id"]] = _evaluate(clause["when"], context, prepared, "$")
        for check in clause["checks"]:
            # Each source predicate was bounded separately during validation.
            # Combining two valid predicates adds only one synthetic all node.
            check_results[check["id"]] = _combine("all", [
                _evaluate(clause["when"], context, prepared, "$.all[0]"),
                _evaluate(check["when"], context, prepared, "$.all[1]")], "$")
    return {"clause_results": clause_results, "check_results": check_results}
