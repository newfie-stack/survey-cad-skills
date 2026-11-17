"""Bounded, literal Markdown for the revision evidence comparison model."""
from __future__ import annotations

from hashlib import sha256
import json
import math
import re
import unicodedata


MAX_MARKDOWN_BYTES = 20 * 1024 * 1024
MAX_TEXT_CHARS = 8192
_STATES = (
    "OBSERVED_TEXT_CHANGED", "NEWLY_OBSERVED_TEXT", "PREVIOUS_OBSERVATION_NOT_FOUND",
    "AMBIGUOUS", "NOT_COMPARED", "SAME_OBSERVED_TEXT",
)
_STATE_LABELS = {
    "SAME_OBSERVED_TEXT": "Same observed text",
    "OBSERVED_TEXT_CHANGED": "Text changed",
    "NEWLY_OBSERVED_TEXT": "Newly observed",
    "PREVIOUS_OBSERVATION_NOT_FOUND": "Previous observation not found",
    "AMBIGUOUS": "Ambiguous",
    "NOT_COMPARED": "Not compared",
}
_TEXT_STATES = {"ADDED", "REMOVED", "COUNT_CHANGED"}
_HASH = re.compile(r"[0-9a-f]{64}\Z")


def _bounded_values(value: object, depth: int = 0, budget: list[int] | None = None) -> None:
    """Reject unbounded/non-JSON source values before formatting any of them."""
    if budget is None:
        budget = [0]
    if depth > 16:
        raise ValueError("Comparison nesting limit exceeded")
    # This is a lower bound on serialized JSON bytes. It also bounds traversal
    # of repeated/shared containers before rendering any unused source fields.
    budget[0] += 1
    if isinstance(value, str):
        if len(value) > MAX_TEXT_CHARS:
            raise ValueError("Comparison text field limit exceeded")
        try:
            budget[0] += len(value.encode("utf-8")) + 2
        except UnicodeEncodeError as exc:
            raise ValueError("Comparison text must be valid UTF-8") from exc
    elif isinstance(value, dict):
        if len(value) > 200:
            raise ValueError("Comparison object field limit exceeded")
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("Comparison object keys must be text")
            _bounded_values(key, depth + 1, budget)
            _bounded_values(item, depth + 1, budget)
    elif isinstance(value, list):
        if len(value) > 200_000:
            raise ValueError("Comparison collection limit exceeded")
        for item in value:
            _bounded_values(item, depth + 1, budget)
    elif value is None or type(value) is bool:
        pass
    elif type(value) is int:
        if value.bit_length() > 1024:
            raise ValueError("Comparison numeric limit exceeded")
    elif type(value) is float and math.isfinite(value):
        pass
    else:
        raise ValueError("Comparison contains unsupported values")
    if budget[0] > MAX_MARKDOWN_BYTES:
        raise ValueError("Comparison input exceeds the 20 MiB UTF-8 limit")


def _literal(value: object) -> str:
    """Encode source punctuation after Markdown tokenization, including URLs.

    Backslash escaping alone does not disable GFM bare-URL autolinking. Numeric
    entities preserve visible punctuation without introducing inline Markdown,
    HTML, autolinks, table boundaries, or fenced/block syntax. Controls are shown
    as explicit Unicode escapes rather than changing the report's structure.
    """
    if value is None:
        return "unknown"
    if not isinstance(value, str) and type(value) not in (int, float, bool):
        raise ValueError("Literal source fields must be scalar values")
    text = str(value)
    result = []
    for char in text:
        if unicodedata.category(char).startswith("C"):
            code = ord(char)
            result.append("&#92;" + (f"u{code:04x}" if code <= 0xffff else f"U{code:08x}"))
        elif char.isalnum() or char == " ":
            result.append(char)
        else:
            result.append(f"&#{ord(char)};")
    return "".join(result)


class _Output:
    """Keep the final join bounded, counting UTF-8 bytes as lines arrive."""

    def __init__(self):
        self.lines = []
        self.size = 0

    def add(self, *lines: str) -> None:
        for line in lines:
            self.size += len(line.encode("utf-8")) + 1
            if self.size > MAX_MARKDOWN_BYTES:
                raise ValueError("Comparison Markdown exceeds the 20 MiB UTF-8 limit")
            self.lines.append(line)

    def finish(self) -> str:
        return "\n".join(self.lines) + "\n"


def _list(value: object, limit: int, label: str) -> list:
    if not isinstance(value, list):
        raise ValueError(label + " must be a list")
    if len(value) > limit:
        raise ValueError(label + " limit exceeded")
    return value


