"""Export reviewer inputs for a wholly invented drafting exercise."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from area_classification_fixture import (
    CASE_IDS as AREA_CASE_IDS, job_brief as area_job_brief, make_plan as make_area_plan,
)
from drafting_plan_fixture import CASE_IDS as DRAFTING_CASE_IDS, job_brief, make_drafting_plan


CASE_IDS = DRAFTING_CASE_IDS + AREA_CASE_IDS


REVIEW_INSTRUCTIONS = """# Drafting exercise

The plan PDF and job instructions are wholly invented. Use `plan.pdf` and
`job-brief.md` as the evidence for this drawing review.

Follow the Crown Plan Agent skill. Read the complete title block and notes on
every sheet first, then orient the main map using the visible drawing. Review
the actual sheets against the job brief and inspect the visible graphics.

Report each finding with its sheet location, observed evidence, and proposed
correction. Identify anything you could not verify and keep it unresolved.
Current regulatory compliance is unverified. Any survey control or geometry
shown is part of the invented exercise.
"""


def export_exercise(output: Path, case_id: str) -> dict:
    """Write a fresh exercise and return the manifest for reproducing it."""
    if case_id not in CASE_IDS:
        raise ValueError(f"Unknown invented drafting case: {case_id!r}")

    output.mkdir(parents=True, exist_ok=False)
    review_inputs = output / "review_inputs"
    review_inputs.mkdir()
    pdf = review_inputs / "plan.pdf"
    brief = review_inputs / "job-brief.md"
    instructions = review_inputs / "REVIEW.md"
    make_plan, make_brief = ((make_area_plan, area_job_brief) if case_id in AREA_CASE_IDS
                             else (make_drafting_plan, job_brief))
    make_plan(pdf, case_id)
    brief.write_text(make_brief(case_id), encoding="utf-8")
    instructions.write_text(REVIEW_INSTRUCTIONS, encoding="utf-8")

    manifest = {
        "schema_version": 1,
        "evidence_class": "WHOLLY_INVENTED_SYNTHETIC",
        "case_id": case_id,
        "files": {
            path.relative_to(output).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (pdf, brief, instructions)
        },
    }
    (output / "exercise-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New exercise directory")
    parser.add_argument("--case", required=True, choices=CASE_IDS, help="Invented drawing case")
    args = parser.parse_args()
    export_exercise(args.output, args.case)
    print(args.output / "exercise-manifest.json")


if __name__ == "__main__":
    main()
