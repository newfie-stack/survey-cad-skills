# Crown drafting checks and regression tests

> **For agentic workers:** Implement the independent fixture and engine tasks, integrate the benchmark, then obtain whole-change review. User authorized execution; no further planning approval is needed.

**Goal:** Catch ordinary drafting mistakes more reliably and make every measured improvement, regression and remaining blind spot visible.

**Architecture:** Retain the existing real-PDF review pipeline. Expand the invented benchmark with a separate two-layout LOC/MSL cohort, fixed hand-derived truth and paired controls. Separate safe execution/regression gates from physical-defect recall. Add the bounded competing-total improvement after a failing test.

**Tech stack:** Existing Python standard library and reviewed PyMuPDF Lite runtime. No new dependencies or native builds.

**Spec:** The user's requested synthetic tests for a plan reviewer that catches everyday omissions and inconsistencies, without office access or work documents.

## Global constraints

- Only wholly invented fixture source and truth enter the repository. Generated PDFs, renders and results stay outside it.
- Preserve source hashes, evidence locations and the existing runtime gate. Do not modify original plan files.
- Only `FAIL` counts as a detected planted defect. `REVIEW_REQUIRED` remains a miss when a physical defect is planted.
- Missing extraction completeness, raster overlap and unsupported graphics must not become inferred omission failures.
- Correct controls must not acquire false alarms. Known defects must not receive `PASS`.
- Drawing QC remains `DRAWING_QC_ONLY`, `REVIEW_REQUIRED` overall and `NOT_ASSESSED` for regulatory status.
- Keep legacy-cohort results separate from new cases. Do not label developer fixtures or a model trial independent professional acceptance.
- Preserve the maintained-release dependency policy. No vulnerability tests or custom native patch builds.

## Review focus

- Repeated equivalent totals must not be called conflicting; equal part rows must still both contribute to the sum.
- Ambiguous selectors or mixed formats must not be forced into a chosen authoritative amount.
- Page rotation, native rotated text, different sheet layouts and inset/history fields must not alter selected context.
- A benchmark must fail on a lost supported detection even if another case improves overall recall.
- An assisted review without supplied regions must be measured separately from deterministic preselected-region tests.

## Task 1: Independent invented drawings

**Files:** `tests/drafting_plan_fixture.py`, `tests/fixtures/drafting_plan_truth.json`, `tests/test_drafting_plan_fixture.py`.

**Interface:** `CASE_IDS`, `make_drafting_plan(path: Path, case_id: str) -> dict` returning a finished-plan specification, `job_brief(case_id: str) -> str`, and `scenario(case_id: str) -> dict`. Generated documents and briefs must not reveal mutation names or expected verdicts.

- [x] Create seven LOC/MSL cases with hand-derived truth: two clean layouts; wrong sum; competing totals; title/identifier/revision/scale disagreements; equivalent repeated rounded totals; raster note plus missing graphical arrow.
- [x] Independently inspect direct PDF text, rendering and source identity against literal expectations; do not compute the oracle using the engine evaluator.
- [x] Preserve the same job expectations across paired clean/defect cases.

## Task 2: Competing totals

**Files:** `engine/finished_plan_review.py`, `tests/test_finished_plan_review.py`.

- [x] Write and observe real-PDF failing tests for conflicting totals and benign equivalent repeats.
- [x] For a complete explicitly labelled final total field, parse every candidate; flag distinct amounts as an internal textual conflict without selecting an authoritative total.
- [x] Collapse numerically equivalent repeats only in that final total slot. Never deduplicate independent part rows.
- [x] Keep malformed, unverified, clipped or raster evidence unresolved; run the focused suite.

## Task 3: Benchmark gates and progress report

**Files:** `tests/finished_plan_benchmark.py`, `tests/test_finished_plan_benchmark.py`, existing frozen truth.

- [x] Add failing tests for per-check regression policies, false clearance, capability gaps and supported improvements.
- [x] Integrate the seven-case cohort only through its public fixture interface; production receives no truth.
- [x] Report detection/miss/false-alarm/false-clearance/unresolved counts by cohort and check category, preserving legacy totals.
- [x] Gate supported detections and clean controls per check; retain mandatory abstention on incomplete evidence. Distinguish regression success from full detection.
- [x] Check the actual CLI opening summary independently of its detailed report suffix.

## Task 4: Assisted exercise and release verification

- [x] Generate an exercise containing only an invented PDF and job brief, with no region specification or answer key in the review inputs.
- [x] Run a separate blind assisted review if the host supports it, then grade its cited observations against frozen truth. Report this separately from the offline benchmark.
- [x] Run the full Crown suite, audit-wrapper suite, synthetic smoke, expanded benchmark, package/privacy checks and ordinary dependency audit.
- [x] Update the test guide and bounded release notes; independently review the complete change before publication.

## Ledger

- Baseline: clean `173f0c4`; isolated branch `feature/crown-plan-agent-drafting-tests`.
- Design review: two read-only agents examined fixture coverage and scoring contracts before implementation.
- Execution choice: implement independent files in parallel; the shared contracts above define their integration.

- Verification: 724 Crown tests ran, 722 passed and two optional source-PDF tests skipped. The ordinary 12-test audit suite and complete 30-package metadata scan passed. Expanded benchmark: 23 cases, 21 planted defects, 18 detected, three missed, zero false alarms or false clearances. Legacy cohort: 12/14 detected; new cohort: 6/7.
- Independent review: P1 empty repeated amount could be dropped; three real-PDF regressions reproduced it, then passed with all 42 focused tests. P2 grouped unresolved counts were missing; focused scorer and generated-report tests reproduced it, then all 14 benchmark tests passed. Scoped review approved both fixes.
- Assisted exercise: one blind model review without supplied regions or answers found the four planted main-title, identifier, scale and revision discrepancies. This is not professional acceptance. Additional clean/visual controls are retained separately.
