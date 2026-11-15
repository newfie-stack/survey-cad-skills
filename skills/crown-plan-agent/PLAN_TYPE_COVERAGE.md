# Plan-type decision coverage inventory

This is a code and test inventory of the offline engine's current development
candidate for PR #8, based on `c0cf741` with the jurisdiction-scope updates,
prepared on 2026-11-14. It records implemented branches and missing coverage;
it adds no regulatory rules. Publication titles, dates and sections below are
the citations already embedded in the implementation. They were not freshly
checked against official sources for this inventory.

The main trace is [plan_type_review.py](engine/plan_type_review.py),
[requirements.py](engine/requirements.py) and
[table_a2_lookup.py](engine/table_a2_lookup.py). The CLI routing and source gates
are included where needed to describe the result a user receives.

## What “supported” means

Every `review_plan_type` result has `status: REVIEW_REQUIRED` and
`regulatory_table_verified: false`. A match means a supplied source row and a
declared plan kind agree. It is not a determination that a proposed plan is
legally sufficient, that the source is current, or that an application is
eligible. The review pipeline also keeps `overall_status: REVIEW_REQUIRED`.

| Scenario | Implemented decision support | Boundary of coverage |
| --- | --- | --- |
| New AER application (`stage: initial`) | Exact supplied Table A2 row lookup and proposed-plan comparison | Requires declared `IN_SCOPE` land, exact disposition, purpose and subactivity. No exception, ownership or acceptance determination. |
| AER amendment | Plan-of-record gate; surveyed-linear scope candidates | No automatic plan-type selection for sketch-based, hybrid, compiled or other amendments; no OneStop Add eligibility decision. |
| AER renewal | Changed-disposition gate; existing-plan comparison with Table A2; legacy-sketch review flag | Does not decide renewal eligibility or approve a variance. |
| Provincial authority (`regulator: Alberta`) | Candidate content sections/checklists; CLI instruction for manual Table A1 review | No Table A1 parser, lookup, required-plan comparison or provincial amendment/renewal route. |
| Unsupported/unknown regulator | Unresolved context; CLI asks for regulator confirmation before source selection | No automatic jurisdiction inference. |
| Private, municipal, federal or other land | Explicit `OUT_OF_SCOPE`; no Crown candidate sections/checks, AER specialized routes or Table A1/A2 request | Classification is declared context, not an independent ownership finding. |
| Missing, unknown or invalid land; mixed land without a resolved Crown component | Explicit `UNRESOLVED_SCOPE`; no Crown candidate sections/checks or AER specialized routes; CLI requests scope first | `land_class: mixed` requires `review_scope: alberta_crown_component`. Review then covers only that declared component. |

## Shared input contract and provisional content selection

`application_context(scenario)` requires a dictionary and validates four core
dimensions plus the declared land scope. Invalid or missing dimensions prevent
`applicability` from selecting content sections and prevent the candidate
catalogue from selecting checks, including checks with wildcard applicability.
`jurisdiction_scope` never infers scope from the regulator or disposition code.
Explicit outside-scope land takes precedence over other missing context.

| Input | Accepted form | Actual validation/result |
| --- | --- | --- |
| `land_class` | `alberta_crown`, `mixed`, `private`, `municipal`, `federal`, `other` | Outer whitespace is stripped. `alberta_crown` gives declared `IN_SCOPE`; private/municipal/federal/other give `OUT_OF_SCOPE`. Missing, blank or `unknown` gives unresolved/missing scope; other values/types give unresolved/invalid scope. |
| `review_scope` | `alberta_crown_component` when `land_class: mixed` | Outer whitespace is stripped. Missing/blank/`unknown` is unresolved/missing; every other value/type is unresolved/invalid. A component declaration does not accept the rest of a mixed-land plan. |
| `regulator` | `AER` or `Alberta` | Surrounding whitespace is stripped; spelling/case must otherwise match. Other values remain unresolved. Recognition does not establish jurisdiction. |
| `stage` | `initial`, `amendment`, `renewal` | Surrounding whitespace is stripped. Reclamation, as-built and other stages have no separate enum or route. |
| `disposition` | Three ASCII letters; legacy `activity` is an alias | Stripped and uppercased. This is a syntax check, not a Table A1/A2 or jurisdiction check. If both fields are supplied, normalized codes must agree. |
| `plan_type` | `sketch`, `surveyor_sketch`, `survey_plan`, `hybrid_plan`, `compiled_plan` | Surrounding whitespace is stripped. The five recognized enums do not represent five fully implemented regulatory decision systems. |
| `purpose` | Nonempty string for resolved top-level plan review | Added to `missing_or_invalid_fields` when absent, blank or nonstring. It is not part of the four-field content-selection gate. |

