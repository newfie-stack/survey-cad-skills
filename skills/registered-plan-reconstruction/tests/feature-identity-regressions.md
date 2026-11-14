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
