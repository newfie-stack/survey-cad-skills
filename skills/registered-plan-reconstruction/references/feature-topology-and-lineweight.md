# Feature membership, lineweight and terminal evidence

## First identify the subject
Inspect the entire plan: title, registration number, legend, bold represented limits, area tables, source plan references, section/quarter labels, road allowances and enlarged details. Distinguish NEW_SUBJECT from EXISTING_REGISTERED_RW, SECTION_EVIDENCE, ROAD_LIMIT, TIE_CONTROL, TRAVERSE and CONTEXT. A width label on a referenced existing R/W does **not** make it the new subject.

## Observation graph
Each course needs immutable raw text, source locator, bearing/distance, feature identity, side identity, start/end identities, monument status and direct/derived status. Join two courses only when same-feature, same-side **and** common-endpoint identity are supported. Do not chain the opposite side, a width/cap or a control tie into the subject traverse. Do not merge visibly separate posts because an extraction model assigned the same label. Label recovery may correct identities, never source measurements or invented geometry.

## Lineweight
Bold/heavy linework is evidence of the depicted surveyed/acquired limit and sometimes continuation along an existing registered boundary. Use it as a topology/association cue together with source notes, endpoints and dimensions. Lineweight cannot independently establish a coordinate, bearing or distance. Do not replace source-based COGO with image tracing.

## Terminals
A supported non-monumented or calculated endpoint can be a legitimate terminal. Notes such as unsuitable for posting do not authorize extension to the nearest road or post. Use a perpendicular cap only when supported. For a surveyed-boundary terminal, intersect **both** corridor sides independently with the established legal boundary. Do not substitute a nearby dashed traverse/tie for that boundary. A road crossing may yield separate acquisition polygons and separate road-limit posts.

## Source details
An enlarged detail may control which line, monument, or crossing a printed observation belongs to. Preserve a reference from each interpreted course to its original sheet and detail. Ambiguous line association is REVIEW_REQUIRED.

## Posted points and reference setbacks
A boundary terminal identified as a planted or found pin must use that exact accepted point. If the computed location conflicts, retain and report the residual; do not move the pin or silently snap away the discrepancy. Keep two separately posted points distinct even when their symbols touch. A reference iron/post and a non-posted terminal are different points: if full course A–R and printed remainder T–R are on the same verified line, establish the directed order A → T → R and shared reference identity before deriving A–T. Retain the full printed course and remainder as independent ledger entries. An explicitly attributed square-cap assumption may support review geometry, but not source-supported PASS; an evidenced legal limit controls its actual intersections.
