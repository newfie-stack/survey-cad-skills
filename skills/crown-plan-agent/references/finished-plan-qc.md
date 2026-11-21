# Finished-plan drawing QC: bounded development pass

This opt-in addition checks selected regions of a potentially finished **native-text PDF**. It does not redraw the plan, change geometry, approve a submission, establish land ownership, or apply Alberta rules to excluded jurisdictions. Existing Crown review gates are unchanged.

## What executes

| Kind | Mechanical comparison | Important limit |
|---|---|---|
| `required_text` | Locate an expected phrase inside its selected context | A textual match is not semantic or regulatory compliance. An absence becomes FAIL only with source-bound, explicit visual-to-text completeness evidence. |
| `same_text` | Compare two or more selected subject fields | Different neighbouring parcels must not be selected as the same subject. Missing/multiple values remain unresolved; use a separate presence check where presence is required. |
| `scale` | Read one numeric ratio in the selected main-plan context and optionally compare its denominator | An inset is not a substitute. This does not measure whether the plotted drawing is actually to scale. |
| `decimal_sum` | Compare selected part values with the selected total, using decimal arithmetic and an explicit tolerance | Last region is the total. Units must match. This is table arithmetic, not a survey-boundary area calculation. |
| `visual` | Preserve a source-located review request | The offline checker leaves symbol interpretation open. When the host can see rendered pages, the agent follows the [visual review procedure](chatgpt-review.md#visually-check-the-north-arrow-and-scale-bar) and reports observations alongside the CLI results. |

Selections use one-based pages and **unrotated, crop-relative PDF points**, the same space as the existing PDF inventory. Text crossing a selected region, clipped text, unsupported text geometry and intersecting raster images stay unresolved. Partially overlapping selections cannot reuse the same observation as independent fields. Multiple competing numeric candidates are not silently resolved.

### Rotated native text

The pass reads native text at cardinal and oblique orientations when its direction
and geometry are usable. It orders fragments and wrapped lines in temporary
reading frames using recovered span quadrilaterals for oblique text and original
rectangular bounds for cardinal text. Oblique geometry must agree with the native
direction, baseline origin and font metrics; inconsistent nonuniform transforms
remain unresolved. Different and opposite directions remain
separate, so their words cannot be joined into an invented phrase.

Page rotation and text direction are distinct. The source PDF, its hash and
selected regions stay unchanged. Findings retain the original unrotated page
boxes, native directions and available quadrilaterals; the temporary reading
coordinates are not survey coordinates or an inferred north reference.

This does not add OCR or recognition of outlined lettering. Missing or unusable
native geometry, unsupported vertical writing, raster overlap and clipping
still require independent reading. Successful rotated-text capture does not
prove extraction completeness or make an unobserved phrase a confirmed omission.

## Source-bound input

Before choosing regions, complete the
[full titleblock and Notes reading](chatgpt-review.md#read-the-complete-titleblock-from-top-to-bottom)
on each reviewed sheet. Use the printed context with source locators, retaining
conflicts and unread portions. A few selected QC fields do not establish that
the entire titleblock was read. Missing survey coordinates do not prevent this
intake or otherwise supported finished-plan checks.

A local UTF-8 JSON object has `schema_version: 1`, the actual original PDF's lowercase `source_sha256`, a `prepared_by` name/role, and `checks`. Each check requires a unique `id`, a supported `kind`, a plain-language `description`, the `basis` for that comparison, and `regions`.

Each region has `page`, `bbox_points: [x0, y0, x1, y1]`, and `role`. Optional `label` selects a literal line prefix (not a regular expression). The agent/reviewer must establish subject/context identities against the opened source; the JSON does not prove those choices are correct. Expected text/job instructions must come from authorized project evidence or a separately verified applicable requirement, not an invented rule.

Additional check fields:

- `required_text`: nonempty `expected` phrase; one region.
- `same_text`: two to twenty regions, each with one unambiguous selected value.
- `scale`: one region; optional positive integer `expected_denominator`.
- `decimal_sum`: three to twenty regions; `unit` (`ha`, `m2` or `m`) and a nonnegative plain-decimal **string** `tolerance`. At least two part regions precede the total. Plain decimal values and units are required; unsupported formats remain unresolved. If an explicitly labelled final total field has declared complete text coverage, distinct stated amounts are a textual conflict even when arithmetic tolerance would admit both. Equivalent repeated amounts can agree; no independent part row is removed from the sum. Without the label/completeness evidence, multiple candidates remain unresolved.
- `visual`: one to twenty source regions; always REVIEW_REQUIRED in this pass.

A region can carry `coverage_review` with `status: "TEXT_COMPLETE"`, `method: "VISUAL_TO_TEXT_COMPARISON"`, a nonempty `reviewer`, and a nonempty `statement` documenting what was compared. This is a supplied declaration bound to the PDF hash, not independent verification performed by the engine. Never manufacture it to obtain a FAIL. Without it, a phrase or scale not found remains REVIEW_REQUIRED. Intersecting raster content overrides this declaration and remains unresolved.

The input is bounded to 1 MB, 100 checks and 200 total regions; duplicate keys, unknown fields, invalid/nonfinite coordinates, duplicate selectors and stale source hashes are rejected. No input expression is executed. The parser does not infer CRS or survey geometry from PDF points.

## Run on an authorized plan

Prepare and retain the specification **outside the repository**, along with the original and its review evidence. The assistant should do this mapping work from the source, rather than ask the draftsman to manually create a JSON file. Existing application-context and regulatory-source instructions still apply.

```bash
python engine/review_cli.py /private/job/proposed-plan.pdf \
  --scenario /private/job/scenario.json \
  --finished-plan-spec /private/job/review-checks.json \
  --offline --reference-cache /private/job/reference-cache \
  --output /private/job/new-review.md
```

The opening summary records the selected drawing-QC checks that actually ran, separately from Crown requirement selection. Checks left unresolved still count as executed attempts and need manual follow-up. The report keeps its **Finished-plan drawing QC** detail section. It includes hashes, actual extracted values, exact page/region locations, supplied coverage declarations, comparison results and correction guidance. Output uses exclusive creation. With `--annotated-pdf`, the standard PDF markup and its notes index cover the existing evidence review. The finished-plan findings appear in the Markdown report.

For a structured ledger, call `finished_plan_review.review_finished_plan(pdf_path, specification)` and retain its returned object privately. `overall_status` remains REVIEW_REQUIRED; `regulatory_status` remains NOT_ASSESSED. No overall green certificate is emitted, even when all selected text comparisons pass.

Generic drawing comparisons may run only when explicitly requested for an out-of-scope plan. The existing Crown ledger still reports OUT_OF_SCOPE; no federal or other jurisdiction's rule module has been added.

## Reproduce the invented benchmark

From the skill folder:

```bash
python tests/finished_plan_benchmark.py --output /tmp/new-crown-qc-benchmark
python -m unittest discover -s tests -p 'test_*.py' -v
```

Use a new output directory. The benchmark takes no real-plan input. It creates invented PDFs, specifications, per-case reports, a JSON scorecard and a Markdown summary. It executes the actual PDF reader and existing review command. The separate frozen answer key is read only after every production review has finished. Test-only mutation names and expected verdicts never enter the production checker.

The score counts detected known defects, missed defects, false alarms, false
clearances, missing/unexpected results and abstentions. **A known defect with
REVIEW_REQUIRED is a missed detection**, even when that conservative behavior is
required by incomplete evidence. A `PASS` on a known defect is a false clearance.

The version-2 scorecard separates `regression_gate_passed` from
`all_defects_detected`. Each check has a frozen regression policy: preserve a
supported detection (`must_detect`), preserve a clean pass (`must_pass`), retain
an evidence-bound abstention (`must_abstain`), or track a planted defect in an
explicit capability gap (`capability_gap`). A gap may remain unresolved or gain
a detection; it must never become a false clearance. A new detection cannot
offset a lost required detection elsewhere. The CLI exits successfully only
when these gates and its report-summary checks pass; full detection is reported
separately.

The scorecard reports the original 16-case cohort separately from the new
seven-case LOC/MSL cohort, with category totals and outstanding missed-defect
IDs. The new drawings include clean controls, rotated identifiers, stale sheet
revisions, mismatched titles/labels/scales, arithmetic errors, equivalent rounded
totals and a raster note. The tests also check the CLI's opening summary.
Fixtures, specifications and answers remain developer-authored, not independently
accepted survey evidence. The deterministic benchmark uses selected regions; it
does not measure the agent selecting those regions or interpreting whole sheets.

## Exercise a review without preselected regions

The [November 21 whole-plan trial](whole-plan-trial-2026-11-21.md) preserves twelve
additional invented cases, source-bound answers and complete claim-level grading
records. Its fixtures can be regenerated and its saved accounting replayed in
CI. Reusing these published cases is a regression exercise; a fresh blind trial
requires new inputs and separately frozen findings and adjudication.

For a correct grand total concealing a shifted new/existing area split, use the
[invented area-category regression pair](area-classification-regression.md).
It includes a clean control, selected category comparisons and answer-free
reviewer exports, with one planted issue counted separately from its two
affected comparisons.

From the skill folder, export an invented review package to a new directory:

```bash
python tests/export_drafting_exercise.py --case msl_multiple_errors --output /tmp/crown-exercise-01
```

Give a reviewer only `/tmp/crown-exercise-01/review_inputs/`. It contains the
invented plan, job brief and review instructions. The generated check
specification and frozen answers are not included. Keep the root manifest,
fixture source and answer key out of that review until the findings are saved.
Use the same procedure with a clean case such as `loc_clean` to check false
alarms. Afterwards compare the cited findings and unresolved items with the
frozen truth. Record the host, model, exact source hashes and tool execution.
This is a separate assisted exercise, not part of the deterministic recall or
independent professional acceptance. Generated files remain outside the source
repository; the installed package contains source generators and invented truth,
not work documents or plan PDFs.

## Unfinished acceptance

This is not an autonomous whole-sheet omission detector. Full visual/semantic extraction, correct context selection on unseen layouts, current-source regulatory verification, field/control evidence, CAD/GIS comparisons, independent technical/agent review and qualified real-plan acceptance remain separate. The source-image and derived-result privacy restrictions are unchanged. Do not publish private example plans, private findings or identifying case mapping.
