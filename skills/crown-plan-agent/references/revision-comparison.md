# Compare two original plan PDFs

Compare the baseline original first and revised original second under one shared
review basis. The result is an evidence comparison, not regulatory acceptance or
automatic comment closure. All regulatory results remain `REVIEW_REQUIRED`.

## ChatGPT workflow

1. Reuse the user's authorized files and confirmed application context. Identify
   which original is the baseline and which is revised; ask one grouped question
   only for genuinely missing inputs. Do not repeat established intake.
2. Check for access to both actual PDF files and a Python execution environment
   with PyMuPDF. Attachment names, screenshots or a command proposal alone do not
   establish execution. Keep the originals and complete inputs/results in a
   private working directory outside the installed skill and owning repository.
3. Run the command below using one confirmed scenario. Both reviews are freshly
   regenerated with the same scenario, catalogue and supplied reference bytes.
   This does not replay an earlier saved report or interpret handwritten/source
   annotations or custom popup comments as review decisions.
4. Explain what changed in supported text, which checklist observations remain
   ambiguous or unmatched, what remains unchecked, and the next manual checks.
   Keep both source locations and governing citations available. No candidate or
   text-change state means fixed, closed, approved or compliant.

Recognized Crown Plan Agent generated review copies are rejected so appended
indexes and generated comments cannot become plan evidence. Use the originals
already supplied; if an original is missing, request that original. The recognizer
does not certify arbitrary third-party or flattened PDFs as originals. It neither
strips comments nor recovers originals from review copies. Source annotations,
popup bodies, links and widgets are not interpreted as review decisions.

If Python, PyMuPDF or actual source access is unavailable, use accessible
authorized evidence for an assisted manual review. State explicitly that the
comparison engine and exports did not run, identify unavailable checks and keep
them unresolved. Label manual observations as manual. Never invent execution,
hashes, JSON records, output links or generated PDFs. No hosted comparison service,
new server or substitute calculator is required.

## Run the offline command

