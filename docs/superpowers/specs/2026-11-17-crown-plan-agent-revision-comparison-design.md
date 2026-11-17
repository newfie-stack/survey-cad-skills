# Crown Plan Agent 0.6: revision comparison

Status: proposed design, November 17, 2026. Implementation has not started.
Base: public `main` at `2112d98272eb2b6892d49ea20b47de574f67f66b` (0.5.0).

## Intent and agreed scope

Give the reviewer an original plan and its revised original, reuse one confirmed
application context, and explain what changed in their text and review evidence.
Link related review items by their finding IDs and show both source locations.
The user selected **comments and text changes first**, rather than adding a
visual drawing overlay to this version.

The result must make a drafting review easier without confusing a changed label
with a corrected deficiency. It must keep missing, ambiguous and unexecuted checks
visible. Original plans, extracted data and complete comparison results stay
private; development and public acceptance examples use invented plans only.

## Approaches

1. **Checklist observations plus literal text differences — selected.** Run the
   existing review on both PDFs under the same basis. Compare matching finding
   IDs and separately list added/removed text occurrences. This links review
   comments while still exposing unexpected names or labels that no longer
   match the supplied scenario. It reuses the existing extraction and source
   gates. It does not detect every graphical change.
2. **Checklist observations only — rejected as too narrow.** A changed applicant
   name can make an expected-value match disappear. Comparing only that match
   would omit the replacement text elsewhere in the drawing.
3. **Text comparison plus registered visual overlays — deferred.** This could
   reveal linework/image changes but adds page registration, rendering and
   layout-noise decisions. The user chose to leave this out of the first version.

The remaining interface, limit and module choices below are implementation
proposals, not additional user decisions already obtained.

## Inputs and common review basis

- Accept two explicitly ordered original PDFs: baseline and revised. Never infer
  order from filenames, metadata dates or filesystem times. Renamed identical
  bytes and the same file supplied twice are valid, clearly identified cases.
- Reuse one confirmed scenario and one catalogue for both reviews. Optional
  locally supplied Table A2 rows must come from the same bounded source snapshot.
  No automatic source download or refresh is introduced.
- Record source names, SHA-256, page counts, comparison schema/engine version,
  and a fingerprint of the shared scenario, catalogue and supplied references.
  Use deterministic canonical JSON for structured-input fingerprints and raw
  byte hashes for PDFs. Preserve omitted versus explicitly blank facts.
- Both reviews are regenerated with the same current engine and basis. This is
  not a replay of a historical review under its old engine or old regulations.
  Arbitrary saved Markdown reports are not accepted as structured baselines.
- Changes to application context, catalogue definitions, reference editions or
  manual facts are not drawing corrections. A future saved-report comparison
  must establish basis equality or report that it cannot compare those results.
- Do not reuse one survey-coordinate dataset or plan-specific clause-fact set as
  evidence for both revisions. Automated comparison in this release covers the
  supported candidate text checks. Geometry, manual visual checks and dated
  clause-workbook decisions remain explicitly not compared.
- Source popup annotations and handwritten/custom comments are not interpreted
  or imported as accepted review decisions. Existing Crown review items are
  regenerated and linked by requirement ID. Generated labels such as `R001` and
  `GLOBAL-001` are local sequence labels, not permanent comment identities.

Require original PDFs. Known Crown Plan Agent review copies, with tool comment
metadata or recognizable appended review-index pages, must be rejected with an
instruction to use the originals. Detection cannot identify every third-party
annotated copy; explain that input requirement rather than promise universal
commentary removal. Annotation popup bodies are not plan text evidence.

## What is compared

### Review observations

Match candidate entries by `requirement_id` under the common catalogue definition.
Never match by table order, PDF note number or similar prose. Retain exact raw
source text, displayed observation, evidence/source status, candidate counts,
citations and separately validated baseline/revised page references.

Use distinct comparison states, separate from regulatory/evidence status:

| Comparison state | Meaning |
|---|---|
| SAME_OBSERVED_TEXT | Both sides have uniquely located comparable candidates with the same normalized text |
| OBSERVED_TEXT_CHANGED | Both sides have uniquely located comparable candidates with different text |
| NEWLY_OBSERVED_TEXT | A uniquely located candidate is now observed where no comparable earlier candidate was recorded |
| PREVIOUS_OBSERVATION_NOT_FOUND | An earlier unique candidate is no longer matched; this does not establish removal or correction |
| AMBIGUOUS | Repeated, conflicting or unreliable evidence prevents a unique comparison |
| NOT_COMPARED | Visual/manual/unsupported or insufficient evidence leaves the check unassessed |

Ambiguity has precedence over apparent equality. The current ledger retains
only the first match plus count/pages; two repeated matches must not be called
unchanged just because their first text and count agree. Conflicting area totals
stay unresolved. A lost text layer or a new scan must not close old comments.

Keep page/bbox/orientation/frame differences in a separate location-change field.
The same text on a different page is not a text edit, and a changed PDF coordinate
does not prove a surveyed feature moved. Baseline drawing pages, revised drawing
pages and regulatory publication pages must remain separately labelled.

All current regulatory findings remain `REVIEW_REQUIRED`. The comparison never
automatically assigns fixed, approved, compliant or accepted states. Reviewer
closure decisions and long-term correction tracking are a later feature.

### Literal document text

Compare a multiset of extracted text groups, retaining occurrence counts and
each side's actual page/bbox provenance. Normalize whitespace only; retain case,
numbers, punctuation and Unicode, with raw extracted text available in the record.
Sorting and traversal order must be deterministic.

