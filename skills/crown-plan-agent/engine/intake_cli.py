"""Offline source-bound plan intake and bounded check-preparation command."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from artifact_publication import publish_artifacts
from finished_plan_spec import load_spec
from pdf_source import read_pdf_snapshot
from plan_intake import discover_plan, prepare_finished_plan

MAX_OUTPUT_BYTES = 64_000_000


def _preflight(pdf, output, context, spec_output):
    if (context is None) != (spec_output is None):
        raise ValueError("--context-spec and --spec-output must be supplied together")
    destinations = [output] + ([spec_output] if spec_output is not None else [])
    resolved = [path.resolve() for path in destinations]
    if len(set(resolved)) != len(resolved):
        raise ValueError("Intake output paths must be distinct")
    inputs = {pdf.resolve()} | ({context.resolve()} if context is not None else set())
    for path, destination in zip(destinations, resolved):
        if path.suffix.lower() != ".json":
            raise ValueError("Intake outputs must be JSON (.json) files")
        if destination in inputs:
            raise ValueError("Intake output must not overwrite or alias an input")
        if path.exists() or path.is_symlink():
            raise FileExistsError("Intake output already exists")
        if not destination.parent.is_dir():
            raise ValueError("Intake output parent directory must already exist")
    _, digest = read_pdf_snapshot(pdf)
    spec = load_spec(context) if context is not None else None
    if spec is not None and spec["source_sha256"] != digest:
        raise ValueError("Source SHA-256 digest does not match the context specification")
    return spec


def _payload(value):
    payload = (json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    if len(payload) > MAX_OUTPUT_BYTES:
        raise ValueError("Intake JSON output size limit exceeded")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline source-bound plan intake (review required)")
    parser.add_argument("pdf", type=Path, help="Authorized local source PDF")
    parser.add_argument("--output", required=True, type=Path, help="New private JSON intake or preparation artifact")
    parser.add_argument("--context-spec", type=Path, help="Strict v1 check requests with reviewed semantic context boxes")
    parser.add_argument("--spec-output", type=Path, help="New ready v1 spec JSON; null if no request is ready")
    args = parser.parse_args(argv)
    try:
        spec = _preflight(args.pdf, args.output, args.context_spec, args.spec_output)
        result = prepare_finished_plan(args.pdf, spec) if spec is not None else discover_plan(args.pdf)
        artifacts = {args.output: _payload(result)}
        if args.spec_output is not None:
            artifacts[args.spec_output] = _payload(result["spec"])
        publish_artifacts(artifacts)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        parser.error("Invalid intake inputs or evidence: " + str(exc))
    print(str(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
