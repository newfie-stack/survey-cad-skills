# Clause evidence expansion implementation plan

> **For agentic workers:** Use focused implementation and independent whole-branch review. User has authorized implementation and publication.

**Goal:** Execute additional source-bound questions from the dated Crown-content workbook and compare supplied CAD/GIS point exports without claiming whole-clause compliance.

**Architecture:** A separate evidence pass reuses the workbook's applicability and override decisions. It reads original PDF fields and optional CSV point exports, returns mechanical findings keyed to selected questions, and preserves source authority and residual manual work separately. Existing manual workbooks and legacy observations remain compatible.

**Tech stack:** Existing Python runtime, hash-locked PDF reader, standard-library CSV and Decimal. No added dependencies or reconstruction calculator.

## Design and constraints

- Source edition: May30,2024,144 numbered clauses. Support7 coordinate questions across5 hybrid clauses, plus4 existing text-comparison questions across4 general clauses. This is9 partially observed clauses, not9 fully automated clauses.
- Hybrid questions: table starts1/consecutive IDs, original coordinate precision/grouping, EC/XC/RC/OC tokens, two distinct accepted OC records, every EC/XC/RC within inclusive10000m of an OC.
- Fields are selectors in the actual source-hashed PDF. Raster, clipping, ambiguity, reused spans and incomplete table review block collective results.
- Spatial checks require reviewed provenance/roles, complete sets, metric units and a declared coordinate frame covering datum/epoch/axes/grid-ground basis. Exact Decimal squared distances avoid tolerance-boundary float errors. No transformation or reconstruction.
- CAD/GIS integration reads actual bounded CSV point exports and checks immutable bytes, unique identifiers, whole-set membership, category and coordinates in a declared common frame. It does not inspect native DWG/SHP or accept survey control.
- General questions reuse actual finished-plan execution: numerical scale, unsurveyed-territory note, detail-reference equality and existing-plan-label equality. Text equality is partial evidence with remaining semantic/visual questions.
- Execution requires the exact shipped dated catalogue and selected workbook questions. Unresolved applicability, out-of-scope land and overrides stop execution. Mechanical PASS/FAIL never changes normative REVIEW_REQUIRED.
- Recheck live official source editions; distinguish verified publisher/resource facts from application-specific authority. Correct proven supersession, preserve older audits, no PDFs or private documents in public source/plugin.

## Review focus

Incomplete tables must not imply missing points; same coordinates cannot count twice as independent OCs; same CRS name does not establish a common frame; custom/mutated catalogues cannot bypass applicability; context selection cannot transfer text completeness.

## Tasks

- [ ] Read live authoritative publisher records and selected clauses; update source inventory and dated audit.
- [ ] Add failing actual-PDF coordinate-table tests, then implement bounded field reader and seven mechanical findings.
- [ ] Add failing actual-CSV tests, then implement point-export comparison including stale snapshots and frame blockers.
- [ ] Add failing applicability/integration tests, then implement clause-evidence execution, CLI input and report/summary integration.
- [ ] Preserve synthetic fixtures/oracles and replayable results; document exact supported questions and residual work.
- [ ] Run focused/full/standalone tests and smoke; independently audit code, package privacy and source assertions.
- [ ] Publish reviewed public branch through CI/PR; update installed skill with guarded release ID and read back contents.
