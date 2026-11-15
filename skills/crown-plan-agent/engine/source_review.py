"""Validate regulatory source citations without certifying current authority.

This is a structural evidence gate. A complete citation is not proof that the
document is current, applicable, or interpreted correctly.
"""
from __future__ import annotations
from datetime import date
from urllib.parse import urlparse

OFFICIAL_HOSTS = frozenset({"open.alberta.ca", "www.alberta.ca", "alberta.ca",
                            "www.aer.ca", "aer.ca", "kings-printer.alberta.ca"})


def review_source_record(record: dict) -> dict:
    if not isinstance(record, dict):
        raise TypeError("Source record must be a mapping")
    missing = []
    for key in ("publication_title", "section", "version_date", "source_url", "accessed_on"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            missing.append(key)
    url = record.get("source_url", "")
    parsed = urlparse(url) if isinstance(url, str) else urlparse("")
    official = parsed.scheme == "https" and parsed.hostname in OFFICIAL_HOSTS
    if not official:
        missing.append("official_https_source")
    for key in ("version_date", "accessed_on"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            try:
                date.fromisoformat(value)
            except ValueError:
                missing.append(key + "_valid_iso_date")
    return {
        "citation_complete": not missing,
        "missing_or_invalid": sorted(set(missing)),
        "source_status": "REVIEW_REQUIRED",
        "requires": [
            "Independently verify source version and supersession",
            "Confirm exact clause text and applicability for regulator, activity and stage",
            "Record independent reviewer and verification evidence",
        ],
    }
