# Crown Plan Agent Revision Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compare two original PDFs under one review basis, linking checklist observations and reporting literal text changes without automatic comment closure.

**Architecture:** Reuse PDF inventories, source-bound note planning, review orchestration and exclusive publication. Add a bounded literal text comparison, a finding comparison model, literal Markdown output and an offline CLI. Keep optional PDF output the standard revised-plan review copy.

**Tech Stack:** Python 3.12, standard library and existing PyMuPDF; no new dependencies or hosted services.

**Spec:** `docs/superpowers/specs/2026-11-17-crown-plan-agent-revision-comparison-design.md`

## Global Constraints

- All regulatory results stay `REVIEW_REQUIRED`; a change is never automatically fixed, approved or compliant.
- Compare two explicitly ordered originals with one shared scenario/catalogue/reference basis; no historical saved-report import.
- Preserve raw text, case, numbers, punctuation and Unicode; normalize whitespace only.
- PDF limits: 100 MB, 100 pages, 200,000 spans per source. Comparison limits: 20,000 unique groups per side, 10,000 changed groups, 8,192 characters per retained text field, 20 MiB per JSON/Markdown artifact. Reject excess explicitly.
- Group literal text by normalized extractor span. Preserve all occurrences. Span fragmentation can yield inventory differences and must be described as such.
- Keep original PDFs and complete results private; develop with synthetic inputs only. Never publish source/derived project drawings or Octopus implementation.
- Fresh outputs stay outside installed skill/owning code repository; prepare all bytes before exclusive publication and rollback owned artifacts on ordinary failures.
- Preserve existing 0.5 CLI signatures, exceptions and default Markdown. Optional annotated output is the existing standard revised-plan review, not a graphical comparison overlay.

## Shared Data Contract

`revision_text.compare_text_inventories(baseline: dict, revised: dict) -> list[dict]` returns deterministic changed groups only. Each has `change_id` (`T00001`...), `normalized_text`, `change_status` (`ADDED`, `REMOVED`, `COUNT_CHANGED`), `before_count`, `after_count`, `baseline_occurrences`, `revised_occurrences`. Occurrences have `raw_text`, `page`, `bbox_points`, `page_size_points`, `text_angle_degrees`; unknown/invalid locations use null coordinates and a reason instead of invented bounds. Counts include every retained occurrence, including repeated identical spans.

`revision_comparison.build_comparison(baseline_inventory: dict, baseline_report: dict, revised_inventory: dict, revised_report: dict, *, basis: dict) -> dict` returns:

- `schema_version: 1`, `comparison_type: CROWN_PLAN_REVISION_TEXT_REVIEW`, `overall_status: REVIEW_REQUIRED`, `assessment_type: REVISION_EVIDENCE_COMPARISON_NOT_COMPLIANCE`.
- `basis`: copied shared basis; fields `engine_version: 0.6.0`, `engine_sha256`, `scenario_sha256`, `catalogue_sha256`, `references` (name/hash records), `basis_sha256`.
- `review_context`: bounded detached copy of the common scenario, with canonical digest equal to `basis.scenario_sha256`; show its actual application values in the human report as well as the hashes.
- `baseline` and `revised`: `{source_filename, source_sha256, pages}`; `identical_source_bytes` boolean.
- `requirements`: sorted IDs; each has `requirement_id`, `requirement_summary`, `review_instruction`, `correction`, `comparison_status`, `baseline`, `revised`, `location_changed` (bool/null), `citation` (title/version/section/page/url). Each side retains `source_text`, `observation`, `evidence_status`, `source_status`, `candidate_count`, `anchor` (page/bbox or null), page-frame provenance/status and `location_reason`. Revision-source inspection records actual page rotation and media/crop/display rectangles; unavailable frames do not establish location equality.
- `text_changes`: Task 1 result; `summary`: `{finding_counts: {each six-state name: count}, changed_text_groups: int}`.
- `baseline_review_summary`, `revised_review_summary`: existing source summaries, unchanged and bounded; `limitations`: explicit manual/visual/geometry/current-authority, text fragmentation and no-auto-closure limits.