Use Python 3.12 and the complete skill folder with its installed requirements
(see the [engine setup](../engine/README.md#install-and-run-the-example)). From
that folder, substitute actual private input paths for this example:

```bash
python engine/revision_cli.py /path/to/private-job/old.pdf /path/to/private-job/new.pdf \
  --scenario /path/to/private-job/scenario.json \
  --output /path/to/private-job/compare.md \
  --json-output /path/to/private-job/compare.json --offline
```

The baseline is `old.pdf`; the revised original is `new.pdf`. The scenario is the
same JSON application-context contract used by the
[single-PDF review](../engine/README.md#offline-pdf-to-review-command), including
explicit land scope. Reuse confirmed values; unknown facts remain unknown.
Do not infer jurisdiction, activity or regulatory currency from a filename.

`--output` and `--json-output` are both required. Their parent directories must
already exist; destinations must be distinct, fresh and outside the installed
skill and owning code repository. Inputs are never overwritten. The command
prepares the complete packet before exclusive publication and removes its owned
outputs after ordinary publication failures. Oversized or inconsistent inputs
are rejected rather than producing a partial comparison.

The command always runs offline; `--offline` makes that intent explicit. It does
not automatically download references. Optional `--catalogue` selects one local
candidate catalogue for both reviews. Add `--table-a2-pdf` only for an already
supplied local Table A2 PDF under confirmed Alberta Crown/AER context. Missing or
unverified authority stays unresolved. Review CLI cache/refresh, drawing-text,
survey-geometry and dated-clause-workbook options are not comparison options.

Add `--annotated-pdf /path/to/private-job/revised-review.pdf` to create the standard
review copy of the revised original, with source-bound notes and a printable
index. This is **not a visual change overlay**. Text-change details remain in the
comparison report. Ambiguous/unlocated findings remain in the index rather than
receiving invented page locations. The PDF reproduces source plan content and
must stay private.

No Octopus checkout is needed for this text comparison, and no reconstruction
runs. Existing provider requirements still govern any separately requested
reconstruction. Use synthetic inputs only for development; do not publish real
originals, extracted text/coordinates, complete comparison records or review PDFs.

## Read the results

Checklist observations link by `requirement_id`, not transient PDF note labels
such as `R001` or `GLOBAL`. Both sides retain their own text, evidence/source
status, candidate count, source location or unlocated reason and citation.

| Finding state | Meaning within the supported text review |
|---|---|
| `SAME_OBSERVED_TEXT` | Both sides have a uniquely located observation with the same whitespace-normalized text. |
| `OBSERVED_TEXT_CHANGED` | Both sides have uniquely located observations with different text. |
| `NEWLY_OBSERVED_TEXT` | The revised side has a located observation where the baseline did not. |
| `PREVIOUS_OBSERVATION_NOT_FOUND` | The baseline observation has no located revised match; correction or removal is not established. |
| `AMBIGUOUS` | Repeated, conflicting or unreliable candidate evidence prevents a unique comparison. |
| `NOT_COMPARED` | The finding is visual/manual or neither side has a supported located observation. |

Ambiguity takes precedence over apparent equality. For example, changing a second
repeated label can leave a finding ambiguous while the separate literal text list
still records the changed groups. Replacing the expected company/legal label can
lose the scenario match; that is not a resolved comment.

Literal extracted-text groups have `ADDED`, `REMOVED` or `COUNT_CHANGED` status.
Only whitespace is normalized; case, numbers, punctuation and Unicode remain
literal. Counts include every retained repeated occurrence across the entire PDF.
Raw text and available locations are retained for each changed group's before
and after occurrences. There is no one-to-one edit or page pairing, fuzzy matching,
semantic interpretation, OCR, visual comparison or geometry comparison.

Extractor span splitting/merging can create inventory differences even when a
reader sees the same wording. Text movement or sheet reordering alone does not
change these group counts; located findings may separately record PDF location
changes. PDF point coordinates are not surveyed coordinates or proof that a
legal feature moved. A missing text layer, scanned/outlined text or linework-only
revision can evade the supported text comparison. An unchanged literal text
multiset does not establish unchanged checklist observations: moving existing
numbers between a selected Total cell and another label can change the observed
total without adding or removing a text group. Report those two channels
separately. An empty literal list means no literal groups or occurrence counts
changed; it must not conceal changed checklist evidence or claim equal plans.

Each finding retains its specific review instruction and corrective-review
action. Actual page rotation and page-box/display-frame information accompany
reliable source locations. Unknown frame information remains unknown rather
than establishing equality. These are PDF provenance facts, not sheet-size
deficiencies or proof that a surveyed feature moved.

## JSON comparison record

The Markdown report presents the evidence in normal reading order. Its companion
JSON is the reproducible comparison record, with these fields:

| Field | Contents |
|---|---|
| `schema_version`, `comparison_type` | `1`, `CROWN_PLAN_REVISION_TEXT_REVIEW`. |
| `overall_status`, `assessment_type` | `REVIEW_REQUIRED`, `REVISION_EVIDENCE_COMPARISON_NOT_COMPLIANCE`. |
| `baseline`, `revised` | Original `source_filename`, `source_sha256` and `pages`. |
| `identical_source_bytes` | Whether the two source SHA-256 values agree; no acceptance inference. |
| `review_context` | Common scenario values used to regenerate both reviews, including any CLI disposition/activity normalization. |
| `basis` | `engine_version` (`0.6.0`), `engine_sha256`, `scenario_sha256`, `catalogue_sha256`, named `references` with hashes, and `basis_sha256`. |
| `requirements` | Requirement IDs/summaries, review instruction/correction, six-state `comparison_status`, each side's observation/evidence/source status, `source_text`, candidate count, anchor/frame/reason, `location_changed` and citation. |
| `text_changes` | Stable-in-record `T00001`-style IDs, normalized text, literal status, counts, and all baseline/revised occurrences with raw text and source-location fields. |
| `summary` | Counts for all six finding states and `changed_text_groups`. |
| `baseline_review_summary`, `revised_review_summary` | Each regenerated review's checked/unchecked operations, needs attention, unresolved inputs and next steps. |
| `limitations` | Text scope, fragmentation, authority, manual/visual/geometry and no-auto-closure limits. |
| `revised_review_copy` | Present only with the optional PDF: `STANDARD_REVISED_REVIEW_NOT_CHANGE_OVERLAY`, filename/hash, source hash, finding-to-note IDs and located/unlocated counts. |

Scenario/catalogue fingerprints are hashes of canonical structured content; the
engine fingerprint covers its Python/JSON files. Named reference hashes identify
the supplied raw inputs, including the catalogue file and optional Table A2 PDF.
The basis hash covers the common basis fields. Preserve the exact private inputs
and results to reproduce a run; hashes bind bytes/content rather than establishing
source authenticity, current authority, applicability or compliance.

Limits are explicit: 100 MB, 100 pages and 200,000 extracted spans per PDF;
20,000 unique text groups per side; 10,000 changed groups; 8,192 characters per
retained text field; 20 MiB per JSON/Markdown artifact. Unknown/invalid source
locations retain null coordinates and a reason. Shared scenario/catalogue JSON
inputs retain the existing 2 MiB/4,096-character input-string limits. Structured
context, basis, definitions and summaries are additionally bounded to depth 12,
10,000 nodes, 200 object fields/list items and 524,288 aggregate text characters
per component; integers are at most 1,024 bits. Markdown validates the complete
model within depth 16 and its 20 MiB input/output budget. Candidate findings also
use the existing note planner's 200-note, 512-character title and 4,096-character
combined body/citation/action limits, whether or not the optional PDF is requested.
These are explicit rejection limits, not truncation rules.

Review visual elements, symbols,
signatures, raster content, geometry, source currency and professional acceptance
independently.