def _hash(value: object) -> None:
    if not isinstance(value, str) or not _HASH.fullmatch(value):
        raise ValueError("Comparison requires canonical source and basis hashes")


def _json_chunks(value: object):
    return json.JSONEncoder(ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                            allow_nan=False).iterencode(value)


def _context_digest(context: dict) -> str:
    digest = sha256()
    size = 0
    for chunk in _json_chunks(context):
        encoded = chunk.encode("utf-8")
        size += len(encoded)
        if size > MAX_MARKDOWN_BYTES:
            raise ValueError("Review context exceeds the 20 MiB UTF-8 limit")
        digest.update(encoded)
    return digest.hexdigest()


def _literal_json(value: object) -> str:
    """Bound nested context's escaped expansion before joining its fragments."""
    chunks, size = [], 0
    for chunk in _json_chunks(value):
        literal = _literal(chunk)
        size += len(literal.encode("utf-8"))
        if size > MAX_MARKDOWN_BYTES:
            raise ValueError("Comparison Markdown exceeds the 20 MiB UTF-8 limit")
        chunks.append(literal)
    return "".join(chunks)


def _validate(comparison: dict) -> None:
    if not isinstance(comparison, dict):
        raise ValueError("Comparison must be an object")
    if (type(comparison.get("schema_version")) is not int or comparison["schema_version"] != 1
            or comparison.get("comparison_type") != "CROWN_PLAN_REVISION_TEXT_REVIEW"
            or comparison.get("overall_status") != "REVIEW_REQUIRED"
            or comparison.get("assessment_type") != "REVISION_EVIDENCE_COMPARISON_NOT_COMPLIANCE"
            or type(comparison.get("identical_source_bytes")) is not bool):
        raise ValueError("Only schema 1 review-only revision comparisons can be rendered")
    requirements = _list(comparison.get("requirements"), 20_000, "Requirement collection")
    changes = _list(comparison.get("text_changes"), 10_000, "Text change collection")
    _bounded_values(comparison)
    basis = comparison["basis"]
    for name in ("engine_sha256", "scenario_sha256", "catalogue_sha256", "basis_sha256"):
        _hash(basis[name])
    context = comparison["review_context"]
    if not isinstance(context, dict) or _context_digest(context) != basis["scenario_sha256"]:
        raise ValueError("Common application context must match the canonical scenario SHA-256")
    if basis["engine_version"] != "0.6.0":
        raise ValueError("Unsupported comparison engine version")
    for reference in _list(basis["references"], 20_000, "Basis reference collection"):
        _hash(reference["sha256"])
        if not isinstance(reference["name"], str):
            raise ValueError("Basis reference name must be text")
    for name in ("baseline", "revised"):
        source = comparison[name]
        _hash(source["source_sha256"])
        if not isinstance(source["source_filename"], str) or type(source["pages"]) is not int or not 1 <= source["pages"] <= 100:
            raise ValueError("Invalid comparison source metadata")
        summary = comparison[name + "_review_summary"]
        if summary.get("status", "REVIEW_REQUIRED") != "REVIEW_REQUIRED":
            raise ValueError("Source summary must remain review-only")
        for key in ("checked", "needs_attention", "not_checked", "next_steps", "input_requests"):
            _list(summary.get(key, []), 20_000, "Source summary collection")
    same = comparison["baseline"]["source_sha256"] == comparison["revised"]["source_sha256"]
    if same != comparison["identical_source_bytes"]:
        raise ValueError("Source-byte identity does not match source hashes")
    counts = comparison["summary"]["finding_counts"]
    if set(counts) != set(_STATES) or any(type(counts[state]) is not int or counts[state] < 0 for state in _STATES):
        raise ValueError("Invalid six-state finding counts")
    if type(comparison["summary"]["changed_text_groups"]) is not int or comparison["summary"]["changed_text_groups"] != len(changes):
        raise ValueError("Invalid changed text group count")
    for entry in requirements:
        if entry["comparison_status"] not in _STATES or entry["location_changed"] not in (None, True, False):
            raise ValueError("Invalid finding comparison state")
        for name in ("baseline", "revised"):
            side = entry[name]
            if side["candidate_count"] is not None and (type(side["candidate_count"]) is not int or side["candidate_count"] < 0):
                raise ValueError("Invalid candidate count")
            if side["anchor"] is not None and not isinstance(side["anchor"], dict):
                raise ValueError("Invalid source anchor")
    for change in changes:
        if change["change_status"] not in _TEXT_STATES:
            raise ValueError("Invalid literal text change state")
        for key in ("before_count", "after_count"):
            if type(change[key]) is not int or change[key] < 0:
                raise ValueError("Invalid literal text occurrence count")
        for name in ("baseline_occurrences", "revised_occurrences"):
            _list(change[name], 200_000, "Text occurrence collection")
    _list(comparison["limitations"], 20_000, "Limitations collection")