`applicability` selects only provisional sections from the cited 2024
plan-content structure. Every row below requires valid core context and declared
`IN_SCOPE` land:

| Declared input | Candidate sections added |
| --- | --- |
| Valid core context with `scope_status: IN_SCOPE` | `Part 1` |
| `sketch` or `surveyor_sketch` | `Part 2` |
| `survey_plan`, `hybrid_plan` or `compiled_plan` | `Part 3` |
| Disposition in `PLA`, `DPL`, `LOC`, `DLO`, `EZE`, `REA`, `VCE`, `RVC` | `Part 4.1` |
| `amendment` or `renewal`, with `survey_plan`, `hybrid_plan` or `compiled_plan` | `Part 3.3` |

This function does not select all activity-specific Part 4 subsections or the
specific hybrid/compiled-plan clauses. Its status remains `REVIEW_REQUIRED`.
With missing/invalid core or scope context it returns no sections and
`applicability_status: UNRESOLVED_APPLICABILITY`. Explicit outside-scope land
returns no sections and `applicability_status: OUT_OF_SCOPE` instead.

`review_plan_type` reports `CANDIDATE_ONLY` when scope is `IN_SCOPE` and the four
core dimensions and purpose are valid. It reports `OUT_OF_SCOPE` for an explicit
excluded land class, otherwise `UNRESOLVED` for unresolved inputs. AER
amendment/renewal subreviews use the four-field and `IN_SCOPE` gate calculated
before the purpose check: a missing purpose can coexist with an amendment-scope
route or an early renewal result. Invalid or absent proposed `plan_type` blocks
those two subreviews, even when an existing plan type is known. The initial A2
branch can identify a row without a valid proposed `plan_type` and leave the
comparison unresolved, but still requires `IN_SCOPE` and all other core inputs.
No specialized route or plan-specific guidance note is added for unresolved or
outside-scope land. General exception-review guidance remains review-only.

## New AER application and exact Table A2 lookup

To create `table_a2_requirement`, supply land declarations resolving to
`scope_status: IN_SCOPE`, a valid AER/initial context other than the optionally
unresolved proposed plan type, `table_a2_rows` (not `None`), a non-`None`
`purpose`, and a non-`None` `subactivity`. In the scenario, `activity`
continues to mean the legacy disposition alias; it is not the Table A2 activity.

`lookup_plan_requirement` requires nonblank string disposition/purpose and a
string activity. An explicit empty `subactivity: ""` can match a blank activity
row; an omitted/`None` activity cannot. Matching is case-insensitive, strips
outer whitespace from the supplied values and requires the complete values;
it does not resolve synonyms or infer an activity from a definition.

| Lookup result | Returned information |
| --- | --- |
| Exactly one matching row | `SOURCE_ROW_IDENTIFIED_REVIEW_REQUIRED`; row/page, `required_plan`, `survey_monuments`, RTF approval/authorization, consultation and footnote; source label `PLAR Table A2, October 28, 2026`; `regulatory_compliance: NOT_ASSESSED` |
| No matching row, duplicate matching rows, or invalid lookup inputs | `UNRESOLVED_APPLICABILITY`; `matches` lists row/page candidates, or is empty. No required plan is selected. |

