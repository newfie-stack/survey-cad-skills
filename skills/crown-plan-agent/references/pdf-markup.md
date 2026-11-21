# Marked-up PDF review copies

The optional export creates a private review copy alongside the normal Markdown
report. It keeps the original source pages and appends printable review notes.
It does not change legal geometry, verify source currency or certify compliance.
Keep the Markdown report with the copy: the PDF covers requirement findings,
summary notes and actionable finished-plan, dated-clause, job-record and point-
export comparisons. PASS comparisons remain in Markdown, as do separate CLI
appendices such as detailed Table A2 and drawing-disposition checks.

## Run the export

Use the actual original PDF and established review context. Keep the source,
Markdown and derived PDF outside the code repository and installed skill folder.
The output directories must already exist and output filenames must be new.
From the complete skill folder:

```bash
python engine/review_cli.py /path/to/private-job/plan.pdf \
  --scenario /path/to/private-job/scenario.json \
  --offline --reference-cache /path/to/private-job/empty-cache \
  --output /path/to/private-job/review.md \
  --annotated-pdf /path/to/private-job/review-copy.pdf
```

The source PDF and scenario must be supplied locally; these paths are
illustrative. Other established review inputs, including supplied Table A2 and
survey-coordinate files, can be added using the existing CLI options. Without
`--annotated-pdf`, the ordinary Markdown workflow remains available.

## Read the copy

- Orange regions identify uniquely located text evidence. Their PDF comments
  contain numbered review notes (`R001`, `R002`, etc.), finding IDs, instructions,
  citations and review/source status. A highlighted candidate is not a defect
  or approval by itself.
- Appended notes pages print the full note register, including source PDF page
  references, publication/section/edition information and the source SHA-256.
  Located entries offer internal navigation to their source page. Publication
  page numbers are identified separately from drawing PDF pages.
- Visual checks, repeated labels, conflicting totals and other findings without
  a reliable location are explicitly unlocated. They stay in the notes index;
  their absence from the plan overlay does not mean they were passed.
- Cross-document comparisons retain reference source IDs and locations as context.
  Only independently matched spans from the actual plan can receive a plan marker;
  an application or registry page number is never reused as a plan-page anchor.
- Aliased finished-plan/clause observations share one note with their linked
  finding/question IDs and distinct scoped results. Independent causes remain
  separate. Multiple valid plan targets remain in the complete index without an
  arbitrarily chosen location. QA discrepancies retain regulatory REVIEW_REQUIRED.
- Original page boxes, rotation, text, linework and existing annotations are
  preserved. Comments are overlays in a derived copy. PDF viewers differ in
  popup support; the printable index provides the same notes without popups.
- Unsupported characters are printed using explicit Unicode escapes where
  needed; the comment metadata retains the original note text.

Keep the original PDF for subsequent reviews and revision checks. The appended
review index is commentary, not additional plan evidence. Review copies do not
replace the original or establish that its approvals or signatures are valid.

## Provenance and limits

The engine binds the source snapshot, inventory and report by SHA-256, then
reinspects actual source spans before locating a comment. A filename match alone
is insufficient. Raw table-cell text is preserved even when the report adds a
descriptive total-column label. Hash binding identifies bytes; it does not
authenticate a reviewer or prove legal feature identity.

Source size, page/span and note limits apply. At most 200 notes and 200 printable
notes pages can be generated. Oversized or inconsistent inputs fail explicitly;
findings are not silently discarded. Existing outputs, source aliases, symlink
destinations and markup outputs inside the skill/code repository are rejected.
Prepared outputs are published without replacement; ordinary publication errors
remove only artifacts created by that call. This is not a crash-recovery guarantee.
All supplied job-record hashes are rechecked after building the PDF, immediately
before publishing the Markdown/PDF pair. Changed references stop both outputs.

The Markdown artifact section records source/output hashes and located/unlocated
counts. Its detailed finding IDs match the PDF note register. Do not upload
either an original or annotated private plan to GitHub or a plugin package.

## ChatGPT availability

The ChatGPT plugin includes the same skill and renderer source, with no hosted
execution server. Use the export only when the conversation can access the
original PDF bytes and execute Python with PyMuPDF. With text, screenshots or
instructions alone, explain the proposed comments and request only the genuinely
missing capability or source file; do not claim that a review PDF was created.
