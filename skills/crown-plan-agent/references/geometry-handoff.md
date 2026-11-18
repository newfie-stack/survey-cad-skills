# Geometry reconstruction handoff contract

When a plan has no separately supplied survey coordinates, prepare a proposal for
the existing survey skills. The offline Crown Plan Agent engine inventories and
reviews evidence; it does not reconstruct a registered plan from the PDF. Calling
`prepare_geometry_handoff(inventory, scenario, survey_geometry=None)` performs no
skill discovery, installation, invocation, CAD work, model call or network access.
The named companions' availability is `UNVERIFIED`. A separate agent workflow
must verify their availability and read their instructions before doing the work.

Before identifying missing specialist inputs, complete the
[top-to-bottom titleblock and Notes reading](chatgpt-review.md#read-the-complete-titleblock-from-top-to-bottom).
Reuse its printed legal location, bearing basis, CRS/datum/zone, units, factor
notes and control references with source locators. An absent coordinate JSON
does not establish that these statements are absent from the drawing. Record
them as source observations and retain unreadable or conflicting portions;
accepted control, alignment and coordinate provenance still need their own
evidence. Finished-plan QC can proceed within its scope without reconstruction.

Then follow the [main-view orientation and RP pass](chatgpt-review.md#orient-the-main-plan-and-locate-reference-points):
establish north, identify supported section/quarter context and locate circled
Reference Point (`RP`) markings. Inspect working-DWG layer `EVIDENCE` when that
convention and actual digital layer data apply; record DIDS target layer `35`
separately when a submission deliverable is relevant. Retain RP identifiers,
actual source/target layers, printed coordinates, point roles and source-supported
ties in the observation/control registers;
preserve uncertain associations and control acceptance separately. PDF page
positions, a circle or a layer name alone do not supply survey coordinates.

The handoff always has `status: REVIEW_REQUIRED` and
`execution_status: NOT_EXECUTED`. These describe the proposed specialist handoff.
Existing numerical diagnostics on separately supplied coordinates can still run;
they do not establish that reconstruction or specialist review was performed.

## Required reconstruction provider

The agent must resolve the reconstruction route to an available, reviewed
**Octopus code checkout**, following the [Octopus provider contract](octopus-reconstruction.md).
Reading a reconstruction skill or writing a new calculator does not execute
Octopus. Use its existing pure geometry module for reviewed partial/sketch
diagnostics; use its full registered-plan adapter only with legitimate source
identity and a supported, reviewed construction. If the provider is unavailable,
record `BLOCKED_MISSING_TOOL`, retain the source registers and stop construction.
Do not replace it with parallel Crown COGO code. The offline handoff helper
continues to prepare a proposal only; it does not discover or invoke Octopus.

## Routing and readiness

When coordinates are missing or their lineage remains unresolved, the proposed
skill order is:

1. `survey-plan-evidence-interpretation`:
   transcribe observations and classify their evidence roles.
2. `registered-plan-reconstruction`:
   execute the required Octopus provider from independently reviewed observations
   and the complete control network, within its supported representation.
3. `survey-dxf-cad-construction`:
   export accepted geometry, preserve evidence layers and reopen the output for checks.
4. `shapefile-validator`, only when the scenario
   explicitly contains `"gis_requested": true`: validate the requested GIS deliverable.

| `readiness` | Meaning |
| --- | --- |
| `RECONSTRUCTION_INPUT_REQUIRED` | No coordinate JSON was supplied. Gather the specialist inputs below. PDF page points never become survey coordinates. |
| `VERIFY_CRS_AND_PROVENANCE` | A coordinate object was supplied but an explicit source, CRS, provenance, role, closure declaration or supported representation gate remains unresolved. Read `acceptance_blockers`. |
| `QA_INPUT_SUPPLIED` | A nonempty ordered coordinate list and required declarations were supplied. Existing numerical QA may inspect them. This is input readiness, not geometric acceptance or regulatory compliance. |

For `QA_INPUT_SUPPLIED`, `requested_skills` is empty unless GIS was explicitly
requested, in which case it contains only `shapefile-validator`. The helper does
not propose evidence interpretation, reconstruction or CAD construction again.
The input and return contracts remain available as evidence requirements; they
do not become new work requests when the coordinate input is ready for QA.

The helper checks container/string/boolean types, finite numeric XY-pair schema
and declarations. It does not calculate coordinates, closure, area,
transformations or geometric validity. Even a single well-typed point can meet
schema readiness; that does not make it a valid traverse or polygon.
The existing diagnostic functions remain responsible for those checks. A caller
cannot establish evidence merely by setting a flag to true.

`source` preserves the known `filename`, `source_id`, observed one-based `pages`,
and document `page_count`. Page counts are not expanded into observation
locators. Unknown identities/counts remain `null`, and pages without observations
remain an empty list. A filename alone does not identify an immutable input snapshot.
The handoff carries no source-coordinate arrays.

## Inputs the specialist must receive

Keep authorized project materials outside this skill's public directory. Each
observation and derived entity must retain its source locator and evidence role.

| `required_inputs[].name` | Required evidence |
| --- | --- |
| `source_locator` | Exact source ID/snapshot, filename, registered-plan identity, and one-based page and detail for each reading. |
| `feature_identity` | The new subject versus existing registered/background identity; feature side, boundary/control/tie/road/context role, endpoint identities, sequence and terminals. |
| `bearing_basis_and_units` | Original bearing basis, assumed/grid/ground status, distance and coordinate units, printed scale notes and any applicable scale basis. |
| `raw_observations` | Original bearings, distances, widths, offsets and full curve definitions, original text, source page/detail, independent transcription confirmation and unresolved alternatives. |
| `control_and_spatial_alignment` | Every source-supported monument, control course, tie and witness relationship; independently established endpoints; CRS/datum/metric units; applicable transformation evidence or documented basis for no transformation; residuals and provisional control. |
| `gis_target`, when requested | Target format/components/schema, applicable published specification/version, CRS and comparison survey/CAD sources. |

Unknown readings, feature sides or coordinate roles remain unresolved. Preserve
original observations before normalization. Visual proximity, a closing polygon
or a similar printed area cannot resolve a boundary's identity.

## Ordered evidence and acceptance gates

1. Identify the exact source and subject/background features. Establish endpoint
   identities and roles before joining courses; review enlarged details separately.
2. Independently verify every printed observation against the source. Keep reading
   conflicts and alternative associations visible in the observation register.
3. Build the complete monument/control/tie graph before deriving the subject
   geometry. Include dimensioned section and road courses outside the subject.
   Unknown endpoints remain conspicuous provisional control and cannot verify alignment.
4. Apply legal constraints and accepted observations using deterministic COGO.
   Preserve full survey courses separately from clipped acquisition limits.
   Do not bridge gaps, adjust dimensions, flatten curves or invent endpoints to
   force closure or area agreement.
5. Verify independent ties, widths, terminals, closure, printed areas, source
   overlay and completeness. Every dimensioned course needs an output entity or
   a specific unresolved exception. Local acceptance precedes spatial alignment.
6. Resolve CRS, units and any applicable transformation from independent evidence.
   Unresolved CRS, coordinate roles or provenance block accepted geometry.
7. Generate and reopen the complete review DXF; check layers, entity counts,
   extents, duplicates, boundary/control content, residuals and preview visibility.
   A boundary-only derivative does not replace the complete review artifact.
8. Validate GIS components, schema, CRS, topology and consistency when GIS was requested.
9. Return the review artifacts and unresolved ledger. Supply explicit coordinate
   JSON to the existing Crown Plan Agent QA only for the representation it supports.
   Keep current regulatory authority/applicability gates separate throughout.

## Expected specialist return

`expected_return_artifacts` requests the following artifacts. Their presence in
the proposal does not mean they exist or have been accepted.

| Artifact name | Return contract |
| --- | --- |
| `source_and_feature_register` | Source snapshots/locators, subject/background identities, evidence roles, sides and endpoint graph. |
| `observation_register` | Every dimensioned course, original reading, normalized observation, provenance, classification, conflicts and unresolved alternatives. |
| `control_network` | Complete monument/control/tie graph, raw ties, independent endpoint identities and provisional exceptions. |
| `derived_geometry_and_verification` | Provenance-linked COGO and independent closure/area/width/terminal/tie/overlay checks, plus spatial-alignment evidence. |
| `review_dxf` | Reopened review DXF with subject boundary and complete control/evidence network on distinct layers, including conspicuous provisional content. |
| `review_preview` | All included dimensioned courses, labels, control/ties and found-evidence markers; identification of omitted courses. |
| `accepted_coordinate_json` | A separate explicit-coordinate envelope after evidence acceptance, compatible with the limited QA input below. |
| `unresolved_items` | Readings, missing courses, control/identity/CRS questions, exceptions, and unsupported specialist geometry, each with `REVIEW_REQUIRED` and next action. |
| `gis_validation`, when requested | GIS artifacts and component/schema/CRS/topology/source-consistency review against the applicable specification. |

The Python QA consumer is `geometry_review.review_survey_geometry`. Its core JSON
fields are `coordinate_source: "EXPLICIT_SURVEY_COORDINATES"`, a nonempty
projected metric `crs_identifier`, explicit boolean `crs_verified`, explicit
boolean `closed_ring`, and ordered numeric XY pairs in `vertices`.
`tolerance_m` and a reviewer-selected `area_label` are optional existing inputs.
See the [engine instructions](../engine/README.md#optional-survey-geometry-input)
for their exact behavior.

The handoff additionally requires explicit `provenance_verified: true` and
`coordinate_roles_resolved: true` for `QA_INPUT_SUPPLIED`. Record the underlying
source and acceptance evidence in the returned registers; these flags are
declarations, not an independent proof. Legacy coordinate JSON remains usable
by the existing numerical reviewer, while handoff readiness stays
`VERIFY_CRS_AND_PROVENANCE` until these declarations are resolved.

The existing QA operates on one ordered straight coordinate sequence. A closed
single ring enables polygon diagnostics; an open sequence only supports its
applicable traverse diagnostics. Curves, holes and multipart geometry have no
faithful representation in that polygon input. Preserve them in specialist
CAD/geometry artifacts with unresolved QA scope. Do not densify or flatten curves,
drop parts, fill holes or select one part and present the result as the complete
accepted subject. Nonempty `curves`, `parts` or `holes`, or an unsupported
`geometry_type`, block this helper's QA readiness. Missing shape metadata does
not prove a plan contains only straight single-ring geometry.

The numerical reviewer uses the same representation gate. A declared unsupported
subject returns `diagnostic_status: REPRESENTATION_UNRESOLVED`, with no traverse,
polygon or area-comparison measurements. It never measures only the outer ring
while silently dropping declared holes, curves or additional parts.

## Geometry coverage and ownership

| Geometry class | Offline engine | Specialist return needed |
| --- | --- | --- |
| Bearings, distances, dimension chains and course identity | PDF text/graphic inventory only; no boundary construction | Independently read observations, endpoint/side identities and deterministic COGO |
| Monuments, ties, widths, terminals and lengths | No legal role or control acceptance from page proximity | Complete control graph and independent tie/width/terminal checks |
| Supplied straight ordered sequence | Traverse diagnostics and, for one closed ring, polygon area/perimeter and basic intersections | Source provenance, resolved roles and independently verified metric CRS |
| Surveyed curves | Graphic Bézier inventory is not a cadastral arc; declared curves block QA measurements | Complete arc definitions and specialist curve geometry/verification |
| Holes, multipart or disconnected subjects | Declared unsupported representation blocks QA measurements | Preserve the complete geometry and verify each component and its relationships |
| Topology and spatial alignment | Limited single-ring diagnostics; no transformation or external alignment | Independent control, residuals, topology and transformation evidence |
| Plan/CAD/GIS consistency | No check without the relevant artifacts | Reopened CAD, source overlay, complete-course reconciliation and requested GIS validation |

This is a coverage assessment and return contract. It does not establish that a
companion has been discovered, executed or accepted for any particular plan.

## Runnable invented-input CLI example

From the `crown-plan-agent` folder, with `requirements.txt` installed, the example
below creates an invented one-page PDF and coordinate envelope in a temporary
directory, then runs the existing offline CLI. All source and acceptance
declarations refer only to the invented fixture. They demonstrate the JSON
contract and must not be copied to a real plan without supporting evidence.

```bash
export CROWN_HANDOFF_EXAMPLE_DIR="$(mktemp -d /tmp/crown-handoff-example.XXXXXX)"
python - <<'PY'
import json
import os
from pathlib import Path
import fitz

folder = Path(os.environ["CROWN_HANDOFF_EXAMPLE_DIR"])
with fitz.open() as document:
    page = document.new_page()
    page.insert_text((40, 60), "Sketch Plan Showing Invented Subject")
    page.insert_text((40, 90), "Invented fixture; no real survey evidence")
    document.save(folder / "invented-plan.pdf")
(folder / "scenario.json").write_text(json.dumps({
    "land_class": "alberta_crown", "regulator": "AER", "disposition": "LOC", "stage": "initial",
    "plan_type": "sketch", "gis_requested": False
}), encoding="utf-8")
(folder / "coordinates.json").write_text(json.dumps({
    "coordinate_source": "EXPLICIT_SURVEY_COORDINATES",
    "crs_identifier": "INVENTED_LOCAL_METRIC",
    "crs_verified": True, "provenance_verified": True,
    "coordinate_roles_resolved": True, "closed_ring": True,
    "vertices": [[7,11],[31,11],[31,24],[7,24],[7,11]]
}), encoding="utf-8")
PY
python engine/review_cli.py "$CROWN_HANDOFF_EXAMPLE_DIR/invented-plan.pdf" \
  --scenario "$CROWN_HANDOFF_EXAMPLE_DIR/scenario.json" \
  --survey-geometry "$CROWN_HANDOFF_EXAMPLE_DIR/coordinates.json" \
  --reference-cache "$CROWN_HANDOFF_EXAMPLE_DIR/empty-cache" \
  --offline --output "$CROWN_HANDOFF_EXAMPLE_DIR/review.md"
```

The report remains `REVIEW_REQUIRED`. Its mechanical diagnostics do not execute
specialist reconstruction or confirm current normative requirements. To inspect
the missing-coordinate route, run the same CLI without `--survey-geometry` and
use a different new output filename. No additional reconstruction command or
network opt-in is needed to prepare the handoff proposal.
