"""Audit declared citation links to a dated manual inventory, without selecting rules.

This offline inventory is review guidance. A citation link establishes neither
implementation coverage nor compliance, applicability, or current authority.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
SOURCE_STATUS = "UNVERIFIED_CURRENT"
REQUIREMENT_STATUSES = frozenset({"required", "conditional_required", "optional", "mixed",
                                  "permission", "exemption"})
FULL_ID = r"[1-4](?:\.[1-9]\d*){2,3}"
CLAUSE_ID = re.compile(FULL_ID + r"\Z")
SECTION_TOKEN = re.compile(r"(" + FULL_ID + r")(?:\s*[-–]\s*(" + FULL_ID + r"))?\Z")
INSTRUCTION_ID = re.compile(r"(?<![\w.])(" + FULL_ID + r")(?!\w|\.\d)")


def _text(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field + " must be a nonempty string")


def _keys(value: object, expected: set[str], field: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(field + " has missing or unsupported fields")


def _strings(value: object, field: str) -> None:
    if not isinstance(value, list):
        raise ValueError(field + " must be a list")
    for item in value:
        _text(item, field)
    if len(value) != len(set(value)):
        raise ValueError(field + " must not contain duplicates")


def _validate_inventory(data: object) -> dict:
    _keys(data, {"schema_version", "source_status", "source", "review_scope", "clauses"}, "Inventory")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("Unsupported inventory schema")
    if data["source_status"] != SOURCE_STATUS:
        raise ValueError("Inventory may not claim current source verification")
    _text(data["review_scope"], "review_scope")
    source = data["source"]
    _keys(source, {"publication_title", "version_date", "source_url", "pdf_page_count"}, "Source")
    for key in ("publication_title", "version_date", "source_url"):
        _text(source[key], "source." + key)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", source["version_date"]):
        raise ValueError("Source version_date must be an ISO calendar date")
    try:
        date.fromisoformat(source["version_date"])
    except ValueError as exc:
        raise ValueError("Source version_date must be an ISO calendar date") from exc
    url = urlsplit(source["source_url"])
    if url.scheme != "https" or not url.netloc or url.username or url.password:
        raise ValueError("Source URL must be a public HTTPS reference")
    page_count = source["pdf_page_count"]
    if type(page_count) is not int or page_count < 1:
        raise ValueError("Source pdf_page_count must be a positive integer")
    clauses = data["clauses"]
    if not isinstance(clauses, list) or not clauses:
        raise ValueError("Inventory clauses must be a nonempty list")
    seen = set()
    fields = {"clause_id", "pdf_page", "summary", "requirement_status", "review_scope", "exceptions",
              "review_notes", "candidate_requirement_ids", "reference_only_requirement_ids"}
    for clause in clauses:
        _keys(clause, fields, "Clause")
        ident = clause["clause_id"]
        if not isinstance(ident, str) or not CLAUSE_ID.fullmatch(ident) or ident in seen:
            raise ValueError("Clause IDs must be unique full IDs in Parts 1 to 4")
        seen.add(ident)
        if type(clause["pdf_page"]) is not int or not 1 <= clause["pdf_page"] <= page_count:
            raise ValueError("Clause PDF page is outside the source page range")
        _text(clause["summary"], "Clause summary")
        if not isinstance(clause["requirement_status"], str) or clause["requirement_status"] not in REQUIREMENT_STATUSES:
            raise ValueError("Unsupported clause requirement_status")
        for key in ("review_scope", "exceptions", "review_notes", "candidate_requirement_ids",
                    "reference_only_requirement_ids"):
            _strings(clause[key], key)
        if set(clause["candidate_requirement_ids"]) & set(clause["reference_only_requirement_ids"]):
            raise ValueError("Direct and reference-only declarations must be separate")
    return data


def load_inventory(path: str | Path | None = None) -> dict:
    """Load a strict, unverified inventory; the default contains 144 dated clauses."""
    selected = ROOT / "requirement_coverage.json" if path is None else Path(path)
    return _validate_inventory(json.loads(selected.read_text(encoding="utf-8")))


def _section_ranges(section: object) -> list[tuple[tuple[int, ...], tuple[int, ...]]] | None:
    """Parse complete IDs/ranges without expanding their integer intervals."""
    if not isinstance(section, str) or not section.strip():
        return None
    ranges = []
    for token in section.split(","):
        match = SECTION_TOKEN.fullmatch(token.strip())
        if match is None:
            return None
        first = tuple(map(int, match[1].split(".")))
        last = tuple(map(int, match[2].split("."))) if match[2] else first
        if first[:-1] != last[:-1] or first[-1] > last[-1]:
            return None
        ranges.append((first, last))
    return ranges


def _section_covers(section: object, clause_id: str) -> bool:
    ranges = _section_ranges(section)
    target = tuple(map(int, clause_id.split(".")))
    return ranges is not None and any(target[:-1] == first[:-1] and first[-1] <= target[-1] <= last[-1]
                                      for first, last in ranges)


def _link_error(records: list[dict], source: dict, clause_id: str, reference_only: bool) -> str | None:
    if not records:
        return "MISSING_CANDIDATE_ID"
    if len(records) != 1:
        return "DUPLICATE_CANDIDATE_ID"
    record = records[0]
    citation = record.get("citation")
    if not isinstance(citation, dict):
        return "MISSING_OR_INVALID_CITATION"
    for key in ("publication_title", "version_date"):
        if citation.get(key) != source[key]:
            return "CITATION_SOURCE_MISMATCH"
    if reference_only:
        instruction = record.get("review_instruction")
        if not isinstance(instruction, str) or clause_id not in INSTRUCTION_ID.findall(instruction):
            return "MISSING_REVIEW_INSTRUCTION_REFERENCE"
        # A reference is usable only on an actual, parseable citation record.
        if _section_ranges(citation.get("section")) is None:
            return "MISSING_OR_INVALID_CITATION"
    elif not _section_covers(citation.get("section"), clause_id):
        return "CITATION_SECTION_MISMATCH"
    return None


def _counts(clauses: list[dict]) -> dict:
    mapped = sum(bool(c["mapped_candidate_ids"]) for c in clauses)
    refs = sum(c["coverage_status"] == "REFERENCE_ONLY" for c in clauses)
    return {"total_clauses": len(clauses), "mapped_candidate_clauses": mapped,
            "reference_only_clauses": refs, "unmapped_clauses": len(clauses) - mapped,
            "unreferenced_clauses": len(clauses) - mapped - refs}


def audit_coverage(entries: list[dict], inventory: dict) -> dict:
    """Check declared links against actual candidate IDs and matching citations.

    Reference-only clauses remain unmapped. Undeclared custom IDs do not inherit
    links. This function never evaluates applicability, plan evidence, or law.
    """
    _validate_inventory(inventory)
    if not isinstance(entries, list) or not all(isinstance(entry, dict) for entry in entries):
        raise ValueError("Candidate entries must be a list of objects")
    records = defaultdict(list)
    for entry in entries:
        _text(entry.get("requirement_id"), "Candidate requirement_id")
        records[entry["requirement_id"]].append(entry)
    clauses = []
    for clause in inventory["clauses"]:
        direct, references, errors = [], [], []
        for field, valid, reference_only in (("candidate_requirement_ids", direct, False),
                                              ("reference_only_requirement_ids", references, True)):
            for ident in clause[field]:
                error = _link_error(records[ident], inventory["source"], clause["clause_id"], reference_only)
                if error:
                    errors.append({"requirement_id": ident, "link_type": "reference_only" if reference_only else "candidate",
                                   "reason": error})
                else:
                    valid.append(ident)
        clauses.append({"clause_id": clause["clause_id"], "pdf_page": clause["pdf_page"],
                        "coverage_status": "MAPPED_CANDIDATE" if direct else "REFERENCE_ONLY" if references else "UNMAPPED",
                        "mapped_candidate_ids": direct, "reference_only_ids": references,
                        "invalid_declared_links": errors})
    return {"status": "REVIEW_REQUIRED", "source_status": SOURCE_STATUS,
            "scope": "Declared citation links to the supplied dated manual inventory only; no applicability, implementation-completeness, compliance, or current-authority determination.",
            "source": dict(inventory["source"]), "counts": _counts(clauses),
            "by_part": {part: _counts([c for c in clauses if c["clause_id"].split(".")[0] == part])
                        for part in sorted({c["clause_id"].split(".")[0] for c in clauses})},
            "duplicate_candidate_ids": sorted(ident for ident, values in records.items() if len(values) > 1),
            "clauses": clauses}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=ROOT / "requirement_coverage.json")
    parser.add_argument("--catalogue", type=Path, default=ROOT / "candidate_requirements.json")
    parser.add_argument("--output", type=Path, help="Create a new JSON audit; existing files are never overwritten")
    args = parser.parse_args(argv)
    try:
        catalogue = json.loads(args.catalogue.read_text(encoding="utf-8"))
        if not isinstance(catalogue, dict) or type(catalogue.get("schema_version")) is not int or catalogue["schema_version"] != 1:
            raise ValueError("Unsupported candidate catalogue schema")
        result = audit_coverage(catalogue.get("requirements"), load_inventory(args.inventory))
        rendered = json.dumps(result, indent=2) + "\n"
        if args.output is None:
            print(rendered, end="")
        else:
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(rendered)
    except (OSError, ValueError) as exc:
        parser.exit(2, "Coverage audit failed: " + str(exc) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
