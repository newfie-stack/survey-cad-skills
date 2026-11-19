"""Source-bound review comments and printable notes, without writing files."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unicodedata

from pdf_inspector import extract_pdf
from pdf_markup_plan import build_markup_plan
from pdf_source import read_pdf_snapshot
from runtime_security import load_pdf_runtime

MAX_NOTES = 200
MAX_INDEX_PAGES = 200
_PAGE_WIDTH = 595.0
_PAGE_HEIGHT = 842.0
_MARGIN = 36.0
_TOP = 112.0
_BOTTOM = 800.0
_TEXT_SIZE = 9.0
_LINE_HEIGHT = 12.0
_LOCATION_LABELS = {
    'UNIQUE_SOURCE_SPAN': 'Located at a unique source text match',
    'VISUAL_REVIEW_LOCATION_UNKNOWN': 'Unlocated: visual review is needed',
    'NO_SOURCE_LOCATION': 'Unlocated: no reliable text location was recorded',
    'MULTIPLE_CANDIDATES': 'Unlocated: several possible text matches',
    'NO_UNIQUE_CANDIDATE': 'Unlocated: a unique text match was not established',
    'INVALID_SOURCE_BOUNDS': 'Unlocated: source coordinates could not be validated',
    'INCONSISTENT_EVIDENCE_REFERENCE': 'Unlocated: evidence references disagree',
    'NO_SOURCE_TEXT': 'Unlocated: original source text was not recorded',
    'SOURCE_SPAN_NOT_UNIQUE_OR_NOT_FOUND': 'Unlocated: source text and location could not be matched uniquely',
    'GLOBAL_REVIEW_ITEM': 'General review item; no plan location is assigned',
}


def _display_text(value: str, font, glyph_cache: dict[int, bool]) -> tuple[str, bool]:
    """Keep common Unicode; escape unsupported, RTL and control scalars explicitly.

    TextWriter's built-in fallback fonts preserve BMP Unicode. Astral ToUnicode
    mappings are not reliable across the supported PDF SDKs, so their printable
    representation is an explicit reversible codepoint. TextWriter does not offer
    general bidirectional shaping here, so RTL letters and numerals use the same
    fallback instead of presenting reordered words. Comments retain originals.
    """
    result, escaped = [], False
    for char in value:
        code = ord(char)
        if 0xD800 <= code <= 0xDFFF:
            raise ValueError("Review note contains an invalid Unicode surrogate")
        if char == "\n":
            result.append(char)
            continue
        if char == "\t":
            result.append("    ")
            continue
        if (code > 0xFFFF or unicodedata.category(char).startswith("C")
                or unicodedata.bidirectional(char) in {"R", "AL", "AN"}):
            result.append(("\\U%08X" if code > 0xFFFF else "\\u%04X") % code)
            escaped = True
            continue
        if code not in glyph_cache:
            glyph_cache[code] = bool(font.has_glyph(code, fallback=True))
        if glyph_cache[code]:
            result.append(char)
        else:
            result.append("\\u%04X" % code)
            escaped = True
    return "".join(result), escaped


def _wrap(text: str, font, size: float, width: float) -> list[str]:
    """Wrap all characters, including long IDs/URLs; never clip an overflow."""
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        lengths = font.char_lengths(paragraph, fontsize=size)
        start = 0
        while start < len(paragraph):
            end, used, last_space = start, 0.0, None
            while end < len(paragraph) and used + lengths[end] <= width:
                used += lengths[end]
                if paragraph[end].isspace():
                    last_space = end
                end += 1
            if end == start:
                raise ValueError("A review-note glyph cannot fit the printable notes width")
            if end < len(paragraph) and last_space is not None and last_space > start:
                end = last_space + 1
            lines.append(paragraph[start:end].rstrip())
            start = end
            while start < len(paragraph) and paragraph[start].isspace():
                start += 1
    return lines


def _note_lines(note: dict, original_pages: int) -> list[str]:
    citation = note["citation"]
    page = note.get("evidence_page")
    valid_page = type(page) is int and 1 <= page <= original_pages
    location = ("Recorded source PDF page: " + str(page) if valid_page
                else "Recorded source PDF page: unassigned")
    lines = [note["note_id"] + " | " + note["finding_id"] + " | " + note["title"],
             "Status: " + note["status"] + "; source status: " + note["source_status"],
             location, "Location: " + _LOCATION_LABELS.get(note["location_reason"],
                                                          'Unlocated: source location has not been established'),
             note["body"]]
    if any(value is not None for value in citation.values()):
        for label, key in (("Publication", "title"), ("Edition", "version"),
                           ("Section", "section"), ("Publication page", "page"),
                           ("Source URL (text only)", "url")):
            if citation[key] is not None:
                lines.append(label + ": " + str(citation[key]))
    return lines


def _index_layout(notes: list[dict], original_pages: int, font) -> tuple[list, dict, list]:
    pages, rows, y = [], [], _TOP
    note_pages, fallback_ids, glyph_cache = {}, [], {}
    width = _PAGE_WIDTH - 2*_MARGIN

    def finish_page():
        nonlocal rows, y
        if len(pages) >= MAX_INDEX_PAGES:
            raise ValueError("Printable review notes exceed the 200-page index limit")
        pages.append(rows)
        rows, y = [], _TOP

    for note in notes:
        first_row = True
        for section in _note_lines(note, original_pages):
            display, escaped = _display_text(section, font, glyph_cache)
            if escaped and note["note_id"] not in fallback_ids:
                fallback_ids.append(note["note_id"])
            for line in _wrap(display, font, _TEXT_SIZE, width):
                if y + _LINE_HEIGHT > _BOTTOM:
                    finish_page()
                    if not first_row:
                        rows.append((note["note_id"] + " (continued)", y, note["note_id"], False))
                        y += _LINE_HEIGHT
                page_ordinal = original_pages + len(pages) + 1
                locations = note_pages.setdefault(note["note_id"], [])
                if page_ordinal not in locations:
                    locations.append(page_ordinal)
                rows.append((line, y, note["note_id"], first_row))
                first_row = False
                y += _LINE_HEIGHT
        y += _LINE_HEIGHT
    if not notes:
        rows.append(("No review notes were recorded. This does not establish compliance.", y, None, False))
    finish_page()
    return pages, note_pages, fallback_ids


def _insert_page_link(document, page, rectangle, target_page: int, fitz) -> None:
    """Create only a page-fit GoTo, avoiding rotated/UserUnit XYZ SDK transforms."""
    existing = {item[0] for item in page.annot_xrefs()}
    page.insert_link({"kind": fitz.LINK_GOTO, "from": rectangle, "page": target_page})
    created = {item[0] for item in page.annot_xrefs()} - existing
    if len(created) != 1:
        raise RuntimeError("Could not identify the new internal review-page link")
    reference = document.page_xref(target_page)
    document.xref_set_key(created.pop(), "A", f"<< /S /GoTo /D [{reference} 0 R /Fit] >>")


def build_annotated_pdf(source_pdf: str | Path, report: dict, inventory: dict, *,
                        max_notes: int = MAX_NOTES) -> tuple[bytes, dict]:
    """Return a private derived review PDF and manifest; never write destinations.

    Independently re-extract the current source instead of trusting caller spans.
    Every hash must bind the exact immutable bytes used for rendering. Original
    pages keep their content, frame and source annotations; new notes are PDF
    comments, with a complete printable index on appended pages.
    """
    if type(max_notes) is not int or not 1 <= max_notes <= MAX_NOTES:
        raise ValueError("max_notes must be an integer from 1 through 200")
    if not isinstance(report, dict) or not isinstance(inventory, dict):
        raise TypeError("Report and inventory must be objects")
    actual = extract_pdf(source_pdf, include_vectors=False)
    snapshot, digest = read_pdf_snapshot(source_pdf)
    if any(value != digest for value in (actual.get("source_sha256"),
                                          report.get("source_sha256"),
                                          inventory.get("source_sha256"))):
        raise ValueError("Markup requires matching current source SHA-256 bindings")
    plan = build_markup_plan(report, actual, source_sha256=digest, max_notes=max_notes)
    fitz = load_pdf_runtime()
    with fitz.open(stream=snapshot, filetype="pdf") as document:
        original_pages = document.page_count
        if original_pages != actual["pages"]:
            raise ValueError("Source page count changed during markup preparation")
        notes = plan["notes"]
        font = fitz.Font("helv")
        index_pages, note_pages, fallback_ids = _index_layout(notes, original_pages, font)
        # Plan and layout validation finish before mutating the in-memory copy.
        for note in notes:
            anchor = note["anchor"]
            if anchor is None:
                continue
            page = document[anchor["page"]-1]
            comment = page.add_rect_annot(fitz.Rect(anchor["bbox_points"]))
            content = "\n".join(_note_lines(note, original_pages))
            comment.set_info(title="Crown Plan Agent", subject=note["note_id"] + ": " + note["finding_id"],
                             content=content + "\nSource PDF SHA-256: " + digest)
            comment.set_colors(stroke=(1, 0.5, 0))
            comment.set_border(width=1.25)
            comment.set_opacity(0.9)
            comment.set_flags(comment.flags | fitz.PDF_ANNOT_IS_PRINT)
            comment.update()
        by_id = {note["note_id"]: note for note in notes}
        for number, rows in enumerate(index_pages, 1):
            page = document.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
            writer = fitz.TextWriter(page.rect)
            writer.append((_MARGIN, 33), f"Crown Plan Agent - Review notes {number} of {len(index_pages)}",
                          font=font, fontsize=13)
            headers = ["REVIEW_REQUIRED. Derived review copy; not a regulatory certificate.",
                       "Source PDF SHA-256: " + digest,
                       f"Original source pages: {original_pages}. Orange regions identify text candidates.",
                       "Unlocated notes have no invented point. Comment bodies are printed in this index.",
                       r"Unsupported characters use explicit \u / \U escapes; comments retain originals."]
            for index, line in enumerate(headers):
                writer.append((_MARGIN, 49+index*11), line, font=font, fontsize=8)
            for line, baseline, note_id, first in rows:
                writer.append((_MARGIN, baseline), line, font=font, fontsize=_TEXT_SIZE)
                if first and by_id[note_id]["anchor"] is not None:
                    target = by_id[note_id]["anchor"]["page"]-1
                    right = min(_PAGE_WIDTH-_MARGIN, _MARGIN+font.text_length(line, fontsize=_TEXT_SIZE))
                    _insert_page_link(document, page,
                                      fitz.Rect(_MARGIN,baseline-_TEXT_SIZE,right,baseline+3),target,fitz)
            writer.write_text(page, color=(0.1, 0.1, 0.1))
            footer = fitz.TextWriter(page.rect)
            footer.append((_MARGIN, 823), f"Review notes - PDF page {page.number+1}",font=font,fontsize=8)
            footer.write_text(page, color=(0.25,0.25,0.25))
        output = document.tobytes(garbage=0, deflate=True)
    if read_pdf_snapshot(source_pdf)[1] != digest:
        raise ValueError("Source PDF changed during markup preparation")
    located = sum(note["anchor"] is not None for note in notes)
    manifest = {"status": "REVIEW_REQUIRED", "source_sha256": digest,
                "original_page_count": original_pages, "notes_page_count": len(index_pages),
                "notes": deepcopy(notes), "located_count": located,
                "unlocated_count": len(notes)-located, "note_index_pages": note_pages,
                "unicode_fallback_note_ids": fallback_ids,
                "coordinate_frame": plan["coordinate_frame"]}
    return output, manifest
