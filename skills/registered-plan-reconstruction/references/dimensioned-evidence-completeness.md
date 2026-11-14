# Dimensioned survey evidence completeness contract

## Scope
The standard **full reconstruction** includes every source-supported course carrying a bearing and distance, whether or not it is part of the subject polygon. Include section and quarter-section evidence, road limits, existing registered boundaries, ties, traverse/control courses, witness offsets and subject right-of-way edges. A **boundary-only export** is optional and must be clearly named as a reduced derivative.

## Observation ledger
Each printed dimensioned course must have a stable ID and fields:
- source plan, page/detail and visual locator;
- raw bearing, distance, units and bearing basis;
- identified or unresolved start and end evidence;
- monument identifiers, descriptions and found/placed/calculated/assumed status;
- role: SUBJECT_BOUNDARY, SECTION_EVIDENCE, ROAD_LIMIT, EXISTING_BOUNDARY, TIE_CONTROL, TRAVERSE, WITNESS or REVIEW_ONLY;
- construction status: ACCEPTED, PROVISIONAL, UNRESOLVED or NOT_APPLICABLE;
- CAD entity ID(s), layer, and independent check residual where applicable.

A course may support more than one relationship; do not duplicate geometry merely to represent another role. Preserve the complete printed observation even if the acquisition boundary uses only a partial course.

## CAD and preview
Use distinct semantic layers for subject, section/quarter evidence, control/ties, monuments, and unresolved/assumed geometry. Include labels and evidence markers in the full review preview. Do not imply provisional endpoints are found monuments or that a visually plausible tie validates the boundary. Preserve raw observations in the audit manifest if the drawing's annotations are simplified.

## Completeness gate
Compare the set of dimensioned source-course IDs to the set of ledger entries and drawn entities:
- **PASS**: every applicable source course has an evidence-backed entity, role and endpoint assignment; independent checks meet documented tolerances.
- **REVIEW_REQUIRED**: all courses are inventoried, but any endpoint, direction, control residual, source association, or terminal is unresolved. Draw a conspicuously provisional candidate only when it is useful and unambiguously identified as such.
- **FAIL**: a source course is omitted without explanation, a tie is promoted to a legal boundary without evidence, or the output misrepresents assumed geometry as surveyed.
- **BLOCKED_MISSING_TOOL**: deterministic construction or DXF readback cannot be performed.

A successful DXF parser audit checks file integrity, **not** survey accuracy. Report source-course count, accepted count, provisional count, unresolved count and omitted count. A full reconstruction cannot PASS with omitted dimensioned courses.

## Synthetic regression fixtures
1. A closed 15 m corridor plus a dimensioned off-corridor section course: full review must contain both.
2. A bearing-distance tie to a found iron post: retain the tie and monument separately; do not add it to subject boundary closure.
3. An ASSUMED course with unknown endpoint: show on review layer and return REVIEW_REQUIRED.
4. A whole-line monument-to-monument distance with a partial acquisition segment: preserve full observation and derived partial segment.
5. A source with one omitted dimensioned course: completeness check must FAIL even if the DXF opens and the acquisition polygon closes.
6. A boundary-only export: clearly state that the full evidence graph remains available in the audit artifact.
All fixture dimensions, locations and identifiers must be synthetic and unconnected to private plans.