For an identified row, the comparison branches execute in this order:

| Row/proposal condition | `table_a2_comparison` |
| --- | --- |
| No `required_plan` resolved | `TABLE_A2_ROW_UNRESOLVED` |
| Required plan is `N/A` | `TABLE_A2_PLAN_TYPE_NOT_APPLICABLE` |
| Proposed type absent/invalid | `PROPOSED_PLAN_TYPE_UNRESOLVED` |
| `Sketch` ↔ `sketch`; `Surveyor Sketch` ↔ `surveyor_sketch`; `Survey` ↔ `survey_plan` | `MATCHES_TABLE_A2` |
| `survey_plan` proposed where `Sketch` or `Surveyor Sketch` is listed | `SURVEY_PLAN_SUBSTITUTION_REVIEW_REQUIRED` |
| `hybrid_plan` or `compiled_plan` proposed | `PLAN_VARIANT_REVIEW_REQUIRED` |
| Any other recognized mismatch | `DIFFERS_FROM_TABLE_A2` |

The substitution branch appends a review note citing Table A2 PDF page 18 and
monument requirements. It does not approve substitution. Hybrid/compiled enums
have no mapping to a Table A2 required-plan value. A2 lookup is not reused as a
new-application rule for amendments or provincial cases.

`verify_disposition` is a separate code-presence check. It returns
`DISPOSITION_FOUND`, `DISPOSITION_NOT_IN_TABLE_A2`,
`DISPOSITION_NOT_PROVIDED` or `INVALID_DISPOSITION_CODE`, with matching row/page
references and `regulatory_compliance: NOT_ASSESSED`. Finding a code alone does
not select a required plan. Drawing-text code presence is a separate check again.

## AER amendments and plan of record

The amendment subreview requires `IN_SCOPE` and valid AER/amendment core context.
Supply `existing_plan_type` from the plan of record; the engine does not find the record
or infer it from a drawing heading. Existing types must exactly match a recognized
enum; this field is not whitespace-normalized.

| Condition | `amendment_review.route` | Comparison / effect |
| --- | --- | --- |
| Missing/invalid `existing_plan_type` | `PLAN_OF_RECORD_REQUIRED` | `REVIEW_REQUIRED`; no scope selection |
| Known existing record and proposed `compiled_plan` | `PLAN_VARIANT_REVIEW_REQUIRED` | Confirm eligibility/current amendment direction under section 3.6.1.1, page 14; the cited edition excludes compiled plans from section 3.3 |
| Existing type other than `survey_plan`, or disposition outside `DPL`, `PLA`, `DLO`, `LOC`, `EZE` | `AMENDMENT_PLAN_TYPE_UNRESOLVED` | Review plan of record and proposed changes under embedded AER Manual 018 (May 2025) section 6.6 citation |
| Existing `survey_plan` and a listed linear disposition | Initially `SURVEY_SCOPE_UNRESOLVED` | Enters the threshold logic below; embedded Crown plan-content manual (May 30, 2024) section 3.3.2, page 11 citation |

For the surveyed-linear route, `existing_length_m` means the total existing
surveyed disposition length, not only the amendment length. A valid length is
an exact Python `int`/`float`, finite and greater than zero; booleans are rejected.
`affected_quarter_sections` must be an exact positive Python `int`; booleans and
fractional counts are rejected. The following precedence is the implemented
behavior, not a fresh interpretation of the manual:

