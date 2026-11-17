"""Bounded original-source preparation for offline revision comparisons.

Known Crown review copies must not contribute their generated commentary as plan
text. This recognizer is deliberately specific; it cannot certify that arbitrary
third-party annotations or flattened copies are original plans.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re

from pdf_inspector import extract_pdf
from pdf_source import read_pdf_snapshot


_READ_CHUNK_BYTES = 1_048_576
_NOTE_SUBJECT = re.compile(r"R\d{3,}:\s+\S")
_INDEX_HEADER = re.compile(r"(?m)^Crown Plan Agent - Review notes \d+ of \d+\s*$")
_REVIEW_COPY_MESSAGE = "Known Crown Plan Agent review copy detected; use the original PDFs"


def read_bounded_file(path: Path, max_bytes: int) -> tuple[bytes, str]:
    """Read one immutable arbitrary-file snapshot, checking bounds during reads."""
    if type(max_bytes) is not int or max_bytes < 1:
        raise ValueError("File size limit must be a positive integer")
    source = Path(path)
    if not source.is_file():
        raise ValueError("Existing file path required")
    if source.stat().st_size > max_bytes:
        raise ValueError("File size limit exceeded")
    chunks = []
    size = 0
    digest = sha256()
    with source.open("rb") as handle:
        while True:
            chunk = handle.read(min(_READ_CHUNK_BYTES, max_bytes - size + 1))
            if not chunk:
                break
            size += len(chunk)
            if size > max_bytes:
                raise ValueError("File size limit exceeded")
            chunks.append(chunk)
            digest.update(chunk)
    return b"".join(chunks), digest.hexdigest()


def inspect_original_pdf(path: Path) -> dict:
    """Return a source-bound text inventory after rejecting known review copies.

    Inspect metadata on immutable source bytes, then verify extraction used those
    same bytes. Popup bodies, links and widgets are neither interpreted as review
    decisions nor removed from the original file.
    """
    source = Path(path)
    snapshot, digest = read_pdf_snapshot(source)
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PyMuPDF is required: pip install pymupdf") from exc
    try:
        document = fitz.open(stream=snapshot, filetype="pdf")
    except (RuntimeError, ValueError) as exc:
        raise ValueError("Invalid original PDF") from exc
    with document:
        if document.needs_pass:
            raise ValueError("Encrypted PDF not supported")
        if document.page_count > 100:
            raise ValueError("Page limit exceeded")
        page_frames = []
        for page in document:
            page_frames.append({
                "page": page.number + 1, "rotation": page.rotation,
                "mediabox_points": list(page.mediabox),
                "cropbox_points": list(page.cropbox),
                "display_rect_points": list(page.rect),
            })
            for annotation in page.annots() or ():
                info = annotation.info
                # The signature lives in metadata. Editing popup prose must not
                # turn a generated review copy into an accepted original.
                if (info.get("title") == "Crown Plan Agent"
                        and _NOTE_SUBJECT.match(info.get("subject") or "")):
                    raise ValueError(_REVIEW_COPY_MESSAGE)
            # The standard index has a stable numbered heading at its top.
            # Require its complete heading rather than a company-name mention.
            text = page.get_text("text", clip=fitz.Rect(0, 0, page.rect.width, 110))
            if _INDEX_HEADER.search(text):
                raise ValueError(_REVIEW_COPY_MESSAGE)
    inventory = extract_pdf(source, include_vectors=False)
    if inventory.get("source_sha256") != digest:
        raise ValueError("Source PDF changed during inspection; SHA-256 binding failed")
    # This register comes from the same immutable bytes whose hash extraction
    # has just verified. The normal 0.5 extractor remains unchanged.
    inventory["page_frames"] = page_frames
    return inventory
