# Regulatory Applicability Tests Implementation Plan

> **For agentic workers:** Use the existing test-first workflow; the coordinator implements and a fresh reviewer checks the branch. Steps use checkbox tracking.

**Goal:** Make regulatory applicability mistakes reproducible without inventing compliance verdicts.

**Architecture:** Independently authored literal scenario data drives the existing review pipeline. Focused integration tests verify cross-layer gates and the renderer conflict fix; the dated catalogue remains a manual review aid.

**Tech Stack:** Existing Python 3.12.16 runtime, unittest and JSON; no new dependencies.

**Spec:** `docs/superpowers/specs/2026-11-20-regulatory-applicability-tests-design.md`

## Global Constraints

- All committed scenarios and evidence are invented; no real plan content.
- Keep `REVIEW_REQUIRED`, `UNVERIFIED_CURRENT` and obligation completeness `NOT_ASSESSED`.
- Never infer jurisdiction, plan type or missing facts from a disposition code.
- Preserve renderer validation; represent invalid context honestly at its source.

## Review Focus

- Conflicting aliases must produce clarification instead of a crash or selected rules.
- Scope/regulator exclusions must hold across every output layer despite plausible text.
- Compiled exceptions must suppress only their cited targets and retain replacements.
- A matching or conflicting invented table row must remain distinct from observed text.
- Unconditional manual questions must not acquire invented exception/missing-fact branches.

## Task 1: Regression and conservative report repair

- [x] Write failing integration tests for conflicting and equivalent disposition aliases, plus forged-context rejection.
- [x] Run the regression on the unchanged engine and retain the failure log.
- [x] Normalize the conflicted disposition dimension as unresolved in `engine/clause_workbook.py`; leave renderer validation intact.
- [x] Run the focused tests and existing workbook/renderer suites.

## Task 2: Independent applicability matrix and integration guards

- [x] Add `tests/fixtures/regulatory_applicability_cases.json` with literal independently reviewed expectations.
- [x] Add `tests/test_regulatory_applicability.py` to execute those cases through `review_inventory`, checking exact selections, blockers and source/evidence states.
- [x] Add coherent cross-layer AER/provincial, table comparison, renewal, compiled/hybrid and scope cases.
- [x] Document actual tested paths and remaining manual/unverified limits in `references/regulatory-applicability-tests.md`.

## Task 3: Verification and delivery

- [x] Run full tests, smoke, existing benchmark and archive build; inspect committed files for source reproductions.
- [x] Conduct any reused public-context exercise privately, preserving known unknowns.
- [x] Obtain an independent code/data review and resolve actionable findings.
- [ ] Commit and create a pull request with exact verification results and scope limits.