| Inputs, in branch order | Route | Instruction / comparison |
| --- | --- | --- |
| Valid affected quarters `> 2`, regardless of whether length is valid | `FULL_RETRACE_CANDIDATE` | Instruction cites section 3.3.2.3 retracement of the entire disposition |
| Otherwise, valid length `< 6500`, even if quarter count is absent/invalid | `FULL_RETRACE_CANDIDATE` | Instruction cites section 3.3.2.2, including its “except where it no longer defines the boundary” qualification |
| Otherwise, valid length `> 6500` and a valid quarter count (therefore one or two after the first branch) | `ITEMIZED_SURVEY_CANDIDATE` | Review adjacent amendment boundaries and section 3.3.3 content; additions/deletions digital polygon covers the entire amended disposition; confirm OneStop Add eligibility separately |
| Remaining combinations, including exactly `6500` with one/two or unknown quarters | `SURVEY_SCOPE_UNRESOLVED` | Obtain direction for exactly 6.5 km and at most two quarters; no boundary convention is invented |

Proposed compiled plans do not enter the ordinary threshold branches. The
content-section helper also omits explicit Part 3.3 for compiled amendments and
renewals; its broader Part 3 family remains provisional. This does not approve a
compiled proposal or fully implement all compiled exceptions.

An itemized candidate with proposed `sketch` or `surveyor_sketch` receives
`comparison: ITEMIZED_SKETCH_CONFLICT`; all other amendment comparisons remain
`REVIEW_REQUIRED`. More than two quarters at exactly 6500 still follows the first
full-retrace branch. Unknown plan of record, sketch-based records, and hybrid or
compiled records never inherit the surveyed-linear scope rule.

## AER renewals and the 2010 legacy boundary

The renewal subreview requires `IN_SCOPE` and valid AER/renewal core context.
The comparison uses `existing_plan_type`, not the proposed `plan_type`, although the latter is
still required by the core gate. The embedded citation is AER Manual 018 (May
2025), sections 7.5.1–7.5.6.

| Condition, in branch order | `renewal_review.comparison` |
| --- | --- |
| `disposition_changed is True` | `AMENDMENT_BEFORE_RENEWAL` |
| `disposition_changed` is anything other than exact `False` after the first branch, including absent, `0` or strings | `DISPOSITION_CHANGE_STATUS_REQUIRED` |
| Existing type absent/invalid | `PLAN_OF_RECORD_REQUIRED` |
| `table_a2_rows is None` | `TABLE_A2_REQUIRED` |
| Exact disposition/purpose/subactivity lookup unresolved | `TABLE_A2_ROW_UNRESOLVED` |
| Required plan `N/A` | `TABLE_A2_PLAN_TYPE_NOT_APPLICABLE` |
| Existing type maps exactly to required plan | `MATCHES_TABLE_A2` |
| Existing `survey_plan`, row requires `Sketch`/`Surveyor Sketch` | `SURVEY_PLAN_SUBSTITUTION_REVIEW_REQUIRED` |
| Existing `hybrid_plan`/`compiled_plan` | `PLAN_VARIANT_REVIEW_REQUIRED` |
| Existing `sketch` mismatch, issue date absent/invalid | `LEGACY_ISSUE_DATE_UNRESOLVED` |
| Existing `sketch` mismatch, parsed `disposition_issued_on` before `2010-09-01` | `LEGACY_SKETCH_VARIANCE_REVIEW` |
| Existing `sketch` mismatch, issue date exactly `2010-09-01` or later | `DIFFERS_FROM_TABLE_A2` |
| Other recognized mismatch | `DIFFERS_FROM_TABLE_A2` |

`disposition_issued_on` is parsed with `date.fromisoformat`. The date flag is
only reached for a sketch mismatch; it is not needed when a sketch matches the
row. The before-September-1 cutoff is strict. It flags review and does not prove
full-term status, mapping/sketch criteria, a permitted variance, renewal
eligibility or regulator approval. Changed-disposition status is not inferred
from geometry, the proposal or an issue date.

## Manual authority, source currency and exceptions

- Only declared `IN_SCOPE` land proceeds to regulator-specific source routing.
  Outside-scope land requests no Crown table; unresolved land requests
  `land_class`/`review_scope` confirmation before table selection. Cached A2 is
  ignored outside `IN_SCOPE`; explicit A2 PDF/refresh/URL inputs are rejected
  before PDF extraction or network refresh.
