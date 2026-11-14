# Shapefile validation checklist
- [ ] Required .shp/.shx/.dbf/.prj components present and readable
- [ ] Geometry type and feature count match expected specification
- [ ] CRS and coordinate units verified against authoritative metadata
- [ ] Required fields, types, lengths and null policies checked
- [ ] Rings closed, non-self-intersecting and topologically valid
- [ ] Duplicate, overlapping, multipart and zero-area features evaluated
- [ ] Feature IDs, legal descriptions and areas cross-checked with authoritative source
- [ ] No silent geometry correction or invented missing attributes
- [ ] Packaging and naming checked against current published specification
Output PASS, FAIL or REVIEW_REQUIRED per item, with evidence and recommended correction.
