# Crown Plan Agent 0.10.0 — development preview

This is a development preview prepared for the public
[newfie-stack/survey-cad-skills repository](https://github.com/newfie-stack/survey-cad-skills)
at the owner's request. Production acceptance, regulatory certification and
completion of the master checklist are separate unfinished work.

## Changes

- Compare the actual plan applicant and heading legal description with supplied
  application/registry records; compare disposition IDs and confirmed job
  instructions separately as job QA. Preserve missing or conflicting references.
- Read source-hashed original PDF fields and actual JSON job instructions with
  reviewed subject, semantic role and current/historical basis. No company name
  is guessed from a logo or treated as its own trusted reference.
- Execute fixed printed sums, amendment additions/deletions, gross/net exclusions,
  width-group lengths and plan-versus-record amounts using original unit evidence
  and exact Decimal tolerances. Compare categories as well as grand totals.
- Add six bounded dated question paths across five additional clauses. The
  combined executors support seventeen paths across fourteen partially observed
  clauses; all 144 manual paths and residual obligations remain available.
- Include actionable finished-plan, clause, job-record and point-export findings
  in the PDF review-copy index, with comments only at uniquely verified plan
  spans. Reference-document coordinates never become guessed plan markers.
- Recheck reference snapshots after PDF generation before publishing artifacts.
  Preserve wrapped, raster, clipped, unselected and ambiguous evidence as open.
- Preserve regression tests for hidden name continuations, wrong record roles/
  jobs, category reallocations, unchanged totals, repeated evidence, unit/scope
  conflicts and source changes. Dependencies and plugin presentation are unchanged.

See [job-record checks](references/job-record-checks.md),
[review-copy exports](references/pdf-markup.md) and
[review readiness](references/review-readiness.md).

Validation: 1,071 tests ran, with 1,069 passes, two optional skips and no failures.
The preserved six-job invented trial found four planted issues: one by executed
comparison and three by assisted reading. Two subsequent holdouts exercised ten
passing area comparisons but still required assisted identity review. These are
small synthetic trials, not an estimate of real-plan accuracy; see the
[frozen results and limitations](references/job-records-forward-trial-2026-11-21.md).

## Version 0.9.0 changes retained

- Execute eleven bounded workbook observations across nine numbered clauses,
  preserving every applicability/override blocker and residual manual obligation.
- Read actual source-hashed PDF coordinate-table fields for hybrid point
  numbering, printed precision/grouping, categories, two distinct OCs and inclusive
  10 km proximity. Derive physical row order and reject cross-row field mixing.
- Compare actual supplied CAD/GIS CSV point exports with the PDF table, retaining
  missing/extra/duplicate points, category/coordinate differences and frame blockers.
  No reconstruction, coordinate transformation or native DWG/SHP parser is added.
- Connect selected numerical-scale, territory-note and detail-label comparisons
  to their dated workbook questions. Keep mechanical results separate from the
  unresolved regulatory verdict, and show executed/blocked/unrequested work.
- Verify official linked editions and supersession: Survey Manual v2.3,
  June 2026 Table A1, October 2026 Table A2 and effective April 2026 MSP. Reinspect
  selected May2024 content clauses and preserve format-specific digital scopes.
- Add actual-PDF/CSV regressions and reproducible invented combined cases.
  No work documents, source PDFs, new dependencies or runtime downloads are added.

See the [clause evidence guide](references/clause-execution.md) and
[source audit](references/regulatory-source-audit-2026-11-21.md).

## Version 0.8.0 changes retained

- Add a source-bound whole-sheet intake map with page geometry, native line
  directions/locators, candidate labels, image regions and visual followups.
- Prepare supported mechanical checks inside explicitly reviewed contexts using
  literal observed labels and bounded native-text overlap closure. Keep every
  ambiguous, wrapped, clipped or unsupported request visible; derived rectangles
  never inherit a completeness declaration.
- Add `--finished-plan-contexts` to the existing review command, with preparation
  counts and followups alongside the checks that actually execute. Direct
  `--finished-plan-spec` reviews retain their supported workflow.
- Read properly grouped printed amounts and one terminal unit period with exact
  decimal arithmetic. Keep malformed grouping, wrong units and competing values
  unresolved. Support explicit `m^2` alongside `m2`/`m²`.
- Validate complete scale-denominator candidates so malformed numeric suffixes
  cannot be accepted as shorter ratios. Preserve independent/opposed native
  directions without imposing an unconfirmed text-facing cutoff near north.
- Reuse the reviewed runtime and dependency locks. No OCR, automatic semantic
  role acceptance, current-authority clearance or professional acceptance is
  added by intake or these printed-format changes.
- Preserve a frozen four-plan forward trial and known-case preparation probe.
  The forward trial found four planted issues through assisted reading, with no
  false alarms; 56 of 93 requests prepared/executed without context retries,
  while 37 preparation requests and two executed comparisons remained unresolved.
  See the [dated results](references/intake-forward-trial-2026-11-21.md); these
  counts are not an unattended coverage or regulatory-acceptance claim.

Version 0.7.9 changes retained:

- Preserve a conflicted disposition alias as unresolved in the dated workbook
  so report generation can retain the invalid-context gate without crashing.
  Renderer validation and current-authority safeguards remain unchanged.
- Add a wholly invented area-category regression and clean control. The shifted
  example retains a correct grand total while its new/existing breakdown fails
  the selected comparisons. One planted issue remains separate from two failed
  comparisons; automatic category discovery is not added.
- Add 45 invented applicability scenarios across 15 families, targeting 26 dated
  clauses and 52 named manual checks, plus cross-layer review regressions for
  selective exceptions, application facts and source/evidence separation.
- Include the reproducible unfamiliar-layout fixtures from the previously
  documented assisted trial. No new model training or assisted accuracy claim
  follows from packaging those source generators.
- Reuse existing public inputs separately as unknown-context controls; no real
  plan content is included in fixtures or the installed package. Source and
  ChatGPT releases retain the same prompts, presentation and evidence gates.

Version 0.7.8 changes retained:

- Flag conflicting amounts in an explicitly labelled, text-complete total field
  without selecting one as authoritative. Accept numerically equivalent repeats
  while retaining every independent part row in the arithmetic.
- Expand the synthetic drawing benchmark with landscape LOC and portrait MSL
  layouts, native rotated identifiers, current-versus-historical revisions,
  title/identifier/scale errors, arithmetic errors, rounding controls and mixed
  raster/native text. Keep the original cohort visible separately.
- Gate individual supported detections and clean controls, record false
  clearances, and separate regression success from detecting every planted
  defect. Unknown text completeness and graphical omissions retain their limits.
- Add a synthetic assisted-review exercise exporter. Reviewer inputs contain
  only an invented PDF and job instructions, without preselected check regions
  or an answer key. An assisted trial is separate from the deterministic score.

Version 0.7.7 changes retained:

- Replace the broad PDF dependency range with the official minimal
  `pymupdf-lite==2.1` runtime, pinned to reviewed wheel hashes. Use a fresh
  environment, binary wheels and the canonical `pymupdf` import.
- Check dated Python patch floors, a single supported PDF provider, binding
  identity and native MuPDF minimum version before engine PDF opening. Keep
  failed runtime checks explicit rather than falling back to an older provider.
- Add weekly package and audit-tool dependency scans, Dependabot updates and
  immutable CI action revisions. Updates require review; no automatic merging
  is enabled.
- Record the remaining native MuPDF signing double-free advisory in the
  [dependency policy](references/dependency-security.md). Version checks and
  zero mapped scanner findings do not establish that this advisory is fixed or
  that all supported operations are unaffected. Runtime hardening adds no
  regulatory certification or production acceptance.

Security documentation follow-up, November 19, 2026: identify the additional
Expat findings and all eight OpenSSL records, distinguish interpreter/provider
updates from pip updates, and document maintained PDF-reader options. Retain
normal published-package updates and synthetic compatibility tests. No package
pin, engine behavior or native-advisory clearance changes in this follow-up;
custom native builds and vulnerability-specific tests are not required for
using the preview.

Version 0.7.6 changes retained:

- Read supported rotated native text in its own direction for selected phrase,
  identity, scale and arithmetic checks. Use recovered native span geometry for
  oblique reading and keep different or opposite directions separate.
- Preserve source PDFs, hashes and unrotated region coordinates. Retain native
  directions and available quadrilaterals with the original evidence locations;
  text rotation does not establish survey orientation or control.
- Keep raster/outlined lettering, unsupported text geometry, clipping and
  ambiguous comparisons unresolved. Absence still needs the existing explicit
  visual-to-text completeness evidence; no OCR or regulatory approval is added.

Version 0.7.5 changes retained:

- Include executed finished-plan drawing QC in the opening review summary, even
  when no Crown requirements can be selected. Report bounded check counts and
  unresolved follow-up without turning drawing-QC results into regulatory approval.

Version 0.7.4 changes retained:

- Correct the RP layer distinction: inspect `EVIDENCE` in working DWGs and keep
  `35` as the RP target for DIDS submission in the supplied workflow. Record
  source and target separately; identify RP entities before any submission
  mapping and retain the working drawing.

Version 0.7.3 changes retained, with the layer correction above:

- After titleblock intake, orient the main plan to its north reference, identify
  supported section/quarter context and look for circled Reference Point (`RP`)
  markings. Retain actual source layer, label and tie evidence. Distinguish north-up
  survey azimuths from original page/CAD axes and keep control acceptance separate.

Version 0.7.2 changes retained:

- Read the complete titleblock from top to bottom on each reviewed sheet,
  including every Notes entry, before selecting QC regions or asking for
  location/spatial context. Reuse printed location and basis information with
  source locators, and identify conflicting or unread portions. Keep observed
  notes separate from accepted survey control and reconstructed coordinates.

Version 0.7.1 changes retained:

- In a plan review with page images, inspect the north arrow and graphical scale
  bar visually, identify their sheet and view, and record unreadable or incomplete
  coverage. The existing offline text checker continues to request visual review
  for those symbols.

Version 0.7.0 changes retained:

- Add opt-in [finished-plan drawing QC](references/finished-plan-qc.md) for expected text,
  field consistency, main-plan scale labels and area-table arithmetic. Findings cite the
  selected page regions and retain unresolved evidence for manual review.
- Keep the Crown regulatory findings separate from drawing QC. The synthetic benchmark
  runs through the review CLI and counts known defects left unresolved as misses.

Version 0.6.1 changes retained:

- Refresh the bounded official-source audit dated November 18, 2026, with
  corrected routes, explicit A1/professional dependencies, distinct publication
  and effective dates, PCS access guidance and unresolved current-law questions.
- Keep listing/metadata checks separate from current clause/applicability
  verification. No source is automatically promoted to `VERIFIED_CURRENT`, and
  no reference PDF, project plan or new download feature is included.

Version 0.6.0 changes retained:

- Add an offline comparison of explicitly ordered original PDFs, regenerating
  both evidence reviews under one shared scenario, catalogue and reference basis.
- Link checklist observations by requirement ID and report literal extracted-text
  additions, removals and count changes, preserving repeated occurrences and
  visible ambiguity. Normalize whitespace only; span fragmentation can produce
  inventory differences. No fuzzy matching, OCR, visual or geometry comparison.
- Write private Markdown and JSON comparison records with source/basis hashes
  and common review context. All regulatory results remain `REVIEW_REQUIRED`;
  observation changes never automatically fix, close or approve comments.
- Reject recognized Crown Plan Agent review copies and require the originals.
  Earlier reports, source annotations and custom popup comments are not replayed
  or interpreted as review decisions. Optional PDF output is the standard revised
  review copy, not a visual change overlay.
- Document the real-file/Python execution gate and evidence-limited manual
  fallback. No automatic source downloads, external provider or new server is
  needed. See the [revision comparison guide](references/revision-comparison.md).

Version 0.5.0 changes retained:

- Add an optional private marked-up PDF with numbered evidence-region comments
  and a complete printable notes index. Preserve original pages and annotations.
- Bind source snapshots, inventories and reports by SHA-256, retaining raw
  table-cell text for reliable locations. Unreliable locations stay unlocated.
- Prepare review artifacts before exclusive publication, reject collisions and
  unsafe output locations, and clean up owned outputs after ordinary failures.
- Keep the default Markdown-only workflow and the existing review/source gates.

Version 0.4.0 changes retained:

- Lead evidence reports with a plain-language summary and specific missing-input
  questions, while retaining detailed checks and source gates below it.
- Keep the same runtime-aware skill instructions in GitHub and ChatGPT, with
  grouped intake questions and explicit manual/executed-operation distinctions.
- Render extracted annotations as literal text and reject conflicting duplicate
  JSON declarations instead of silently accepting the last value.
- Build the ChatGPT archive from reviewed source, presentation metadata and
  existing light/dark icons. External Octopus code remains separately required.

Version 0.3.1 changes retained:

- Require actual reviewed [Octopus code](references/octopus-reconstruction.md)
  for reconstruction: its geometry module for bounded partial/sketch diagnostics,
  or its supplied-observation adapter for supported registered constructions.
  Record execution provenance; do not substitute parallel COGO calculations.
  The Crown CLI still prepares a handoff without invoking the provider.

Version 0.3.0 changes retained:

- Add an explicitly selected [dated-source clause workbook](references/clause-workbook.md)
  for all 144 numbered clauses of the May 2024 content manual: 323 manual
  review checks containing 326 prompts, with 105 typed applicability facts.
- Preserve missing, unknown, invalid and unsupported-provenance facts as
  unresolved. Separate required checks, optional guidance, permissions and
  exemptions; apply four source-backed exclusion/replacement controllers.
- Add opt-in local catalogue, fact and coverage-inventory inputs to the CLI
  and Python pipeline. Validate them before source inspection or an explicitly
  requested refresh; keep the default observation review unchanged.
- Keep manual questions separate from declared observation references. The
  workbook does not run adapters, inspect drawings or certify compliance.
- Match clause-path coverage only against an explicitly supplied source
  inventory; atomic-obligation completeness remains unassessed.

Earlier candidate changes retained:

- Require declared Alberta Crown scope before selecting Crown checks or A2
  sources. Mixed land is limited to the declared Crown component.
- Prepare an explicitly unexecuted handoff to existing evidence interpretation,
  reconstruction and CAD skills; request GIS validation only when specified.
- Withhold partial measurements for declared curves, holes or multipart
  geometry. Reject malformed coordinate and Table A2 row data.
- Preserve inclusive area/traverse tolerances, conflicting-area ambiguity,
  PDF provenance, rotated/clipped text and distinct plan-heading candidates.
- Extend general content review to supported hybrid/compiled variants, with
  their separate title and compiled-declaration review paths.
- Keep compiled amendment proposals in variant review under the dated
  exemption, preserving the plan-of-record gate.
- Inventory dated manual clauses and expose remaining gaps. Citation links,
  manual review paths and executed numerical checks are different measures.

## Compatibility and verification

Older scenarios without `land_class` remain readable but do not select Crown
checks. Use the [input contract](SKILL.md#first-run-and-input-contract) and
[geometry contract](references/geometry-handoff.md). Programmatic Table A2 rows
must meet the supported row schema; validation does not establish their origin
or current authority.

Exact code/test fingerprints, executed test counts, clean-copy evidence and
independent review are recorded in [TECHNICAL_REVIEW.md](TECHNICAL_REVIEW.md).
Installation instructions are in the [engine README](engine/README.md).

## Distribution boundary

Only general-purpose source, original summaries and invented fixtures belong in
the package. Original real plans, images, inventories, accepted coordinates,
application identifiers and case mappings remain outside GitHub. Authorized
case summaries use fictional company names.

Original repository contributions are covered by the existing
[MIT license](https://github.com/newfie-stack/survey-cad-skills/blob/main/LICENSE).
That license does not relicense external dependencies or source publications.
PyMuPDF is an external dependency; the inspected 1.26.6 package metadata and the
[publisher's licensing documentation](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright)
identify AGPL and commercial licensing options. Dependency installation does not
resolve the appropriate licensing basis or redistribution obligations for a
release. The source package does not bundle PyMuPDF binaries.

Octopus is a separate external implementation requiring authorized access to a
reviewed checkout. Its code, dependencies and license are not included or
relicensed by this preview. The offline PDF review and synthetic example can run
without it; reconstruction reports a provider blocker when it is unavailable.

The owner authorized publication of this development preview to the existing
public repository; see [publication scope](PUBLICATION_REVIEW.md). Current-source
verification, requirements outside the dated manual, accepted real-plan geometry,
qualified survey/regulatory sign-off and native session discovery remain open in
the [master checklist](MASTER_CHECKLIST.md). Dependency and future distribution
obligations still require the appropriate licensing basis.
