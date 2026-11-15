"""Fail-closed official PDF cache refresh.

The caller supplies a discovered official PDF resource URL. This module does not
guess resource URLs, interpret regulatory currency, or update legal rules.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlparse
from urllib.request import build_opener, HTTPRedirectHandler, Request


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ValueError("Redirect requires separate official-source validation")


def _validate_table_a2(data: bytes) -> None:
    """Require the known Table A2 revision and complete row extraction."""
    # Structural and document-identity validation; not legal currency verification.
    try:
        from table_a2_rows import extract_a2_rows
        with tempfile.NamedTemporaryFile(suffix=".pdf") as candidate:
            candidate.write(data)
            candidate.flush()
            extract_a2_rows(candidate.name)
    except (RuntimeError, ValueError, OSError) as exc:
        raise ValueError("Downloaded PDF failed structural validation") from exc

def refresh_official_pdf(url: str, directory: str | Path, *, fetch=None,
                         max_bytes: int = 40_000_000) -> dict:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "open.alberta.ca" or parsed.username or parsed.password:
        raise ValueError("Only direct HTTPS open.alberta.ca PDF resources are accepted")
    if type(max_bytes) is not int or not 100 <= max_bytes <= 100_000_000:
        raise ValueError("Invalid download size limit")
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    active = folder / "plar_table_a2.pdf"
    manifest = folder / "plar_table_a2.json"
    if fetch is None:
        opener = build_opener(_NoRedirect())
        def fetch(resource_url):
            with opener.open(Request(resource_url, headers={"User-Agent": "CrownPlanAgent/0.1"}), timeout=20) as response:
                if response.headers.get("Content-Length") and int(response.headers["Content-Length"]) > max_bytes:
                    raise ValueError("PDF exceeds size limit")
                return response.read(max_bytes + 1)
    data = fetch(url)
    if not isinstance(data, bytes) or len(data) > max_bytes or len(data) < 100 or not data.startswith(b"%PDF-"):
        raise ValueError("Download is not a valid-size PDF candidate")
    _validate_table_a2(data)
    digest = hashlib.sha256(data).hexdigest()
    previous = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
    version = folder / ("plar_table_a2_" + digest[:16] + ".pdf")
    if version.exists():
        if hashlib.sha256(version.read_bytes()).hexdigest() != digest:
            raise ValueError("Historical PDF version checksum mismatch; manual review required")
    else:
        with version.open("xb") as handle:
            handle.write(data)
    if (previous.get("sha256") == digest and active.is_file()
            and hashlib.sha256(active.read_bytes()).hexdigest() == digest):
        return {"status": "UNCHANGED", "sha256": digest, "path": str(active),
                "currency": "NOT_VERIFIED", "source_url": url}
    # Atomically update active PDF, then manifest. Historical hash-named copies remain.
    with tempfile.NamedTemporaryFile(dir=folder, suffix=".pdf", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
    try:
        os.replace(temporary, active)
    finally:
        temporary.unlink(missing_ok=True)
    new_manifest = {"source_url": url, "sha256": digest,
                    "source_file": version.name,
                    "currency": "NOT_VERIFIED",
                    "review_required": True}
    with tempfile.NamedTemporaryFile(dir=folder, suffix=".json", mode="w",
                                     encoding="utf-8", delete=False) as handle:
        temp_manifest = Path(handle.name)
        json.dump(new_manifest, handle, indent=2)
    try:
        os.replace(temp_manifest, manifest)
    finally:
        temp_manifest.unlink(missing_ok=True)
    return {"status": "UPDATED", "sha256": digest, "path": str(active),
            "currency": "NOT_VERIFIED", "source_url": url}
