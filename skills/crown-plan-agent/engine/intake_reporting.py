"""Render source-bound preparation and unresolved work, never compliance."""
from __future__ import annotations

import re

from finished_plan_spec import validate_spec
from revision_markdown import _literal


def preparation_counts(preparation: dict) -> dict:
    """Validate preparation accounting before presenting it as completed work."""
    if (not isinstance(preparation, dict)
            or preparation.get("assessment_scope") != "SOURCE_BOUND_CHECK_PREPARATION"
            or preparation.get("overall_status") != "REVIEW_REQUIRED"
            or preparation.get("regulatory_status") != "NOT_ASSESSED"):
        raise ValueError("Only review-only source-bound preparation can be summarized")
    digest = preparation.get("source_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise ValueError("Preparation needs a source SHA-256 digest")
    resolutions = preparation.get("resolutions")
    if (not isinstance(resolutions, list) or not 1 <= len(resolutions) <= 100
            or any(not isinstance(item, dict) for item in resolutions)):
        raise ValueError("Preparation needs every requested check resolution")
    ids = [item.get("check_id") for item in resolutions]
    if (any(not isinstance(cid, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,63}", cid)
            for cid in ids) or len(set(ids)) != len(ids)):
        raise ValueError("Preparation check IDs must be distinct")
    if any(item.get("status") not in {"READY", "REVIEW_REQUIRED"} for item in resolutions):
        raise ValueError("Preparation has an unsupported resolution status")
    ready = {item["check_id"] for item in resolutions if item["status"] == "READY"}
    spec = preparation.get("spec")
    if spec is None:
        if ready:
            raise ValueError("Ready resolutions require the generated specification")
    else:
        validate_spec(spec)
        if spec["source_sha256"] != digest:
            raise ValueError("Prepared specification source identity differs")
        if ready != {check["id"] for check in spec["checks"]}:
            raise ValueError("Prepared specification must match every ready resolution")
    tasks = preparation.get("visual_tasks", [])
    if not isinstance(tasks, list) or any(not isinstance(task, dict) for task in tasks):
        raise ValueError("Visual preparation followups must be recorded as objects")
    return {"requested": len(resolutions), "ready": len(ready),
            "unresolved": len(resolutions) - len(ready), "visual_tasks": len(tasks)}


def render_intake_preparation(preparation: dict) -> str:
    counts = preparation_counts(preparation)
    literal = lambda value: _literal(str(value).replace("\n", " / "))
    lines = ["\n## Plan intake and check preparation", "",
             "Status: REVIEW_REQUIRED", "Regulatory compliance: NOT_ASSESSED",
             f"Source SHA-256: {preparation['source_sha256']}",
             f"Prepared {counts['ready']} of {counts['requested']} requested checks; "
             f"{counts['unresolved']} unresolved requests.",
             "Preparation identifies checkable source regions; comparison results are recorded separately.",
             "Context identities remain reviewer-supplied. No text-completeness declaration is created."]
    for resolution in preparation["resolutions"]:
        lines.extend(["", "### " + literal(resolution["check_id"]),
                      "Preparation status: " + resolution["status"]])
        if resolution.get("description"):
            lines.append(literal(resolution["description"]))
        reason = resolution.get("reason", resolution.get("reasons"))
        if reason:
            lines.append("Review: " + literal(reason))
        for region in resolution.get("regions", []):
            role = region.get("role", region.get("request", {}).get("role", "Source context"))
            page = region.get("page", region.get("request", {}).get("page", "unresolved"))
            lines.append(f"Context: page {literal(page)}; {literal(role)}")
            if region.get("context_bbox_points"):
                lines.append("Reviewed context (PDF points): " + literal(region["context_bbox_points"]))
            if region.get("support_bbox_points"):
                lines.append("Derived native-text support (PDF points): " + literal(region["support_bbox_points"]))
            reason = region.get("reason", region.get("reasons"))
            if reason:
                lines.append("Selection: " + literal(reason))
            for candidate in region.get("matching_candidates", region.get("candidates", [])):
                if isinstance(candidate, dict):
                    lines.append("Native candidate: " + literal(candidate.get("text", candidate)))
                else:
                    lines.append("Native candidate: " + literal(candidate))
    if preparation.get("visual_tasks"):
        lines.extend(["", "### Visual followups", ""])
        for task in preparation["visual_tasks"]:
            lines.append("- Page " + literal(task.get("page", "unresolved")) + ": "
                         + literal(task.get("reason", task.get("instruction", "Inspect the source image"))))
    lines.extend(["", "Unresolved preparation requests were not executed as mechanical comparisons. "
                  "Scanned/outlined lettering, graphical symbols and source completeness need independent visual review.", ""])
    return "\n".join(lines)
