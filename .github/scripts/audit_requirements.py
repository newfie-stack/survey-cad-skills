"""Audit every explicitly pinned package without pip's bootstrap omissions."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name, canonicalize_version
from packaging.version import Version


def _version(value):
    if not isinstance(value, str):
        raise ValueError("Package version must be a string")
    return canonicalize_version(str(Version(value)))


def expected_dependencies(paths):
    """Read the full hash-locked graph, applying current-environment markers."""
    if not paths:
        raise ValueError("At least one requirements file is required")
    expected = {}
    for path in paths:
        pending = ""
        for physical in Path(path).read_text(encoding="utf-8").splitlines():
            line = physical.strip()
            if not line or line.startswith("#"):
                continue
            pending += line[:-1] + " " if line.endswith("\\") else line
            if line.endswith("\\"):
                continue
            lexer = shlex.shlex(pending, posix=False)
            lexer.whitespace_split = True
            tokens = list(lexer)
            pending = ""
            if not tokens:
                continue
            if tokens in (["--only-binary=:all:"], ["--only-binary", ":all:"], ["--require-hashes"]):
                continue
            requirement_tokens, hashes = [], []
            index = 0
            while index < len(tokens):
                token = tokens[index]
                if token == "--hash":
                    index += 1
                    if index == len(tokens):
                        raise ValueError(f"Missing hash in {path}")
                    hashes.append(tokens[index])
                elif token.startswith("--hash="):
                    hashes.append(token.partition("=")[2])
                elif token.startswith("-"):
                    raise ValueError(f"Unsupported requirements option: {token}")
                else:
                    requirement_tokens.append(token)
                index += 1
            if not hashes or any(not re.fullmatch(r"sha256:[a-fA-F0-9]{64}", value) for value in hashes):
                raise ValueError(f"Each requirement needs a complete SHA256 hash in {path}")
            requirement = Requirement(" ".join(requirement_tokens))
            pins = list(requirement.specifier)
            if requirement.url or len(pins) != 1 or pins[0].operator != "==" or "*" in pins[0].version:
                raise ValueError(f"Exact version pin required: {requirement.name}")
            version = _version(pins[0].version)
            if requirement.marker and not requirement.marker.evaluate():
                continue
            name = canonicalize_name(requirement.name, validate=True)
            if name in expected and expected[name] != version:
                raise ValueError(f"Conflicting version pins: {name}")
            expected[name] = version
        if pending:
            raise ValueError(f"Unfinished requirements continuation in {path}")
    if not expected:
        raise ValueError("No active pinned dependencies to audit")
    return expected


def verify_coverage(expected, report):
    """Require one matching, unskipped, vulnerability-free entry per package."""
    if not isinstance(report, dict) or not isinstance(report.get("dependencies"), list):
        raise ValueError("Audit report has no dependency list")
    normalized = {canonicalize_name(name, validate=True): _version(version)
                  for name, version in expected.items()}
    observed = {}
    for dependency in report["dependencies"]:
        if not isinstance(dependency, dict) or "skip_reason" in dependency:
            raise ValueError("Audit contains skipped or malformed dependency evidence")
        name = canonicalize_name(dependency.get("name", ""), validate=True)
        if name in observed:
            raise ValueError(f"Duplicate audited package: {name}")
        observed[name] = _version(dependency.get("version"))
        if not isinstance(dependency.get("vulns"), list) or dependency["vulns"]:
            raise ValueError(f"Vulnerabilities or incomplete vulnerability evidence: {name}")
    missing = sorted(set(normalized) - set(observed))
    extra = sorted(set(observed) - set(normalized))
    if missing or extra:
        raise ValueError(f"Audit coverage mismatch; missing={missing}, unexpected={extra}")
    wrong = sorted(name for name in normalized if normalized[name] != observed[name])
    if wrong:
        raise ValueError(f"Audited version mismatch: {wrong}")
    return len(normalized)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-r", "--requirement", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        expected = expected_dependencies(args.requirement)
        if os.path.lexists(args.output):
            raise ValueError(f"Output already exists: {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".dependency-audit-", dir=args.output.parent) as directory:
            scratch = Path(directory) / "audit.json"
            command = [sys.executable, "-m", "pip_audit", "--disable-pip", "--strict",
                       "--require-hashes", "--vulnerability-service", "pypi",
                       "--cache-dir", str(Path(directory) / "http-cache"),
                       "--progress-spinner", "off", "--format", "json", "--output", str(scratch)]
            for path in args.requirement:
                command += ["-r", str(path)]
            result = subprocess.run(command, check=False)
            coverage_error = None
            if scratch.is_file():
                raw = scratch.read_bytes()
                with args.output.open("xb") as destination:
                    destination.write(raw)
                try:
                    verify_coverage(expected, json.loads(raw))
                except (ValueError, TypeError) as error:
                    coverage_error = str(error)
            else:
                coverage_error = "Auditor did not produce a JSON report"
            if coverage_error:
                print(f"Audit evidence rejected: {coverage_error}", file=sys.stderr)
            if result.returncode:
                print(f"Auditor exited {result.returncode}; report: {args.output}", file=sys.stderr)
                return result.returncode if result.returncode > 0 else 128 - result.returncode
            if coverage_error:
                return 1
        print(f"Audited all {len(expected)} pinned packages; no known findings; report: {args.output}")
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(f"Dependency audit failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
