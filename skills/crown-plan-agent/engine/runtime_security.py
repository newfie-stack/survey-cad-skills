"""Fail closed before PDF parsing on unmaintained or mixed runtime providers.

These dated minimum versions are a maintenance gate, not an advisory scanner or
security certificate. In particular, this does not clear native MuPDF advisories;
PDF signing/locking is outside the Crown Plan Agent's supported operations.
"""
from __future__ import annotations

import importlib
from importlib import metadata
import json
import re
import sys


POLICY_CHECKED_ON = "2026-11-19"
PYTHON_PATCH_FLOORS = {(3, 11): 18, (3, 12): 16, (3, 13): 18,
                       (3, 14): 10, (3, 15): 2}
PDF_PROVIDERS = ("pymupdf-lite", "PyMuPDF")
MINIMUM_BINDING = (2, 1, 0)
MINIMUM_MUPDF = (1, 28, 6)
_STABLE = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)(?:\.(0|[1-9]\d*))?(?:\.post(?:0|[1-9]\d*))?")


def _version(value, label):
    match = _STABLE.fullmatch(value) if isinstance(value, str) else None
    if match is None:
        raise RuntimeError(f"Unsupported {label} version; use the reviewed stable wheel set")
    return tuple(int(part or 0) for part in match.groups())


def _python_version():
    version = sys.version_info
    current = tuple(version[:3])
    if (len(current) != 3 or any(type(part) is not int for part in current)
            or current[:2] not in PYTHON_PATCH_FLOORS):
        raise RuntimeError("Unsupported Python branch; use a maintained Python release listed in the runtime policy")
    release = getattr(version, "releaselevel", version[3] if len(version) > 3 else "final")
    floor = PYTHON_PATCH_FLOORS[current[:2]]
    if release != "final" or current[2] < floor:
        needed = ".".join(map(str, (*current[:2], floor)))
        raise RuntimeError(f"Python security update required: use Python {needed} or a newer patch on this branch")
    return current


def _checked_runtime():
    python = _python_version()
    providers = []
    for name in PDF_PROVIDERS:
        try:
            providers.append((name, metadata.version(name)))
        except metadata.PackageNotFoundError:
            continue
    if not providers:
        raise RuntimeError("PDF runtime missing: install the reviewed requirements.txt in a fresh environment")
    if len(providers) != 1:
        raise RuntimeError("Conflicting PDF providers installed; create a fresh environment with the reviewed requirements.txt")
    provider, installed = providers[0]
    binding = _version(installed, "PyMuPDF")
    if binding[0] != 2 or binding < MINIMUM_BINDING:
        raise RuntimeError("PyMuPDF security update required: use supported stable version 2.1 or newer 2.x")
    try:
        module = importlib.import_module("pymupdf")
    except ImportError as exc:
        raise RuntimeError("Cannot import the reviewed PDF runtime; reinstall requirements.txt in a fresh environment") from exc
    reported = _version(getattr(module, "VersionBind", None), "PyMuPDF binding")
    if reported != binding:
        raise RuntimeError("PDF provider metadata and loaded binding disagree; use a fresh reviewed environment")
    native_text = getattr(module, "VersionFitz", None)
    native = _version(native_text, "MuPDF")
    if native < MINIMUM_MUPDF:
        raise RuntimeError("MuPDF security update required: use a reviewed build with MuPDF 1.28.6 or newer")
    info = {"minimum_runtime_policy": "SATISFIED", "policy_checked_on": POLICY_CHECKED_ON,
            "python": ".".join(map(str, python)), "provider": provider,
            "provider_version": installed, "pymupdf_version": module.VersionBind,
            "mupdf_version": native_text,
            "assessment_scope": "MINIMUM_RUNTIME_VERSIONS_ONLY",
            "advisory_review_required": True}
    return module, info


def load_pdf_runtime():
    """Return the canonical PDF module only after minimum-version validation."""
    return _checked_runtime()[0]


def runtime_status():
    """Report actual versions without opening any PDF or querying a service."""
    return _checked_runtime()[1]


def main():
    try:
        status = runtime_status()
    except RuntimeError as exc:
        print(f"PDF runtime unavailable: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(status, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
