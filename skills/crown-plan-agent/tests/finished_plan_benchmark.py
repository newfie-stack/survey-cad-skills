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
from benchmark_scoring import DEFAULT_POLICY, score_case, summarize_cases

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
    from drafting_plan_fixture import CASE_IDS, make_drafting_plan, scenario as drafting_scenario
    legacy_scenario = {"land_class": "alberta_crown", "regulator": "AER", "stage": "initial",
                       "disposition": "LOC", "plan_type": "sketch"}
    actual_cases = {}
    for name in (*CASE_MUTATIONS, *CASE_IDS):
        folder = output / name
        folder.mkdir()
        pdf = folder / "invented-plan.pdf"
        if name in CASE_MUTATIONS:
            spec = make_plan(pdf, **CASE_MUTATIONS[name])
            scenario, cohort = legacy_scenario, "legacy"
            checks = {check["id"]: check for check in spec["checks"]}
            presence_region = copy.deepcopy(checks["subject"]["regions"][1])
            presence_region.pop("label", None)
            spec["checks"].append({"id": "subject_presence", "kind": "required_text",
                                   "description": "Expected repeated subject field is present",
                                   "basis": "Invented job instruction: include a subject reference in this mapped region",
                                   "regions": [presence_region], "expected": "SUBJECT:"})
            if name == "tolerance_boundary":
                checks["area_sum"]["tolerance"] = "0.001"
            if name == "unverified_note_omission":
                checks["units_note"]["regions"][0].pop("coverage_review")
        else:
            spec = make_drafting_plan(pdf, name)
            scenario, cohort = drafting_scenario(name), "drafting"
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
        opening = text.split("## Finished-plan drawing QC", 1)[0]
        counts = {status: sum(item["status"] == status for item in ledger["findings"])
                  for status in ("PASS", "FAIL", "REVIEW_REQUIRED")}
        summary_line = (f"Executed {len(ledger['findings'])} selected finished-plan drawing-QC checks "
                        f"(PASS={counts['PASS']}; FAIL={counts['FAIL']}; REVIEW_REQUIRED={counts['REVIEW_REQUIRED']})")
        attention = f"Selected drawing QC has {counts['FAIL']} failed and {counts['REVIEW_REQUIRED']} unresolved checks"
        summary_matches = (summary_line in opening
                           and (not (counts["FAIL"] or counts["REVIEW_REQUIRED"]) or attention in opening)
                           and ledger["overall_status"] == "REVIEW_REQUIRED"
                           and ledger["regulatory_status"] == "NOT_ASSESSED")
        actual_cases[name] = {"ledger": ledger, "cohort": cohort, "cli_exit_code": exit_code,
                              "cli_summary_matches": summary_matches,
                              "cli_qc_section_matches": text.endswith(ledger["report_markdown"])}
    # Truth is used only after every production review has finished.
    truth_paths = {"legacy": skill / "tests/fixtures/finished_plan_truth.json",
                   "drafting": skill / "tests/fixtures/drafting_plan_truth.json"}
    truth_bytes = {cohort: path.read_bytes() for cohort, path in truth_paths.items()}
    truths = {cohort: json.loads(raw) for cohort, raw in truth_bytes.items()}
    all_truth_names = [name for truth in truths.values() for name in truth["cases"]]
    if len(set(all_truth_names)) != len(all_truth_names) or set(all_truth_names) != set(actual_cases):
        raise ValueError("Benchmark cases and frozen answer key differ")
    case_results = []
    for name, actual in actual_cases.items():
        truth = truths[actual["cohort"]]
        answer = truth["cases"][name]
        expected = answer.get("expected", {**truth.get("default_expected", {}), **answer.get("overrides", {})})
        policies = {key: DEFAULT_POLICY[status] for key, status in expected.items()}
        policies.update(answer.get("policy_overrides", {}))
        score = score_case(expected, answer["known_defects"], actual["ledger"]["findings"], policies=policies)
        case_results.append({"case_id": name, "cohort": actual["cohort"],
                             "categories": truth["categories"], **score,
                             "source_sha256": actual["ledger"]["source_sha256"],
                             "spec_sha256": actual["ledger"]["spec_sha256"],
                             "cli_exit_code": actual["cli_exit_code"],
                             "cli_summary_matches": actual["cli_summary_matches"],
                             "cli_qc_section_matches": actual["cli_qc_section_matches"]})
    totals = summarize_cases(case_results)
    import pymupdf
    truth_hashes = {cohort: hashlib.sha256(raw).hexdigest() for cohort, raw in truth_bytes.items()}
    report = {"schema_version": 2, "evidence_class": "WHOLLY_INVENTED_SYNTHETIC",
              "benchmark_scope": "DETERMINISTIC_SELECTED_REGIONS", "assisted_agent_review_evaluated": False,
              "independent_reviewer_acceptance": "NOT_PERFORMED", "production_acceptance": "NOT_ESTABLISHED",
              "case_count": len(case_results), "check_count": sum(len(r["expected"]) for r in case_results),
              "code_test_fingerprint": code_fingerprint(skill),
              "truth_sha256": hashlib.sha256(json.dumps(truth_hashes, sort_keys=True).encode()).hexdigest(),
              "truth_files": truth_hashes,
              "python_version": platform.python_version(), "pymupdf_version": pymupdf.VersionBind,
              **totals, "defect_recall": totals["detected_defects"] / totals["known_defects"] if totals["known_defects"] else None,
              "all_defects_detected": totals["missed_defects"] == 0,
              "regression_gate_passed": all(r["regression_gate_passed"] and r["cli_exit_code"] == 0
                                            and r["cli_summary_matches"] and r["cli_qc_section_matches"] for r in case_results),
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
             f"Known planted defects: {totals['known_defects']}; detected: {totals['detected_defects']}; missed: {totals['missed_defects']}; false alarms: {totals['false_alarms']}; false clearances: {totals['false_clearances']}.",
             f"Regression gate passed: {report['regression_gate_passed']}; all defects detected: {report['all_defects_detected']}.",
             "Regression success preserves the required checks and evidence limits; it does not mean all defects were detected.",
             f"Python {report['python_version']}; PyMuPDF {report['pymupdf_version']}.",
             f"Code/test fingerprint: `{report['code_test_fingerprint']}`", f"Answer-key SHA-256: `{report['truth_sha256']}`", "",
             "| Case | Cohort | Detected | Missed | False alarms | False clearances | Gate |", "|---|---|---:|---:|---:|---:|---|"]
    for row in case_results:
        lines.append(f"| {row['case_id']} | {row['cohort']} | {row['detected_defects']} | {row['missed_defects']} | {row['false_alarms']} | {row['false_clearances']} | {row['regression_gate_passed']} |")
    for title, buckets in (("Cohorts", report["by_cohort"]), ("Check categories", report["by_category"])):
        lines.extend(["", f"## {title}", "", "| Group | Known | Detected | Missed | False alarms | False clearances | Unresolved |",
                      "|---|---:|---:|---:|---:|---:|---:|"])
        for name, row in buckets.items():
            lines.append(f"| {name} | {row['known_defects']} | {row['detected_defects']} | {row['missed_defects']} | {row['false_alarms']} | {row['false_clearances']} | {row['unresolved']} |")
    lines.extend(["", "## Follow-up", ""])
    for row in case_results:
        if row["missed_defect_ids"] or row["regression_failure_ids"]:
            lines.append(f"- {row['case_id']}: missed defects={row['missed_defect_ids']}; regression failures={row['regression_failure_ids']}.")
    lines.extend(["", "## Limits", "", *["- " + note for note in report["limitations"]], ""])
    (output / "benchmark.md").write_text("\n".join(lines), encoding="utf-8")
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Run wholly invented finished-plan error-detection cases")
    parser.add_argument("--output", required=True, type=Path, help="New directory; never overwritten")
    args = parser.parse_args(argv)
    report = run_benchmark(args.output)
    print(json.dumps({k: report[k] for k in ("case_count", "known_defects", "detected_defects", "missed_defects", "false_alarms", "false_clearances", "regression_gate_passed", "all_defects_detected")}, indent=2))
    print("Synthetic benchmark only; known unresolved defects are counted as misses.")
    return 0 if report["regression_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
