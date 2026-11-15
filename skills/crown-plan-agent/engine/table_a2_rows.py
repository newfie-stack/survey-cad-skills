"""Extract row-indexed PLAR Table A2 entries from the 2026 PDF.

Fail closed on unexpected structure; no compliance determination.
"""
from __future__ import annotations

import re
from pathlib import Path


def _combine(parts):
    return " ".join(" ".join(p.split()) for p in parts if p and p.strip()).strip()


def extract_a2_rows(pdf: str | Path) -> list[dict]:
    import fitz
    document = fitz.open(str(pdf))
    try:
        if document.needs_pass or len(document) != 18:
            raise ValueError("Encrypted or unexpected Table A2 page count")
        cover = " ".join(document[0].get_text().split())
        if any(marker not in cover for marker in (
                "Public Lands Administration Regulation Table A2",
                "October 28, 2026", "Alberta Energy Regulator")):
            raise ValueError("Unrecognized Table A2 revision")
        entries = []
        current = None
        for page_index in range(3, 17):
            tables = document[page_index].find_tables().tables
            if len(tables) != 1:
                raise ValueError(f"Page {page_index+1}: expected one requirements table")
            table = tables[0]
            if table.col_count != 27:
                raise ValueError(f"Page {page_index+1}: unexpected table columns")
            # First five rows are repeated table headers, not data.
            for cells in table.extract()[5:]:
                first = (cells[0] or "").strip()
                match = re.fullmatch(r"(\d{1,3})\.(?:\s+(\d+))?", first)
                if match:
                    number = int(match.group(1))
                    current = {"row": number, "page": page_index + 1,
                               "footnote": int(match.group(2)) if match.group(2) else None,
                               "_parts": {field: [] for field in
                                          ("disposition", "purpose", "activity",
                                           "definition", "rtf_approval", "rtf_authorization",
                                           "consultation", "required_plan", "survey_monuments")}}
                    entries.append(current)
                if current is None:
                    continue
                for field, column in (("disposition", 3), ("purpose", 7),
                                      ("activity", 8), ("definition", 9),
                                      ("rtf_approval", 10), ("rtf_authorization", 13),
                                      ("consultation", 17),
                                      ("required_plan", 20), ("survey_monuments", 23)):
                    if cells[column]:
                        current["_parts"][field].append(cells[column])
        if [entry["row"] for entry in entries] != list(range(1, 136)):
            raise ValueError("Incomplete or duplicate Table A2 row sequence")
        for entry in entries:
            for field, parts in entry.pop("_parts").items():
                entry[field] = _combine(parts)
            if entry["required_plan"] not in {"Sketch", "Survey", "Surveyor Sketch", "N/A"}:
                raise ValueError(f"Row {entry['row']}: unexpected plan type")
            if entry["disposition"] and not re.fullmatch(r"[A-Z]{3}", entry["disposition"]):
                raise ValueError(f"Row {entry['row']}: invalid disposition code")
            if any(entry[field] not in {"Yes", "No"}
                   for field in ("rtf_approval", "rtf_authorization")):
                raise ValueError(f"Row {entry['row']}: invalid RTF option")
            if entry["consultation"] not in {"PA", "AD", "AA", "N/A", "P/A", "PA*", "AA*", "N/A*"}:
                raise ValueError(f"Row {entry['row']}: unexpected consultation entry")
        return entries
    finally:
        document.close()
