"""Read bounded, immutable PDF source snapshots for evidence binding."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path


def read_pdf_snapshot(path: str | Path, max_file_bytes: int = 100_000_000) -> tuple[bytes, str]:
    """Return source bytes and their lowercase SHA-256; PDF parsing is separate."""
    if type(max_file_bytes) is not int or max_file_bytes < 1:
        raise ValueError("PDF file size limit must be a positive integer")
    source = Path(path)
    if source.suffix.lower() != ".pdf" or not source.is_file():
        raise ValueError("Existing PDF path required")
    if source.stat().st_size > max_file_bytes:
        raise ValueError("PDF file size limit exceeded")
    # A file may grow after stat; never use an unbounded read of that path.
    with source.open("rb") as handle:
        snapshot = handle.read(max_file_bytes + 1)
    if len(snapshot) > max_file_bytes:
        raise ValueError("PDF file size limit exceeded")
    if not snapshot:
        raise ValueError("Empty PDF not supported")
    return snapshot, sha256(snapshot).hexdigest()
