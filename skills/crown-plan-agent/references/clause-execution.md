# Executed evidence for dated clause questions

Version 0.9.0 adds eleven bounded observations across nine numbered clauses of
the May 30, 2024 Crown-content manual. The [source audit](regulatory-source-audit-2026-11-21.md)
reinspected the publisher-linked edition and selected clauses. The separate
workbook still contains144 manual paths and323 manual checks; these observations
do not make a whole clause or plan compliant.

| Workbook question | Executed comparison | Evidence and residual review |
|---|---|---|
|3.5.2.1 / `_01`,`_02`|Starts1; consecutive unique integer point numbers, no suffixes|Complete reviewed table; physical native row order is derived from the PDF. No caller sorting to repair numbering.|
|3.5.2.2 / `_01`,`_02`|Two decimal places; no grouping spaces/commas in northing/easting strings|Original native strings retained; no float reformatting.|
|3.5.2.3 / `_01`|Every row has an EC/XC/RC/OC token|Lexical check only; actual evidence roles still require review.|
|3.5.6.2 / `_01`|At least two distinct accepted OC coordinate records|Complete table and independently reviewed roles/provenance/common metric frame; coincident rows do not count twice. Body portrayal remains visual.|
|3.5.6.3 / `_01`|Every EC/XC/RC lies within inclusive 10000m of an OC|Complete table/full OC set, reviewed roles/provenance/metric frame. Exact squared Decimal distances; no reconstruction or transformations.|
|1.2.2.3 / `_01`|Numerical scale in the selected main-plan field|Printed ratio only; graphical bar, plotted scale and applicability remain separate.|
|1.3.3.5 / `_01`|Locate the candidate phrase `UNSURVEYED TERRITORY` in the selected plan-body context|Requires selected provenance-backed applicability. The clause does not prescribe exact wording: missing phrase remains unresolved even with complete extraction, pending alternative-wording review. No ownership inference.|
|1.3.7.1 / `_02`|Selected detail label agrees with main-view reference|Actual independent same-subject fields; all-view completeness, meaning and unique identities remain manual.|
|1.3.7.3 / `_02`|Selected existing-plan label agrees between detail and main view|Same-feature field selection is reviewed, not inferred; plotted positions/extents remain manual.|

Full question IDs have form `C_3_5_2_1_01`. Supported paths are independent of
legacy candidate-adapter links. The engine only accepts the exact shipped dated
catalogue for this mapping. Missing/invalid context, unresolved facts, out-of-scope
land, exemptions and replacement decisions stop execution. Every requested
observation is retained as executed or blocked; unrequested questions remain open.

## Private review command

Read the complete titleblock, then inspect actual page images and select the
relevant contexts. The agent prepares the specification; routine JSON preparation
is not work to hand back to the draftsman. Use authorized originals and the
[reviewed runtime](dependency-security.md), keeping all inputs and derived evidence
outside the repository/installed package.

```sh
python skills/crown-plan-agent/engine/review_cli.py /private/plan.pdf \
  --scenario /private/scenario.json --output /private/review.md --offline \
  --clause-catalogue skills/crown-plan-agent/engine/dated_clause_catalogue.json \
  --clause-facts /private/facts.json \
  --regulatory-evidence-spec /private/evidence-spec.json
```

With a supplied point export, add `--point-export /private/points.csv` and the
matching `point_export` specification described below. No network access is added.
The actual PDF hash is checked before native processing or an explicitly requested
source refresh. Fresh output paths are required; input files are never rewritten.

The structured API is
`review_regulatory_evidence(pdf, scenario, catalogue, facts, spec, point_export=None)`
in `engine/regulatory_evidence.py`. It returns findings, raw field evidence,
artifact comparisons, spec/source hashes and separate counts. The CLI includes
these observations in its opening summary and source-located Markdown detail.
In version 0.10.0, actionable observations also enter the requested annotated
review-copy index. A uniquely verified plan span receives a comment; multiple,
unsupported or reference-only locations stay unlocated. PASS results remain in
Markdown. The [job-record pass](job-record-checks.md) adds six further bounded
question paths across five additional clauses, without accepting whole clauses.

## Specification contract

The strict top-level JSON object has exactly:

- `schema_version:1`, `source_sha256` of the actual plan and `prepared_by`.
- `hybrid_table`: a table selection object or null.
- `drawing`: `{spec,bindings}` or null. `spec` is the existing source-bound
  [finished-plan specification](finished-plan-qc.md); bindings are objects with
  `workbook_check_id` and `drawing_check_id`. Each observation and target must be
  unique and supported; no unbound check or imported PASS is accepted. The scale
  path requires kind `scale`, territory requires kind `required_text` with the exact
  expected phrase above, and the two label paths require kind `same_text`.
