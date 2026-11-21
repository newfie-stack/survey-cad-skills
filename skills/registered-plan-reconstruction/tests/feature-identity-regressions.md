# Synthetic reconstruction regression cases
All cases use fictional points, invented bearings and synthetic coordinates. They are **not** copies of any registered plan.

1. **Existing zigzag trap:** new 15 m R/W runs east; an existing 15 m registered R/W branches southwest with longer printed courses. Expected: existing courses remain contextual, never chained into new subject.
2. **Two posts across a road:** independent subject courses terminate at distinct planted posts on opposite road limits. Expected: preserve both points and the road gap; do not subtract road width from either printed course.
3. **Whole-line versus partial:** A-C=120 m and B-C=30 m on the same verified line and shared endpoint. Expected: derive A-B=90 m only after confirming collinearity/identity, retain A-C and B-C as separate evidence.
4. **Tie-line masquerading as boundary:** tie from subject point to found iron lies along bold outline in raster. Expected: classify from plan context and monument evidence; do not promote to legal terminal without support.
5. **Lineweight ambiguous:** bold segment coincides with an older registered boundary. Expected: preserve both plan identities and explain the supported legal relationship.
6. **Two independent found-iron ties:** two separate courses terminate at same accepted monument. Expected: preserve both, compute residual and flag conflict.
7. **No-post terminal:** calculated end lies before nearby road. Expected: retain calculated endpoint; do not extend.
8. **Missing control course:** polygon closes but one explicit tie is absent. Expected: no PASS.
9. **Area mismatch:** corridor geometry checks, area differs. Expected: REVIEW_REQUIRED without changing source observations.
10. **Disconnected road components:** no independent control for second component. Expected: REVIEW_REQUIRED, not placement by road-width projection.
These cases are test specifications until exercised by an executable deterministic reconstruction engine.

## Consolidated multi-section and output cases
11. **Verified versus contextual section cut:** A fictional 15 m corridor occupies x=0–80 and x=100–180, with the road excluded and each piece tied independently. The evidenced quarter division at x=130 yields areas 1,650 and 750 m² (net 2,400); the context-only line x=150 creates no cut. Expect separately recorded areas and no road geometry in the acquisition layer.
12. **Compensating area error:** Use the same geometry but printed quarter areas 1,600 and 800 m². The total still agrees; with a fixture tolerance of 1 m², both quarter checks require review. If the legal cut is unknown, report the affected checks NOT_EVALUATED, not PASS.
13. **Local distance and failed placement:** A 100 m printed course with an unrequested .9998 combined factor remains 100 m locally. A failed independent third-point placement check cannot alter that local result or qualify the transformed output as accepted control.
14. **Source freshness:** An older accepted export exists; a changed source revision produces an unresolved endpoint. The current export is REVIEW_REQUIRED and may not replace the historical accepted file; reopening the old valid DXF cannot prove the new result.
15. **15 m deflection:** An eastbound course from (0,0) to (100,0) turns north to (100,60). Left-hand offset lines intersect at (85,15); perpendicular width is 15 m on both legs. Preserve the primary course and verify the miter, not a guessed split or averaged width.
16. **Reference setback:** A–R is 80 m and T–R is 15 m. Derive A–T = 65 m only with verified order A → T → R and an identified shared R. Drawing a pin at T or accepting the same subtraction with reversed order fails.
17. **ATS-only display:** With a supported local solution but no evidenced link to section control or other accepted absolute control, retain the local solution. An ATS-only display is a placement proposal, not a production-coordinate release; return ALIGNMENT_REVIEW_REQUIRED for placement.
