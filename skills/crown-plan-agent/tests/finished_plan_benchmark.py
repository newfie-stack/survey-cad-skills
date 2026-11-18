"""Reproducible invented-plan benchmark with an isolated answer key.

Production checks receive PDFs and review intent only, never expected verdicts.
Known defects with REVIEW_REQUIRED outcomes remain missed detections in the score.
No real plan input is accepted by this fixture generator.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import platform
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from finished_plan_fixture import make_plan
from finished_plan_review import review_finished_plan
from review_cli import main as review_main

STATUSES = {"PASS", "FAIL", "REVIEW_REQUIRED"}
CASE_MUTATIONS = {
    "clean": {},
    "subject_conflict": {"subject": "LOT 8"},
    "note_omission": {"note": False},
    "main_scale_omission": {"scale": None},
    "scale_mismatch": {"scale": "1:2000"},
    "total_mismatch": {"total": "0.400"},
    "multiple_errors": {"subject": "LOT 8", "note": False, "scale": None, "total": "0.400"},
    "raster_only": {"raster": True},
    "competing_totals": {"duplicate_total": True},
    "missing_subject_field": {"second_subject": False},
    "rotated_clean": {"rotated": True},
    "split_font_clean": {"split_note": True},
    "two_sheet_conflict": {"subject": "LOT 8", "alternate_layout": True},
    "tolerance_boundary": {"total": "0.301"},
    "unverified_note_omission": {"note": False},
    "north_arrow_omission": {"north_arrow": False},
}


def score_case(expected: dict[str, str], known_defects: list[str], findings: list[dict]) -> dict:
    if not isinstance(expected, dict) or not expected or any(not isinstance(k, str) or v not in STATUSES for k, v in expected.items()):
        raise ValueError("Expected results must map check IDs to supported statuses")
    if not isinstance(known_defects, list) or any(not isinstance(k, str) for k in known_defects):
        raise ValueError("Known defects must be a list of check IDs")
    if len(set(known_defects)) != len(known_defects) or set(known_defects) - expected.keys():
        raise ValueError("Known defects must be distinct expected checks")
    if not isinstance(findings, list):
        raise ValueError("Findings must be a list")
    actual = {}
    for finding in findings:
        if not isinstance(finding, dict):
            raise ValueError("Each finding must be an object")
        key, status = finding.get("check_id"), finding.get("status")
        if not isinstance(key, str) or not isinstance(status, str) or status not in STATUSES or key in actual:
            raise ValueError("Duplicate or invalid actual check result")
        actual[key] = status
    detected = sum(actual.get(key) == "FAIL" for key in known_defects)
    false_alarms = sum(status == "FAIL" and key not in known_defects for key, status in actual.items())
    missing = sorted(expected.keys() - actual.keys())
    return {"known_defects": len(known_defects), "detected_defects": detected,
            "missed_defects": len(known_defects) - detected, "false_alarms": false_alarms,
            "correct_abstentions": sum(status == "REVIEW_REQUIRED" and actual.get(key) == status for key, status in expected.items()),
            "unexpected_abstentions": sum(status != "REVIEW_REQUIRED" and actual.get(key) == "REVIEW_REQUIRED" for key, status in expected.items()),
            "missing_checks": missing, "unexpected_checks": sorted(actual.keys() - expected.keys()),
            "expected_behavior_matched": actual == expected,
            "missed_defect_ids": [key for key in known_defects if actual.get(key) != "FAIL"],
            "expected": expected, "actual": actual}


def code_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    paths = sorted(path for folder in ("engine", "tests") for path in (root / folder).rglob("*")
                   if path.is_file() and path.suffix in {".py", ".json"} and "__pycache__" not in path.parts)
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode() + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def run_benchmark(output: Path) -> dict:
    """Generate new invented fixtures, run actual CLI, then consult frozen truth."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    skill = Path(__file__).resolve().parents[1]
    scenario = {"land_class": "alberta_crown", "regulator": "AER", "stage": "initial",
                "disposition": "LOC", "plan_type": "sketch"}
    actual_cases = {}
    for name, mutations in CASE_MUTATIONS.items():
        folder = output / name
        folder.mkdir()
        pdf = folder / "invented-plan.pdf"
        spec = make_plan(pdf, **mutations)
        presence_region = copy.deepcopy(spec["checks"][0]["regions"][1])
        presence_region.pop("label", None)
        spec["checks"].append({"id": "subject_presence", "kind": "required_text",
                               "description": "Expected repeated subject field is present",
                               "basis": "Invented job instruction: include a subject reference in this mapped region",
                               "regions": [presence_region], "expected": "SUBJECT:"})
        if name == "tolerance_boundary":
            spec["checks"][3]["tolerance"] = "0.001"
        if name == "unverified_note_omission":
            spec["checks"][2]["regions"][0].pop("coverage_review")
        spec_path, scenario_path = folder / "checks.json", folder / "scenario.json"
        spec_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        scenario_path.write_text(json.dumps(scenario, indent=2) + "\n", encoding="utf-8")
        ledger = review_finished_plan(pdf, spec)
        (folder / "qc-ledger.json").write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = review_main([str(pdf), "--scenario", str(scenario_path), "--offline",
                                     "--reference-cache", str(folder / "empty-cache"),
                                     "--finished-plan-spec", str(spec_path), "--output", str(folder / "review.md")])
        text = (folder / "review.md").read_text(encoding="utf-8")
        actual_cases[name] = {"ledger": ledger, "cli_exit_code": exit_code,
                              "cli_qc_section_matches": text.endswith(ledger["report_markdown"])}
    # Truth is used only after every production review has finished.
    truth_path = skill / "tests" / "fixtures" / "finished_plan_truth.json"
    truth_bytes = truth_path.read_bytes()
    truth = json.loads(truth_bytes)
    if set(truth["cases"]) != set(actual_cases):
        raise ValueError("Benchmark cases and frozen answer key differ")
    case_results = []
    for name, actual in actual_cases.items():
        answer = truth["cases"][name]
        expected = {**truth["default_expected"], **answer["overrides"]}
        score = score_case(expected, answer["known_defects"], actual["ledger"]["findings"])
        case_results.append({"case_id": name, **score,
                             "source_sha256": actual["ledger"]["source_sha256"],
                             "spec_sha256": actual["ledger"]["spec_sha256"],
                             "cli_exit_code": actual["cli_exit_code"],
                             "cli_qc_section_matches": actual["cli_qc_section_matches"]})
    totals = {key: sum(row[key] for row in case_results) for key in
              ("known_defects", "detected_defects", "missed_defects", "false_alarms", "correct_abstentions", "unexpected_abstentions")}
    import fitz
    report = {"schema_version": 1, "evidence_class": "WHOLLY_INVENTED_SYNTHETIC",
              "independent_reviewer_acceptance": "NOT_PERFORMED", "production_acceptance": "NOT_ESTABLISHED",
              "case_count": len(case_results), "check_count": sum(len(r["expected"]) for r in case_results),
              "code_test_fingerprint": code_fingerprint(skill),
              "truth_sha256": hashlib.sha256(truth_bytes).hexdigest(),
              "python_version": platform.python_version(), "pymupdf_version": fitz.VersionBind,
              **totals, "defect_recall": totals["detected_defects"] / totals["known_defects"] if totals["known_defects"] else None,
              "all_expected_behaviors_matched": all(r["expected_behavior_matched"] and r["cli_exit_code"] == 0 and r["cli_qc_section_matches"] for r in case_results),
              "case_results": case_results,
              "limitations": ["Developer-authored fixtures, review specifications and answer key; not independent acceptance",
                              "Selected native-text regions and supplied completeness declarations, not automatic whole-sheet understanding",
                              "Graphical omissions and incomplete/ambiguous evidence remain unresolved, and known defects among them count as misses",
                              "No private plans, current-source regulatory validation, geometric reconstruction or field-truth verification"]}
    (output / "benchmark.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = ["# Finished-plan QC: synthetic error-detection benchmark", "",
             "**Not a production acceptance or regulatory-compliance result.**", "",
             f"Cases: {report['case_count']}; check outcomes: {report['check_count']}.",
             f"Known planted defects: {totals['known_defects']}; detected: {totals['detected_defects']}; missed: {totals['missed_defects']}; false alarms: {totals['false_alarms']}.",
             f"Expected bounded behavior matched: {report['all_expected_behaviors_matched']}. This does not mean all defects were detected.",
             f"Python {report['python_version']}; PyMuPDF {report['pymupdf_version']}.",
             f"Code/test fingerprint: `{report['code_test_fingerprint']}`", f"Answer-key SHA-256: `{report['truth_sha256']}`", "",
             "| Case | Detected | Missed | False alarms | Expected behavior |", "|---|---:|---:|---:|---|"]
    for row in case_results:
        lines.append(f"| {row['case_id']} | {row['detected_defects']} | {row['missed_defects']} | {row['false_alarms']} | {row['expected_behavior_matched']} |")
    lines.extend(["", "## Limits", "", *["- " + note for note in report["limitations"]], ""])
    (output / "benchmark.md").write_text("\n".join(lines), encoding="utf-8")
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run wholly invented finished-plan error-detection cases")
    parser.add_argument("--output", required=True, type=Path, help="New directory; never overwritten")
    args = parser.parse_args(argv)
    report = run_benchmark(args.output)
    print(json.dumps({k: report[k] for k in ("case_count", "known_defects", "detected_defects", "missed_defects", "false_alarms", "all_expected_behaviors_matched")}, indent=2))
    print("Synthetic benchmark only; known unresolved defects are counted as misses.")
    return 0 if report["all_expected_behaviors_matched"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
