# Crown Plan Agent 0.4.0 — development preview

This is a development preview prepared for the public
[newfie-stack/survey-cad-skills repository](https://github.com/newfie-stack/survey-cad-skills)
at the owner's request. Production acceptance, regulatory certification and
completion of the master checklist are separate unfinished work.

## Changes

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
