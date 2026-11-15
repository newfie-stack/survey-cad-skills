# Plan type and applicability matrix

The May 2024 Crown-land plan-content publication is organized into:
- **Part 1:** general requirements — layout, title block, main body, georeferencing, cadastral fabric, water, activity extents, areas/widths/lengths and details.
- **Part 2:** additional requirements for sketches and surveyor sketches, including declaration conditions where applicable.
- **Part 3:** survey-plan content — monuments, dimensions, linear dispositions, natural boundaries, amendments/renewals, conventional interaction with hybrid plans, hybrid cadastre and compiled plans.
- **Part 4:** activity-specific content — linear dispositions, piezometer/heave sites, exploration, material authorizations/leases, wetland/waterbody activities, sales and reservations.

Select Part 1 plus the applicable plan-type part and any applicable activity-specific section. Do not apply all sections universally. Validate exact clause wording against the current official publication.

Before checking, capture:
`land_class, regulator, disposition_code, activity_code, application_stage, plan_type, statutory_or_nonstatutory, affected_land_description, current_source_versions`.

Possible decision states: `IN_SCOPE`, `OUT_OF_SCOPE`, `AMBIGUOUS`, `HISTORICAL_ONLY`.

For linear dispositions, separately assess subject geometry, road allowances, access, intersecting interests, discontinuities, dimensions, areas and plan-to-GIS consistency; don't assume overlaps are either prohibited or approved from geometry alone.

An ALS professional judgment, legal status, and approval decision are never inferred solely from CAD/GIS data.
