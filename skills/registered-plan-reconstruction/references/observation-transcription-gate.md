# Observation transcription and course-to-feature verification gate

## Before COGO
1. Inspect the complete source sheet, then enlarge the original raster around each controlling dimension, without substituting a prior model-generated CSV or overlay for the original.
2. Preserve **exact printed text** (including decimals, seconds, CALC and ASSUMED), normalized value, unit, page/detail locator and reading confidence. Record ambiguous glyphs as alternatives rather than guessing.
3. Independently re-read every controlling bearing and distance before promoting it to accepted COGO input. Specifically check decimal digits and near-identical 6/8, 1/7 and 5/3 glyphs; a 20 m reading error is not a rounding discrepancy.
4. Verify each observation belongs to the *new subject*, and to the correct side and endpoints. An existing registered R/W may carry the same width and a visually connected line; that is not sufficient.
5. Test a COGO chain's **unscaled** segment lengths and bearings against the source sheet. If a candidate alignment requires independently stretching a segment to fit the raster, reject its endpoint/observation association instead of rubber-sheeting it.
6. Establish the controlling side before deriving the opposite side. Do not display two mutually exclusive offset alternatives as though either were accepted.
7. Keep raster registration a secondary topology check. Its transform is separate from legal COGO and must not be used to alter printed distances.
8. Compare printed quarter-specific areas, road terminals and independent ties; incomplete checks remain NOT_EVALUATED.

## Machine-readable QA
For every controlling course record `raw_text`, `normalized_azimuth`, `distance_m`, `source_locator`, `feature_id`, `side_id`, `from_evidence_id`, `to_evidence_id`, `reading_status`, `association_status`, and `independent_review`. Any unresolved reading or association blocks PASS and labels the geometry REVIEW_REQUIRED.

## Synthetic regression
A synthetic plan prints 69.56 m, while the first extraction incorrectly reads 89.56 m. The independent reading gate must reject the 89.56 m input, retain both candidate readings in the log, and prevent acceptance of any COGO built from the incorrect reading. A second synthetic case prints 280.71 m but the extraction reads 280.75 m; the gate must preserve the printed hundredths exactly.