Each source report must match its inventory's canonical SHA-256, source count and review-only assessment. Reject different report scenarios, mismatched finding definitions/citations or missing/noncanonical basis hashes. Use `requirement_id` identity, never R/GLOBAL sequence labels. Reuse pure note planning to validate actual source anchors and raw table cells; unknown/repeated/conflicting data takes precedence over apparent equality. Both report scenarios must canonicalize to `basis.scenario_sha256`; catalogue fingerprint is supplied by trusted orchestration and definitions are compared between both reports.

`revision_markdown.render_comparison_markdown(comparison: dict) -> str` consumes that schema. Source strings render literally. Output includes a clear scope, summary, source/basis hashes, per-finding before/after and source locations/citations, literal text changes with counts/locations, each side's unresolved review summary, and limitations. It does not embed remote resources or turn source text into active links/images.

## Review Focus

- Repeated second label changes while first text/count agree: ambiguity plus independent literal delta (Task 2).
- Replaced expected company/legal label no longer matches scenario: lost match plus literal old/new groups, never fixed (Tasks 1/2/4).
- Text layer disappears or only linework changes: report restricted text scope, no equality/compliance claim (Tasks 1/3/4).
- Review-copy index is mistaken for plan text: reject known Crown generated copies before comparison (Task 4).
- Output collides with a shared input, reference mutates or second publication fails: no partial packet/source overwrite (Task 4).

### Task 1: Literal Text Groups

**Files:** Create `skills/crown-plan-agent/engine/revision_text.py`; test `skills/crown-plan-agent/tests/test_revision_text.py`.

**Interfaces:** Consume the existing inventory spans/pages. Produce `compare_text_inventories` per Shared Data Contract; export comparison bounds as named constants.

- [ ] Write failing tests for added/removed/count changes, whitespace-only normalization, preserved Unicode/case/numbers, repeated occurrences, moved/reordered text (no content delta), split spans, malformed provenance, huge text/groups/change counts and nonfinite boxes.
- [ ] Observe targeted RED, then implement grouping and deterministic sorting without fuzzy pairing or ordinal sheet matching. Invalid provenance stays unlocated rather than obtaining invented coordinates.
- [ ] Run `python -m unittest discover -s skills/crown-plan-agent/tests -p test_revision_text.py`; record GREEN and immutable source hashes.
- [ ] Review task for spec and quality, then commit its explicit files.

### Task 2: Linked Review Observations

**Files:** Create `engine/revision_comparison.py` and `tests/test_revision_comparison.py` within the skill.

**Interfaces:** Consume Task 1's exact API and existing `build_markup_plan`. Produce `build_comparison` with the shared schema and six exact states from the spec. Scenario/hash validation uses deterministic canonical JSON (`ensure_ascii=False`, `sort_keys=True`, compact separators, `allow_nan=False`).

- [ ] Write failing tests for all six comparison states, raw table-cell text, unchanged text plus location-only change, repeated second-match edits, conflicting totals, missing/lost text, independent source-hash binding, changed scenario/definition/citation/basis and input immutability.
- [ ] Observe RED. Implement ordered finding comparison with ambiguity precedence; uniquely valid anchors on both sides are required for same/changed observed text. Both missing/visual remain not compared; lost/new observations are evidence transitions only. Keep source-page and publication-page references separate.
- [ ] Include literal text changes so unexpected replacement values are visible. Bound all carried strings and summaries; no silent trimming or row loss.
- [ ] Preserve actual display-frame changes and each finding's specific review actions. An empty literal multiset delta does not suppress a changed checklist observation or justify an overall no-change message.
- [ ] Run focused GREEN, review for spec and quality, then commit explicit files.

### Task 3: Readable Comparison Output

**Files:** Create `engine/revision_markdown.py` and `tests/test_revision_markdown.py` within the skill.

**Interfaces:** Consume only the shared comparison schema. Produce `render_comparison_markdown` with the declared size cap. It may render valid fixed fixtures before Tasks 1/2 finish; final integration must use the real model.

- [ ] Write failing tests for before/after values, unknown versus publication/source page labels, all states and counts, differing bytes with unchanged text, identical source-byte fact without approval, unresolved input requests, and literal hostile Markdown/HTML/URLs/control-looking text.
- [ ] Observe RED. Implement summary-first output, independently labelled source columns and escaped literal source fields. Never call a lost match removed geometry, a text change fixed, or matching text identical plans. No source string creates a report image, HTML block or remote hyperlink.
- [ ] Verify deterministic output and the 20 MiB UTF-8 bound; targeted GREEN, task review and explicit-file commit.

