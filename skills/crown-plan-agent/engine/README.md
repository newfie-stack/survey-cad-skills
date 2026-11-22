# Crown Plan Agent offline engine — development

This module implements **candidate applicability**, source version safeguards, and structured evidence gating. It is not a regulator-approved compliance engine.

Version 0.3 adds an explicitly selected [dated-source clause workbook](../references/clause-workbook.md). The existing observation report remains available without enabling that workbook.

Version 0.4 starts the report with a plain-language summary and specific next
steps. It distinguishes reviewed text, unresolved application facts, uncomputed
geometry and unexecuted reconstruction; the detailed evidence remains below it.
Read the [ChatGPT review guide](../references/chatgpt-review.md) for assisted
reviews when a host cannot execute Python or access Octopus.

Version 0.5 adds an optional private [marked-up PDF](../references/pdf-markup.md):
add `--annotated-pdf /path/to/private-job/review-copy.pdf` to the existing command.
It places review comments on verified source-text locations and appends a
printable index for all notes, including unlocated findings. Source hashes bind
the original, inventory and report. This is a derived review copy, not a corrected
or approved survey plan, and it must remain outside GitHub.

Version 0.6 adds an offline [revision comparison](../references/revision-comparison.md)
of two original PDFs under one shared review basis, with Markdown and JSON
outputs. Literal text changes and candidate observation states remain
`REVIEW_REQUIRED`; they do not close comments or establish correction.

## Install and run the example

Use a patched Python runtime, preferably **Python 3.12.16 or a newer 3.12 patch**, and read the [dated dependency policy](../references/dependency-security.md), including the open native advisory. Its supported-branch patch floors are enforced before engine PDF opening; satisfying them is not a security certificate. For Codex, copy the entire `crown-plan-agent` folder into your project's `.agents/skills/` directory or your user's `~/.agents/skills/` directory, then start a new session and invoke `$crown-plan-agent`. Keep `engine`, `references`, and `tests` beside `SKILL.md`.

In a Codex Cloud task, select the branch containing the skill and copy the complete skill folder into `.agents/skills/crown-plan-agent` before starting a new session. This public repository does not supply that discovery link automatically. Where the host supports it, invoke `$crown-plan-agent Run the offline synthetic example.` Automatic discovery in a fresh host session remains unverified. You can also ask the agent to read `skills/crown-plan-agent/SKILL.md` explicitly and run the repository-root commands below. PDF operations require the separately installed reviewed runtime; the default is the official minimal PyMuPDF Lite distribution.

From the repository root, create a new empty virtual environment using the patched interpreter. Choose another environment path if `.venv` already exists; do not repair a mixed-provider installation in place.

```bash
python3.12 -m venv .venv
# Bash or zsh
source .venv/bin/activate
# In Windows PowerShell, use .\.venv\Scripts\Activate.ps1 instead.
python -m pip install --require-hashes -r .github/bootstrap-pip.txt
python -m pip install --require-hashes -r skills/crown-plan-agent/requirements.txt
python skills/crown-plan-agent/engine/runtime_security.py
python skills/crown-plan-agent/tests/smoke_review.py
```

