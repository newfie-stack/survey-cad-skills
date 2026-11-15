# Private validation and release acceptance plan

This plan prepares the unfinished validation milestones. The user authorized a separate private real-plan validation stage and designated its first input; a bounded first case has been exercised. Further inputs still require their own authorization and acceptance evidence. This document by itself does not authorize additional inputs or publication. Keep real inputs, extracted evidence and reports outside this repository.

## Evidence needed before a real review

1. Record who authorized each input and the permitted private working location.
2. Have a qualified reviewer identify the governing jurisdiction, regulator, application stage, disposition, purpose, subactivity, proposed plan type and any plan of record.
3. Supply the applicable official publications locally. Independently record publication versions, source URLs, effective dates, supersession and exact applicable clauses. The presence of a Table A2 PDF alone does not establish current authority or full requirement coverage.
4. Agree an answer key before running the engine: expected text observations, visual checks, unresolved cases, applicable source rows and independently calculated geometry. Include enough evidence to distinguish a correct observation from a coincidental label match.
5. Record the exact candidate snapshot (commit or review-archive SHA-256), Python/PyMuPDF versions and input hashes in the private validation record. Filename provenance in the current report is not an immutable artifact identifier.

## Suggested case matrix

| Case family | Evidence to compare |
|---|---|
| New AER application | Exact Table A2 purpose/activity row, supplied plan type, consultation and monument qualifiers |
| Amendment | Existing plan of record, total existing length, affected quarters, proposed changes and scope exceptions |
| Renewal | Unchanged/changed disposition evidence, plan on file, issue date and any regulator-approved variance |
| Provincial/Table A1 case or unsupported variant | Explicit unresolved result; independent manual assessment of applicability |
| Rotated, cropped, scanned or outlined PDF | Extraction fidelity, preserved provenance and visible limitations |
| Multiple headings or area totals | Unresolved ambiguity in both checklist and numerical comparison |
| Survey geometry | Independently verified CRS, ordered boundary coordinates, closure/area answer key and supplied tolerances |
| Missing/inconsistent inputs | Clear unresolved result with no invented authority, measurement or compliance finding |

Use only cases whose handling is authorized. Cases outside the implemented scope remain open; selecting an easier sample does not establish complete coverage.

## Local command after authorization

From the complete installed skill folder, using authorized private paths:

```bash
python engine/review_cli.py /private/validation/plan.pdf \
  --scenario /private/validation/scenario.json \
  --table-a2-pdf /private/validation/table-a2.pdf \
  --survey-geometry /private/validation/survey.json \
  --offline \
  --reference-cache /private/validation/empty-reference-cache \
  --output /private/validation/review.md
```

Omit `--survey-geometry` when separately sourced coordinates are unavailable. Use a new output path for each review; the CLI rejects overwrites. Do not use refresh flags. Keep current-source verification independent of the drawing-text and geometry checks.

## Acceptance record

- Reviewer identity, qualifications, review scope and candidate snapshot.
- Expected versus observed findings, with source clauses and artifact/page/bounding-box provenance.
- Missed or spurious observations, extraction failures and geometry discrepancies.
- Each unresolved item, owner, disposition and evidence needed to close it.
- Regressions for confirmed software defects using invented, redistributable fixtures; no real-plan derivatives in this repository.
- Explicit acceptance criteria and reviewer decision. Do not infer acceptance from a zero exit code or a passing synthetic suite.

Retain only an authorized, non-sensitive summary with any release package. The owner authorized publication of the development preview to the existing public repository; its [publication scope](PUBLICATION_REVIEW.md) preserves the private-input boundary and separate dependency obligations. Additional input handling and later releases need their own applicable authorization. Installation acceptance must separately demonstrate skill discovery and the offline example in a fresh supported runtime.