- With `IN_SCOPE`, `regulator: Alberta` produces `PLAR Table A1 manual review`,
  requests the exact disposition/purpose/activity and current provincial
  requirements, and leaves currency `UNVERIFIED` and compliance `NOT_ASSESSED`.
  Cached A2 is ignored; explicit A2 PDF/refresh/URL inputs require both `IN_SCOPE`
  and `regulator: AER`. Declared scope does not independently establish ownership,
  regulator jurisdiction or current authority.
- The October 28, 2026 A2 parser validates its expected 18-page revision, table
  shape, 135-row sequence and accepted plan labels. That supports a particular
  document structure; it does not establish that the revision governs today.
  A different revision/layout is rejected rather than silently interpreted.
- `review_source_record` validates citation fields, ISO dates and an allowed
  official HTTPS host. Even a complete citation retains
  `source_status: REVIEW_REQUIRED` and requests independent version,
  supersession and applicability verification. Existing citation-validation
  tests do not amount to fresh authoritative-source checks.
- The candidate catalogue permits only `UNVERIFIED_CURRENT` entries. The
  pipeline retains that source status. Successful optional A2 refresh reports
  `CHECKED_OFFICIAL_SOURCE` with `regulatory_currency: NOT_VERIFIED`; the CLI
  still prints `Source currency: UNVERIFIED`. Refresh failure does not silently
  proceed with stale cached A2 when refresh was explicitly requested.
- Generic `evaluate` permits evidence-level `PASS`/`FAIL`, but its regulatory
  status stays `REVIEW_REQUIRED` unless the caller supplies an exact boolean
  `current_authority_verified=True`. The review pipeline does not supply such
  an attestation or implement independent verification.
- All plan-type reviews carry an exception-review note. Within declared
  `IN_SCOPE`, surveyor sketches add an ALS preparation/signature note; AER
  surveyor sketches add the existing Bulletin 2025-31 oil-sands/coal scope caution and Public Lands Act section 23
  note. These are prompts, not tests of eligibility, signature or exceptions.
  RTF, consultation and footnote values are preserved as row evidence; their
  conditions are not adjudicated. There is no exception/approval override
  model that promotes a comparison to regulatory acceptance.

## Concrete test references

These are existing offline/synthetic tests, except for the two explicitly
optional local-official-PDF checks. They establish implementation behavior only.