`runtime_security.py` reports the actual interpreter, provider and native MuPDF versions without opening a PDF. The engine calls the same gate before native PDF operations. Its minimum-version result leaves advisory review required; see the [unresolved native advisory](../references/dependency-security.md#remaining-native-advisory).

The offline review engine and invented example do not require Octopus. Reconstruction requires a separately authorized, reviewed Octopus checkout following the [provider contract](../references/octopus-reconstruction.md); its implementation is not distributed here. When it is unavailable, the agent must record the missing-provider blocker. The offline CLI only prepares an unexecuted handoff; it does not discover or invoke Octopus.

For a standalone command-line check, open a terminal in the copied `crown-plan-agent` folder and run:

```bash
python3.12 -m venv .venv
# Bash or zsh
source .venv/bin/activate
# In Windows PowerShell, use .\.venv\Scripts\Activate.ps1 instead.
python -m pip install --require-hashes -r requirements.txt
python engine/runtime_security.py
python tests/smoke_review.py
python -m unittest discover -s tests -p 'test_*.py' -v
```

The example prints a report for an invented plan. It uses neither a network connection nor a regulator PDF and should end with `Offline synthetic review passed.` The request for a local Table A2 PDF is expected in the example. For real reviews, keep project inputs and reports outside both the repository and the installed skill folder.

The [master checklist](../MASTER_CHECKLIST.md) records what is implemented, the evidence available, and the open acceptance criteria. A successful smoke run verifies the offline example, not all ten project milestones.

For fresh-layout testing and the separate assisted model-review procedure, see
the [unfamiliar-layout trial](../references/unfamiliar-layout-trial.md). Its former
holdout drawings are now reproducible regression fixtures. Passing the ordinary
tests does not run a new model evaluation or train the agent.

For maintainers, the
[ChatGPT packaging source](https://github.com/newfie-stack/survey-cad-skills/tree/main/skills/crown-plan-agent/packaging/chatgpt)
and
[archive builder](https://github.com/newfie-stack/survey-cad-skills/blob/main/skills/crown-plan-agent/tools/build_chatgpt_plugin.py)
produce the same canonical skill for ChatGPT. Packaging is separate from running
a review, and no execution server or external provider is installed by an archive.

`source_catalog.json` is a **versioned source inventory** grounded in public documents. It records the October 28, 2026 Table A2 revision. Current authority and applicability still require separate verification before any normative PASS/FAIL finding.

`inspect_text` is only a text-candidate locator; it does not inspect graphical objects, distinguish all annotation roles, or prove that a required drawing element exists. The PDF adapter preserves page coordinates and source provenance; use visual review when text extraction is insufficient.

No private project data, source plans, employer documents, or derived real-plan fixtures are stored here.

## PDF text-position adapter

PDF inspection requires the reviewed PyMuPDF runtime and a successful minimum-version/provider check. The default lock installs official `pymupdf-lite`; do not install it beside the full `PyMuPDF` distribution. Call `extract_pdf(path)` from `engine/pdf_inspector.py` to inventory text spans, page numbers, and PDF-point bounding boxes. The adapter is read-only, bounded by page/span limits, rejects encrypted PDFs, and does not overwrite output inventories. It does **not** extract graphical symbols, establish line-to-label associations, or certify geometry or legal compliance. Run only with authorized files in a private environment; never commit inventories of client plans.

Synthetic bounding-box and full PDF extraction tests are in `tests/test_pdf_inspector.py` and `tests/test_pdf_integration.py`.

The PDF adapter now inventories straight PDF vector strokes as `UNCLASSIFIED_GRAPHIC` with page-point endpoints. These are drawing-page coordinates only, **not surveyed positions**. Curves, symbols, hatches, text-to-line associations, and feature identity remain unresolved; never use these strokes directly to derive legal areas or boundaries.

## Candidate label associations

`associations.py` ranks nearby text spans and PDF vector strokes on the same page using shortest page-point distance. It returns only `REVIEW_REQUIRED` candidates, never authoritative identities. The default radius (18 PDF points) is an illustrative review threshold, not a survey tolerance. Labels in tables, rotated annotations, dimension chains, curves, leaders and crossing linework may be incorrectly associated by proximity. No feature is promoted without independent geometry/evidence checks and reviewer confirmation.

## Multi-signal review candidates

`feature_candidates.py` combines generic text-pattern hints (R/W, C/L, tie line, road/access) with same-page vector proximity. Multiple similarly close lines are flagged as ambiguous. **These are review hints, not feature classifications**: table labels, leaders, rotated text, scale details and overlapping features remain possible confounders. No automatic compliance PASS or legal boundary identity is emitted.

## Possible leader segments

`leaders.py` produces candidate associations where a PDF straight-line endpoint is near a text span and the segment length is within configurable page-point limits. These are **not confirmed CAD leader objects**: dimension extensions, table rules, centreline segments and other graphics can satisfy the heuristic. Output always remains `REVIEW_REQUIRED`. No private drawings or their extracted coordinates are stored in the repository.

## Leader candidate review ranking

`leader_review.py` adds oblique/orthogonal stroke and callout/layout-text signals to prioritize possible leader candidates. `ELEVATED` and `LOW` are **review priorities only**, not confidence probabilities or verified feature identities. Orthogonal dimension extensions, leader arrowheads, tables and boundaries can still be confused; all results remain `REVIEW_REQUIRED`.

## Orientation-aware annotation candidates

`orientation.py` compares PDF text-baseline direction to nearby straight vector strokes, treating parallel and antiparallel orientations as equivalent. This changes review ordering only; it cannot distinguish a labelled right-of-way edge from a parallel table rule, dimension extension, or nearby unrelated boundary. Missing direction remains unknown and all candidate associations remain `REVIEW_REQUIRED`.

## Resource bounds and review limitations

PDF extraction enforces positive integer limits for page count, text spans, vector segments, Bézier curves and input file size (default 100 MB). The span/curve/vector caps apply independently; the curve cap is cumulative across pages. These limits mitigate accidental resource exhaustion but are not a sandbox for hostile PDFs. Use an isolated environment with memory/time limits, maintain the runtime and review the [dependency policy's open advisories](../references/dependency-security.md). The minimum-version gate does not establish that native parser vulnerabilities are absent. Neither visual extraction nor line association establishes Crown plan compliance.

## Offline PDF-to-review command

The review command extracts PDF text and positions. It skips vector inventory because the report's geometry checks use separately supplied survey coordinates. The full PDF inventory adapter still supports bounded vector extraction.

Text positions use unrotated, crop-relative page points, including on rotated sheets. A partially visible text box is clipped to the page bounds; the inventory retains its extracted box as `original_bbox_points`. Clipped or incomplete text still needs visual review.

Run only on an authorized local PDF, using a private working directory. Create a local `scenario.json` file containing the review context:

```json
{
  "land_class": "alberta_crown",
  "regulator": "AER",
  "disposition": "PLA",
  "stage": "initial",
  "plan_type": "sketch"
}
```

From the skill folder:

```bash
python engine/review_cli.py /private/path/plan.pdf \
  --scenario /private/path/scenario.json \
  --table-a2-pdf /private/path/plar-table-a2.pdf \
  --output /private/path/review.md
```

The command reports Table A2 matching row numbers and drawing-text evidence separately. It checks PDF text by default. For a DWG, export its annotation text locally as UTF-8, with one annotation per line, and add `--drawing-text /private/path/drawing.txt`. The drawing check uses the supplied code and reports where it was observed. Confirm context visually, including text in tables, legends and neighbouring dispositions. Scanned or outlined labels can require manual inspection. A text export covers only the annotations it contains.

Candidate checklist selection requires an explicit supported land scope, `regulator` (`AER` or `Alberta`), `stage` (`initial`, `amendment` or `renewal`), `plan_type` (`sketch`, `surveyor_sketch`, `survey_plan`, `hybrid_plan` or `compiled_plan`), and a three-letter `disposition` (or legacy `activity` alias). Use `land_class: "alberta_crown"` for a declared Alberta Crown review. For mixed land, `land_class: "mixed"` also requires `review_scope: "alberta_crown_component"`; the declaration does not establish whole-plan ownership. `private`, `municipal`, `federal` and `other` are `OUT_OF_SCOPE`; missing, unknown or invalid scope selects no Crown checks. A disposition code cannot replace land-scope evidence. Custom catalogue wildcards cannot bypass these context gates.

Version 0.2 requires this explicit scope declaration: older four-field scenarios remain readable but produce an unresolved review until scope is supplied. A2 inputs/cache/refresh require both in-scope context and AER; provincial reviews keep Table A1 manual review separate.

The Table A2 parser supports the October 28, 2026 revision and rejects unsupported layouts. For a new AER application, add an explicit `purpose` and `subactivity` to look up the exact Table A2 row and required plan type. For a row with a blank activity, supply an empty `subactivity` string. The legacy scenario field `activity` remains an alias for the disposition code. The command runs offline by default and requests a user-provided PDF if neither an explicit PDF nor a cached copy is available. `--refresh-table-a2` and `--table-a2-url` opt in to network access. Table A2 revision and regulatory currency are tracked separately.

The command uses `candidate_requirements.json` unless `--catalogue` is specified. It creates a new Markdown evidence review marked `REVIEW_REQUIRED`. Keep input files, reports and extracted evidence private. To verify the parser and the review workflow against a locally supplied October 2026 PDF, set `CROWN_A2_TEST_PDF` to its absolute path before running the test suite.

Scenario and survey-geometry inputs must be JSON objects with unique keys and
finite values. The CLI uses the same bounded reader as clause inputs (at most
2 MiB, with bounded nesting and text). Conflicting duplicate declarations produce
a concise input error before any requested source refresh or report creation.

The ledger's `review_summary` contains the short result, completed/unchecked
operations, targeted `input_requests`, one grouped `context_question` and
`next_steps`. These expose missing information without changing candidate
eligibility or regulatory status. For example, a missing subactivity remains
unknown while an explicitly blank string can match a genuinely blank source row.
The Markdown report places this summary before the full evidence.

The programmatic ledger includes every field declared in `SKILL.md`. Unsupported authority, expected-value, severity and verification-time values remain unresolved (`null`); extraction time is not source verification. Known PDF filename/page/bounding-box provenance is retained. The filename is not an immutable input hash, so a private validation record should separately identify the exact input snapshot.

An exact Table A2 row adds a comparison with the supplied `plan_type`, plus the row's monument, consultation and additional RTF options. The report preserves the consultation qualifiers for review. A plan of survey provided in place of a sketch or surveyor sketch requires review of the substitution and monument requirements in PDF page 18. The comparison does not determine exceptions, consultation completion or application eligibility.

For an AER amendment, supply `existing_plan_type` from the OneStop plan of record. For a previously surveyed linear disposition also supply `existing_length_m` for the entire existing disposition and `affected_quarter_sections` for the amendment. The report distinguishes candidate itemized survey scope, full retracement and unresolved scope under sections 3.3.2–3.3.3 of the May 2024 manual. It leaves sketch-based and other amendments for review under AER Manual 018 section 6.6. The new-application Table A2 lookup is separate.

If regulator direction for the unresolved exact-6,500-m case is already supplied,
retain its text and source in `survey_scope_direction`. The summary asks for its
review instead of repeating the request. This informational field does not
override the unresolved survey-scope gate or establish that direction is current.

For an AER renewal, supply the active `existing_plan_type`, the confirmed `disposition_changed` boolean, and the applicable disposition, purpose and subactivity for the Table A2 row. For a sketch mismatch, supply `disposition_issued_on` from the disposition record. A date before September 1, 2010 flags possible legacy variance review under AER Manual 018 section 7.5.6. Confirm full-term status, sketch and mapping criteria, and regulator approval separately. The reported comparison does not determine renewal eligibility.

The default drawing checklist cites the May 30, 2024 Crown plan-content manual for numerical scale, scale bar and north arrows. A PDF ratio is a text candidate. Confirm that it is in the title block and check any scale exceptions. Scale bars and north arrows remain visual checks. Detail views are exempt from the scale-bar requirement under section 1.3.7.2. The cited edition's currency must be checked separately.

The checklist also locates the proposed plan heading and optional `applicant_name` and `municipality_name` from the scenario. It looks for whole PDF text spans and permits the corresponding applicant or municipality field prefix. Confirm candidate placement and compare names with the authoritative application records. Split, outlined or scanned text may require visual review. The legal description, plan extents and legend require visual and application review.

Full-span headings may include a description after the plan type, such as `Sketch Plan Showing ...`, `Surveyor Sketch Plan Showing ...` or `Plan of Survey Showing ...`. This is a text candidate, not statutory classification. Fragmented titles and damaged OCR remain unresolved when they do not match.

Main-plan review includes referenced checks for geo-referencing, cadastral fabric, nearby interests, hydrography and the activity outline. The review can locate a whole-span total area label in hectares or a single hectare value under a split Total heading with paired hectare and acre columns. It reports the numeric cell's page and location. Conflicting totals or multiple plausible table cells stay unresolved. The independent area comparison uses the reviewer-selected label and supplied survey coordinates.

## Offline revision comparison command

Use the actual original PDFs in explicit order: baseline first, revised second.
Reuse the confirmed application context in one scenario JSON. The command
regenerates both reviews with that scenario and the same catalogue/references;
it does not import saved reports or interpret custom popup comments. Recognized
Crown Plan Agent review copies are rejected; retain and use the originals.

From the complete skill folder, after installing its requirements, substitute
existing private input paths below. The output parent directory must already
exist, and all output names must be new and outside both the installed skill and
its owning code repository:

```bash
python engine/revision_cli.py /path/to/private-job/old.pdf /path/to/private-job/new.pdf \
  --scenario /path/to/private-job/scenario.json \
  --output /path/to/private-job/compare.md \
  --json-output /path/to/private-job/compare.json --offline
```

`--offline` documents intent; this command always runs offline and never downloads
references. Add `--table-a2-pdf /path/to/private-job/table-a2.pdf` only for an
already supplied A2 source under confirmed in-scope AER context. `--catalogue`
selects a common local candidate catalogue. Missing references stay unresolved.
The separate single-PDF CLI's refresh, cache, drawing-text, clause-workbook and
survey-geometry flags are not revision-comparison options.

Optional `--annotated-pdf /path/to/private-job/revised-review.pdf` creates the
**standard revised-plan review copy**, with notes and its printable index. It is
not a graphical change overlay. Keep both originals, complete results and the
derived PDF private; use synthetic inputs only for development.

The JSON record includes both source hashes, the common `review_context`, engine,
scenario, catalogue and reference hashes, and before/after findings linked by
`requirement_id`. Literal groups normalize whitespace only and retain repeated
occurrences; extraction span splitting or merging can create inventory changes.
There is no fuzzy matching, OCR, visual comparison or geometry comparison. A lost
match, identical text or no reported text changes never establishes a fixed,
closed or compliant result. Unknown locations and manual checks stay visible.

Read the [comparison guide](../references/revision-comparison.md) for record
fields, state meanings and the ChatGPT/manual fallback. Execution requires both
real source files, Python and PyMuPDF; without them, describe the accessible
evidence and state that no engine comparison or exports were generated. This
workflow needs neither Octopus nor a new server.

## Optional dated-source clause workbook

Add `--clause-catalogue` to append a separate manual-review workbook for one
publication and edition. The supplied `dated_clause_catalogue.json` represents
144 numbered paths from the May 30, 2024 content manual, with 323 atomic manual
review checks (326 question prompts), 105 fact definitions and four cited override
controllers. This is dated source-path coverage, not 323 automated compliance
checks or verified current authority. Results stay `REVIEW_REQUIRED` and
`UNVERIFIED_CURRENT`.

From the complete skill folder, with private inputs outside both the repository
and installed skill (replace the illustrative `/path/to/private-review`):

```bash
python engine/review_cli.py /path/to/private-review/plan.pdf \
  --scenario /path/to/private-review/scenario.json \
  --clause-catalogue engine/dated_clause_catalogue.json \
  --clause-facts /path/to/private-review/clause-facts.json \
  --clause-inventory engine/requirement_coverage.json \
  --reference-cache /path/to/private-review/empty-cache \
  --offline --output /path/to/private-review/review-with-clauses.md
```

The PDF, scenario and facts in this example must be supplied locally; the paths
are illustrative. The workbook needs no regulator PDF to prepare manual
questions. The separate Table A2 check still requests an appropriate source when
none is available. Offline mode is the default and does not initiate a download.

`--clause-facts` and `--clause-inventory` require the explicit catalogue flag.
Omitting the facts file uses an empty fact map, leaving relevant applicability
questions unresolved. Each supplied fact has exactly `value` and `provenance`;
`null` means unknown and is not converted to `false`. Inspect the selected
catalogue's definitions before supplying typed values or provenance. Optional,
permitted and exemption paths are distinguished from required checks, and
missing replacement evidence never restores an exempted/replaced route.

No clause workbook is inferred from the legacy `--catalogue` option, a filename
or matching citation. Without an explicit inventory, its source universe remains
unknown; a matching supplied inventory still leaves atomic obligation
completeness `NOT_ASSESSED`. The CLI does not bind PDF observations to workbook
questions automatically. Programmatic observation references are caller
assertions, not adapter execution or compliance evidence.

Read the [workbook guide](../references/clause-workbook.md) for an invented fact
example, definition inspection, selection/override meanings and the
`prepare_clause_workbook` / `render_clause_workbook` APIs. Keep generated reports
and project evidence private, and verify current sources independently.

## Optional survey geometry input

When coordinates are missing, the report prepares an unexecuted specialist proposal. Follow the [geometry handoff contract](../references/geometry-handoff.md): establish evidence and feature identity, reconstruct through the existing survey skill, then export and reopen CAD. Verify companion availability first; names in a proposal do not mean installed or executed skills. GIS validation is proposed only with `gis_requested: true`. No new PDF-to-boundary engine is implied.

For a geometry review, supply a separate local JSON file with explicitly sourced coordinates. This example is **entirely synthetic** and is not an EPSG/3TM/UTM definition:

```json
{
  "coordinate_source": "EXPLICIT_SURVEY_COORDINATES",
  "crs_identifier": "SYNTHETIC_PROJECTED_METRIC",
  "crs_verified": true,
  "closed_ring": true,
  "vertices": [[500000,5600000],[500100,5600000],[500100,5600020],[500000,5600020],[500000,5600000]]
}
```

Pass `--survey-geometry /private/path/survey.json` to `review_cli.py`. Set `crs_verified` to true only when the input coordinates and metric projection have actually been independently verified. This option does not extract survey coordinates from the PDF. The diagnostics remain review-only and are not survey adjustments or regulatory approvals.

To compare a displayed area with the calculated boundary area, add `"area_label": {"page": 1, "text": "AREA 0.200 ha", "tolerance_ha": 0.001}` to the survey JSON. Select one exact PDF text span on the stated page and confirm that it describes the supplied boundary. The report leaves the comparison unresolved for absent or duplicate spans, open geometry, or an unverified CRS. The tolerance is supplied by the reviewer.

For a split measurement table, use `"area_label": {"source": "table_total", "page": 1, "text": "2.400", "tolerance_ha": 0.001}`. Supply the exact numeric cell text. The selected page must have a unique detected hectare total with that text. The report leaves competing cells and value mismatches unresolved.

The checklist and survey-area comparison share a document-wide total-area ambiguity check. Conflicting hectare totals or multiple plausible table cells leave the comparison `AREA_LABEL_UNRESOLVED`, even when one selected value would numerically agree with the boundary. Resolve the annotation context before comparing it.

Polygon areas use the supplied coordinates' decimal representation through subtraction and cross-products. The JSON-compatible `area_ha_decimal` measurement preserves that arithmetic for the comparison; numeric area fields remain available for display. A difference exactly equal to the supplied tolerance is within tolerance, without widening the tolerance by a floating-point epsilon. This preserves input precision; it does not establish coordinate accuracy or a valid legal boundary.

## Source-record maintenance (0.6.1)

The [November 18, 2026 source audit](../references/regulatory-source-audit-2026-11-18.md)
updates publisher observations and the source inventory. It does not change
review logic or add automatic current-authority verification. The revision
comparison implementation/schema version remains `0.6.0`; the loaded
Python/JSON fingerprint records the exact source snapshot, including inventory
updates. Package/skill version `0.6.1` identifies this maintenance release.

## Execute dated clause observations (0.9.0)

Use `--regulatory-evidence-spec /private/evidence-spec.json` with the explicit
dated `--clause-catalogue` and applicable `--clause-facts`. This executes supported
PDF observations only after workbook selection/override gates. Add
`--point-export /private/points.csv` when its actual source-hashed CAD/GIS export
contract is in the evidence specification. No file is downloaded automatically.

The [clause execution guide](../references/clause-execution.md) documents all
eleven bounded question paths across nine clauses, the strict selectors/export
contracts, frame and completeness gates, source-located Markdown results and
remaining manual obligations. The [November 21 source audit](../references/regulatory-source-audit-2026-11-21.md)
records inspected current publisher resources and explicit supersession. These
edition checks and mechanical observations do not certify a plan's compliance.

## Compare actual job records and area balances (0.10.0)

The [job-record guide](../references/job-record-checks.md) explains the actual-file
reader, three identity bindings, fixed balances and three optional arithmetic
bindings. Use `--job-record-spec /private/records-spec.json` and repeat
`--job-record-file SOURCE_ID=/private/original.pdf` for explicit additional sources.
Actual record bytes, selected fields, subjects, semantic roles and currentness
basis are retained; missing sources/fields stay unresolved without invented
page locations. Unbound job QA can use a confirmed private JSON instruction.

`--annotated-pdf` now includes actionable finished-plan, clause, job-record and
point-export findings in the complete notes index and places comments at uniquely
verified plan spans. PASS results remain in Markdown. All job reference hashes
are checked again after building the marked copy, before publishing both outputs.

Known invented integration documents are generated by
`tests/job_record_examples.py`; run the relevant tests without any work input:

```sh
python -m unittest discover -s skills/crown-plan-agent/tests -p 'test_job_record_*.py' -v
```

Keep the [readiness boundary](../references/review-readiness.md) with the results.
