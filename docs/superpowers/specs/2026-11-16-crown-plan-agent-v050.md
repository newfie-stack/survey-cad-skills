# Crown Plan Agent 0.5.0: marked-up review copies

The user approved adding marked-up PDFs. Add an optional derived PDF to the
existing offline Markdown review. Keep actual plans and derived review copies
private; annotated source pages remain source reproductions even if note text
uses fictional company names.

## Behavior

- `--annotated-pdf /private/review-copy.pdf` requests an additional review copy.
  Without it, the existing Markdown workflow and return type stay compatible.
- Keep original pages and existing annotations, with unchanged page boxes,
  rotation, unannotated appearance and text. Do not overwrite the source.
- Use numbered orange evidence-region comments on uniquely located text
  candidates. Comments identify the finding, review instruction, evidence page,
  citation/edition and unverified-source/review status. They do not assert a
  missing feature or regulatory failure.
- Append a printable notes index containing every emitted note, source-page
  references, source SHA-256 and review status. Located notes may link back to
  their source page using internal PDF navigation only. Unlocated items state
  their reason and receive no invented point on the plan. Source/context,
  unsupported geometry and unexecuted checks remain review-only index entries.
- A candidate is locatable only when its page and finite positive bbox identify
  a unique actual source text span, its raw source text agrees and its candidate
  count is exactly one. Preserve raw source text separately when a table cell's
  display label has been synthesized. Multiple candidates, missing/invalid
  provenance, visual checks and conflicting totals remain index-only.
- Bind the report, inventory and renderer's immutable PDF snapshot by SHA-256.
  Missing/mismatched binding aborts export. Reinspect source spans independently
  in the renderer before accepting anchors; caller-supplied hashes alone do not
  prove extraction. Cap source size/pages/spans and at most 200 notes; reject
  excess/oversized note data rather than silently dropping findings.
- PDF coordinates are unrotated CropBox-relative page points. Do not apply
  another rotation to extracted bboxes. Preserve the validated input anchor;
  PyMuPDF's reopened annotation rectangle can be misleading for rotated pages
  with UserUnit, so appearance checks must validate those cases.
- Every new output is exclusive and outside the installed skill/code repository.
  Preflight paths before inspection/refresh, prepare artifacts before publication
  and clean up only files created by this call if publication fails. Never
  overwrite an existing report or a symlink target.

## Components and interfaces

- `pdf_source.read_pdf_snapshot(path, max_file_bytes=100000000)` returns immutable
  PDF bytes and their SHA-256 after bounded reading.
- `extract_pdf` uses that snapshot and returns `source_sha256`; the pipeline
  propagates it into the report. Evidence records retain raw `source_text`.
- `pdf_markup_plan.build_markup_plan(report, inventory, *, source_sha256,
  max_notes=200)` returns a review-only plan with source hash and ordered notes.
  Each note has `note_id`, `finding_id`, `kind`, `title`, `body`, `citation`,
  `status`, `source_status`, `anchor` (page/bbox or null), and `location_reason`.
- `pdf_markup.build_annotated_pdf(source_pdf, report, inventory, *, max_notes=200)`
  returns `(pdf_bytes, manifest)` without writing output. The manifest records
  source hash, original/notes page counts, notes, located/unlocated counts and
  review status. It independently binds source spans and preserves source pages.
- CLI `run_review(..., annotated_pdf=None)` retains its Path return value. Its
  optional artifact section links notes to detailed finding IDs and records
  source/output hashes and located/unlocated counts.

Use the existing PyMuPDF dependency and real Octopus contract. No new hosted
service, OCR, CAD reconstruction or automatic normative findings are introduced.

## Verification

Use synthetic PDFs only. Test source hash mutation, repeated labels, missing
locations, generated table labels, source comments, print-index completeness,
overflow, malformed bounds, scanned-only/empty evidence and safe destinations.
Reopen outputs and check annotation metadata, page boxes/text, internal links and
unchanged source bytes. Render original pages with annotations disabled to prove
unchanged appearance, then verify annotation placement for rotations, CropBox
origins, clipped text and UserUnit-scaled pages. Test exclusive/failed publication
and packaging/source parity. Publish through existing public PR/CI and update
the existing private ChatGPT plugin, preserving its workflow/theme and audience.
