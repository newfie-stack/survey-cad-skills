# Dated manual citation coverage

[requirement_coverage.json](../engine/requirement_coverage.json) inventories 144 numbered clauses in Parts 1–4 of the Government of Alberta's *Content Requirements for Survey Plans and Sketches for Dispositions on Crown Lands*, dated May 30, 2024. The [official publication listing](https://open.alberta.ca/publications/content-requirements-for-survey-plans-and-sketches) identifies the source; its current authority has not been verified.

The export contains short original summaries, PDF page references, requirement categories, review scope and exception notes, and declared links to candidate requirement IDs. It includes no source PDF, plan geometry, project data, local validation paths, or source-file hashes. Referenced external standards are dependencies, not additional requirements synthesized by this inventory.

All scope and exception text is **manual review guidance**. The inventory does not select rules, change activity/stage eligibility, expand the candidate catalogue, or determine plan compliance. A citation link does not establish that every subcondition has been implemented or evidenced.

Version 0.9.0 adds a separate [executed evidence pass](clause-execution.md) for
eleven bounded question paths across nine clauses. Seven hybrid-table predicates
read actual PDF fields; four general observations reuse supported finished-plan
comparisons. An optional actual CAD/GIS point-export comparison adds artifact
consistency evidence. Only explicitly selected questions run, with complete-table,
native-reading, role and metric-frame gates where needed. This does not change
the legacy citation-link counts, the 144 manual paths, atomic completeness or
any regulatory verdict. Even the nine supported clauses retain manual obligations.

The [November 21 source audit](regulatory-source-audit-2026-11-21.md) verifies the
linked May2024 content edition and selected clauses; the inventory's fixed
`UNVERIFIED_CURRENT` status still does not attest case-specific authority.

## Legacy observation links

The existing 17 candidates cite 29 distinct clauses directly. **115 clauses lack a direct candidate mapping.** Two of those are mentioned only in review instructions; those mentions do not close the gaps.

| Part | Clauses inventoried | Directly linked clauses | Clauses without direct links |
| --- | ---: | ---: | ---: |
| 1 | 48 | 26 | 22 |
| 2 | 8 | 0 | 8 |
| 3 | 52 | 3 | 49 |
| 4 | 36 | 0 | 36 |
| Total | 144 | 29 | 115 |

These counts describe the dated local inventory only. They do not establish completeness against current legislation, other publications, submission-stage requirements, or a particular application.

The separate, opt-in [clause workbook](clause-workbook.md) now supplies conditional manual review paths for all 144 clauses. Its 323 manual review checks contain 326 prompts; they are not 323 executed observations. Supplying this inventory explicitly to that workbook establishes that no numbered clause path is missing from this dated source universe. It does not change the 29 legacy citation links above, assess atomic-obligation completeness, prove the interpretation of every exception, or establish current authority. The workbook's declared observation links never execute adapters or bind observations automatically.

Important review conditions remain explicit in the data: compiled-plan exemptions at 3.6.1.1 and replacement certification; optional area precision and contour branches; the exactly-6.5-km amendment ambiguity; narrower activity codes within broader headings; the final-sketch-only overlapping-lease treatment; unspecified wetland exceptions; and DRS activity/applicant/risk conditions. This inventory export remains descriptive. Workbook selection separately requires typed application facts, with provenance for the dated catalogue; selection still means a review request rather than regulatory eligibility.

## Interface and safeguards

`load_inventory(path=None)` returns the validated inventory dictionary. The default path is the adjacent JSON export. Validation checks exact schema fields, unique full clause IDs, valid PDF pages, field/list types, requirement categories, and the fixed `UNVERIFIED_CURRENT` source status. Unsupported fields, including added verification claims, are rejected. A smaller invented inventory can be loaded for offline tests.

`audit_coverage(entries, inventory)` accepts a list of candidate dictionaries and a loaded inventory. It revalidates the inventory, then checks each declared ID against the actual entries. A direct link requires a unique existing ID and an exact matching citation publication title, version date, and section covering the clause. Supported section syntax is complete IDs, comma-separated complete IDs, and ascending ranges of complete IDs sharing the same parent, using `-` or `–`. Abbreviated, reversed, cross-parent, malformed, or ancestor-only references do not establish direct links. Ranges are compared as integer intervals without expansion.

A reference-only link additionally requires the full clause ID in the candidate's actual `review_instruction`, plus a valid citation with matching publication/version. References remain separate from direct links. Missing, duplicate, stale, or mismatched candidate IDs leave gaps and appear in `invalid_declared_links`; an undeclared replacement ID does not inherit a mapping.

The result always has `status: REVIEW_REQUIRED` and `source_status: UNVERIFIED_CURRENT`. `counts` and `by_part` contain:

- `total_clauses`: entries in the local inventory.
- `mapped_candidate_clauses`: clauses with at least one validated direct link.
- `unmapped_clauses`: clauses without a validated direct link, including reference-only clauses.
- `reference_only_clauses`: the subset of direct gaps with a validated review-instruction reference.
- `unreferenced_clauses`: gaps with neither kind of validated link.

Per-clause results contain validated IDs, `MAPPED_CANDIDATE` / `REFERENCE_ONLY` / `UNMAPPED` link categories, and invalid-link reasons. Those categories are not evidence or compliance statuses.

## Offline command

Run from the repository root to write the audit to standard output:

```sh
python skills/crown-plan-agent/engine/coverage_inventory.py \
  --catalogue skills/crown-plan-agent/engine/candidate_requirements.json
```

Add `--output coverage-audit.json` to create a new file. Existing outputs are never overwritten. `--inventory` can select another schema-valid JSON inventory. The command reads JSON only and performs no network requests or plan/PDF processing.
