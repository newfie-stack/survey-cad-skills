"""Attempt Table A2 refresh before review, with explicit stale-source status."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
from official_pdf_cache import refresh_official_pdf
from table_a2_discovery import (START_PAGE, _direct_a2_candidates, discover_a2_pdf, discover_a2_publication,
                                discover_a2_resource, fetch_publication_html)


def refresh_table_a2(cache_dir: str | Path, *, page_url: str = START_PAGE,
                     fetch_html=None, fetch_pdf=None, pinned_url: str | None = None) -> dict:
    folder = Path(cache_dir)
    active = folder / "plar_table_a2.pdf"
    try:
        if pinned_url is not None:
            target = urlparse(pinned_url)
            if (target.scheme != "https" or target.hostname != "open.alberta.ca"
                    or not target.path.lower().endswith(".pdf")
                    or target.username or target.password):
                raise ValueError("Invalid official pinned Table A2 PDF URL")
            pdf_url = pinned_url
        else:
            html = fetch_html(page_url) if fetch_html else fetch_publication_html(page_url)
            direct = _direct_a2_candidates(page_url, html)
            if len(direct) > 1:
                raise ValueError("Multiple direct Table A2 PDFs; refusing ambiguous update")
            if len(direct) == 1:
                pdf_url = discover_a2_pdf(page_url, html)
            else:
                publication_url = discover_a2_publication(page_url, html)
                publication_html = (fetch_html(publication_url) if fetch_html
                                    else fetch_publication_html(publication_url))
                pdf_url = discover_a2_resource(publication_url, publication_html)
        result = refresh_official_pdf(pdf_url, folder, fetch=fetch_pdf)
        return {**result, "refresh_status": "CHECKED_OFFICIAL_SOURCE",
                "regulatory_currency": "NOT_VERIFIED",
                "review_required": True}
    except (ValueError, OSError, TimeoutError) as exc:
        return {"refresh_status": "UNRESOLVED_SOURCE",
                "cached_pdf_available": active.is_file(),
                "regulatory_currency": "NOT_VERIFIED",
                "review_required": True,
                "reason": str(exc)}
