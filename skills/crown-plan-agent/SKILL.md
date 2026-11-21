---
name: crown-plan-agent
description: Use when reviewing Alberta Crown/public-land survey or sketch plans, comparing original plan PDF revisions, checking disposition plan requirements, or assessing evidence-based CAD/GIS submission readiness.
version: 0.10.0
---
# Crown Plan Agent

## Scope and authority
Evaluate proposed Alberta Crown/public lands survey plans and sketches using **current authoritative public requirements**. The skill supports plan preparation, technical checking, and evidence-based review; it does not replace an Alberta Land Surveyor, regulator decision, title opinion, or approved submission.

**No private project plans, client drawings, employer templates, credentials, or project-specific configuration are permitted in this skill or its public test fixtures.** Source materials are cited by publication title, version, section, and official public URL; do not reproduce regulator PDFs wholesale.

Authorized real inputs, source images, extracted inventories and derived drawings stay in a separate private working directory outside the repository. Publish development results only within the user's authorization, using fictional company names and excluding the original plan, identifying case mapping and source reproductions.

## Read the complete titleblock first

On every reviewed plan sheet, read the entire titleblock from top to bottom,
including every entry in the Notes frame, following the
[complete-titleblock review](references/chatgpt-review.md#read-the-complete-titleblock-from-top-to-bottom).
Do this before preparing selected QC regions, asking for plan context or
declaring location, bearing basis or CRS information missing. Reuse the printed
information with its source location; identify unreadable or conflicting parts.
Printed spatial notes can establish the plan's stated location and basis, while
accepted control and reconstructed coordinates require their own evidence.

Next, inspect the main plan view, normally to the left of the titleblock, using
the [north, quarter-section and RP reading sequence](references/chatgpt-review.md#orient-the-main-plan-and-locate-reference-points).
Orient to the plan's north reference before identifying quarters. Look for
circled `RP` (Reference Point) markings on working-DWG layer `EVIDENCE` where
that convention and digital layer data are available. Keep the DIDS submission
target layer `35` distinct from this source layer. Retain the actual symbol,
label, source/target layer and tie evidence; these clues do not independently
accept survey control or establish a quarter corner.

## Finished-plan quality control

The primary goal is pre-submission checking of potentially finished plans for
omissions and mistakes, not redrafting or mandatory reconstruction. When the
reviewed Python runtime is available, use the [source-bound plan intake](references/plan-intake.md)
to map native text, directions and image regions, then use the review CLI's
`--finished-plan-contexts` option to prepare supported text, identity, scale and
arithmetic checks inside reviewed contexts. The existing `--finished-plan-spec`
pass remains available for directly prepared regions, as described in
[finished-plan QC](references/finished-plan-qc.md).
Read the actual authorized plan and its relevant page images before preparing
source-bound context selections. The agent prepares this private specification;
do not shift routine extraction/mapping work onto the draftsman. Do not invent
job expectations, context identities or visual completeness declarations.

Use observed literal labels to locate fields inside their own reviewed panel or
view; never locate a field by searching for the expected job value. Preserve
competing, blank or wrapped fields as unresolved source evidence. Preparation
expands native-text support only within the supplied context and never creates
or transfers a completeness declaration to a derived region. Report every
unresolved preparation request alongside the checks that actually executed.
Keep scanned, outlined, clipped and unsupported evidence on the visual-review
path, including when other parts of the same sheet have native text.

The selected-text pass reads supported rotated native text in its own direction,
retaining original page locations and source identity. Outlined lettering,
scans and unsupported text geometry still require visual review.
Nearby labels can face opposite directions, including readability flips near
north. Read each native baseline separately. PDF text direction, survey azimuth
and an office's text-facing convention are distinct; no unconfirmed angular
cutoff may be used to flag a drafting violation.

For a clearly identified, text-complete total field, flag conflicting stated
amounts without choosing an authoritative total. Numerically equivalent repeated
totals may agree; independent part rows must each remain in the sum. Preserve
the source locations and keep ambiguous, clipped or raster evidence unresolved.

This is bounded drawing QA, not a new jurisdictional compliance route. Its
PASS/FAIL results never promote the Crown ledger or establish current authority.
Graphical interpretation, unsupported/ambiguous extraction and broader plan
coverage require manual review. Use the scoped CLI pass when a finished-plan
review is requested and the authorized source, review basis, and runtime are
available. State which checks actually ran and which need manual review.

When reviewing any plan with visible page images, use
[visual review of plan symbols](references/chatgpt-review.md#visually-check-the-north-arrow-and-scale-bar)
to inspect the north arrow and graphical scale bar directly. Report the
observation and page location even when the offline CLI leaves visual checks
open. Obtain a readable page image or keep the visual result unresolved.

## First run and input contract
Use the established task and supplied authorized inputs. For an offline first run, execute `python tests/smoke_review.py` from the complete skill folder (or the repository-root path in the engine README). The invented example needs no regulator PDF; its missing-source notice is expected and is not a request to obtain a document for the example.

## Execute supported clause observations

Use the [clause evidence pass](references/clause-execution.md) when the reviewed
plan and applicable question support it. The agent prepares private source-bound
selectors from the actual PDF, then runs `--regulatory-evidence-spec` with the
explicit dated workbook and provenance-backed applicability facts. Do not ask the
draftsman to write selectors or supply a claimed result. This pass supports eleven
bounded question paths across nine numbered clauses; it does not complete those
clauses or the 144-clause review.

For hybrid plans, read the coordinate table's actual native fields and check its
numbering, two-decimal formatting, grouping and EC/XC/RC/OC tokens. Complete,
source-located table review is required. Two distinct OC records and inclusive
10 km proximity checks additionally require reviewed roles/provenance and a
verified common metric frame, including datum/epoch/axes/grid-ground basis.
Missing evidence, raster fields, ambiguous or inconsistent physical rows remain
unresolved. Never repair printed numbering by rearranging selected rows or pair
coordinates with another row's point ID. This is a diagnostic, not reconstruction.

When an authorized CAD/GIS point-export CSV is available, supply `--point-export`
and its source-hashed specification to compare the actual file with that table.
Preserve missing/extra/duplicate points, category/coordinate differences and
frame blockers. This export comparison does not inspect native DWG/SHP, verify
control, transform coordinates, or replace the Octopus workflow.

General clause observations cover numerical main-plan scale, the applicable
unsurveyed-territory note, and selected detail/reference or existing-plan-label
text comparisons. Execute only selected questions after workbook applicability
and override gates; retain every residual semantic, visual and record check.
Report executed, blocked and unrequested work separately. Actionable findings
enter the private PDF review-copy index when requested, with plan-page comments
only where actual plan evidence has one verified location. Reference-document
coordinates and ambiguous locations must never become guessed plan markers.

Consult the [November 21 source verification](references/regulatory-source-audit-2026-11-21.md):
the published Survey Manual v2.3 supersedes v2.2, Table A1 is June 2026,
Table A2 is October 2026, and the published MSP revisions took effect April 17,
2026. Edition verification does not establish application-specific authority.
Keep mechanical results separate from the unresolved regulatory verdict.

## Compare the plan with actual job records

Use the [job-record review](references/job-record-checks.md) to compare the plan
with authorized application, client-registry, approved-record and confirmed job
instructions. Read the actual records, identify which job and subject they cover,
and record their current or historical review basis. The agent prepares private
selectors and runs `--job-record-spec` with explicit `--job-record-file` inputs;
never invent an applicant, record version, source location or authority.

A company printed on the plan is an observation, not its own trusted reference.
Keep applicant, operator, landowner and surveyor roles separate. A name explicitly
confirmed by the user may be saved literally in private job instructions and used
for job QA; reuse an existing confirmation rather than asking again. It does not
replace the application form or client registry for their dated questions. When
records conflict, show each comparison and resolve the authoritative reference;
do not choose by familiarity, logo, majority or whichever value makes a pass.

Execute the three supported identity questions for plan-heading legal description
versus form and applicant versus form/registry only after workbook selection.
Disposition-number checks and confirmed job expectations remain job QA. Six new
bounded question paths, including the area/length paths below, bring the combined
supported dated observations to seventeen across fourteen partially observed
clauses. All complete clauses retain their residual manual obligations.

Use fixed printed balances for components/total, approved plus added minus deleted,
gross minus exclusions, width-group length totals, and plan amounts versus actual
records. Preserve the reviewed component identities, measurement scope, original
units and explicit tolerance. Compare individual category amounts as well as
grand totals where the records support it. A correct sum does not establish
correct categories, spatial nonoverlap, legal exclusions or boundary geometry.
Do not create an arithmetic expression or change values to force agreement.

Missing records and unselected fields use explicit unresolved entries; use a null
selector instead of inventing a page or rectangle. Scanned, outlined, clipped,
wrapped, split or ambiguous native fields remain unresolved. Preserve original
strings; no abbreviation, punctuation, suffix, compatibility-character or leading-
zero ID equivalence is inferred. Unconfirmed Unicode case equivalence stays open.
Never let unrelated field/unit selections hide a possible continuation of a name.
Distinct source-known typed labels and complete printed quantity/unit tokens can
separate supported dense rows. A supplied prefix must stop at its actual known
header's colon; it cannot consume a name or number. Unknown prefixes, repeated
or alias labels, same-line competing values and incomplete quantities stay open.
Typed unit headers must identify units, without erasing another field's data.

For a requested PDF review copy, include actionable finished-plan, dated-clause,
job-record and point-export findings in its complete index. Keep PASS results in
the detailed report, and keep multiple or unsupported locations unlocated in the
index. Verify every reference snapshot again after PDF generation before publishing
the private artifacts. Follow the [PDF review-copy guide](references/pdf-markup.md).

Before engine PDF operations, follow the dated [dependency and runtime policy](references/dependency-security.md), including its unresolved native-advisory record. Use a fresh environment with the hash-locked requirements and run `python engine/runtime_security.py` from the skill folder. This checks minimum runtime versions and provider identity before native PDF opening; it is not security clearance. If the check fails or the required runtime cannot be established, keep the engine unexecuted and use the evidence-limited assisted review available in the host. Do not bypass the runtime gate.

In ChatGPT, first check the capabilities actually available in the conversation.
If there is no Python or shell execution environment, use authorized attachment
or connected-file evidence for an assisted manual review and explicitly state
that the offline engine and reconstruction did not run. Leave checks requiring
unavailable execution, source evidence or Octopus unresolved; do not invent
outputs or replace Octopus with a new calculator. A complete control network
remains an acceptance gate for complete reconstruction, while the provider
contract permits independently reviewed partial diagnostics within their scope.

Follow the [ChatGPT review guide](references/chatgpt-review.md): reuse the user's
existing authorized files and confirmed context, ask one grouped question for
genuinely missing information, and lead with a short summary in normal language.
Separate what was checked, what needs attention, what remains unchecked and
specific next steps. Keep the detailed ledger and source citations available;
observed text and a matching source row do not establish compliance.

When a marked-up PDF is requested, follow the
[PDF review-copy guide](references/pdf-markup.md) and use the existing export
command with `--annotated-pdf`. It requires the actual source PDF, a Python
execution environment and PyMuPDF. Place notes only on source-bound evidence;
keep ambiguous or unlocated findings in the printable index. If the required
file or execution capability is unavailable, provide the review/comment list
and say that a PDF was not generated. Annotated copies reproduce the source
plan and must stay private even when the accompanying notes are anonymized.

For old-versus-revised PDFs, follow the
[revision comparison guide](references/revision-comparison.md). Reuse confirmed
context and explicitly identify the baseline original first and revised original
second. With both actual PDFs, Python and PyMuPDF available, run
`python engine/revision_cli.py` with the guide's arguments to create a private
Markdown comparison and JSON record. Both reviews are regenerated under the
same scenario, catalogue and supplied references; earlier reports and custom
popup comments are not replayed or interpreted. Recognized Crown Plan Agent
review copies are rejected: use the originals. Without the files or runtime,
provide an evidence-limited manual review and say the comparison engine and
exports did not run; never invent files or execution. Text changes and candidate
states never close comments or establish correction/compliance. Visual, geometry,
OCR and current-authority checks remain unresolved. Optional `--annotated-pdf`
produces the standard revised-plan review copy, not a visual change overlay.

A minimal invented in-scope scenario is:
```json
{"land_class":"alberta_crown","regulator":"AER","disposition":"LOC","stage":"initial","plan_type":"sketch","purpose":"Pipeline","subactivity":"Fresh Water"}
```
Declare `land_class` explicitly. `alberta_crown` enables provisional Crown review; `private`, `municipal`, `federal` and `other` are out of scope. Missing/unknown scope selects no Crown checks. For mixed land, use `land_class: "mixed"` plus `review_scope: "alberta_crown_component"` only when the reviewed Crown component is explicitly identified. A declaration does not prove ownership. Supported automated stages are `initial`, `amendment` and `renewal`; other stages remain unresolved.

## Mandatory workflow
1. **Classify jurisdiction and purpose.** Establish whether the land and activity fall under applicable Crown/public lands rules; identify regulator (AER or provincial authority), disposition/activity code, application/amendment/renewal/reclamation stage, legal land context and current governing publication. Do not assume a public land rule applies to private, municipal, federal, or other excluded land.
2. **Select plan type.** Distinguish sketch, surveyor's sketch, statutory survey plan, compiled plan, hybrid cadastre, amendment/as-built, and existing filed plan. Confirm whether an ALS signature/declaration is required; do not infer from document title alone.
3. **Resolve requirement hierarchy.** Build an applicability matrix from current legislation, regulation/PLAR tables, current regulator manuals, general plan-content requirements, plan-type requirements, and activity-specific requirements. A requirement from one class must not silently apply to all classes. Record source version/date and effective date; superseded versions are historical context, not current rules. For an explicitly selected dated-source question workbook, follow the [clause workbook guide](references/clause-workbook.md); preserve missing-fact and override blockers.
4. **Inventory evidence.** Identify available plan PDF, CAD/DXF, GIS dataset, application details, cadastral/ATS control, title/interest evidence, geometry and notes. Keep each evidence item tagged by origin and permission class. Never use a private example as a source of normative requirements.
5. **Validate deterministically where possible.** Check file integrity, page layout, text/scale, title/legend, legal description, bearings/distances, monuments, dimensions, areas, access, watercourses, existing interests, CRS and geometry/topology, using the applicable requirement matrix. When survey coordinates are missing, read the [geometry handoff contract](references/geometry-handoff.md) and [required Octopus code provider](references/octopus-reconstruction.md). Reconstruction must execute reviewed Octopus code: its pure geometry module for reviewed partial/sketch diagnostics, or its full supplied-observation adapter when the source and construction satisfy that contract. If unavailable, report the provider blocker; do not write a parallel COGO calculator. Use the evidence-interpretation and CAD companions around that provider; add `shapefile-validator` when GIS is requested. Return source/feature and observation registers, the complete control network, provider execution evidence, reviewed CAD/preview, unresolved items and accepted coordinate JSON when supported. Preserve unknown roles/control/CRS; a proposal is not executed reconstruction. Compare plan, CAD, shapefile and application consistently; do not alter legal geometry to make a check pass.
6. **Classify results.** For each applicable requirement, return PASS, FAIL, REVIEW_REQUIRED or NOT_APPLICABLE; distinguish missing source/ambiguous applicability from actual noncompliance. Include evidence, section citation, version, and precise corrective action.
7. **Prepare deliverable-readiness report.** Provide an unresolved-item list and required human decisions. Never submit to external portals or assert regulator acceptance without explicit authorization and independent evidence.

## Mandatory source and evidence gates
- **Current-source gate:** Resolve jurisdiction before selecting sources. Before making a normative PASS/FAIL finding, verify the applicable PLAR table (A2 for AER; provincial A1 where applicable), exact purpose/activity entry, regulator notices/bulletins, plan-content publication and any supersession. If these cannot be independently confirmed, set `REVIEW_REQUIRED` for the affected regulatory requirement; never assume that a disposition code universally requires a particular plan type.
- **Two distinct statuses:** `source_status` describes whether a requirement is verified from an authoritative current source; `evidence_status` describes whether the submitted plan actually satisfies it. A successfully identified requirement is not a plan PASS.
- **Missing artifact gate:** Without the plan PDF or equivalent evidence, all visual plan-content checks remain `REVIEW_REQUIRED`. Without CAD/GIS artifacts, no geometry/schema check may be claimed as executed.
- **Synthetic test gate:** Explicitly separate fixture expectations and executed mechanical checks from live regulatory compliance verification. A synthetic fixture must never be mistaken for a real approved plan.

## Output contract
The offline CLI generates a Markdown evidence review. Use the fields below when an agent or integration prepares a structured requirements ledger. Leave unsupported or unverified fields unresolved.

Produce a machine-readable requirements ledger with fields:
`requirement_id, authority, publication_title, version_date, section, regulator, land_class, review_scope, scope_status, activity, stage, plan_type, applicability, requirement_summary, check_method, input_evidence, observed_value, expected_value, source_status, evidence_status, status, severity, correction, verified_at`.

Separate **normative requirement**, **implementation recommendation**, and **unverified interpretation**. Never convert a quoted historical manual into a present-day mandatory rule without checking its current authority.

## Sources and implementation
Read [source hierarchy](references/source-hierarchy.md), [plan and activity decision matrix](references/plan-type-decision-matrix.md), [evidence-based validation](references/validation-and-evidence.md), and [publication and privacy controls](references/privacy-and-testing.md).

For setup, run the [offline synthetic example](engine/README.md#install-and-run-the-example). For a local AER disposition review, use the [offline review command](engine/README.md#offline-pdf-to-review-command). Use the Table A2 PDF already supplied for the review. When no copy is available, ask the user to download and provide the current PDF. Keep the Table A2 row check separate from the drawing-text check. Use the expected disposition code for drawing-text presence and record the PDF page or DWG text export line. A text mention still requires context review. Select the Table A2 row from explicitly supplied purpose and activity for a new application or a renewal comparison against the active plan on file.

Read the [clause coverage inventory guidance](references/requirement-coverage.md) when assessing catalogue completeness. Inventory membership is not an implemented check or verified applicability. The companion `aer-onestop-guide` may provide procedural guidance; this skill governs requirement applicability and authority. Read each requested reconstruction/CAD/GIS skill's instructions before executing it; if unavailable, record the missing capability rather than claim a handoff ran.

Consult the [official-source verification record](SOURCE_VERIFICATION.md) and
[development preview release notes](RELEASE_NOTES.md) for observed editions,
unresolved authority, supported behavior and distribution limits.

**Release status:** DEVELOPMENT PREVIEW. The offline review engine is available for assisted reviews; verify current sources and review all findings independently. Reconstruction requires separately authorized access to the external Octopus checkout; it is not bundled. See the [publication scope](PUBLICATION_REVIEW.md) and [master checklist](MASTER_CHECKLIST.md) for licensing, installation and acceptance limits.
