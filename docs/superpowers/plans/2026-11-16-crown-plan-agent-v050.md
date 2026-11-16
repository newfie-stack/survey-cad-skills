# Crown Plan Agent 0.5.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce traceable private marked-up PDF review copies alongside the existing Markdown report.

**Architecture:** Bind snapshots and evidence, plan trustworthy note locations, render annotations plus a printable index, then publish requested artifacts exclusively. Keep provenance, rendering and CLI orchestration separate.

**Tech Stack:** Python 3.12 standard library, existing PyMuPDF, unittest.

**Spec:** `docs/superpowers/specs/2026-11-16-crown-plan-agent-v050.md`

## Global Constraints

- Version 0.5.0; original PDF/pages and existing annotations remain preserved.
- Synthetic development only; no actual source plan or derived review PDF enters GitHub or the plugin archive.
- No guessed locations or normative PASS/FAIL; all markup remains review-only.
- Immutable SHA-256 binding, bounded inputs/notes, exclusive outputs and no newly generated external PDF links/actions.
- Actual Octopus code remains the reconstruction provider; no reconstruction work in this feature.

## Review Focus

- Rotated/cropped/UserUnit pages must receive correct visible evidence marks without a second transformation.
- A forged/stale report cannot attach notes to another PDF merely through a filename match.
- Ambiguous/visual/unknown findings need complete index entries without fabricated marks.
- Notes must not silently overflow, disappear, introduce remote actions or obscure original page content permanently.
- A collision or write failure must preserve original/existing files and leave no misleading incomplete packet.

### Task 1: Source snapshots and trustworthy note planning

**Files:** new `engine/pdf_source.py`, new `engine/pdf_markup_plan.py`; `engine/pdf_inspector.py`, `inventory_review.py`, `deficiency_report.py`, `review_pipeline.py`; new provenance/planner tests.

- [ ] Write failing synthetic tests for SHA binding/mismatch, transformed table cell raw text, unique/multiple spans, invalid bounds, unlocated notes and note limits.
- [ ] Add bounded immutable snapshots to extraction and propagate source hash/raw evidence text.
- [ ] Implement `build_markup_plan(report, inventory, *, source_sha256, max_notes=200)` with the spec's exact note fields and deterministic IDs.
- [ ] Run focused planner/PDF/pipeline tests; preserve legacy review/status behavior.

### Task 2: PDF comments and printable notes index

**Files:** new `engine/pdf_markup.py`, new `tests/test_pdf_markup.py`.

- [ ] Freeze expected source geometry and test cases before implementation.
- [ ] Implement `build_annotated_pdf(source_pdf, report, inventory, *, max_notes=200)` returning bytes/manifest, independently reinspecting source spans and checking SHA binding.
- [ ] Add visible orange region comments, complete bounded index pages and internal source-page links. Preserve source annotations/page frames/content.
- [ ] Test reopens, note/citation completeness, overflow, repeated labels and clipped/rotated/cropped/UserUnit placement using appearance as well as metadata.

### Task 3: Optional CLI output and safe publication

**Files:** `engine/review_cli.py`, new artifact-publication helper if needed, new CLI/output regression tests.

- [ ] Observe failing tests for `--annotated-pdf`, default compatibility, output collisions/aliases, repository/skill destinations and induced write failures.
- [ ] Preserve the existing `run_review` interface, adding keyword-only `annotated_pdf=None`.
- [ ] Preflight all artifacts before refresh/extraction, prepare both outputs and publish with exclusive semantics and owned-file cleanup.
- [ ] Add traceable artifact counts/hashes to Markdown only when markup is requested; run focused CLI integration tests.

### Task 4: Skill, package and release integration

**Files:** canonical `SKILL.md`, new `references/pdf-markup.md`, engine/release/verification docs, portable manifest and repository plugin version.

- [ ] Teach the actual export command, reliable versus unlocated notes, source-copy privacy and host-execution requirements; keep one canonical skill.
- [ ] Set skill/private plugin version 0.5.0 and preserve names, prompts, colours, icons and private audience.
- [ ] Run full tests, compile, smoke, actual synthetic marked-up export, package build and source/privacy/link scans.
- [ ] Obtain independent technical and fresh installed-package/visual acceptance; resolve reproducible findings.
- [ ] Commit/push, verify exact-head CI, merge the public update, update the existing ChatGPT plugin with a guarded release ID and verify saved source/cloud instruction loading.
- [ ] Record source/markup/package fingerprints and remaining normative/native-UI limitations; summarize in normal language.