| Path / test class | Relevant test methods |
| --- | --- |
| [test_plan_type_review.py](tests/test_plan_type_review.py), `PlanTypeReviewTests` | `test_table_a2_plan_type_comparison_stays_review_only`; `test_table_a2_does_not_pick_between_duplicate_rows`; `test_renewal_compares_active_plan_and_routes_legacy_sketch_for_review`; `test_surveyed_linear_amendment_scope`; `test_sketch_plan_of_record_does_not_inherit_survey_scope_rule`; `test_amendment_requires_manual_table_check`; missing purpose/type and nonmapping tests |
| [test_jurisdiction_scope.py](tests/test_jurisdiction_scope.py), `JurisdictionScopeTests` | Excluded/missing/unknown/invalid scope, wildcard gates, declared Crown and mixed Crown component; scope precedence; all three stage routes and plan-specific guidance blocked outside scope; unresolved proposed type identifies A2 row only within Crown scope |
| [test_cli_jurisdiction_scope.py](tests/test_cli_jurisdiction_scope.py), `CLIJurisdictionScopeTests` | Outside-scope reports request no Crown sources; unresolved land asks scope before PLAR; cached A2 ignored; explicit A2 options/direct inputs rejected before extraction/refresh; confirmed Crown and mixed-component AER/A1 routing |
| [test_application_context.py](tests/test_application_context.py), `ApplicationContextTests` | Missing/invalid core context, wildcard guards, disposition aliases/conflicts, both recognized regulators; `test_amendment_uses_normalized_proposed_plan_type`; `test_unresolved_core_context_cannot_select_specialized_routes`; `test_missing_purpose_preserves_known_amendment_scope_review` |
| [test_requirements_engine.py](tests/test_requirements_engine.py), `RequirementsEngineTests` | `test_sketch_and_survey_plan_are_not_conflated`; `test_invalid_context_does_not_select_content_sections`; `test_disposition_alias_selects_the_same_content_sections`; source inventory remains unverified; evidence/authority and missing-evidence gates |
| [test_table_a2_lookup.py](tests/test_table_a2_lookup.py), `A2LookupTests` | Exact/duplicate/unknown row lookup; explicit blank versus missing activity; disposition-only presence, missing, invalid and unlisted code results |
| [test_review_cli.py](tests/test_review_cli.py), `ReviewCLITests` | `test_provincial_review_requests_manual_table_a1_review`; `test_unknown_regulator_requires_confirmation_before_source_selection`; non-AER cached/explicit A2 rejection tests; amendment/renewal report tests; local A2 without network; missing table; refresh/error guards |
| [test_source_review.py](tests/test_source_review.py), `SourceReviewTests` | Complete citation still requires review; missing section; bad date; HTTP and lookalike host rejection |
| [test_regulatory_catalog.py](tests/test_regulatory_catalog.py), `RegulatoryCatalogTests` | Candidate-not-PASS selection, unknown scenario, unselected plan kind, rejection of forged verified source |
| [test_table_a2_refresh.py](tests/test_table_a2_refresh.py), `RefreshTests`; [test_official_pdf_cache.py](tests/test_official_pdf_cache.py), `OfficialPDFCacheTests` | Synthetic/injected refresh and cache behavior, ambiguous discovery, pinned-host rejection and persistent unverified currency; not a live network check |
| [test_table_a2_rows.py](tests/test_table_a2_rows.py), `TableA2RowsTests` | Unrelated PDF rejection; `test_official_october_2026_pdf` and `test_official_pdf_to_report_integration` run only with `CROWN_A2_TEST_PDF`, using a locally supplied official publication and a synthetic drawing, not a private project plan |

## Actionable gaps requiring no private inputs

The following work can use invented scenarios, small synthetic row dictionaries
and public-source citations. Where new regulatory behavior is involved, verify
the applicable current public source first; absence of a test does not justify
inventing the rule.

| Gap | Concrete next work and acceptance boundary |
| --- | --- |
| Declared land scope still needs evidence | The engine now blocks excluded or unresolved land and limits mixed-land selection to an explicitly declared Crown component. Independently establish land/component identity and regulator jurisdiction for an actual application; these declarations are input gates, not evidence verification or regulatory rules. |
| Plan variants still need complete source coverage | The new decision matrix covers initial/renewal variants, exact mappings, mismatches, substitutions and N/A precedence. The catalogue now includes general content, exact hybrid/compiled title candidates and compiled Appendix D review; the remaining variant-specific clauses are not implemented. |
| Provincial Table A1 remains manual | All three Alberta stages are tested to stay outside AER specialized routes; CLI tests retain manual A1 instructions. A future A1 adapter needs its own source/revision/row tests; A2 presence or enum recognition is insufficient. |
| Amendment authority and threshold interpretation remain open | The matrix now covers all five linear codes, invalid/missing length/quarter dimensions, non-linear/other record types and independent precedence cases. Oversized integer lengths no longer abort review. Exactly 6500 m remains unresolved for at most two quarters until authoritative direction supports a change. |
| Plan-of-record evidence remains external | Missing, arbitrary, padded and wrong-type existing records are tested across amendment/renewal; other variants cannot acquire surveyed-linear scope from dimensions alone. Actual active-record identity still requires evidence. |
| Renewal eligibility remains manual | Tests now cover nonboolean changed flags, invalid dates, before/at/after cutoff, matching-sketch precedence, variant/substitution/N/A paths, duplicate rows and missing purpose/subactivity. These comparisons do not establish full-term eligibility or variance approval. |
| Programmatic row provenance remains unverified | Row shape, codes, locators, required plan labels and supplied optional fields now receive explicit validation before matching; malformed labels cannot reach a mapping error. Code-presence lookup retains its smaller record contract. Shape validation does not attest origin or revision; carry explicit row-set provenance before supporting additional revisions. |
| No independent current-authority attestation workflow | Test full-path source status remains unverified despite complete citations, matching rows or successful refresh. A future verification workflow must record version/supersession, exact clause applicability, reviewer and evidence rather than accepting citation completeness as authority. |
| Exceptions are notes, not a decision model | Add tests preserving ALS/Bulletin/substitution/consultation/footnote cautions and proving no exception becomes an approval. Any structured exception path needs current public-source predicates and independent evidence, not a private approved plan as precedent. |
| Full A2 extraction depends on an optional local publication | Existing two PDF integration tests may be skipped. Synthetic parser rejection/layout tests can be added without committing a publication. Execute the local-publication tests separately when an authorized supported official PDF is available; do not treat skipped tests as extraction verification. |

