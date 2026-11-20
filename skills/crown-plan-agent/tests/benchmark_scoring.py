"""Test-only scoring: physical defects and regression policy are separate."""
from __future__ import annotations


STATUSES = {"PASS", "FAIL", "REVIEW_REQUIRED"}
ALLOWED = {"must_pass": {"PASS"}, "must_detect": {"FAIL"},
           "must_abstain": {"REVIEW_REQUIRED"},
           "capability_gap": {"FAIL", "REVIEW_REQUIRED"}}
DEFAULT_POLICY = {"PASS": "must_pass", "FAIL": "must_detect",
                  "REVIEW_REQUIRED": "must_abstain"}
TOTAL_FIELDS = ("known_defects", "detected_defects", "missed_defects", "false_alarms",
                "false_clearances", "correct_abstentions", "unexpected_abstentions", "unresolved")


def score_case(expected, known_defects, findings, *, policies=None):
    """Grade actual results without equating a safe abstention with detection."""
    if (not isinstance(expected, dict) or not expected
            or any(not isinstance(k, str) or not k or not isinstance(v, str)
                   or v not in STATUSES for k, v in expected.items())):
        raise ValueError("Expected results must map check IDs to supported statuses")
    if (not isinstance(known_defects, list)
            or any(not isinstance(k, str) for k in known_defects)
            or len(set(known_defects)) != len(known_defects)
            or set(known_defects) - expected.keys()):
        raise ValueError("Known defects must be distinct expected checks")
    if policies is None:
        policies = {key: DEFAULT_POLICY[value] for key, value in expected.items()}
    if not isinstance(policies, dict) or set(policies) != set(expected):
        raise ValueError("Regression policies must cover exactly the expected checks")
    for key, policy in policies.items():
        if not isinstance(policy, str) or policy not in ALLOWED:
            raise ValueError("Unsupported regression policy")
        if ((policy == "must_pass" and (expected[key] != "PASS" or key in known_defects))
                or (policy == "must_detect" and (expected[key] != "FAIL" or key not in known_defects))
                or (policy in {"must_abstain", "capability_gap"} and expected[key] != "REVIEW_REQUIRED")
                or (policy == "capability_gap" and key not in known_defects)):
            raise ValueError("Regression policy contradicts frozen truth")
    if not isinstance(findings, list):
        raise ValueError("Findings must be a list")
    actual = {}
    for finding in findings:
        if not isinstance(finding, dict):
            raise ValueError("Each finding must be an object")
        key, status = finding.get("check_id"), finding.get("status")
        if (not isinstance(key, str) or not key or not isinstance(status, str)
                or status not in STATUSES or key in actual):
            raise ValueError("Duplicate or invalid actual check result")
        actual[key] = status
    missed = [key for key in known_defects if actual.get(key) != "FAIL"]
    false_clearance = sorted(key for key in expected if actual.get(key) == "PASS"
                             and (key in known_defects or policies[key] == "must_abstain"))
    failures = sorted(key for key in expected if actual.get(key) not in ALLOWED[policies[key]])
    missing, unexpected = sorted(expected.keys() - actual.keys()), sorted(actual.keys() - expected.keys())
    false_alarms = sum(status == "FAIL" and key not in known_defects for key, status in actual.items())
    return {"known_defects": len(known_defects), "known_defect_ids": list(known_defects),
            "detected_defects": len(known_defects) - len(missed), "missed_defects": len(missed),
            "false_alarms": false_alarms, "false_clearances": len(false_clearance),
            "unresolved": sum(status == "REVIEW_REQUIRED" for status in actual.values()),
            "false_clearance_ids": false_clearance,
            "correct_abstentions": sum(status == "REVIEW_REQUIRED" and actual.get(key) == status
                                       for key, status in expected.items()),
            "unexpected_abstentions": sum(status != "REVIEW_REQUIRED" and actual.get(key) == "REVIEW_REQUIRED"
                                          for key, status in expected.items()),
            "abstained_defect_ids": [key for key in known_defects if actual.get(key) == "REVIEW_REQUIRED"],
            "clear_abstention_ids": sorted(key for key in expected if key not in known_defects
                                          and actual.get(key) == "REVIEW_REQUIRED"),
            "missing_checks": missing, "unexpected_checks": unexpected,
            "expected_behavior_matched": actual == expected,
            "regression_gate_passed": not (failures or unexpected or false_clearance or false_alarms),
            "regression_failure_ids": failures,
            "missed_defect_ids": missed, "policies": dict(policies),
            "expected": dict(expected), "actual": actual}


def summarize_cases(rows):
    """Keep original-cohort progress and individual check categories visible."""
    totals = {key: sum(row[key] for row in rows) for key in TOTAL_FIELDS}
    cohorts, categories = {}, {}
    for row in rows:
        cohort = cohorts.setdefault(row["cohort"], {"case_count": 0, "check_count": 0,
                                                    **{key: 0 for key in TOTAL_FIELDS},
                                                    "regression_gate_passed": True})
        cohort["case_count"] += 1
        cohort["check_count"] += len(row["expected"])
        for key in TOTAL_FIELDS:
            cohort[key] += row[key]
        cohort["regression_gate_passed"] &= row["regression_gate_passed"]
        if set(row["categories"]) != set(row["expected"]):
            raise ValueError("Frozen categories must cover every expected check")
        for key in row["expected"]:
            category = row["categories"][key]
            if not isinstance(category, str) or not category:
                raise ValueError("Each check requires a category")
            bucket = categories.setdefault(category, dict.fromkeys(
                ("check_count", "known_defects", "detected_defects", "missed_defects",
                 "false_alarms", "false_clearances", "unresolved", "regression_failures"), 0))
            defect = key in row["known_defect_ids"]
            status = row["actual"].get(key)
            bucket["check_count"] += 1
            bucket["known_defects"] += defect
            bucket["detected_defects"] += defect and status == "FAIL"
            bucket["missed_defects"] += defect and status != "FAIL"
            bucket["false_alarms"] += not defect and status == "FAIL"
            bucket["false_clearances"] += key in row["false_clearance_ids"]
            bucket["unresolved"] += status == "REVIEW_REQUIRED"
            bucket["regression_failures"] += key in row["regression_failure_ids"]
    return {**totals, "by_cohort": cohorts, "by_category": categories}
