# Whole-plan review trial — November 21, 2026

This dated record preserves an assisted review experiment as reusable regression
evidence. Its twelve drawings and all job facts are invented. These cases have
now been seen and published; use genuinely new cases for a future blind trial.

## Recorded result

| Plans | Sheets | Clean controls | Planted issues | Found | Missed | False alarms | False clearances |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 12 | 16 | 6 | 12 | 12 | 0 | 0 | 0 |

One additional finding described the other changed component of the same area
category issue. It remains in the record as a duplicate and earns no additional
detection credit. No unsupported scored claim or outside-key issue was recorded.

Two separate authors prepared six paired layouts: a multi-sheet access package,
a cabin/access sheet with image-only Notes, an activity/exclusion area ledger,
a portrait PLA illustration, a two-sheet RTF route and an oblique LOC drawing.
The reviewers found conflicting sheet identities and township, an operating-note
reference typo, an incorrect length sum, a decimal-place width error, conflicting
CRS zones, a missing main-view north marker, category amounts concealed by a
correct total, and an inconsistent exclusion note.

## What was executed

Each case had a fresh reviewer context using Crown Plan Agent 0.7.9 at source
commit `ea800aedfcf2d922f13a997776f7ee9366252fe1`. Reviewers received only their
assigned PDF, normal job brief, whole-sheet images and uniform instructions.
They received no selected check regions, answer key, other cases or prior
findings. They inspected actual images, made their own crops and selected their
own mechanical comparisons. Visual observations and manual arithmetic remained
separate from CLI results.

All twelve literal reports were frozen before grading. Separate model graders
compared the actual drawings, briefs, frozen answers and every saved claim.
All 378 original claims were preserved through kind-preserving normalization
into 647 atomic units. Existing normalization and scoring helpers validated the
accounting. An unresolved planted issue earns no detection credit.

The maintained runtime was Python 3.12.16, official pymupdf-lite 2.1 and MuPDF
1.28.6. Its minimum-version gate passed; that is not native-advisory clearance.
The host did not expose exact reviewer model/effort metadata. Blinding was
procedural on a shared filesystem. Saved artifacts support source/output
identity and reported results, but do not authenticate every historical tool
call or the reviewer's gaze. No instruction or engine change occurred between
cases, and there is no before/after or model-training claim.

## Preserved evidence

- [Portable fixture generator](../tests/whole_plan_trial.py) and its drawing
  modules recreate the invented PDFs and unchanged briefs in a new caller-owned
  directory. Generated drawings and renders stay outside the repository.
- [Frozen truth](../tests/fixtures/whole_plan_trial_truth.json) retains both
  source-bound author records and the combined case index.
- [Portable evidence](../tests/fixtures/whole_plan_trial_evidence.json) retains
  the original and normalized claims, Markdown reviews, adjudications, mappings,
  source identities, scores and provenance records. Host paths use documented
  placeholders. Original literal-byte hashes and portable-content hashes are
  distinct; a redacted export is not presented as the original byte stream.
- The complete unmodified experiment is separately archived as
  `crown-plan-agent-whole-plan-trial-2026-11-21.zip`: 435 original files plus an
  internal member manifest. SHA-256:
  `b5ffa8d3008ab5a3e779341ba40b21691278a5a36f5538fb9cd5d48f7cacd782`.
  Only two bytecode caches created during later inspection were excluded.

No work documents, original public project PDFs, regulatory PDFs, Octopus source
or real project data are included in these fixtures. The archive contains only
the original invented experiment. Hashes identify retained artifacts; they are
not third-party attestation or professional acceptance.

## Reuse the cases

From the repository root, using the existing reviewed dependency environment:

```bash
python -m unittest discover -s skills/crown-plan-agent/tests \
  -p 'test_whole_plan_trial*.py'
```

This regenerates fixtures and replays the saved grading through the existing
scoring helpers. It does **not** rerun a model review or semantically regrade a
new review in CI.

To create a packet outside the repository:

```python
import sys
from pathlib import Path

sys.path.insert(0, "skills/crown-plan-agent/tests")
from whole_plan_trial import write_case

write_case(Path("/tmp/crown-regression-X95"), "X95")
```

Give a reviewer only that packet and the selected skill snapshot. Keep the
public generator, truth, other cases and old findings out of its input context.
A repeat on these published cases is a regression exercise, not a new blind
test. Freeze the new literal output before separate semantic adjudication; never
reuse old grades as if they evaluated new findings.

## Open work

Several initial text regions intersected neighbouring font boxes and needed
technical adjustment. Some mechanical checks remained unresolved; assisted
reading or manual arithmetic supplied separately scoped observations. Terminal
punctuation also left one route's numeric totals unresolved in the strict reader.
These are useful targets for future evidence-selection and numeric-format
regressions, without weakening the current extraction/completeness gates.

This is a small sample of readable, stylized synthetic drawings with explicit
job facts. It does not establish accuracy on dense real plans, current-law
verification, complete regulatory coverage, accepted control, reconstruction or
CAD/GIS agreement. It adds no autonomous whole-sheet discovery, OCR or symbol
recognition to the offline engine. The separate deterministic benchmark remains
18 detections out of 21 planted issues in 23 selected-region cases. Production
and professional real-plan acceptance remain open.
