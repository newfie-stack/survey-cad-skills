# Compare a plan with its job records

Version 0.10.0 compares actual selected fields from the plan and supplied records.
It also checks declared printed balances and puts actionable findings into the
requested private PDF review copy. It does not determine a correct applicant from
a logo, authenticate a record, accept geometry or certify regulatory compliance.

## Use in ChatGPT

Provide the original plan and the relevant application, registry or earlier
approved record when available. Existing authorized attachments/Drive links and
confirmed instructions should be reused. A useful instruction is:

> Review this plan against the application and registry. Check the applicant,
> disposition, legal description and area breakdown, and give me a marked-up copy.

If the user says “The applicant for this job is Prairie Example Energy Ltd.”,
the agent can preserve that exact confirmation in a private job-instruction JSON
file, including who confirmed it and the source of the instruction. The engine
reads its actual bytes and selected string fields. This is an explicit expectation
for job QA, not evidence that the registry or application contains that name.

The agent reads the full titleblock, actual reference documents, source roles
and job/version context before preparing selectors. It selects by observed labels
and reviewed subject context, not by searching for the value it hopes to match.
Routine preparation is the agent's work. No user-authored JSON is required for a
normal assisted review. If the host lacks execution or original file access,
perform an evidence-limited manual review and state which engine/exports did not run.

With only a plan, the agent can report printed names and internal inconsistencies.
The correct company remains unconfirmed until supported by an actual reference or
explicit user confirmation. Applicant, operator, landowner and survey firm names
are distinct roles. Conflicting sources are shown separately; no majority or
preferred company is chosen automatically. Missing records stay visible.

## What executes

| Comparison | Basis | Remaining limit |
|---|---|---|
| Plan applicant versus actual client-registry legal name | `C_1_2_2_1_01` | Reviewed record role, currentness and legal identity are independent evidence gates. |
| Plan applicant versus accompanying form | `C_1_2_2_1_02` | Job instructions cannot replace that form. |
| Heading legal description versus accompanying form | `C_1_2_1_4_01` | Literal selected text only; illustrated extents remain a spatial question. |
| Full disposition ID versus a job record | Job QA | Preserve prefix and all digits, including leading zeros; no missing-number deficiency is invented. |
| Applicant versus explicitly confirmed job instructions | Job QA | Does not close form/registry questions. |
| Parts total | Partial `C_1_3_6_3_01` or job QA | Does not accept categories, extent or boundaries. |
| Plan amount versus an actual record amount | Job QA only | Does not close a dated regulatory question or accept categories, extent or boundaries. |
| Approved + additions − deletions = amended total | Partial `C_3_3_3_1_05`, when selected | A fixed implementation comparison; underlying records and itemized-survey conditions remain separate. |
| Width-group lengths total correctly | Partial `C_1_3_6_6_02`, when selected | Does not extend its access-road/literal-PLA branch to all pipelines. |
| Gross − exclusions = net | Job QA | Does not accept an exclusion, nonoverlap, ownership or hectare-and-acre obligations. |

Together with the existing eleven paths, these six dated bindings support
seventeen bounded observations across fourteen partially observed clauses.
All 144 manual clause paths and their residual questions remain available. A
source's publication edition and a plan's mechanical result remain distinct from
application-specific current authority.

## Fixed printed balances

`parts_total` sums independently selected components. `amendment` uses exactly
one approved term and one or more additions/deletions. `gross_net` uses one gross
term and exclusions. `length_schedule` sums distinct width-group lengths.
`record_match` compares one plan amount with one actual reference amount.
Arbitrary expressions are not accepted.

Each term has a unique component identity and source field. The reviewed equation
must cover its declared complete scope, using the same subject, measurement basis,
unit and an explicit tolerance with a stated basis. Equal-valued independent rows
remain separate; reused source observations cannot be counted twice. Decimal
comparisons include exact tolerance endpoints without binary floating-point error.
No implicit hectare/square-metre conversion or geometry calculation occurs.

Compare individual category amounts with the corresponding record fields where
available. Crown/private amounts shifted in opposite directions can preserve a
correct grand total; the per-category record comparisons expose that discrepancy.
The supplied category/subject association remains a reviewed declaration, not a
spatial classification inferred from matching numbers.

An amount needs its printed unit suffix or an actual selected unit/header field.
Headers are read and source-bound, not supplied as an unverified unit claim.
Conflicting suffix/header units stay unresolved. A historical approved value can
support an amendment's approved term or a `record_match` only in its explicit
`APPROVED_RECORD`/`HISTORICAL_BASIS` role; it is not a current applicant reference.

## Private command

Run from the repository root with actual authorized local originals and fresh
output names. The agent prepares this specification after reading the sources.

```sh
python skills/crown-plan-agent/engine/review_cli.py /private/job/plan.pdf \
  --scenario /private/job/scenario.json --offline \
  --clause-catalogue skills/crown-plan-agent/engine/dated_clause_catalogue.json \
  --clause-facts /private/job/facts.json \
  --job-record-spec /private/job/records-spec.json \
  --job-record-file form=/private/job/application.pdf \
  --job-record-file registry=/private/job/registry.pdf \
  --output /private/job/review.md --annotated-pdf /private/job/review-copy.pdf
```

