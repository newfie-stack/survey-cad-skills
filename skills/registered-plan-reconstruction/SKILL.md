---
name: registered-plan-reconstruction
description: Reconstruct registered survey-plan geometry from printed observations and verified control using deterministic COGO.
version: 1.0.0
---
# Registered Plan Reconstruction
## Workflow
**Required order: Known Control → Observations → Control Network → Legal Constraints → Derived Points → Derived Acquisition Geometry → Verification → Spatial Alignment.**

1. Record source identity, bearing basis, units, printed distances, widths, curves, monuments, ties and plan notes.
2. Identify the NEW subject versus existing registered corridors; classify each observation as subject boundary, section evidence, tie/control, traverse, road limit, offset or annotation.
3. Build the complete source-supported monument/control network, then resolve point identity, feature side, sequence, terminals and full-line versus partial-line observations.
4. Construct the accepted subject controlling side, then compute bearing-distance positions, companion offsets, intersections, curves and closure deterministically.
5. Verify independent ties, widths, terminal intersections, printed areas, closure and source overlay; align to production coordinates only after local acceptance.

## Rules
- Preserve original observations and their source locations; do not trace raster strokes as geometry authority.
- Do not chain opposite sides of a right-of-way or treat a tie as a subject boundary.
- A calculated or non-monumented endpoint may still be a valid terminal.
- Keep full controlling survey courses separate from clipped acquisition limits.
- Do not apply ground/grid scale adjustments without a documented, applicable transformation.
- Do not invent bridging geometry to force closure or an expected area.
- Flag unresolved geometry as REVIEW_REQUIRED with supporting evidence and alternatives.

## Output
An observation register, provenance-linked derived geometry, residual/closure/area checks, and review status.

## Supporting references
- [observation register md](references/observation-register.md)
- [cogo construction md](references/cogo-construction.md)
- [verification checklist md](references/verification-checklist.md)

Read the applicable supporting reference before carrying out the corresponding technical workflow. Do not assume a regulatory rule is current without checking the official source.
- [spatial alignment md](references/spatial-alignment.md)
- [acceptance and failure modes md](references/acceptance-and-failure-modes.md)

## Complete survey evidence network — required
For a full registered-plan reconstruction, retain every source-supported found/placed monument, observation, tie line, control course, witness relationship and shared endpoint in a separate evidence/control graph, even when the final deliverable is boundary-only. Do not terminate reconstruction at a closed right-of-way polygon. Each tie must carry its raw bearing, distance, source locator, endpoint identities and evidence classification. If a tie's endpoint cannot be established independently, draw it only on a conspicuous PROVISIONAL_CONTROL layer with REVIEW_REQUIRED status; never imply it verifies alignment. Include both boundary and control networks in the standard review DXF and preview. A boundary-only DXF is an optional derivative, not the complete reconstruction. Recompute tie residuals against independently accepted monuments before claiming PASS.

## Section evidence and dimensioned boundary completeness
A full review reconstruction must inventory every source course with an explicit bearing and distance, including section/quarter boundaries, road-limit courses, monument-to-monument observations, ties, existing registered boundaries, and subject right-of-way edges. Classify each course by legal/evidence role; retain it on a distinct CAD layer and include its printed observation in the audit register. Preserve stated ASSUMED or calculated status. Never silently omit a dimensioned section course because it lies outside the subject polygon. If endpoints or direction are not independently established, include a visibly provisional construction with REVIEW_REQUIRED status, not a verified legal boundary. Distinguish undimensioned contextual linework from mathematically supported surveyed courses. The review preview must show all included courses, labels and found-evidence markers; report any dimensioned source course still omitted.

## Mandatory completeness gate
Read [dimensioned evidence completeness](references/dimensioned-evidence-completeness.md) before full reconstruction. Match every dimensioned source observation to a ledger entry and a correctly classified output entity or explicit unresolved exception. Do not report PASS with omitted dimensioned courses.

## Existing-corridor versus subject-corridor classification gate
Before joining any printed courses, identify the plan's **newly surveyed subject** using the title, bold represented limits, area labels, source plan references and enlarged details. Explicitly classify every other nearby corridor as EXISTING_REGISTERED_RW, ROAD, TIE_CONTROL or CONTEXT. A width label on an existing registered plan does not make that corridor the new subject. Require a feature-identity ledger mapping each candidate line to its plan number and role; never join courses merely because their endpoints look close or their bearings can form a traverse. Compare the proposed subject's footprint to the source image and both stated quarter-section areas before exporting. If feature identity remains unresolved, return REVIEW_REQUIRED rather than creating a zigzag. Raster digitization may be used as a clearly labeled visual topology check, never as authoritative COGO geometry.

## Consolidated specialist references
Read these before constructing a full plan:
- [Control-first survey reasoning](references/control-first-survey-reasoning.md)
- [Feature topology, endpoint identity and lineweight](references/feature-topology-and-lineweight.md)
- [Road, area and acceptance rules](references/road-area-and-acceptance.md)
- [Synthetic feature-identity regression specifications](tests/feature-identity-regressions.md)

Do not import plan-specific examples from private source material into this general-purpose library. Treat tests as specifications until executed.

## Independent dimension-reading gate
Before computing any accepted COGO, follow [observation transcription and course verification](references/observation-transcription-gate.md). Do not reuse a prior extracted number without rechecking the original source. An unresolved reading or feature-side association blocks PASS.

## Enlarged detail graph gate
Before propagating COGO through an enlarged detail, read [detail graph endpoint validation](references/detail-graph-endpoint-validation.md). A course attached to an existing registered R/W must originate at its source-shown monument, not the nearest point on the new subject or an adjacent continuation. Validate graph adjacency before accepting geometry.
