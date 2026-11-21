# Area-category reconciliation regression

This wholly invented pair preserves a review-selection miss: the grand total
agrees even though area has moved between the new-cut and existing-clearing
summaries. No source drawing, real project values, client details or source
layout is reproduced.

The three invented parcel rows total **0.700 ha new cut** and **0.450 ha existing
clearing**, giving **1.150 ha overall**. The shifted version instead prints
**0.820 ha** and **0.330 ha** in those category summaries. Its parcel rows and
grand total are unchanged. The clean control has the correct breakdown.

The existing finished-plan checker runs four selected comparisons per drawing:

| Comparison | Clean | Shifted |
|---|---|---|
| Category summaries sum to the grand total | PASS | PASS |
| Parcel totals sum to the grand total | PASS | PASS |
| New-cut components sum to their category summary | PASS | FAIL |
| Existing-clearing components sum to their category summary | PASS | FAIL |

The test also executes a totals-only specification against the shifted drawing.
Its two narrow comparisons pass and no unselected category findings appear.
That freezes the selection limitation: a correct grand total is not a clearance
of the category breakdown. Both reports retain `overall_status: REVIEW_REQUIRED`.

The frozen answer key records **one planted reallocation issue with two affected
checks**. Do not count its two failed comparisons as two independent issues.
Display-rounding bounds are 0.0015 ha for three nearest-0.001-ha cells and
0.0020 ha for four cells; the 0.120 ha discrepancy exceeds either bound.

## Run the regression

From the complete skill folder, after the normal runtime check:

```bash
python -m unittest discover -s tests -p 'test_area_classification.py' -v
```

The tests read the actual generated PDFs, compare literal source rows and
summary fields, run `review_finished_plan()` and the existing review CLI, and
check the clean control and exported reviewer packets. Ordinary CI discovers
these tests automatically. Generated PDFs remain outside the repository.

## Export a separate assisted review

```bash
python tests/export_drafting_exercise.py --case area_split_shift --output /tmp/crown-area-review-01
python tests/export_drafting_exercise.py --case area_split_clean --output /tmp/crown-area-review-02
```

Give a fresh reviewer only one output's `review_inputs/` directory. It contains
`plan.pdf`, a neutral job brief and ordinary review instructions. Both versions
have identical briefs and instructions. Keep the export command, case ID,
parent manifest, generator, selected regions and answer key out of that review.
Use separate reviewer contexts for the paired drawings and freeze their literal
findings before opening the answers. Follow the existing
[assisted review protocol](../tests/unfamiliar_review_protocol.md) for evidence
locations, claim limits and independent adjudication; this pair uses its own
[issue-level truth](../tests/fixtures/area_classification_truth.json).

This change adds reproducible selected-region regression coverage and exportable
review inputs. It does not execute a fresh assisted model evaluation, train a
model, add automatic category discovery or improve the historical 23-case
benchmark's reported detection rate. Inline units keep this test independent
of the separate table-header unit-inheritance gap.