The added [decision matrix](tests/test_plan_type_decision_matrix.py),
[row contract](tests/test_table_row_contract.py) and
[variant catalogue cases](tests/test_plan_variant_catalogue.py) use invented
inputs. The first two have 13 and 12 test methods respectively; variant cases
have eight. Source-current and professional acceptance remain separate.

## Reproduction and inventory verification

Before the explicit scope gate, an entirely invented `land_class: private` case
with valid AER/LOC/initial/sketch core context selected `Part 1`, `Part 2` and
`Part 4.1`, reached `CANDIDATE_ONLY`, and selected a matching synthetic
catalogue entry. Regulatory statuses stayed review-only, but the declared
private land did not prevent Crown candidate selection.

The regression now asserts the following behavior with invented inputs:

| Declared scope | Candidate content / plan-type result | Source behavior |
| --- | --- | --- |
| `private`, `municipal`, `federal`, `other` | No sections or selected checks; plan type `OUT_OF_SCOPE`; no specialized stage route | No Crown table request; explicit A2 rejected before extraction/refresh; cache ignored |
| Missing, blank, `unknown`, invalid, or mixed without the Crown component | No sections or selected checks; plan type `UNRESOLVED`; no specialized stage route | Confirm land/component scope before PLAR selection; explicit A2 rejected; cache ignored |
| `alberta_crown` | Provisional sections/checks permitted for valid core context; plan type remains candidate/review-only | AER routes to A2; Alberta routes to manual A1 |
| `mixed` with `review_scope: alberta_crown_component` | Same permitted candidate paths, limited to the declared Crown component | Regulator-specific source route applies only to that component |

The two jurisdiction modules were run from the repository root with bytecode
writing disabled:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=skills/crown-plan-agent/tests \
  python -m unittest test_jurisdiction_scope test_cli_jurisdiction_scope -v
```

Result: **15 tests run, OK, zero skipped**. These checks used generated PDFs,
invented scenarios and mocked source/refresh calls. No network, private project
inputs or fresh authority verification was used.

The earlier baseline inventory at `c0cf741` also ran `test_plan_type_review`,
`test_requirements_engine`, `test_table_a2_lookup`, `test_application_context`,
`test_source_review`, `test_regulatory_catalog`, `test_review_cli`,
`test_table_a2_refresh`, `test_official_pdf_cache` and `test_table_a2_rows` with
`CROWN_A2_TEST_PDF` unset: **95 tests run, OK, 2 skipped**. That historical result
is not a test count for the current development candidate; the skips were the
two optional local-official-PDF checks.

This inventory contains no private-plan excerpts, extracted project coordinates,
client scenarios or fresh authority claim. The implemented scope policy does not
establish regulatory authority or independent ownership verification.
