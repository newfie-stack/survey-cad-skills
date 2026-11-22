# Job records and review completion implementation plan

> **For agentic workers:** Execute the owner's instruction to continue through the actionable work, using focused agents and independent review. Routine design choices are delegated to the implementation team.

**Goal:** Catch ordinary plan/record disagreements and printed area-balance errors, export actionable findings to review copies, and demonstrate the advertised assistance scope with fresh evidence.

**Architecture:** A bounded source reader reads original PDF fields and actual structured job instructions. Separate comparison and balance predicates consume these observations; a coordinator preserves workbook applicability and job-QA scope. Existing reports and PDF markup receive the new source-bound findings. No records are guessed from company logos, no reconstruction calculator or dependency is added.

**Tech stack:** Existing reviewed Python/PDF runtime and standard-library JSON/Decimal. All real inputs, record selections, review copies and complete run outputs stay outside the repository.

## Design choices

The alternatives were accepting expected strings, reading actual records, or assuming correctness from internal plan consistency. Actual records are the primary approach because they preserve the reference evidence and its reviewed job/role. An explicitly confirmed job-instruction file can provide an expectation for job QA; it does not substitute for a registry or application in regulatory question bindings. Internal consistency remains a separate bounded check.

The specification has `schema_version:1`, `records`, `comparisons`, `balances`.
`records` has `schema_version:1`, `prepared_by`, `subject_id`, `sources`, `fields`.
The `plan` source is the original CLI PDF; additional paths are explicit CLI/API
arguments, never instructions or URLs inside a document. Source metadata records
kind, format, immutable hash, subject and reviewed currency/basis. Field metadata
records source, semantic role, subject, measurement scope and native/PDF or JSON
pointer selectors. Actual values come from the supplied files.

Three new dated identity question paths compare plan-heading legal description
with the form and plan applicant with the form/registry. Disposition consistency
and confirmed instructions are job QA. The amount pass supports fixed sums,
approved+added−deleted=amended, gross−exclusions=net and width-group length sums.
Three optional dated arithmetic links remain partial observations. Printed
arithmetic does not accept categories, spatial partitions or legal boundaries.

Narrow string normalization preserves meaningful punctuation, suffixes,
compatibility characters and leading-zero IDs. Native geometry/raster/clipping,
ambiguous or multi-span/wrapped field evidence stays unresolved. Missing/stale
records, wrong roles/jobs/scopes, repeated underlying evidence, unit conflicts,
incomplete ledgers and unresolved applicability cannot become passes.

Source-located actionable findings from finished-plan, clause and job-record
passes enter the PDF review copy and complete index. Reference-document boxes
never become plan-page anchors. Reused aliases are deduplicated while linked
questions and differing scoped results remain visible. Regulatory status remains
REVIEW_REQUIRED even when a mechanical comparison fails.

## Files and tasks

- [ ] `engine/record_fields.py`, `tests/test_record_fields.py`: actual source snapshots, strict selectors and original field evidence; red/green tests before implementation.
- [ ] `engine/job_record_checks.py`, `tests/test_job_record_checks.py`: role/job/current-source gates and conservative identity comparisons.
- [ ] `engine/record_balances.py`, `tests/test_record_balances.py`: complete declared printed balances, source-bound units and exact inclusive tolerances.
- [ ] `engine/job_record_review.py`, CLI/report/summary integration and actual multi-document integration tests: execute only selected bound questions and keep every blocked request.
- [ ] `engine/pdf_markup_findings.py`, existing markup adapter and actual reopened-PDF tests: all actionable findings accounted for without invented anchors.
- [ ] Freeze code/instructions; independently review fresh invented job bundles without the oracle; freeze literal outputs before grading and preserve results.
- [ ] Exercise authorized real/public sources only within their actual evidence; retain missing references and provisional geometry as blockers.
- [ ] Update installation/review instructions, capability/readiness record, release metadata, test suite and package; independently audit and publish public source plus the existing personal skill.

## Review focus and acceptance

Tests must cover role decoys, inconsistent independent references, same bytes
relabelled as different records, wrong job/measurement scope, duplicate equal
components, shifted categories with unchanged totals, exact tolerance endpoints,
scans/rotations/clipping, stale hashes and plan-versus-reference PDF anchors.

Completion here means the advertised assistance features work from actual
evidence, preserve known tests, catch independently planted mistakes, export
findings and install reproducibly. Complete current-law interpretation,
representative real-plan professional acceptance, actual control/CRS acceptance,
unprovided records and dependency licensing remain external acceptance gates;
they cannot be closed by synthetic software tests or publication.
