# Intake forward trial — November 21, 2026

Four fresh invented drawings tested the frozen 0.8.0 intake workflow at commit
`3a3e5697ccf4e48f75032054131131ed3a7f3ea9`. Reviewers saw no selected regions,
answer key, other cases or prior findings. Two new layout families supplied six
sheets: dense portrait current/history fields with differently facing near-north
labels, and a wide multi-view layout containing an image-only note. All job
facts and names are invented; no work document was used.

## Assisted findings

| Plans | Sheets | Clean controls | Planted issues | Found | Missed | False alarms | False clearances |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 6 | 2 | 4 | 4 | 0 | 0 | 0 |

**All four detections were assisted visual/manual findings.** They were a
conflicting subject-file identifier, an incorrect length-summary total, a
malformed main-view scale and a conflicting zone in a raster note. The
deterministic engine emitted no FAIL in this set. Its unresolved cases must not
be presented as automatic detections or as clean-plan clearance.
Here, manual means the reviewing model's source-based visual or arithmetic
observations, not validation by a qualified human plan checker.

Every original Markdown report and its claims were frozen before separate model
grading against actual PDF images, job briefs and the frozen oracle. All 233
original claims survive as 246 kind-preserving atomic units. Existing scoring
and normalization helpers verified every mapping and verdict. No duplicate,
unsupported claim or additional issue requiring oracle review was recorded.

## Intake and executed checks

| Case | Requested | Ready and executed | Preparation unresolved | Mechanical PASS | Mechanical FAIL | Mechanical REVIEW_REQUIRED | Context retries |
|---|---:|---:|---:|---:|---:|---:|---:|
| L38 | 19 | 14 | 5 | 13 | 0 | 1 | 0 |
| P72 | 26 | 12 | 14 | 12 | 0 | 0 | 0 |
| R46 | 24 | 18 | 6 | 18 | 0 | 0 | 0 |
| U91 | 24 | 12 | 12 | 11 | 0 | 1 | 0 |
| Total | 93 | 56 | 37 | 54 | 0 | 2 | 0 |

Graders independently recomputed saved context preparation and ready-subset
results. Discovery, saved preparation and review-command recomputation with the
same contexts counted as one attempt. Every first attempt, unresolved request
and separately recorded visual observation was retained.

The 37 preparation followups include stacked/wrapped associations and graphics;
they are not all engine failures or planted defects. The two executed unresolved
checks were an unsupported length-summary comparison and the malformed ratio.
Correctly scoped history, independent views and separately stated quantities
were not substituted for the requested current evidence.

An additional known-case probe used 25 fully labelled requests from the earlier
saved study. Nineteen prepared without manual box adjustment and ran as sixteen
PASS and three FAIL, with no unresolved reader result. Six wrapped/descriptor
associations stayed located followups. This selected subset is a separate probe,
not a whole-plan success rate or a matched before/after experiment.

## Preserved regressions and reuse

The [portable fixture generator](../tests/intake_forward_layouts.py) regenerates
all four original PDFs and briefs on the recorded runtime. Its [frozen truth](../tests/fixtures/intake_forward_truth.json)
and [portable evidence](../tests/fixtures/intake_forward_evidence.json) retain
source binding, review content with identified path redactions, first attempts, mechanical evidence,
normalization, grading and the saved result. Original hashes and path-redacted
portable-content hashes have distinct roles. Generated PDFs and renders remain
outside the repository; the complete original experiment is separately archived.
The archive `crown-plan-agent-intake-v080-evidence.zip` contains 265 original
trial/source/verification files plus a member manifest; SHA-256 is
`b060a0337325c39e9dd8e99f8e82f0bdd4ae2dd9a7f034633093623b9b49d1cb`.
Release staging, installed-plugin metadata and coordinator notes are excluded.

Run the regression/replay tests from the repository root:

```bash
python -m unittest discover -s skills/crown-plan-agent/tests \
  -p 'test_intake_forward*.py'
```

To create a packet outside the repository, import `write_case` from
`tests/intake_forward_layouts.py` and pass a new directory and one of
`L38`, `P72`, `R46`, `U91`. Give only that packet to a reviewer. These published
cases are now known regressions. CI checks fixture/replay integrity; it does not
rerun a model review or semantically regrade new output. Future blind trials
require new cases and independently frozen new reviews and grading.

## Limits

The small, stylized sample and explicit job facts do not establish real-plan
reliability. Blinding was procedural on a shared filesystem; exact host model
metadata was not exposed. Hashes and saved artifacts support source/results,
but do not independently authenticate every historical tool call or gaze.

The code, instructions and supplied sources stayed frozen during this single
phase. No model training, case-dependent tuning or before/after accuracy claim
follows. The near-north baseline examples test independent reading directions;
the user's approximate office text-facing cutoff remains unconfirmed and is
not a violation rule. Scanned/outlined/graphical and ambiguous native evidence
still require visual review. Current-law, professional, control, CAD/GIS and
production acceptance remain open.
