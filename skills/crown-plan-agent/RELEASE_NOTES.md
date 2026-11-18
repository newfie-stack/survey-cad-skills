# Crown Plan Agent 0.7.2 — development preview

This is a development preview prepared for the public
[newfie-stack/survey-cad-skills repository](https://github.com/newfie-stack/survey-cad-skills)
at the owner's request. Production acceptance, regulatory certification and
completion of the master checklist are separate unfinished work.

## Changes

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
