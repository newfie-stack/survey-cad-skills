"""Tally source-bound semantic adjudication; never infer matches from wording.

A reviewer and a separate grader make the observations and semantic decisions.
This helper validates their accounting and counts unique frozen truth issues.
It is not a language-model grader or professional acceptance. Compound claims
must be split into traceable atomic units before this accounting step; preserve
the original review and the normalization record separately.
"""
from __future__ import annotations

import re


KINDS = {"finding", "clearance", "unresolved", "manual"}
VERDICTS = {
    "finding": {"FOUND", "FALSE_ALARM", "DUPLICATE", "UNSUPPORTED", "ORACLE_REVIEW"},
    "clearance": {"CLEAR", "FALSE_CLEARANCE", "UNSUPPORTED"},
    "unresolved": {"UNRESOLVED"}, "manual": {"MANUAL"},
}


def _identifier(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 200


def _ids(values, label):
    if (not isinstance(values, list) or any(not _identifier(v) for v in values)
            or len(set(values)) != len(values)):
        raise ValueError(f"{label} must contain distinct nonempty identifiers")
    return values


def validate_normalization(original, normalized, mappings):
    """Check source/claim coverage; semantic faithfulness still needs a grader."""
    for review in (original, normalized):
        if (not isinstance(review, dict) or not isinstance(review.get("claims"), list)
                or any(not isinstance(c, dict) for c in review["claims"])):
            raise ValueError("Normalization requires original and atomic claim records")
    source = original.get("source_sha256")
    if (not isinstance(source, str) or not re.fullmatch(r"[a-f0-9]{64}", source)
            or normalized.get("source_sha256") != source):
        raise ValueError("Normalization must preserve source identity")
    original_ids = _ids([c.get("id") for c in original["claims"]], "Original claims")
    normalized_ids = _ids([c.get("id") for c in normalized["claims"]], "Atomic claims")
    if not isinstance(mappings, list) or any(not isinstance(m, dict) for m in mappings):
        raise ValueError("Normalization requires a mapping list")
    parents = _ids([m.get("parent_id") for m in mappings], "Mapped original claims")
    if set(parents) != set(original_ids):
        raise ValueError("Every original claim must survive normalization")
    raw = {c["id"]: c for c in original["claims"]}
    atomic = {c["id"]: c for c in normalized["claims"]}
    assigned = set()
    for mapping in mappings:
        units = _ids(mapping.get("normalized_ids"), "Mapped atomic units")
        if (not units or not isinstance(mapping.get("rationale"), str)
                or not mapping["rationale"].strip() or set(units) - set(normalized_ids)
                or assigned.intersection(units)):
            raise ValueError("Each atomic unit needs one traceable original and rationale")
        parent = mapping["parent_id"]
        for unit in units:
            if atomic[unit].get("parent_id") != parent or atomic[unit].get("kind") != raw[parent].get("kind"):
                raise ValueError("Normalization cannot reassign or reclassify a saved claim")
        assigned.update(units)
    if assigned != set(normalized_ids):
        raise ValueError("Atomic claims cannot be invented outside the original mapping")
    return len(normalized_ids)


def score_trial(expected_defect_ids, review, adjudications, *, source_sha256):
    """Count adjudicated claims against one exact, frozen source document."""
    expected = _ids(expected_defect_ids, "Frozen defects")
    if (not isinstance(source_sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", source_sha256)
            or not isinstance(review, dict) or review.get("source_sha256") != source_sha256):
        raise ValueError("Review and frozen source identity disagree")
    claims = review.get("claims")
    if not isinstance(claims, list):
        raise ValueError("Review requires an atomic claim list")
    by_claim = {}
    for claim in claims:
        if (not isinstance(claim, dict) or not _identifier(claim.get("id"))
                or claim.get("id") in by_claim or not isinstance(claim.get("kind"), str)
                or claim["kind"] not in KINDS
                or not isinstance(claim.get("claim"), str) or not claim["claim"].strip()
                or not isinstance(claim.get("location"), str) or not claim["location"].strip()
                or not isinstance(claim.get("evidence"), list) or not claim["evidence"]
                or any(not isinstance(v, str) or not v.strip() for v in claim["evidence"])):
            raise ValueError("Each saved claim needs a unique ID, supported kind and source evidence")
        by_claim[claim["id"]] = claim
    if not isinstance(adjudications, list):
        raise ValueError("Adjudication requires a list")
    graded = {}
    for row in adjudications:
        if not isinstance(row, dict) or row.get("claim_id") not in by_claim:
            raise ValueError("Adjudication references an unknown claim")
        cid = row["claim_id"]
        if cid in graded:
            raise ValueError("Each atomic claim needs exactly one adjudication")
        verdict = row.get("verdict")
        if not isinstance(verdict, str) or verdict not in VERDICTS[by_claim[cid]["kind"]]:
            raise ValueError("Adjudication verdict contradicts the claim kind")
        if not isinstance(row.get("rationale"), str) or not row["rationale"].strip():
            raise ValueError("Semantic adjudication needs a rationale")
        defects = _ids(row.get("defect_ids"), "Adjudicated defects")
        if set(defects) - set(expected):
            raise ValueError("Adjudication references an issue outside frozen truth")
        if verdict in {"FOUND", "FALSE_CLEARANCE"} and not defects:
            raise ValueError("A matched finding or false clearance needs a truth issue")
        if verdict == "FOUND" and len(defects) != 1:
            raise ValueError("An atomic finding matches exactly one frozen issue; split compound claims first")
        if verdict not in {"FOUND", "FALSE_CLEARANCE", "UNRESOLVED", "MANUAL"} and defects:
            raise ValueError("This verdict cannot receive truth-issue credit")
        if verdict != "DUPLICATE" and "duplicate_of" in row:
            raise ValueError("Only duplicate findings may reference another claim")
        graded[cid] = row
    if set(graded) != set(by_claim):
        raise ValueError("Every saved claim must be adjudicated; claims cannot silently disappear")
    for cid, row in graded.items():
        if row["verdict"] == "DUPLICATE":
            target = graded.get(row.get("duplicate_of"))
            if (target is None or target is row or by_claim[target["claim_id"]]["kind"] != "finding"
                    or target["verdict"] not in {"FOUND", "FALSE_ALARM", "UNSUPPORTED", "ORACLE_REVIEW"}):
                raise ValueError("Duplicate findings require a canonical finding, without cycles")
    found, duplicates = set(), []
    for cid in by_claim:
        row = graded[cid]
        if row["verdict"] == "FOUND":
            issues = set(row["defect_ids"])
            if issues <= found:
                duplicates.append(cid)
            found.update(issues)
        elif row["verdict"] == "DUPLICATE":
            duplicates.append(cid)

    def selected(verdict):
        return [cid for cid in by_claim if graded[cid]["verdict"] == verdict]

    false_alarm, false_clearance = selected("FALSE_ALARM"), selected("FALSE_CLEARANCE")
    unsupported, oracle = selected("UNSUPPORTED"), selected("ORACLE_REVIEW")
    falsely_cleared = {issue for cid in false_clearance for issue in graded[cid]["defect_ids"]}
    missed = [issue for issue in expected if issue not in found]
    return {
        "source_sha256": source_sha256, "known_defects": len(expected),
        "detected_defects": len(found), "found_defect_ids": [v for v in expected if v in found],
        "missed_defects": len(missed), "missed_defect_ids": missed,
        "false_alarms": len(false_alarm), "false_alarm_claim_ids": false_alarm,
        "duplicate_findings": len(duplicates), "duplicate_claim_ids": duplicates,
        "false_clearances": len(false_clearance), "false_clearance_claim_ids": false_clearance,
        "false_clearance_claims": len(false_clearance), "falsely_cleared_defects": len(falsely_cleared),
        "falsely_cleared_defect_ids": [v for v in expected if v in falsely_cleared],
        "contradicted_defect_ids": [v for v in expected if v in falsely_cleared & found],
        "unsupported_claims": len(unsupported), "unsupported_claim_ids": unsupported,
        "oracle_review_claim_ids": oracle, "measurement_complete": not oracle,
        "unresolved_claim_ids": selected("UNRESOLVED"), "manual_claim_ids": selected("MANUAL"),
        "verified_clearance_claim_ids": selected("CLEAR"),
        "all_planted_defects_found": not missed,
        "no_contradicted_or_unsupported_claims": not (false_alarm or false_clearance or unsupported or oracle),
        "acceptance_scope": "DEVELOPER_GRADED_SYNTHETIC_TRIAL_ONLY",
    }
