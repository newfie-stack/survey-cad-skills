# Unfamiliar-layout review trial — November 20, 2026

This is a maintainer testing guide and a bounded result record. Normal plan
review still starts with the plan and its job context; the user does not prepare
test JSON. All drawings in this study were newly invented. No work documents,
current regulatory PDFs or real survey control were used.

## What was tested

An independent fixture author prepared four paired layout families: a long-route
index with a side register and two-column crossing notes; a three-sheet lease
with current and historical revisions and separate area schedules; a rotated
foldout with an image-only note strip; and a tabular plot index with a distinct
service detail and square-metre area label.

Six initial plans were reviewed before their answers were opened. Two additional
plans remained reserved until the initial findings and grades were frozen. Each
reviewer received only its assigned PDF, job brief and neutral instructions, with
no supplied check regions or answers. The model configuration was
`gpt-6.2-sol`, high reasoning, using Crown Plan Agent 0.7.8 at source commit
`653a67e1fdfe0437e629f28b9bfb4acbb58adda1` and the maintained Python/PDF runtime.
Both phases used that same reviewer snapshot. The initial results did not justify
a defect-based instruction or engine change. This is not a before/after claim.

| Phase | Plans | Clean controls | Planted issues | Found | Missed | False alarms | False-clearance claims |
|---|---:|---:|---:|---:|---:|---:|---:|
| Initial | 6 | 3 | 6 | 6 | 0 | 0 | 0 |
| Reserved | 2 | 1 | 2 | 2 | 0 | 0 | 0 |

The findings covered transposed identifiers and a utility-reference number,
a stale current revision, incorrect gross-minus-exclusion arithmetic, an absent
units note and north arrow, a wrong plot-area label and a wrong detail scale.
The reviews correctly retained legitimate history entries, differently scoped
areas, inset scales and a visually readable raster note as controls.

An independent model adjudicator compared the saved claims with the actual PDFs,
briefs and frozen developer-authored truth. All 159 original claims survived
normalization into 166 atomic units: eight matched findings, 108 supported
clearances, 12 unresolved statements and 38 manual scope limits. No duplicate,
unsupported or outside-key finding was recorded. Unresolved statements and
manual referrals earned no detection credit. The coordinating scorer reproduced
the recorded grades. This is developer/model evaluation, not professional
acceptance or an accuracy estimate for unseen real plans.

These assisted results are separate from the existing deterministic benchmark,
which still detects 18 of 21 planted defects in 23 selected-region cases. The
offline engine has not gained graphical recognition or automatic whole-sheet
context selection from this study. No model training took place.

## Repeat the method

The [portable reviewer protocol](../tests/unfamiliar_review_protocol.md) describes
the study's input restrictions and claim format. The
[machine-readable result summary](../tests/fixtures/unfamiliar_layouts_results.json)
keeps both phases and the source/freeze hashes; no raw plan or work record is
embedded in it.

The former packets can be reproduced from the skill folder using the existing
reviewed dependencies and a new directory outside the repository:

```python
import sys
from pathlib import Path
sys.path.insert(0, "tests")
from unfamiliar_layouts import write_case

write_case(Path("/tmp/crown-trial-01/review_inputs"), "01")
```

Give a reviewer only that input directory. Do not provide the fixture source,
answer key, other cases or prior findings. Save the literal review and its source
hash before grading. The source and answers are now public regression material;
these same cases must no longer be described as fresh holdouts. Create new
layouts and literals for a new forward test.

Use an independent semantic adjudicator to map atomic findings to frozen issue
IDs by feature, job expectation and actual evidence. Do not equate similar wording
or equal finding counts with a match. Keep the original-to-atomic mapping and
account for every claim. The `assisted_trial_scoring.py` helper validates source
identity, coverage, claim kinds and issue IDs. A finding matches exactly one
truth issue. Duplicate findings cannot inflate recall. Explicit false clearances
are reported as raw claim counts and as unique affected truth issues. Unsupported
claims and verified discoveries outside the key remain separate; the latter
require oracle review rather than silently changing the frozen answers.

When a miss or false alarm justifies a correction, first reproduce it as a test,
then make the smallest supported change and run the existing regressions. Keep
reserved cases untouched until changes and initial results are frozen. Ordinary
fixture/scoring tests run in CI; assisted model reviews and their semantic
adjudication require a separate host-supported exercise and are not run by CI.

## Evidence limits

Blinding was procedural: reviewers used fresh contexts and restricted input
instructions, but shared filesystem access was not an isolation boundary. The
source author preflighted the packets with one rendering stack. Four layout
families, explicit invented briefs and eight planted errors are a small sample.
No real-plan, field/control, CAD/GIS, current-law or production acceptance follows.
The existing dependency policy and open native-library findings are unchanged.
The fixture suite binds generated inputs to the recorded artifact hashes on
Linux x86_64 with Python 3.12, PyMuPDF 2.1 and MuPDF 1.28.6. Other stacks retain
direct-content/rendering checks and skip that specific byte-identity assertion;
their output has not thereby been accepted as the original study artifact.
Generated PDFs, renders and detailed study outputs stay outside the source
repository and installed skill. Only synthetic source, frozen truth and a
bounded result summary are published.
