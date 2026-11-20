# Portable assisted-review trial protocol

This is a maintainer test protocol, not an additional task for a plan owner.
The recorded November 20 trial used these constraints with the exact source,
input/output directories and Python executable supplied by the coordinator.

Use a fresh reviewer context. Supply only one invented case's `review_inputs`
directory, this protocol and the selected Crown Plan Agent skill snapshot.
Do not supply the generator, oracle, other cases, previous findings or grader
records. Freeze the oracle before the reviewer starts. These are procedural
blinding controls; do not claim filesystem isolation.

Review the actual plan against its job brief. Read the complete titleblock and
Notes on every sheet before the main-view orientation and selected checks.
Use readable rendered images as well as native text, preserving the source.
Use the existing reviewed dependencies and runtime gate when executing engine
checks. Derive any selected regions from the supplied source. Do not install
dependencies, obtain current regulator documents or reconstruct CAD for this
invented exercise. Regulatory authority, real control/geometry and professional
acceptance remain unverified.

Save a normal `review.md` and a structured `findings.json` before revealing the
answer key. The JSON records `source_sha256`, `tools_used`, `claims`,
`overall_status: REVIEW_REQUIRED`, and `regulatory_status: NOT_ASSESSED`.
Each atomic claim has a unique `id`, `kind`, `claim`, `location` and nonempty
`evidence` list; retain the applicable sheet numbers. Supported kinds are:

- `finding`: confirmed discrepancy, with source location, job expectation and
  correction. One condition per claim.
- `clearance`: an affirmative, bounded statement that a checked condition agrees.
- `unresolved`: an inspected condition that cannot be decided from the evidence.
- `manual`: work not performed or outside the completed scope.

Zero findings is valid. Do not infer absence from empty extraction or turn
unstated generic preferences into defects. The coordinator locks the literal
review and its source hash. A separate grader then examines the source, brief,
saved claims and frozen key. Compound statements are split only with a retained
original-to-atomic mapping. Every saved claim must survive, and its type cannot
be changed after the answers are known. Semantic faithfulness needs actual
adjudication; the score helper checks accounting, not language meaning.

Keep initial and reserved results separate. Open the reserved inputs only after
the initial findings, grades and any resulting changes are frozen. Once cases
and answers are published, call them regression cases and create genuinely new
inputs for the next fresh-layout trial.