Repeat `--job-record-file SOURCE_ID=PATH` for additional known sources. The original
plan is always source `plan`; it cannot be overridden with this option. Paths come
from explicit arguments, not document text or a remote URL. Unknown/duplicate
source IDs, stale hashes and malformed input fail before native processing or an
opted-in reference refresh. Missing expected files remain unresolved evidence.
The default workflow adds no automatic downloads.

The Python API is `review_job_records(plan_pdf, spec, record_paths, scenario=...,
clause_catalogue=..., clause_facts=...)`. Unbound job QA can run without a dated
catalogue; bound questions require the exact shipped catalogue and workbook
selection. Outside-scope or unresolved/overridden questions do not execute.

## Specification and evidence contract

The exact top-level object has `schema_version:1`, `records`, `comparisons`,
`balances`. IDs are bounded ASCII identifiers. `records` contains:

- `schema_version:1`, `prepared_by`, reviewed `subject_id`.
- `sources`: one to ten source metadata objects, including `plan`. Each has
  `source_kind`, `format`, `source_sha256`, `subject_id` and
  `review:{status,reviewer,basis}`. Kinds are `PLAN`, `APPLICATION_FORM`,
  `CLIENT_REGISTRY`, `JOB_INSTRUCTION`, `APPROVED_RECORD`, `OTHER_RECORD`.
  Formats are `PDF`, or `JSON` for job instructions. Review status is
  `CURRENT_FOR_REVIEW`, `HISTORICAL_BASIS` or `UNCONFIRMED`. A null hash represents
  an unavailable source; a supplied file requires its actual SHA-256.
- `fields`: one to 100 field specifications. Each has `source_id`,
  `semantic_role`, `subject_id`, `measurement_scope`, `selector`, `unit_selector`.
  Roles are applicant/operator/landowner/surveyor/disposition_id/legal_description/
  area/length. Identity scopes may be null when equally scoped; balance scopes
  must be known. A PDF selector is `{region:{page,bbox_points,role,label?}}`;
  a JSON selector is `{pointer:"/applicant"}` using bounded RFC6901. A null
  selector represents an unselected/unavailable field without an invented page.
  Unit selectors are optional and permitted only for area/length fields.

The original native span is retained without compatibility normalization or
invented joins. Initial automatic support requires one unambiguous native span;
wrapped/split/scanned/outlined/clipped fields remain open. Adding unrelated fields
or auxiliary unit selectors cannot hide a possible name continuation. The numeric
reader may separate only its own actual recognized unit token.

Supported dense rows use the source's actual finite typed field labels, including
their colon, or a complete printed quantity/unit token in a reviewed measurement
scope. Independently different known labels can separate fields; repeated/alias
labels still compete, including immediately above the selected field. A caller's
prefix cannot consume any payload after the actual header. Unknown prefixes and
unknown/wrong-role unit captions stay unresolved. With no prefix, the original
whole span is preserved. Same-line competing quantities, unknown continuations
and incomplete/split numbers stay open; bare ambiguous table cells are not inferred.

Comparison objects have `id`, `kind`, `plan_field_id`, `reference_field_id`,
`workbook_check_id` (supported ID or null). Kinds are `applicant_name`,
`legal_description`, `disposition_id`. Narrow NFC/ASCII-case/whitespace treatment
preserves punctuation, legal suffixes, abbreviations and compatibility characters.
Unconfirmed Unicode-case equivalence stays unresolved; it never creates a PASS.

Balance objects have `id`, `kind`, `scope_review:{status,reviewer,basis}`,
`subject_id`, `measurement_scope`, `unit`, `tolerance`, `tolerance_basis`,
`terms:[{field_id,component_id,role}]`, `total_field_id`, `workbook_check_id`.
Scope status is `COMPLETE_FOR_DECLARED_EQUATION` or `UNCONFIRMED`; units are `ha`,
`m2`, or `m` for lengths. Fixed term roles follow the balances above: component;
approved/addition/deletion; gross/exclusion; reference. Unknown subjects, scopes,
currentness, unit evidence or placeholders block a result.

The reader hashes all supplied snapshots, parses only selected active evidence,
and verifies that the sources remain unchanged. A hash identifies bytes; role,
subject, version and authority remain review declarations. JSON is data only;
duplicate keys, nonfinite values, arbitrary expressions and embedded paths are
not execution instructions. Limits are 100 MB per PDF, 2 MiB per JSON and 200 MB total.

## Results and correction copies

The opening summary identifies executed, blocked and inapplicable work. Markdown
retains each comparison/balance, original values, source hashes/locations,
currentness basis, arithmetic difference and tolerance. Every regulatory verdict
remains `REVIEW_REQUIRED`; job-QA expectations are identified separately.

Requested review copies include all actionable new findings in their index and
place comments only on unambiguous independently matched plan spans. Application
or registry coordinates remain reference context. PASS results and full raw
comparison details stay in Markdown. All reference snapshots are checked again
after PDF generation before publishing the output pair.

Known regressions are preserved in the actual-document unit/integration tests and
`tests/job_record_examples.py`. Fresh forward evaluation and real-input limitations
are recorded separately; no synthetic pass authenticates a real job record.