### Task 4: Offline Source Preparation and Artifact Packet

**Files:** Create `engine/revision_cli.py`, `engine/revision_sources.py`, `tests/test_revision_cli.py`, `tests/test_revision_sources.py` within the skill. Reuse existing modules without changing default review behavior.

**Interfaces:** `revision_sources.inspect_original_pdf(path: Path) -> dict` returns a normal source-bound inventory after rejecting known generated review copies. `revision_sources.read_bounded_file(path: Path, max_bytes: int) -> tuple[bytes,str]` supports shared source snapshots. `revision_cli.run_comparison(baseline_pdf: Path, revised_pdf: Path, output: Path, json_output: Path, scenario: dict, catalogue_path: Path, *, a2_pdf: Path|None=None, annotated_pdf: Path|None=None) -> Path` prepares and publishes the whole packet. CLI accepts ordered PDF positionals, `--scenario`, `--output`, `--json-output`, optional `--catalogue`, `--table-a2-pdf`, `--annotated-pdf`, and explicit `--offline` (offline always; no refresh flags).

- [ ] Write failing synthetic source tests for normal/renamed originals, source notes/widgets/URI, known 0.5 generated review copies, encrypted/invalid PDFs, snapshot bounds and source mutation.
- [ ] Write failing CLI tests for a real changed scale and expected company replacement; run same-source and scanned/linework-only cases; verify both source hashes, a common basis, private JSON/Markdown/optional standard current PDF, and no network calls.
- [ ] Test preflight before extraction for every collision/symlink/parent/repository/skill/input-alias path; test shared source/reference mutation and injected second-file publication failure leave no partial packet. Preserve original bytes.
- [ ] Implement bounded loaders and consistent scenario alias normalization, one shared loaded catalogue/reference snapshot, same-version review of both inventories, common basis fingerprints, full validation/serialization before publication and final source/shared-file rehash.
- [ ] Use existing `publish_artifacts`. Optional standard PDF must bind to revised source/report and be explicitly labelled standard review copy; comparison changes remain in the comparison report. Record actual current PDF note IDs only if used.
- [ ] Run focused source/CLI tests and 0.5 CLI compatibility tests; review for spec and quality, commit explicit files. Full suite belongs to final integration so parallel workers do not duplicate it.

### Task 5: Instructions, Acceptance and Release

**Files:** Update skill `SKILL.md`, new `references/revision-comparison.md`, engine README, release notes, master checklist, technical review, ChatGPT portable manifest, repository README/root manifest. Maintain source docs and runtime payload parity.

- [ ] Add the real runnable CLI example and plain-language ChatGPT flow: reuse context, ordered originals, no fake execution/files, manual checks unresolved, no overlay or automatic closure. Advance skill/plugin to 0.6.0 and repo plugin to 1.4.0 while preserving all other presentation/audience fields.
- [ ] Fresh consumer checks actual PDF/runtime, no runtime, known annotated inputs and ambiguous labels; correct instructions as needed without new user gates.
- [ ] Whole-branch independent technical review; resolve reproduced blockers with focused regressions and recheck. No unrelated refactor.
- [ ] Run final full tests, compilation, repository-root smoke, normal Markdown compatibility and both installed dependency versions when relevant. Compute reviewed code/test manifest, build archive, run independent clean-install synthetic acceptance with network denied and original/PDF preservation.
- [ ] Audit changed public text and archive payload: no private input/source reproduction/account email or Octopus implementation; only existing approved icons are binary.
- [ ] Commit/push feature, create public PR, verify exact-head CI, merge with expected SHA and verify main CI/tree identity/anonymous source bytes. Update existing private ChatGPT plugin with guarded release ID, verify saved manifests/core source/loaded skill+guide and preserved audience/presentation. Save external release receipts and provide a synthetic comparison example.

## Self-review and execution rulings

The approved spec is covered by Tasks 1–5; the shared model is the sole cross-task
contract. Source/basis fingerprinting and complete packet publication are owned
by Task 4. Manual decisions remain unassessed, not re-used across revisions.
Independent modules in Tasks 1–3 may be implemented concurrently with disjoint
file ownership, with Task 4 integrated by the controller. Each gets a fresh task
review, followed by a whole-branch review. This continues the last release's
working method under the user's explicit approval to implement and publish.
No second implementation-approval gate is added.
