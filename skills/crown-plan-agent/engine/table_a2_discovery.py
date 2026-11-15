"""Conservative official-link discovery for PLAR Table A2.

Resolve only unambiguous, official PDF links. Ambiguity or an intermediate
publication page is not permission to guess a download URL.
"""
from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.request import Request, build_opener
from official_pdf_cache import _NoRedirect

START_PAGE = "https://www.alberta.ca/public-lands-administration-regulation"
MAX_HTML_BYTES = 2_000_000


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.href = None
        self.label = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.label = []

    def handle_data(self, data):
        if self.href is not None:
            self.label.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append((self.href, " ".join(self.label).strip()))
            self.href = None
            self.label = []


def _direct_a2_candidates(page_url: str, html: str) -> list[str]:
    parser = _Links()
    parser.feed(html)
    candidates = set()
    for href, label in parser.links:
        url = urljoin(page_url, href)
        target = urlparse(url)
        if (target.scheme == "https" and target.hostname == "open.alberta.ca"
                and target.path.lower().endswith(".pdf")
                and ("table a2" in label.casefold() or
                     ("plar" in label.casefold() and "a2" in label.casefold()))):
            candidates.add(url)
    return sorted(candidates)


def discover_a2_pdf(page_url: str, html: str) -> str:
    parsed = urlparse(page_url)
    if parsed.scheme != "https" or parsed.hostname not in {"www.alberta.ca", "alberta.ca", "open.alberta.ca"}:
        raise ValueError("Untrusted publication page")
    distinct = _direct_a2_candidates(page_url, html)
    if len(distinct) != 1:
        raise ValueError("No unique official Table A2 PDF link; manual source review required")
    return distinct[0]


def fetch_publication_html(page_url: str = START_PAGE) -> str:
    parsed = urlparse(page_url)
    if parsed.scheme != "https" or parsed.hostname not in {"www.alberta.ca", "alberta.ca", "open.alberta.ca"}:
        raise ValueError("Untrusted publication page")
    opener = build_opener(_NoRedirect())
    with opener.open(Request(page_url, headers={"User-Agent": "CrownPlanAgent/0.1"}), timeout=20) as response:
        data = response.read(MAX_HTML_BYTES + 1)
    if len(data) > MAX_HTML_BYTES:
        raise ValueError("Publication HTML exceeds size limit")
    return data.decode("utf-8", errors="replace")

def discover_a2_publication(page_url: str, html: str) -> str:
    """Find exactly one official Table A2 publication page."""
    parsed = urlparse(page_url)
    if parsed.scheme != "https" or parsed.hostname not in {"www.alberta.ca", "alberta.ca"}:
        raise ValueError("Untrusted Alberta listing page")
    parser = _Links()
    parser.feed(html)
    matches = set()
    for href, label in parser.links:
        target = urljoin(page_url, href)
        parsed_target = urlparse(target)
        if (parsed_target.scheme == "https" and parsed_target.hostname == "open.alberta.ca"
                and parsed_target.path.startswith("/publications/")
                and ("table a2" in label.casefold() or
                     "plar table a2" in parsed_target.path.casefold().replace("-", " "))):
            matches.add(target)
    if len(matches) != 1:
        raise ValueError("No unique official Table A2 publication page")
    return matches.pop()


def discover_a2_resource(publication_url: str, html: str) -> str:
    """Find one direct official PDF on the specifically selected publication page."""
    parsed = urlparse(publication_url)
    if parsed.scheme != "https" or parsed.hostname != "open.alberta.ca" or not parsed.path.startswith("/publications/"):
        raise ValueError("Untrusted publication URL")
    parser = _Links()
    parser.feed(html)
    pdfs = set()
    for href, label in parser.links:
        target = urljoin(publication_url, href)
        parsed_target = urlparse(target)
        if (parsed_target.scheme == "https" and parsed_target.hostname == "open.alberta.ca"
                and parsed_target.path.lower().endswith(".pdf")
                and "/resource/" in parsed_target.path):
            pdfs.add(target)
    if len(pdfs) != 1:
        raise ValueError("Publication PDF is ambiguous or unavailable")
    return pdfs.pop()
