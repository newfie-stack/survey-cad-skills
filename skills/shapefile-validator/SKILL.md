---
name: shapefile-validator
description: Validate shapefile components, attributes, CRS, topology and consistency with survey sources.
version: 1.0.0
---
# Shapefile Validator
Verify .shp, .shx, .dbf and .prj presence; check readable geometry, geometry types, schema and required attributes against the applicable published specification. Check CRS, units, ring closure, self-intersections, duplicate features, multipart structure, null attributes and spatial extents. Compare relevant boundaries and metadata with authoritative survey observations and approved CAD/PDF artifacts. Propose fixes, but do not silently alter legal geometry or claim compliance without authoritative requirements. Report PASS, FAIL, REVIEW_REQUIRED and source/version for each check.

## Supporting references
- [validation checklist md](references/validation-checklist.md)

Read the applicable supporting reference before carrying out the corresponding technical workflow. Do not assume a regulatory rule is current without checking the official source.