def _location(out: _Output, label: str, location: dict | None, reason: object = None) -> None:
    location = location or {}
    out.add("- " + label + " source page: " + _literal(location.get("page")),
            "- " + label + " PDF bbox (points): " + _coordinates(location.get("bbox_points"), 4))
    for key, title in (("page_size_points", "page size (points)"), ("text_angle_degrees", "text angle (degrees)")):
        if key in location:
            value = _coordinates(location[key], 2) if key == "page_size_points" else _literal(location[key])
            out.add("- " + label + " " + title + ": " + value)
    reason = reason or location.get("location_reason") or location.get("reason")
    if reason:
        out.add("- " + label + " location reason: " + _literal(reason))


def _coordinates(value: object, length: int) -> str:
    if value is None:
        return "unknown"
    if not isinstance(value, list) or len(value) != length or any(type(item) not in (int, float) for item in value):
        raise ValueError("Source coordinate fields must be bounded numeric vectors")
    return _literal(str(value))


def _review_summary(out: _Output, label: str, summary: dict) -> None:
    out.add("", "## " + label + " unresolved review summary", "", _literal(summary.get("headline", "No review headline recorded.")))
    for key, title in (("needs_attention", "Needs attention"), ("not_checked", "Unchecked manual work"),
                       ("checked", "Recorded checks"), ("next_steps", "Next steps")):
        out.add("", "### " + title, "")
        for item in summary.get(key, []) or ["None recorded."]:
            out.add("- " + _literal(item))
    if summary.get("context_question"):
        out.add("", "Context question: " + _literal(summary["context_question"]))
    if summary.get("input_requests"):
        out.add("", "### Unresolved input requests", "")
        for request in summary["input_requests"]:
            out.add("- " + _literal(request["field"]) + ": " + _literal(request["question"]))


def render_comparison_markdown(comparison: dict) -> str:
    """Render the fixed comparison schema without interpreting source markup.

    Raises ValueError on unsupported models, excess fields/collections, or an
    artifact exceeding 20 MiB. No output is returned before validation completes.
    """
    try:
        _validate(comparison)
        return _render(comparison)
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("Malformed revision comparison schema") from exc


