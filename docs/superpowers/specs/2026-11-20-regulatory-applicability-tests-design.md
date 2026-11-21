# Regulatory applicability regression design

The user authorized the next applicability test round: correct cases, errors,
exceptions and missing evidence, using the existing examples where useful.
The public plan intake established the relevant LOC/MSL/PLA/RTF and jurisdiction
families. Public drawings do not supply invented facts or prove current law.

## Scope

- Add independently authored, wholly invented scenario expectations for
  under-tested conditional paths in the explicitly selected May 30, 2024 manual.
- Exercise the complete review pipeline: candidate filtering, plan-type route,
  clause selection, evidence/source separation, summary and Markdown rendering.
- Preserve unknown facts, provenance blockers, specific exception controls and
  the distinction between a manual question and an executed compliance check.
- Fix the reproduced report crash caused by conflicting disposition aliases.
  The workbook must retain an unresolved disposition rather than silently choose
  a valid-looking canonical code after losing the contradictory alias.
- Record targeted clause/check coverage separately from global context-gate
  coverage and from complete regulatory-obligation acceptance.

## Approach

The existing unit suites already cover many individual thresholds. More tests
of those isolated functions would leave integration gaps. An independent literal
case matrix plus focused cross-layer regression tests supplies better coverage.
Rechecking more public drawings without application records would repeat known
scope blockers, so no new drawing download is needed for this round.

Use the existing Python runtime, catalogues, review pipeline and JSON fixtures;
no new dependencies, legal rule engine, OCR, geometry reconstruction or current-
authority promotion. Keep real drawing content, extracts and private paths out
of committed fixtures. The user's Midwest reference remains the accepted
drafting reference; this work tests conditional routing, not its validity.

## Acceptance

The alias-conflict regression fails before the fix and produces a renderable,
review-required report afterward. All literal scenario expectations pass, with
source/overall statuses unchanged. The complete existing suite, smoke test,
benchmark, packaging and publication checks pass. A separate reviewer inspects
the changes. Any cached public-context trial remains outside the repository and
is reported separately from invented tests and professional acceptance.
