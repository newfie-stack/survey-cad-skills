"""Prepare a review-only proposal for external survey geometry skills."""
from __future__ import annotations

from geometry_representation import requires_specialist_geometry, validate_xy_pairs


def prepare_geometry_handoff(inventory: dict, scenario: dict,
                             survey_geometry: dict | None = None) -> dict:
    """Describe requested specialist work without invoking or accepting geometry.

    Readiness checks declarations and container types only. The existing geometry
    reviewer owns numerical diagnostics; a specialist owns reconstruction and its
    independent evidence checks. Input coordinates are never copied to this result.
    """
    if not isinstance(inventory, dict) or not isinstance(scenario, dict):
        raise TypeError("Inventory and scenario must be objects")
    if survey_geometry is not None and not isinstance(survey_geometry, dict):
        raise TypeError("Survey geometry must be an object or None")
    if "gis_requested" in scenario and type(scenario["gis_requested"]) is not bool:
        raise ValueError("gis_requested must be an explicit boolean")

    skill_purposes = [
        ("survey-plan-evidence-interpretation", "Transcribe and classify source observations and conflicts"),
        ("registered-plan-reconstruction", "Reconstruct from accepted observations and complete control evidence"),
        ("survey-dxf-cad-construction", "Export and reopen accepted geometry with boundary and control layers"),
    ]
    if scenario.get("gis_requested") is True:
        skill_purposes.append(("shapefile-validator", "Validate requested GIS files, CRS, schema and topology"))
    requested_skills = [
        {"name": name, "purpose": purpose, "availability": "UNVERIFIED",
         "execution_status": "NOT_EXECUTED"} for name, purpose in skill_purposes
    ]

    required_inputs = [
        {"name": "source_locator", "fields": [
            "source_id and exact source snapshot identity", "filename and source plan identity",
            "one-based page and detail for every observation"]},
        {"name": "feature_identity", "fields": [
            "new subject versus existing registered/background plan identity",
            "boundary/control/tie/road/context roles and feature side",
            "endpoint identities, sequence and terminal conditions"]},
        {"name": "bearing_basis_and_units", "fields": [
            "printed bearing basis including assumed/grid/ground status",
            "distance and coordinate units", "source notes and applicable scale basis"]},
        {"name": "raw_observations", "fields": [
            "original bearings, distances, widths, offsets and complete curve definitions",
            "original text and source page/detail", "independent reading confirmation and unresolved alternatives"]},
        {"name": "control_and_spatial_alignment", "fields": [
            "all source-supported monuments, control courses, ties and witness relationships",
            "independently identified tie endpoints and control status",
            "CRS/datum/metric units and applicable transformation evidence or documented no-transformation basis",
            "independent control residuals and any provisional control"]},
    ]
    expected_return_artifacts = [
        {"name": "source_and_feature_register", "contents":
         "Exact source locators; subject/background identities, feature roles, sides and endpoint graph."},
        {"name": "observation_register", "contents":
         "Every dimensioned source course with original reading, normalized observation, role, provenance and unresolved alternatives."},
        {"name": "control_network", "contents":
         "Complete monument/control/tie graph with raw observations, independently established endpoints and provisional exceptions."},
        {"name": "derived_geometry_and_verification", "contents":
         "Provenance-linked COGO, independent ties/residuals, widths, terminals, closure, areas, source overlay and alignment evidence."},
        {"name": "review_dxf", "contents":
         "Reopened review DXF including boundary and complete evidence/control network on distinct layers; provisional geometry conspicuous."},
        {"name": "review_preview", "contents":
         "Boundary, all included dimensioned courses, control/ties, found evidence markers and labels; omitted courses identified."},
        {"name": "accepted_coordinate_json", "contents":
         "Separately supplied explicit coordinates compatible with coordinate_input_contract, only after provenance, feature roles and CRS are resolved."},
        {"name": "unresolved_items", "contents":
         "Unresolved readings, omitted courses, control/CRS/identity questions and unsupported curves/multipart results kept separate with REVIEW_REQUIRED."},
    ]
    if scenario.get("gis_requested") is True:
        required_inputs.append({"name": "gis_target", "fields": [
            "requested GIS format, components and schema", "applicable published specification and version",
            "target CRS and comparison survey/CAD sources"]})
        expected_return_artifacts.append({"name": "gis_validation", "contents":
                                         "Requested GIS artifacts plus component, schema, CRS, topology and source-consistency review."})

    blockers = ["EXPLICIT_SURVEY_COORDINATES_REQUIRED"]
    readiness = "RECONSTRUCTION_INPUT_REQUIRED"
    if survey_geometry is not None:
        survey = survey_geometry
        for name in ("crs_verified", "provenance_verified", "coordinate_roles_resolved", "closed_ring"):
            if name in survey and type(survey[name]) is not bool:
                raise ValueError(f"{name} must be an explicit boolean")
        for name in ("coordinate_source", "crs_identifier"):
            if name in survey and not isinstance(survey[name], str):
                raise ValueError(f"{name} must be a string")
        if "vertices" in survey:
            validate_xy_pairs(survey["vertices"])
        specialist_geometry = requires_specialist_geometry(survey)
        blockers = []
        if survey.get("coordinate_source") != "EXPLICIT_SURVEY_COORDINATES":
            blockers.append("EXPLICIT_SURVEY_COORDINATES_REQUIRED")
        if not survey.get("vertices"):
            blockers.append("ORDERED_COORDINATES_REQUIRED")
        if not survey.get("crs_identifier", "").strip():
            blockers.append("CRS_IDENTIFIER_REQUIRED")
        for name, blocker in [
            ("crs_verified", "CRS_UNVERIFIED"),
            ("provenance_verified", "PROVENANCE_UNVERIFIED"),
            ("coordinate_roles_resolved", "COORDINATE_ROLES_UNRESOLVED"),
        ]:
            if survey.get(name) is not True:
                blockers.append(blocker)
        if "closed_ring" not in survey:
            blockers.append("CLOSURE_DECLARATION_REQUIRED")
        if specialist_geometry:
            blockers.append("SPECIALIST_GEOMETRY_OUTSIDE_QA_SCOPE")
        readiness = "VERIFY_CRS_AND_PROVENANCE" if blockers else "QA_INPUT_SUPPLIED"

    if readiness == "QA_INPUT_SUPPLIED":
        requested_skills = [item for item in requested_skills
                            if item["name"] == "shapefile-validator"]

    return {
        "status": "REVIEW_REQUIRED", "execution_status": "NOT_EXECUTED",
        "readiness": readiness, "source": _source_locator(inventory),
        "requested_skills": requested_skills, "required_inputs": required_inputs,
        "expected_return_artifacts": expected_return_artifacts,
        "coordinate_input_contract": {
            "consumer": "geometry_review.review_survey_geometry",
            "required_fields": ["coordinate_source", "crs_identifier", "crs_verified",
                                "closed_ring", "vertices"],
            "coordinate_source": "EXPLICIT_SURVEY_COORDINATES",
            "vertices": "Ordered numeric XY pairs in the explicitly identified projected metric CRS; never PDF page points",
            "acceptance_flags": ["crs_verified", "provenance_verified", "coordinate_roles_resolved"],
            "optional_fields": ["tolerance_m", "area_label"],
            "supported_geometry": "One ordered straight coordinate sequence; closed_ring=true enables single-ring polygon diagnostics",
            "unsupported_geometry": "Curves, holes and multipart geometry stay in separate specialist artifacts; do not flatten or fill them to fit this JSON",
        },
        "acceptance_blockers": blockers,
        "limitations": [
            "Proposal only: no skill discovery, installation, invocation or reconstruction was executed",
            "Skill names do not establish companion availability; verify availability before a separate authorized handoff",
            "QA_INPUT_SUPPLIED is declared-input readiness, not geometric acceptance or a normative PASS",
            "Unresolved coordinate roles, source provenance or CRS block accepted geometry",
            "Numerical validation belongs to the existing geometry reviewer; this helper computes no coordinates or measurements",
            "Curves, holes and multipart results remain separate unresolved specialist artifacts for this QA engine",
        ],
    }


def _source_locator(inventory: dict) -> dict:
    """Retain known page locators without interpreting page-space geometry."""
    for name in ("source_filename", "source_id"):
        if inventory.get(name) is not None and not isinstance(inventory[name], str):
            raise ValueError(f"{name} must be a string or None")
    page_count = inventory.get("pages")
    if type(page_count) is not int or page_count < 1:
        page_count = None
    # A declared document size is not an observation on every page. Preserve
    # the count separately so handcrafted metadata cannot expand a huge range.
    pages = set()
    for name in ("spans", "vectors", "curves"):
        entries = inventory.get(name, [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            page = entry.get("page") if isinstance(entry, dict) else None
            if type(page) is int and page > 0:
                pages.add(page)
    return {"filename": inventory.get("source_filename"),
            "source_id": inventory.get("source_id"), "pages": sorted(pages),
            "page_count": page_count}