def _render(comparison: dict) -> str:
    out = _Output()
    out.add("# Crown Plan Agent — Revision Evidence Comparison", "",
            "**Status: REVIEW_REQUIRED. Regulatory compliance and professional acceptance remain unassessed.**", "",
            "## Comparison summary", "", "| Finding comparison state | Count |", "|---|---|")
    for state in _STATES:
        out.add(f'| {_STATE_LABELS[state]} | {comparison["summary"]["finding_counts"][state]} |')
    out.add("", f'Changed text groups: {comparison["summary"]["changed_text_groups"]}')
    if not comparison["text_changes"] and not any(
            entry["comparison_status"] in _STATES[:3] for entry in comparison["requirements"]):
        out.add("No changes found in the supported text comparison.")
    out.add("", "## Scope", "",
            "This compares extracted text groups and candidate review observations under one shared basis.",
            "Linework, symbols, signatures, raster content, legal boundaries and geometry require independent review.",
            "Span fragmentation or merging may produce extracted-text inventory differences; these are not inferred semantic edits.",
            "A previous observation not found does not establish removed geometry or correction. No comment is closed by this comparison.",
            "Source page references below belong to each original PDF; publication pages belong to the governing citation.",
            "PDF coordinate changes do not prove a surveyed feature moved.", "", "## Source and basis", "")
    for name, label in (("baseline", "Baseline"), ("revised", "Revised")):
        source = comparison[name]
        out.add("- " + label + " original filename: " + _literal(source["source_filename"]),
                "- " + label + " source SHA-256: " + source["source_sha256"],
                "- " + label + " source pages: " + str(source["pages"]))
    out.add("")
    out.add("Source PDF bytes are identical (SHA-256 fact); this does not establish regulatory acceptance."
            if comparison["identical_source_bytes"] else "Source PDF bytes differ; text results cover only the supported comparison.")
    basis = comparison["basis"]
    out.add("", "- Engine version: " + _literal(basis["engine_version"]))
    for key, label in (("engine_sha256", "Engine"), ("scenario_sha256", "Scenario"),
                       ("catalogue_sha256", "Catalogue"), ("basis_sha256", "Shared basis")):
        out.add("- " + label + " SHA-256: " + basis[key])
    for reference in basis["references"]:
        out.add("- Reference: " + _literal(reference["name"]) + "; SHA-256: " + reference["sha256"])
    out.add("", "## Common application context", "")
    context = comparison["review_context"]
    if not context:
        out.add("No application context fields were supplied.")
    for key in sorted(context):
        value = context[key]
        rendered = _literal(value) if isinstance(value, str) else _literal_json(value)
        out.add("- " + _literal(key) + ": " + rendered)
    out.add("", "## Finding comparison", "")
    for entry in comparison["requirements"]:
        out.add("### " + _literal(entry["requirement_id"]), "",
                "- Requirement: " + _literal(entry["requirement_summary"]),
                "- Review instruction: " + _literal(entry.get("review_instruction") or entry.get("correction")),
                "- Correction / review action: " + _literal(entry.get("correction")),
                "- Comparison state: " + entry["comparison_status"],
                "- Location changed: " + ("unknown" if entry["location_changed"] is None else "yes" if entry["location_changed"] else "no"), "")
        for name, label in (("baseline", "Baseline"), ("revised", "Revised")):
            side = entry[name]
            out.add("#### " + label + " (" + ("before" if name == "baseline" else "after") + ")", "")
            for key, title in (("source_text", "Source text"), ("observation", "Observation"),
                               ("evidence_status", "Evidence status"), ("source_status", "Source status"),
                               ("candidate_count", "Candidate count")):
                out.add("- " + title + ": " + _literal(side[key]))
            _location(out, label, side["anchor"], side["location_reason"])
            for key, title in (("page_size_points", "page size (points)"), ("text_angle_degrees", "text angle (degrees)")):
                if key in side:
                    value = _coordinates(side[key], 2) if key == "page_size_points" else _literal(side[key])
                    out.add("- " + label + " " + title + ": " + value)
            frame = side.get("page_frame") or {}
            out.add("- " + label + " source frame status: " + _literal(side.get("frame_status", "UNKNOWN")),
                    "- " + label + " PDF page rotation (degrees): " + _literal(frame.get("rotation")))
            for key, title in (("mediabox_points", "MediaBox (points)"),
                               ("cropbox_points", "CropBox (points)"),
                               ("display_rect_points", "display rect (points)")):
                out.add("- " + label + " " + title + ": " + _coordinates(frame.get(key), 4))
            if side.get("frame_reason"):
                out.add("- " + label + " source frame reason: " + _literal(side["frame_reason"]))
            out.add("")
        citation = entry["citation"]
        for key, title in (("title", "Publication title"), ("version", "Publication version"),
                           ("section", "Publication section"), ("page", "Publication page"), ("url", "Publication URL (literal)")):
            out.add("- " + title + ": " + _literal(citation[key]))
        out.add("")
    out.add("## Literal extracted-text changes", "",
            "Added and removed groups describe extracted text only. Counts retain repeated occurrences; no one-to-one edit pairing is inferred.", "")
    if not comparison["text_changes"]:
        out.add("No literal text groups or occurrence counts changed.")
    for change in comparison["text_changes"]:
        out.add("### " + _literal(change["change_id"]), "", "- Literal text status: " + change["change_status"],
                "- Normalized text: " + _literal(change["normalized_text"]),
                f'- Baseline count: {change["before_count"]}; Revised count: {change["after_count"]}', "")
        for name, label in (("baseline_occurrences", "Baseline"), ("revised_occurrences", "Revised")):
            out.add("#### " + label + " source occurrences", "")
            if not change[name]:
                out.add("None recorded.")
            for index, occurrence in enumerate(change[name], 1):
                out.add("Occurrence " + str(index), "", "- Raw text: " + _literal(occurrence["raw_text"]))
                _location(out, label, occurrence)
                out.add("")
    for name, label in (("baseline_review_summary", "Baseline"), ("revised_review_summary", "Revised")):
        _review_summary(out, label, comparison[name])
    out.add("", "## Limitations", "")
    for limitation in comparison["limitations"]:
        out.add("- " + _literal(limitation))
    out.add("- Verify current authority, visual/manual checks and geometry independently; all regulatory findings remain REVIEW_REQUIRED.",
            "- Matching text and byte identity do not establish regulatory acceptance.")
    return out.finish()
