# Source-bound plan intake and check preparation

This assisted workflow helps the agent find native fields and prepare mechanical
checks without repeatedly drawing tight text boxes. The agent reads the actual
plan and prepares the inputs; the plan owner does not write JSON or identify
text coordinates. Continue to read every titleblock and Notes frame completely,
then identify the main view, details, schedules and their subjects.

## Discover the actual evidence

With the existing reviewed Python runtime, from the complete skill folder:

```bash
python engine/intake_cli.py /private/job/plan.pdf \
  --output /private/job/intake.json
```

The new private artifact records the actual PDF digest, independent page sizes
and rotations, native line candidates with original locations and directions,
literal label suggestions, image rectangles and source-located visual tasks.
Candidate IDs are source locators. A label or heading suggestion does not verify
that a region is the titleblock, belongs to the subject parcel, or supplies the
current revision. Check those identities against the page image and job facts.
The map never chooses an authoritative field by its expected value.

Read each label in its native direction. Nearby text can have opposite baselines
or different oblique orientations; its fragments must not be combined into an
invented phrase. Survey azimuth is clockwise from north; PDF text axes and
readability flips are separate. An office threshold near north remains
unconfirmed until independently established and is not an automated violation
rule in this workflow.

Image-only text is listed for visual reading. The map also requests full-sheet
visual coverage because outlined lettering can exist beside ordinary native
text without appearing as an image. No native words, or native words elsewhere
on a sheet, do not establish that a note or symbol is absent or fully read.

## Prepare comparisons inside reviewed contexts

Use the existing strict v1 finished-plan specification as a context request.
Its source digest, preparer, check kinds, basis and expected job facts have the
same contract as [finished-plan QC](finished-plan-qc.md). In this mode each
`bbox_points` describes the reviewed panel/view context rather than a manually
tight glyph box. Supply the observed literal `label` for a field when available.
Keep current and historic entries, adjoining parcels and independent inset
views in their actual contexts. No first, nearest or expected-value match is
silently selected.

Preparation includes all matching candidates, chooses an unambiguous whole
native field, and expands its support rectangle until every intersecting font
box is fully included. Expansion stops at the supplied context boundary and
has a fixed iteration limit. A context that cannot safely isolate a field stays
unresolved. Multiple/blank labels, uncertain stacked or wrapped associations,
crossing context boundaries, raster overlap and unsupported/clipped geometry
receive explicit followups. Source text and all original requests are retained.

Derived rectangles never inherit `coverage_review`: a reviewed broad context
does not automatically prove completeness of a different, narrower selection.
Directly prepared legacy specs retain their existing completeness contract.

Run preparation and comparisons together:

```bash
python engine/review_cli.py /private/job/plan.pdf \
  --scenario /private/job/scenario.json \
  --finished-plan-contexts /private/job/contexts.json \
  --offline --reference-cache /private/job/references \
  --output /private/job/review.md
```

The opening summary separates prepared requests from executed checks. The
report retains every unresolved request, competing native text and visual task.
An unresolved request is not a passed or executed comparison. Regulatory scope,
current-source and professional acceptance gates remain separate.

For structured tooling, `discover_plan(pdf)` returns the source-bound map and
`prepare_finished_plan(pdf, context_spec)` returns the ready v1 spec (or `None`),
all resolutions, the map and visual tasks. The preparation result must accompany
any mechanical review; do not publish only its ready subset and hide the rest.
The CLI can save both preparation and spec with `--context-spec contexts.json
--spec-output ready.json`; if no request is ready, the latter contains JSON null
and must not be passed as an executable specification. Existing outputs and
source/input aliases are protected. Keep all job artifacts outside the public
repository and installed skill folder.

## Printed number formats

Amounts retain exact Decimal arithmetic and explicit canonical units (`ha`,
`m`, `m2`). The reader supports plain decimal numbers, properly grouped thousands
using one consistent comma or space separator, normalized nonbreaking spaces,
and one terminal sentence period after the unit. `m²` and `m^2` are explicit
square-metre spellings. No unit conversion is performed.

Malformed or mixed grouping, decimal commas, signs, exponents, ranges, extra
prose and multiple amounts in a selected cell remain unresolved. Limits remain
18 integer digits and 12 decimal places. Specification tolerances stay plain
decimal strings. Distinct competing totals, independent repeated part rows and
equivalent repeated totals retain the existing evidence/ambiguity handling.

Scale ratios consume the complete numerical denominator candidate. Correct
grouping and one terminal period are supported. A malformed scale such as
`1:2,50` or `1:2,500.0` cannot be accepted as `1:2`; it remains unresolved.
Multiple ratios, unsupported ratios and missing evidence retain their guards.
Reading a stated ratio does not measure plotted feature scale.
