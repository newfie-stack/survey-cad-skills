"""Review separately supplied survey coordinates, never PDF page geometry."""
from __future__ import annotations

import re
from decimal import Decimal, localcontext
from math import isfinite

from area_table import (AREA_HECTARES, NUMBER, TOTAL_AREA_PREFIX,
                        total_area_cells, total_area_evidence)
from geometry import check_polygon
from geometry_representation import requires_specialist_geometry, validate_xy_pairs
from traverse import traverse_closure


AREA_LABEL = re.compile(
    rf"(?:{TOTAL_AREA_PREFIX}|area\s*[:=]?\s*)?{AREA_HECTARES}", re.IGNORECASE)


def compare_plan_area(selection: dict, spans: list[dict], polygon: dict | None) -> dict:
    if not isinstance(selection, dict):
        raise ValueError("area_label must be an object")
    page, label = selection.get("page"), selection.get("text")
    tolerance = selection.get("tolerance_ha")
    source = selection.get("source", "text")
    if type(page) is not int or page < 1 or not isinstance(label, str):
        raise ValueError("area_label requires a one-based page and exact label text")
    if type(tolerance) not in (int, float) or not isfinite(tolerance) or tolerance < 0:
        raise ValueError("area_label requires a finite nonnegative tolerance_ha")
    if source not in ("text", "table_total"):
        raise ValueError("area_label source must be text or table_total")
    if source == "table_total":
        pattern = NUMBER.fullmatch(label)
        number = pattern[0] if pattern else None
        matches = [span for _, span in total_area_cells(
            [span for span in spans if span["page"] == page])]
    else:
        pattern = AREA_LABEL.fullmatch(label.strip())
        number = pattern[1] if pattern else None
        matches = [span for span in spans if span["page"] == page and span["text"] == label]
    observed = float(number) if number is not None else None
    if observed is None or not isfinite(observed):
        if source == "table_total":
            raise ValueError("area_label text must be the numeric hectare cell text")
        raise ValueError("area_label text must contain one area in hectares")
    result = {"page": page, "tolerance_ha": tolerance, "status": "REVIEW_REQUIRED",
              "source": source}
    candidates, ambiguity = total_area_evidence(spans)
    if ambiguity or len(matches) != 1 or (source == "table_total" and matches[0]["cell_text"] != label):
        return {**result, "comparison": "AREA_LABEL_UNRESOLVED",
                "matching_spans": sum(span.get("cell_text", span["text"]) == label for span in matches),
                "candidate_count": len(matches),
                "total_candidate_count": len(candidates), "reason": ambiguity}
    result.update({"observed_ha": observed, "bbox_points": matches[0]["bbox_points"]})
    if polygon is None or polygon["crs_status"] != "VERIFIED":
        return {**result, "comparison": "SURVEY_AREA_UNRESOLVED"}
    calculated = polygon["area_ha"]
    if not isfinite(calculated):
        return {**result, "comparison": "SURVEY_AREA_UNRESOLVED"}
    measured = Decimal(polygon.get("area_ha_decimal", str(calculated)))
    observed_decimal, tolerance_decimal = Decimal(number), Decimal(str(tolerance))
    values = (measured, observed_decimal, tolerance_decimal)
    with localcontext() as context:
        context.prec = max(28, max(v.adjusted() for v in values)
                           - min(v.as_tuple().exponent for v in values) + 3)
        difference = abs(observed_decimal - measured)
        comparison = ("WITHIN_SUPPLIED_TOLERANCE" if difference <= tolerance_decimal
                      else "OUTSIDE_SUPPLIED_TOLERANCE")
    return {**result, "comparison": comparison, "calculated_ha": calculated,
            "difference_ha": float(difference)}


def review_survey_geometry(survey: dict, *, plan_spans: list[dict] | None = None) -> dict:
    if not isinstance(survey, dict):
        raise TypeError("Survey geometry input must be an object")
    if survey.get("coordinate_source") != "EXPLICIT_SURVEY_COORDINATES":
        raise ValueError("Only explicit survey coordinates are accepted")
    if type(survey.get("crs_verified")) is not bool:
        raise ValueError("Explicit boolean crs_verified required")
    if not isinstance(survey.get("crs_identifier"), str) or not survey["crs_identifier"].strip():
        raise ValueError("A projected metric CRS identifier is required")
    vertices = survey.get("vertices")
    validate_xy_pairs(vertices)
    if type(survey.get("closed_ring")) is not bool:
        raise ValueError("Explicit boolean closed_ring required")
    crs_verified = survey["crs_verified"]
    result = {
        "coordinate_source": "EXPLICIT_SURVEY_COORDINATES",
        "crs_identifier": survey["crs_identifier"],
        "status": "REVIEW_REQUIRED",
    }
    if requires_specialist_geometry(survey):
        return {**result, "diagnostic_status": "REPRESENTATION_UNRESOLVED",
                "reason": "Declared curves, holes, parts or geometry type are outside straight-coordinate QA; preserve the complete subject for specialist review."}
    result["traverse"] = traverse_closure(vertices, crs_verified=crs_verified,
                                          tolerance_m=survey.get("tolerance_m"))
    if survey.get("closed_ring") is True:
        result["polygon"] = check_polygon(vertices, crs_verified=crs_verified)
    if "area_label" in survey:
        result["area_comparison"] = compare_plan_area(
            survey["area_label"], plan_spans or [], result.get("polygon"))
    return result