- `point_export`: the export contract or null; requires `hybrid_table` and the
  actual CSV file supplied separately.

At least one of `hybrid_table`/`drawing` must be present. Nested PDF hashes must
match the envelope. Unknown fields and unbounded/malformed inputs are rejected
before execution; a source hash identifies bytes, not legal authenticity.

A `hybrid_table` object has exactly `schema_version:1`, `source_sha256`,
`prepared_by`, `table_complete`, `crs_identifier`, `coordinate_frame_id`,
`coordinate_units`, `crs_verified`, `provenance_verified`,
`coordinate_roles_resolved`, and `rows`.

Each of 1–500 selected rows contains `point_id`, `northing`, `easting` and `type`.
Each field is a source selector with `page` (one based), `bbox_points`, `role`,
and optional literal `label`; no claimed field value is accepted. Select complete
native field support and retain the printed formatting. Overlapping/reused spans,
clipped/raster/wrapped/ambiguous fields, inconsistent physical rows or unsupported
table layout block the table. Source-located row evidence remains available.

`table_complete` is null or an explicit review record with `status:TEXT_COMPLETE`,
`method:VISUAL_TO_TEXT_COMPARISON`, `reviewer` and `statement`. It attests that the
entire relevant table was compared with the source image. It is supplied review
evidence, not a completeness claim inferred by the engine. Without it, collective
predicates stay blocked. Do not copy completeness from a different source/context.

CRS/frame fields are nonempty reviewed identifiers or null; units are `m` or null,
and the three acceptance fields are explicit booleans. The frame identifier covers
datum, epoch, axes, grid/ground basis and any applicable transformation evidence.
It does not itself establish those facts. Unverified flags/frame block spatial
checks; lexical formatting/numbering can still execute on a complete readable table.

## Actual CAD/GIS point-export connection

The export specification has exactly `schema_version:1`,
`format:CSV_POINT_EXPORT`, `origin_kind:CAD` or`GIS`, `source_sha256` (CSV bytes),
`complete` (boolean), plus the CRS/frame/unit and three acceptance fields above.
The two artifacts must describe the same complete reviewed point set and identical
verified metric frame. There is no implicit axis swap, CRS conversion, rounding,
tolerance, ID suffix removal or automatic georeferencing acceptance.

CSV is UTF-8 (optional BOM), comma delimited, with exact header order:

```csv
point_id,easting,northing,type
1,500000.00,6000000.00,OC
2,500000.00,6001000.00,OC
3,510000.00,6000000.00,EC
```

The reader binds actual bytes, checks duplicate/invalid/missing/extra IDs and
compares exact numeric coordinates and category tokens by stable ID. It preserves
CSV line numbers, raw values, PDF locators and differences. Unsupported numeric
formats, duplicate/ambiguous identities, incomplete sets and unresolved frames
stay unresolved. Files are bounded to 5 MiB/10000 rows. Export comparison is
supplemental artifact consistency evidence, not another completed manual clause.

This adapter inspects a point export, not native DWG/DXF layers, shapefile schema,
topology, boundaries or control. Use the CAD/GIS companion tools and reviewed
Octopus provider for those workflows. Working-DWG `EVIDENCE` and DIDS target layer 35
remain distinct. Current PDF, CAD and OneStop shapefile requirements have different
scopes; see the dated source audit rather than applying one format's rule to all.

## Results and proof

Every regulatory `status`/`source_status` remains `REVIEW_REQUIRED`/
`UNVERIFIED_CURRENT`. `mechanical_status` describes only the bounded comparison.
`execution_status:BLOCKED` records a PDF read whose predicate could not run;
`NOT_EXECUTED` records a selection gate that stopped execution. Counts distinguish
requested, actually executed, blocked and still-unrequested work. A lexical match
never accepts roles, field truth, a signature or a whole regulatory clause.

Synthetic generators and static expected results live in
`tests/clause_evidence_examples.py` and its regression tests, alongside focused
actual-PDF/CSV tests. They recreate invented files outside the repository. These
are known regression cases, not blind validation or real-plan acceptance evidence.

Generate one example into a fresh private directory:

```sh
python skills/crown-plan-agent/tests/clause_evidence_examples.py \
  /private/invented-clause-example --case clean_exact_10km
```

The 18-case integration record matched all 187 requested observations:178 executed
(167 PASS, 7 FAIL, 4 unresolved) and 9 blocked. The 63 added unit/integration methods
include physical-row, rotated-reading, source/hash, selection and frame regressions.
The [technical review](../TECHNICAL_REVIEW.md) retains the scope and exact fingerprint.
