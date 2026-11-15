# Evidence-bound Crown plan validation

## Inputs
Plan PDF/plot; optional CAD/DXF; optional GIS shapefile components; application metadata; ATS/legal description; source evidence register; governing regulatory source versions. Inputs may be missing. Do not claim a check ran without the required input.

## Check classes
- Plan layout and legibility: page dimensions, margins, scale, text, details and multi-sheet applicability.
- Title block and notes: plan type, activity/purpose, applicant/municipality/legal description, legend, declarations where required.
- Survey evidence: monument roles, bearings, distances, curves, ties, road limits, section control, natural boundaries and surveyed versus calculated geometry.
- Geometry: widths, lengths, closure, areas, topology, self-intersections, spatial alignment, coordinate reference and units.
- Existing interests: registered dispositions, access, road allowances, encumbrances and water features when required by current source.
- CAD/GIS/package: permitted file types, field schema, CRS, geometry type, naming, submission package and consistency with plan/application; only when the specific current regulator instruction makes them applicable.

Each result must contain requirement ID, source clause, input artifact ID, check method, measured/observed value, expected rule, result and reviewer note. If a check is only visual or inferential, label it REVIEW_REQUIRED rather than numerical PASS.

## Safety
Never auto-correct surveyed legal geometry, fabricate a missing plan label, invent regulatory requirements, or perform portal submission. Human confirmation is required for consequential changes.
