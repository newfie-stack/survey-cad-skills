# Crown Plan Agent 0.4.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make assisted ChatGPT reviews easier to start and understand without changing compliance or reconstruction authority.

**Architecture:** Derive a compact summary and intake actions from the existing ledger. Keep rendering and strict input handling separate, and build the ChatGPT archive from the same reviewed skill source.

**Tech Stack:** Python 3.12 standard library, existing PyMuPDF dependency, unittest, portable Agent Plugins 1.0.

**Spec:** `docs/superpowers/specs/2026-11-16-crown-plan-agent-v040.md`

## Global Constraints

- Version 0.4.0; existing review-only and current-source gates remain unchanged.
- Actual Octopus code only; no hosted service or parallel COGO implementation.
- Synthetic fixtures only; no project data, source PDFs or private account attribution in public files.
- Existing ChatGPT plugin identity, private audience, prompts and themed presentation are preserved.

## Review Focus

- Missing versus explicitly blank AER subactivity must remain distinct.
- Amendment precedence must avoid asking for facts that cannot change the selected route.
- Supplied inventories and blocked geometry must not be described as executed extraction or measurements.
- Source annotations must stay literal even when they contain Markdown/HTML.
- Packaging must reject symlinks, unexpected artifacts and overwrites, and must not introduce a second skill variant.

### Task 1: Strict scenario and geometry input

**Files:** `engine/review_cli.py`, new `tests/test_review_cli_inputs.py` under the skill.

**Interfaces:** Keep `main(argv)` and `run_review(...)` signatures. Reuse the existing bounded JSON loader for CLI scenario/geometry files.

- [ ] Reproduce duplicate-key jurisdiction/coordinate declarations and malformed/nonfinite JSON before implementation.
- [ ] Add actual CLI regressions requiring a concise input error, no report and no refresh on rejected JSON.
- [ ] Apply the smallest strict-loader and error-handling change; preserve explicit blank activity.
- [ ] Run focused CLI/input regression tests and record results.

### Task 2: Derived summary and missing-input actions

**Files:** new `engine/review_summary.py`, new `tests/test_review_summary.py`.

**Interfaces:** `build_review_summary(report: dict) -> dict` returns `status`, `headline`, `checked`, `needs_attention`, `not_checked`, `input_requests`, `context_question`, `next_steps`. Each request has `field` and `question`. The report's existing `scenario`, plan-type, requirement and geometry fields are inputs; do not change existing eligibility statuses.

- [ ] Freeze expected outcomes for missing subactivity, explicit blank, amendment record/threshold precedence, renewal change status and out-of-scope cases.
- [ ] Observe failing tests, then implement deterministic deduplicated action selection and concise execution-aware wording.
- [ ] Cover empty/manual ledgers, observed-candidate versus compliance, conflicting area labels and uncomputed geometry.
- [ ] Run focused summary tests; leave the renderer and pipeline integration to Task 3.

### Task 3: Safe summary-first reporting and common instructions

**Files:** `engine/report_markdown.py`, `engine/review_pipeline.py`, `tests/test_report_markdown.py`, integration tests, `SKILL.md`, references and release/setup documents.

**Interfaces:** The pipeline exposes `review_summary`; Markdown renders the derived summary before detailed evidence and reuses its action list at the end.

- [ ] Reproduce active image/HTML syntax from a synthetic PDF annotation and failing summary-first integration expectations.
- [ ] Render user text literally while preserving original ledger values and readable evidence/citations.
- [ ] Integrate Task 2 without implying extraction, geometry or Octopus execution that was not recorded.
- [ ] Merge the ChatGPT capability guard and grouped plain-language intake into canonical SKILL.md; document version 0.4.0 behavior and limits.
- [ ] Run renderer/integration/smoke tests and fresh instruction-consumer probes.

### Task 4: Reproducible ChatGPT packaging

**Files:** new `packaging/chatgpt/` manifest/README/assets, `agents/openai.yaml`, `tools/build_chatgpt_plugin.py`, packaging regression tests.

**Interfaces:** A documented builder accepts an explicit fresh output ZIP path and packages the canonical skill, unchanged presentation assets and source metadata. No account IDs or normalized account author fields enter public templates.

- [ ] Test deterministic output, canonical source parity, version mismatch, missing assets, forbidden source artifacts, symlinks and output non-overwrite before implementation.
- [ ] Implement a standard-library builder with a contained single-plugin archive and reproducible file order/timestamps.
- [ ] Preserve existing public author handle and all three default prompts in their original order.
- [ ] Run packaging tests, inspect the final archive and perform an independent privacy/component audit.

### Integration and delivery

- [ ] Run full tests, compile, root smoke, JSON/YAML/frontmatter/link checks and independent acceptance cases.
- [ ] Commit only intended public files, push the feature branch, verify exact-head CI, and merge the authorized public update.
- [ ] Update the existing private ChatGPT plugin with an expected-release guard, verify stored components and cloud skill loading, and record exact source/release fingerprints.
- [ ] Report implemented behavior, tests and remaining host/professional limitations plainly.
