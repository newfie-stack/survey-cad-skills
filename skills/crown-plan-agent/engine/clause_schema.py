"""Bounded conditional-clause data; validation never attests legal authority."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
import ipaddress
import json
from math import isfinite
from pathlib import Path
import re
from urllib.parse import urlsplit

MAX_BYTES = 2 * 1024 * 1024
MAX_CLAUSES = 500
MAX_CHECKS = 5000
MAX_FACTS = 200
MAX_PREDICATE_NODES = 256
MAX_PREDICATE_DEPTH = 16
MAX_STRING = 4096
MAX_ID = 128
MAX_NUMERIC_STRING = 50
ADAPTER_IDS = frozenset({"CANDIDATE-PLAN-SCALE", "CANDIDATE-PLAN-HEADING",
                         "CANDIDATE-MUNICIPALITY", "CANDIDATE-APPLICANT",
                         "CANDIDATE-TOTAL-AREA", "CANDIDATE-HYBRID-PLAN-HEADING",
                         "CANDIDATE-COMPILED-PLAN-HEADING"})
CONTEXT_FIELDS = frozenset({"regulator", "disposition", "stage", "plan_type",
                            "land_class", "review_scope", "scope_status"})
KINDS = frozenset({"required", "conditional_required", "optional", "mixed", "permission", "exemption"})
CLAUSE_ID_PATTERN = re.compile(r"[0-9]+(?:\.[0-9]+)+\Z")
DECIMAL_PATTERN = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?\Z")


def _keys(value: object, required: set[str], label: str,
          optional: set[str] = frozenset()) -> None:
    if not isinstance(value, dict) or not required <= value.keys() or value.keys() - required - optional:
        raise ValueError(label + " has missing or unsupported keys")


def _text(value: object, label: str, *, limit: int = MAX_STRING) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(label + " must be a nonempty bounded string")


def _identifier(value: object, label: str) -> None:
    _text(value, label, limit=MAX_ID)


def _text_list(value: object, label: str, *, nonempty: bool = False,
               unique: bool = False, identifiers: bool = False) -> None:
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(label + " must be a list" + (" with entries" if nonempty else ""))
    for item in value:
        (_identifier if identifiers else _text)(item, label)
    if unique and len(set(value)) != len(value):
        raise ValueError(label + " must not contain duplicates")


def _bounded_data(value: object) -> None:
    """Bound programmatic JSON trees without serializing an unbounded tree."""
    remaining = MAX_BYTES
    active = set()

    def visit(item: object, depth: int) -> None:
        nonlocal remaining
        if depth > 2 * MAX_PREDICATE_DEPTH + 16:
            raise ValueError("Catalogue data nesting exceeds the bounded schema")
        if isinstance(item, str):
            if len(item) > MAX_STRING:
                raise ValueError("Catalogue string exceeds 4096 characters")
            try:
                size = len(json.dumps(item, ensure_ascii=False).encode("utf-8"))
            except (UnicodeError, ValueError) as exc:
                raise ValueError("Catalogue strings must be valid UTF-8 JSON") from exc
        elif item is None or type(item) is bool:
            size = 4 if item is None or item is True else 5
        elif type(item) is int:
            # A conservative decimal-length bound avoids huge int-to-string
            # conversion. Ordinary integer bounds are preserved exactly.
            size = 1 if item == 0 else (abs(item).bit_length() * 30103 // 100000 + 1 + (item < 0))
        elif type(item) is float and isfinite(item):
            size = len(repr(item))
        elif isinstance(item, (dict, list)):
            if id(item) in active:
                raise ValueError("Catalogue JSON data must not contain cycles")
            if len(item) > MAX_BYTES // 2:
                raise ValueError("Catalogue JSON exceeds 2 MiB")
            active.add(id(item))
            remaining -= 2 + max(0, len(item) - 1)
            if remaining < 0:
                raise ValueError("Catalogue JSON exceeds 2 MiB")
            if isinstance(item, dict):
                for key, child in item.items():
                    if not isinstance(key, str):
                        raise ValueError("Catalogue JSON object keys must be strings")
                    visit(key, depth + 1)
                    remaining -= 1
                    visit(child, depth + 1)
            else:
                for child in item:
                    visit(child, depth + 1)
            active.remove(id(item))
            return
        else:
            raise ValueError("Catalogue contains an unsupported JSON scalar or container")
        remaining -= size
        if remaining < 0:
            raise ValueError("Catalogue JSON exceeds 2 MiB")

    visit(value, 1)


def _decimal(value: object) -> bool:
    return (isinstance(value, str) and len(value) <= MAX_NUMERIC_STRING
            and DECIMAL_PATTERN.fullmatch(value) is not None)


def _scalar(definition: dict, value: object) -> bool:
    kind = definition["type"]
    if kind == "boolean":
        return type(value) is bool
    if kind == "integer":
        return type(value) is int
    if kind == "decimal":
        return _decimal(value)
    return isinstance(value, str) and value in definition["allowed_values"]


def _validate_fact(definition: object) -> None:
    _keys(definition, {"id", "type", "unit", "minimum", "maximum", "allowed_values",
                       "provenance_required", "purpose"}, "Fact definition",
          {"exclusive_minimum", "exclusive_maximum"})
    _identifier(definition["id"], "Fact id")
    if definition["id"].startswith("context:"):
        raise ValueError("Fact id uses the reserved context issue namespace")
    kind = definition["type"]
    if not isinstance(kind, str) or kind not in {"boolean", "integer", "decimal", "enum"}:
        raise ValueError("Unsupported fact type")
    if type(definition["provenance_required"]) is not bool:
        raise ValueError("Fact provenance_required must be boolean")
    if definition["purpose"] not in ("applicability", "manual_applicability"):
        raise ValueError("Unsupported fact purpose")
    if definition["purpose"] == "manual_applicability" and not definition["provenance_required"]:
        raise ValueError("Manual applicability requires provenance")
    if kind in {"integer", "decimal"}:
        if definition["unit"] is not None:
            _text(definition["unit"], "Numeric fact unit")
        if definition["allowed_values"] is not None:
            raise ValueError("Numeric facts must not declare allowed_values")
        for name in ("minimum", "maximum"):
            bound = definition[name]
            if bound is not None and not _scalar(definition, bound):
                raise ValueError("Numeric fact bound has an incompatible scalar type")
            exclusive = "exclusive_" + name
            if exclusive in definition and (type(definition[exclusive]) is not bool or bound is None):
                raise ValueError("Exclusive bounds require a numeric non-null bound and boolean flag")
        low, high = definition["minimum"], definition["maximum"]
        if low is not None and high is not None:
            if (Decimal(low) if kind == "decimal" else low) > (Decimal(high) if kind == "decimal" else high):
                raise ValueError("Fact minimum exceeds maximum")
    else:
        if any(definition[name] is not None for name in ("unit", "minimum", "maximum")):
            raise ValueError("Non-numeric fact unit and bounds must be null")
        if "exclusive_minimum" in definition or "exclusive_maximum" in definition:
            raise ValueError("Exclusive bounds are numeric-only")
        if kind == "boolean":
            if definition["allowed_values"] is not None:
                raise ValueError("Boolean allowed_values must be null")
        else:
            _text_list(definition["allowed_values"], "Enum values", nonempty=True, unique=True)


def validate_fact_definitions(definitions: dict[str, dict]) -> dict[str, dict]:
    """Validate an ID-keyed definition mapping without copying or normalizing it."""
    _bounded_data(definitions)
    if not isinstance(definitions, dict) or len(definitions) > MAX_FACTS:
        raise ValueError("Fact definitions must be a mapping of at most 200 facts")
    for name, definition in definitions.items():
        _identifier(name, "Fact reference")
        _validate_fact(definition)
        if definition["id"] != name:
            raise ValueError("Fact reference must equal its definition id")
    return definitions


def is_valid_fact_value(definition: dict, value: object) -> bool:
    """Check an exact scalar and its declared input domain, without conversion."""
    try:
        _bounded_data({"definition": definition, "value": value})
        _validate_fact(definition)
        if not _scalar(definition, value):
            return False
        if definition["type"] not in {"integer", "decimal"}:
            return True
        measured = Decimal(value) if definition["type"] == "decimal" else value
        for name, below in (("minimum", True), ("maximum", False)):
            bound = definition[name]
            if bound is None:
                continue
            bound = Decimal(bound) if definition["type"] == "decimal" else bound
            if (measured < bound if below else measured > bound):
                return False
            if definition.get("exclusive_" + name, False) and measured == bound:
                return False
        return True
    except (ValueError, TypeError, OverflowError, RecursionError):
        return False


def _predicate(predicate: object, definitions: dict[str, dict]) -> None:
    nodes = 0

    def visit(expression: object, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > MAX_PREDICATE_NODES or depth > MAX_PREDICATE_DEPTH:
            raise ValueError("Predicate exceeds 256 nodes or depth 16")
        if not isinstance(expression, dict) or len(expression) != 1:
            raise ValueError("Predicate must contain exactly one operator")
        operator, operand = next(iter(expression.items()))
        if operator == "const":
            if type(operand) is not bool:
                raise ValueError("Predicate const must be boolean")
        elif operator in {"all", "any"}:
            if not isinstance(operand, list) or not operand:
                raise ValueError("Logical predicates require nonempty child lists")
            for child in operand:
                visit(child, depth + 1)
        elif operator == "not":
            visit(operand, depth + 1)
        elif operator in {"eq", "in", "lt", "le", "gt", "ge"}:
            if not isinstance(operand, dict):
                raise ValueError("Comparison operand must be an object")
            refs = {"fact", "context"} & operand.keys()
            if len(refs) != 1:
                raise ValueError("Comparison requires exactly one fact or context reference")
            reference_kind = next(iter(refs))
            value_key = "values" if operator == "in" else "value"
            _keys(operand, {reference_kind, value_key}, "Comparison")
            name = operand[reference_kind]
            _identifier(name, "Predicate reference")
            if reference_kind == "fact":
                if name not in definitions:
                    raise ValueError("Unknown fact reference")
                definition = definitions[name]
                if operator not in {"eq", "in"} and definition["type"] not in {"integer", "decimal"}:
                    raise ValueError("Ordered comparisons require numeric facts")
            elif name not in CONTEXT_FIELDS or operator not in {"eq", "in"}:
                raise ValueError("Unknown context reference or incompatible context operator")
            values = operand[value_key] if operator == "in" else [operand[value_key]]
            if not isinstance(values, list) or not values:
                raise ValueError("Membership requires a nonempty values list")
            normalized = []
            for value in values:
                if reference_kind == "context":
                    _text(value, "Context comparison literal")
                elif not _scalar(definition, value):
                    raise ValueError("Comparison literal has an incompatible scalar type")
                normalized.append(Decimal(value) if reference_kind == "fact" and definition["type"] == "decimal" else value)
            if operator == "in" and len(set(normalized)) != len(normalized):
                raise ValueError("Membership literals must not contain semantic duplicates")
        else:
            raise ValueError("Unsupported predicate operator")

    visit(predicate, 1)


def validate_predicate(predicate: dict, definitions: dict[str, dict]) -> None:
    """Validate a bounded expression against explicit, validated fact metadata."""
    validate_fact_definitions(definitions)
    _bounded_data(predicate)
    _predicate(predicate, definitions)


def _validate_source(source: object) -> None:
    _keys(source, {"title", "version_date", "url", "page_count", "classification"}, "Source")
    for name in ("title", "version_date", "url"):
        _text(source[name], "Source " + name)
    if any(character.isspace() or ord(character) < 32 or ord(character) == 127
           for character in source["url"]):
        raise ValueError("Source URL must not contain whitespace or control characters")
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", source["version_date"]):
        raise ValueError("Source version_date must be an ISO calendar date")
    try:
        date.fromisoformat(source["version_date"])
        url = urlsplit(source["url"])
        host = url.hostname
        port = url.port
    except ValueError as exc:
        raise ValueError("Invalid source date or URL") from exc
    if (url.scheme != "https" or not host or url.username is not None or url.password is not None
            or (port is not None and not 1 <= port <= 65535)):
        raise ValueError("Source URL must be public HTTPS without credentials")
    try:
        public = ipaddress.ip_address(host).is_global
    except ValueError:
        try:
            host = host.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise ValueError("Invalid source hostname") from exc
        public = ("." in host and not host.rsplit(".", 1)[-1].isdigit()
                  and not host.endswith((".local", ".localhost", ".internal", ".invalid", ".test"))
                  and all(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
                          for label in host.split(".")))
    if not public:
        raise ValueError("Source URL must identify a public host")
    if type(source["page_count"]) is not int or source["page_count"] < 1:
        raise ValueError("Source page_count must be a positive integer")
    if source["classification"] not in ("DATED_MANUAL", "INVENTED"):
        raise ValueError("Unsupported source classification")


def validate_clause_catalogue(data: dict) -> dict:
    """Validate the complete strict catalogue and return it unchanged."""
    _bounded_data(data)
    _keys(data, {"schema_version", "catalogue_id", "source_status", "source", "facts", "clauses"}, "Catalogue")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("Unsupported catalogue schema_version")
    _identifier(data["catalogue_id"], "Catalogue id")
    if data["source_status"] != "UNVERIFIED_CURRENT":
        raise ValueError("Catalogue cannot claim current source verification")
    _validate_source(data["source"])
    facts, clauses = data["facts"], data["clauses"]
    if not isinstance(facts, list) or len(facts) > MAX_FACTS:
        raise ValueError("Catalogue facts must be a list of at most 200 definitions")
    definitions = {}
    for definition in facts:
        _validate_fact(definition)
        if definition["id"] in definitions:
            raise ValueError("Duplicate fact id")
        definitions[definition["id"]] = definition
    if not isinstance(clauses, list) or len(clauses) > MAX_CLAUSES:
        raise ValueError("Catalogue clauses must be a list of at most 500 clauses")
    clause_ids, checks, controllers = set(), {}, {}
    for clause in clauses:
        _keys(clause, {"id", "kind", "citation", "summary", "when", "checks", "overrides"}, "Clause")
        ident = clause["id"]
        _identifier(ident, "Clause id")
        if not CLAUSE_ID_PATTERN.fullmatch(ident) or ident in clause_ids:
            raise ValueError("Clause IDs must be unique dotted-numeric strings")
        clause_ids.add(ident)
        if not isinstance(clause["kind"], str) or clause["kind"] not in KINDS:
            raise ValueError("Unsupported clause kind")
        _keys(clause["citation"], {"section", "page"}, "Citation")
        citation = clause["citation"]
        if (citation["section"] != ident or type(citation["page"]) is not int
                or not 1 <= citation["page"] <= data["source"]["page_count"]):
            raise ValueError("Citation must match clause section and source page range")
        _text(clause["summary"], "Clause summary")
        _predicate(clause["when"], definitions)
        if not isinstance(clause["checks"], list) or not clause["checks"]:
            raise ValueError("Clause checks must be a nonempty list")
        if clause["kind"] == "exemption" and (len(clause["checks"]) != 1
                or not isinstance(clause["checks"][0], dict) or clause["checks"][0].get("kind") != "exemption"):
            raise ValueError("Exemption clause requires exactly one exemption guidance check")
        for check in clause["checks"]:
            _keys(check, {"id", "kind", "when", "questions", "adapter_links"}, "Check")
            _identifier(check["id"], "Check id")
            if check["id"] in checks:
                raise ValueError("Check IDs must be globally unique")
            checks[check["id"]] = ident
            if len(checks) > MAX_CHECKS:
                raise ValueError("Catalogue exceeds 5000 checks")
            if not isinstance(check["kind"], str) or check["kind"] not in KINDS - {"mixed"}:
                raise ValueError("Unsupported atomic check kind")
            if clause["kind"] in {"optional", "permission"} and check["kind"] != clause["kind"]:
                raise ValueError("Optional and permission clauses require matching guidance check kinds")
            _predicate(check["when"], definitions)
            _text_list(check["questions"], "Check questions", nonempty=True)
            _text_list(check["adapter_links"], "Adapter links", unique=True, identifiers=True)
            if any(adapter not in ADAPTER_IDS for adapter in check["adapter_links"]):
                raise ValueError("Unknown observation adapter")
        if not isinstance(clause["overrides"], list):
            raise ValueError("Clause overrides must be a list")
        if clause["overrides"]:
            controllers[ident] = clause["overrides"]
    graph = {ident: set() for ident in clause_ids}
    for ident, effects in controllers.items():
        targets = set()
        for effect in effects:
            _keys(effect, {"action", "targets"}, "Override")
            if effect["action"] not in ("exclude", "replace"):
                raise ValueError("Unsupported override action")
            _text_list(effect["targets"], "Override targets", nonempty=True, unique=True, identifiers=True)
            for target in effect["targets"]:
                if target not in checks or checks[target] == ident or target in targets:
                    raise ValueError("Override target is unknown, self-owned or duplicated per controller")
                targets.add(target)
                owner = checks[target]
                if owner in controllers:
                    raise ValueError("Override controllers cannot themselves be targets")
                graph[ident].add(owner)
    # Keep cycle validation explicit even though the controller-target guard is
    # stronger than acyclicity in this version of the contract.
    incoming = {ident: 0 for ident in graph}
    for children in graph.values():
        for child in children:
            incoming[child] += 1
    ready = [ident for ident, count in incoming.items() if count == 0]
    visited = 0
    while ready:
        ident = ready.pop()
        visited += 1
        for child in graph[ident]:
            incoming[child] -= 1
            if incoming[child] == 0:
                ready.append(child)
    if visited != len(graph):
        raise ValueError("Override graph must not contain cycles")
    return data


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("Duplicate JSON object key")
        result[name] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError("Nonfinite JSON constants are unsupported")


def load_bounded_json(path: str | Path) -> object:
    """Read at most 2 MiB of UTF-8 JSON, rejecting duplicate keys and constants."""
    selected = Path(path)
    if selected.stat().st_size > MAX_BYTES:
        raise ValueError("JSON file exceeds 2 MiB")
    with selected.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("JSON file exceeds 2 MiB")
    try:
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                            parse_constant=_invalid_constant)
    except (UnicodeError, RecursionError, ValueError) as exc:
        raise ValueError("Invalid bounded JSON: " + str(exc)) from exc
    _bounded_data(result)
    return result


def load_clause_catalogue(path: str | Path) -> dict:
    """Load only the explicit, selected catalogue; never infer one from a PDF."""
    return validate_clause_catalogue(load_bounded_json(path))
