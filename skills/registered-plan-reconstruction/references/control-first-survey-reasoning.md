# Control-first survey reconstruction

## Mandatory sequence
1. Identify accepted known control: found/placed monuments, section/quarter posts, coordinate control, and independently verified older-plan anchors.
2. Extract **all** printed observations, including bearings, distances, widths, areas, ties, curves, road evidence, plan references, monument labels and details.
3. Build a **complete control/tie skeleton**, including disconnected chains, before creating the subject acquisition polygon.
4. Establish legal and topological constraints: registered boundaries, road limits, section evidence, terminals and caps.
5. Compute derived points by deterministic COGO.
6. Compute acquisition geometry by supported offset, intersection, trim/extend and terminal operations.
7. Independently verify control residuals, widths, topology, areas and source overlay.
8. Only then align locally verified geometry to accepted survey coordinates.

## Separate survey courses from acquisition limits
A printed monument-to-monument or target-to-monument bearing and distance represents the full observed course. It may pass through a road or beyond the acquired strip. Preserve it intact in the control graph. Derive only the supported acquisition portion separately. A course may serve multiple compatible roles, but shared role requires independent evidence; neither its label nor its location makes it a subject boundary.

## Disconnected components
Across a government road, canal, railway or excluded gap, locate **each** component from its own cited control chain. Do not project across the gap from an assumed road width. Keep distinct posts on opposite road limits distinct. An explicit 20.12 m road allowance is not automatically a traverse distance or a subtraction from a printed course.

## Found evidence and reference points
Preserve each monument identity, evidence description, role and raw observation. A named reference point or calculated point is not necessarily a found monument. Retain valid non-monument reference ties as supporting evidence but do not use them as independent monument control without proof. Multiple independent ties to the same found evidence are valuable residual checks and must not be collapsed.

## Failure policy
Never adjust source observations, shift monuments, manufacture a closure, or relabel endpoints merely to force an area or preview to match. If a required tie is omitted, the full review is incomplete even if the subject boundary closes. Report REVIEW_REQUIRED for unresolved identities and BLOCKED_MISSING_TOOL when COGO or DXF verification cannot run.

## Monument-anchored detail reconstruction
When an enlarged detail identifies a found iron and separately dimensioned upper and lower R/W courses, establish a local origin at that monument, compute each printed course independently, and retain the exact monument-to-monument connection. Do not replace the two observed course lengths with a single averaged line or a generic offset. Do not force their opposite ends to coincide or assume their distance equals the perpendicular corridor width; the endpoints may be controlled by different intersections. Preserve related existing-plan courses and tie lines in separate control layers. Require explicit evidence before attaching an uncertain western course chain or accepting a terminal. The standard azimuth equations (ΔE=d sin A, ΔN=d cos A) compute geometry but do not determine legal point identity.
