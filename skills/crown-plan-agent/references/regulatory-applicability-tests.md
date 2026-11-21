# Regulatory applicability test matrix

This follow-up tests which dated manual questions are requested, which specific
exceptions suppress them, and which facts remain unresolved. It does not assess
current legal compliance or train a model.

## Invented scenarios

The independent [literal matrix](../tests/fixtures/regulatory_applicability_cases.json)
contains **45 scenarios across 15 families**, targeting **26 numbered clauses
and 52 named manual checks** in the explicitly selected May 30, 2024 content
manual. Expected selections, fact blockers and check kinds were authored from
the source summaries without executing the production condition evaluator.

The families cover PLA versus related-code length reporting, multipage review,
mixed-land presentation alternatives, continuous-sheet approval questions,
the existing-MSL-area threshold, surface/buried facilities, RTF family limits,
surveyor-sketch certification, accepted hybrid points, unfiled XC sources,
compiled bearings and existing monuments, natural boundaries, and FSL exception
evidence. Missing, explicitly unknown, invalid and unproven facts remain distinct.

These are applicability expectations. An unconditional question does not become
unselected merely because its supporting document is missing. An exception may
select a different evidence question instead of removing the subject entirely.
RTF syntax and an explicit regulator label do not establish regulatory eligibility.

The [integration tests](../tests/test_regulatory_pipeline_cases.py) also exercise
observed text versus an invented table row, missing scale evidence, compiled
and hybrid amendments, renewal against the plan of record, AER/provincial
differences, and private/mixed/unknown context across the complete report.
The table rows and text inventories are invented; no regulator PDF or real
application is embedded in these tests.

## Conflicting disposition aliases

The regression reproduces a report crash when a valid-looking `disposition`
conflicts with the legacy `activity` alias. The workbook formerly dropped the
alias while retaining the canonical code, so its renderer could not reproduce
the recorded invalid-context gate. It now retains that disposition dimension
as unresolved, produces clarification rather than selecting rules, and leaves
renderer validation intact. Equivalent aliases remain accepted. A forged
workbook that restores a valid-looking code while retaining a conflict is rejected.

## Run

From the repository root with the normal reviewed runtime:

```bash
python -m unittest discover -s skills/crown-plan-agent/tests -p 'test_regulatory*.py' -v
```

Ordinary full-suite CI also discovers these tests. The matrix is executed through
`review_inventory`, including candidate filtering, the dated workbook, summary
and Markdown rendering. Selected workbook questions stay manual; observations
are not automatically bound to them. Every case retains `REVIEW_REQUIRED`,
`UNVERIFIED_CURRENT` and obligation completeness `NOT_ASSESSED`.

## Coverage and remaining limits

The matrix's 26 targeted clauses are not complete semantic coverage of all 144
inventory clauses, every subcondition, other standards or every application.
Global status/context guards across all paths are separate from those targeted
conditional assertions. See the [coverage inventory](requirement-coverage.md).

The five already authorized public project packages were separately reused as
six original-PDF context controls. Their prior application scenarios were kept
unchanged; unresolved regulator, stage or plan-class facts kept the workbook
paths unresolved, as expected. No new drawing downloads or complete plan-review
acceptance resulted. Originals, extracted text and detailed results remain outside
the repository; no private/work plan was used.

Scenario fields and workbook facts remain separate declared inputs. These tests
use coherent pairs; synchronization of contradictory lengths, quarter counts or
surveyed-status declarations is not implemented by this change. Current-source
authority, evidence acceptance, CAD/GIS and professional review remain separate.
