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

Selections use one-based pages and **unrotated, crop-relative PDF points**, the same space as the existing PDF inventory. Text crossing a selected region, clipped text, nonhorizontal text and intersecting raster images stay unresolved. Partially overlapping selections cannot reuse the same observation as independent fields. Multiple competing numeric candidates are not silently resolved.

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
- `decimal_sum`: three to twenty regions; `unit` (`ha`, `m2` or `m`) and a nonnegative plain-decimal **string** `tolerance`. At least two part regions precede the total. Plain decimal values and units are required; unsupported formats remain unresolved.
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

The score counts detected known defects, missed defects, false alarms, missing/unexpected results and correct abstentions. **A known defect with REVIEW_REQUIRED is a missed detection**, even when that conservative behavior is expected. Exit zero means the documented bounded behavior matched, not that every error was caught. Fixtures, specifications and expected answers are developer-authored, not independently accepted survey evidence.

## Unfinished acceptance

This is not an autonomous whole-sheet omission detector. Full visual/semantic extraction, correct context selection on unseen layouts, current-source regulatory verification, field/control evidence, CAD/GIS comparisons, independent technical/agent review and qualified real-plan acceptance remain separate. The source-image and derived-result privacy restrictions are unchanged. Do not publish private example plans, private findings or identifying case mapping.
