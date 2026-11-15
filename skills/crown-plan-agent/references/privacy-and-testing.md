# Privacy, licensing and test strategy

## Absolute exclusions
- No client-specific or employer-specific plan files, names, coordinates, images, screenshots, attachments or metadata.
- No source package, full government PDF or third-party copyrighted document copied into this repository.
- No real project example or derivative fixture from a private plan.
- No API keys, login details or submission portal credentials.

## Synthetic test suite specification
1. Sketch vs statutory survey-plan requirements differ; prevent false universal checks.
2. Application vs amendment/renewal stage selects appropriate source clauses.
3. Linear disposition with disconnected pieces yields applicability review, not invented approval.
4. Missing governing source version yields REVIEW_REQUIRED.
5. Legacy 2022 document and 2024 document conflict: flag supersession/version review.
6. Missing CRS, malformed polygon or attribute schema is evaluated only when GIS submission is applicable.
7. Overlapping registered interests trigger evidence review; do not infer permission or prohibition.
8. Unknown professional declaration requirement cannot be marked PASS.
9. Deliberately missing plan PDF blocks visual plan checks.
10. Privacy scanner rejects non-synthetic plan files, company/client identifiers and credentials before publication.

Treat extracted requirements as candidates until the exact source clause and applicability have been verified.