List added/removed text or changed occurrence counts independently of checklist
matches. Do not invent before/after edit pairs based solely on nearby coordinates
or text similarity. A replacement company name can therefore appear as an old
text occurrence no longer found plus a new text occurrence, while its checklist
row correctly says the prior expected match was not found.

Text movement, page insertion and page reordering must not alone become text
additions/removals. Do not pair sheets by ordinal position. Formatting that splits
or merges extracted spans may create literal inventory differences; label those
as extracted-text differences requiring review, rather than semantic edits.
Unmatched or repeated occurrences do not receive a guessed one-to-one pairing.

Text results do not assess changed linework, symbols, signatures, raster content,
legal boundaries or geometry. For different source bytes with identical compared
text, say **no changes found in the supported text comparison**, not that the
plans are identical. Exact byte equality may be reported separately as a hash
fact; it does not establish regulatory acceptance.

## Reviewer workflow and artifacts

In ChatGPT, reuse authorized files and confirmed context. Ask only for genuinely
missing inputs, with the baseline/revised order made explicit. Without original
PDF bytes and execution, explain the available manual comparison and do not
claim the engine or export ran. Readable results lead with changed observations,
newly observed text, previous observations not found, and unresolved work.

Proposed local interface, from the complete skill folder:

```bash
python engine/revision_cli.py /private/job/old-plan.pdf /private/job/new-plan.pdf \
  --scenario /private/job/scenario.json \
  --output /private/job/revision-comparison.md \
  --json-output /private/job/revision-comparison.json
```

Paths are illustrative and must already have private parent directories. The
normal 0.5 review command remains available and compatible.

The Markdown report includes a short summary, an explicit comparison scope,
common review basis, per-finding before/after evidence and actions, literal text
differences, page references, citations and unassessed work. The bounded JSON
record retains the same facts and input fingerprints for reproducibility. Render
source strings literally, including HTML/Markdown-like annotations; neither
format should turn extracted text into active images or links.

An optional `--annotated-pdf` may produce the **standard review copy of the revised
original**, reusing the 0.5 source-bound renderer. Label it accurately: the
comparison report contains the text-difference list; the standard PDF contains
the revised review's comments and printable notes. This version does not add a
visual overlay, annotate every raw text difference, or invent a revised anchor
for removed baseline evidence. Show current PDF note IDs only when obtained
from its actual emitted manifest; use requirement IDs for cross-revision links.

The optional copy preserves current source pages, annotations, links and widgets.
Keep both original PDFs, extracted observations and all derived artifacts out of
GitHub and plugin packages, even when company names in prose are fictional.

## Implementation boundaries

- Reuse `pdf_source`, `pdf_inspector`, `review_inventory`, current applicability
  and evidence checks, source-location validation and `publish_artifacts`.
- Add comparison orchestration, a bounded deterministic comparison model,
  Markdown rendering, the offline CLI and a runtime-aware reference guide.
  Function/module names beyond the proposed CLI are the implementer's call.
- Normalize scenario aliases consistently with the existing CLI. Refactor only
  shared preparation needed to avoid divergent review behavior; retain existing
  public call signatures, default output and exception compatibility.
- Keep supplied reference currency unverified unless the existing independent
  source gate establishes it. File hashes bind bytes, not current authority or
  an authenticated reviewer. Never label an arbitrary reference as a verified
  edition just because it was supplied locally.
- Do not add dependencies, a hosted service, a parallel COGO calculator or an
  Octopus invocation. No reconstruction is needed for this text-only comparison.

## Source binding, bounds and publication

Read bounded immutable source snapshots and verify each regenerated report is
bound to its corresponding inventory. Revalidate actual source spans before
locating optional PDF comments. Recheck both source files and shared file inputs
before publication; source replacement cancels the whole packet.

Preflight all destinations before extraction. Both sources and every output
must be distinct where writing could overwrite an input; output paths must be
fresh and outside the installed skill and owning code repository. Reject existing
files, destination symlinks, aliases and missing parent directories. Prepare all
requested artifacts, then publish without replacement. On ordinary failure,
remove only outputs created by that call and preserve competing files. Retain
the documented hard-link/filesystem and crash-recovery limits.

Retain existing per-PDF limits of 100 MB, 100 pages and 200,000 spans. Proposed
additional comparison limits are 20,000 unique text groups per side, 10,000
changed groups, 8,192 characters per retained text field and 20 MiB per serialized
JSON/Markdown artifact. The implementer may choose stricter bounded internals
and must document them. Reject overflow explicitly; do not silently drop changes
or observations. Optional standard PDF note/index limits continue to apply.

## Verification and release

Use synthetic PDFs only. Freeze expected outcomes independently of the engine.
Cover identical/renamed bytes, metadata-only rewrite, unique scale/area edits,
added/lost expected labels, unexpected replacement names, repeated labels whose
second match changes, conflicting totals, lost/scanned text, span fragmentation,
location-only changes, inserted/reordered pages, rotation/CropBox/UserUnit,
graphical-only changes, generated review-copy rejection, changed shared basis,
source replacement, hostile report text, size bounds, collision/symlink/input
aliases and multi-output rollback. Distinguish extraction artifacts from meaning.

Verify current source preservation and optional PDF contents, independent package
execution with networking denied, package/source parity and unchanged normal
review behavior. Run the existing suite, compilation and repository-root smoke,
plus meaningful new comparison regressions and an independent code review.
The baseline has 502 tests, including two optional source-PDF skips.

After design approval and implementation acceptance, publish the reviewed 0.6
preview through the existing public repository's PR/CI workflow and update the
existing private ChatGPT plugin. Preserve prompts, colours, icons and audience.
Record exact reviewed, public, package and plugin identities. This feature does
not complete current-source, professional, complete-geometry or mobile-runtime
acceptance gates.
