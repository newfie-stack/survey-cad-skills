# Assisted review in ChatGPT

Use this guide with the main skill's authority, evidence and privacy gates.
The same instructions serve ChatGPT and a copied Codex skill; available tools
determine which operations can actually run.

## Start from the existing context

Reuse the plan, connected-file link and review facts already provided in the
conversation. Do not ask the user to attach the same file or repeat an answer
that is still applicable. Resolve only an actual access failure, ambiguous file
identity or conflicting declaration. Keep original inputs and generated project
artifacts outside public repositories and the installed skill folder.

Check whether document inspection, Python execution and the reviewed Octopus
provider are available. With text or visual access alone, provide an assisted
manual review and say which automated operations did not run. Supporting Python
files in a plugin are not an execution server. With Python, use the supplied
engine only after its dependencies and file access are available. Reconstruction
uses the [Octopus provider contract](octopus-reconstruction.md).

## Read the complete titleblock from top to bottom

Read the entire titleblock on each reviewed sheet, including the complete Notes
frame, before selecting QC regions, asking for location/context or reporting
spatial information as missing. Use the actual page image at readable resolution.
Locate the whole frame in the sheet overview, then inspect adjoining enlarged
views as needed to cover it completely. Follow its visual order from top to
bottom; for columns, read each logical column in order without skipping the
lower entries. Extracted PDF span order or a few keyword matches do not establish
that the frame was read in full.

Capture every titleblock field and note in a private source-located reading
record. Include the heading and legal location, applicant/operator identities,
plan/drawing identifiers, dates and revisions, scales, legends and declarations
where present. Read every Notes entry, including those below the initially
relevant location note. Retain exact wording and page/frame or region locators
for information used in a finding; do not publish private transcriptions.

Use the frame to establish the plan's stated location and spatial basis:
legal description or ATS location, coordinate values and their named roles,
datum, projection/CRS and zone, units, bearing reference, grid/ground statements,
scale/combined factors and control references where supplied. Keep the printed
statements distinct and compare them with relevant drawing annotations and
existing job evidence. Notes can supply information absent from a separate
coordinate file. Ask only for facts still unresolved after this reading.

Record conflicting statements with both locators. If the frame is cropped,
illegible or inaccessible, identify the unread portions and obtain a fuller or
clearer view where available; otherwise report incomplete reading. Never claim
whole-frame coverage or a missing note from a partial crop or incomplete text
extraction. A printed CRS or location statement is observed plan evidence; it
does not by itself verify ownership, control, alignment or coordinate provenance.
Preserve scale-factor notes unchanged under the Octopus provider contract.

This intake also applies to finished-plan QC without reconstruction. Read the
whole frame before narrowing the check regions, and report which parts were
actually read. Keep selected mechanical checks and visual observations explicit.

## Orient the main plan and locate reference points

After reading the full titleblock and Notes frame, inspect the main plan view,
normally to the left of the titleblock. Locate the actual main view on other
layouts; do not use an inset or a fixed page region as its substitute.

Establish the main view's north arrow and the Notes' stated bearing reference,
using the [visual symbol procedure](#visually-check-the-north-arrow-and-scale-bar).
Orient the reading view to north-up. In this north-up reading frame, survey
azimuth is clockwise from north: up/N = 0 degrees, right/E = 90 degrees,
down/S = 180 degrees and left/W = 270 degrees. Retain whether the source states
grid, true or assumed north. A tilted arrow or rotated sheet does not make the
original page top north. CAD's default angle convention and PDF page axes are
separate; preserve source bearings, coordinates and original page locators.
If orientation is unresolved, record that limitation before assigning quarters.

Use the oriented section and quarter-line fabric, section identifiers, legal
labels and township/range/meridian context to identify NE, SE, SW and NW quarters.
Their relative positions in a reliable north-up section are supporting evidence;
the four page quadrants or a nearby label alone are insufficient. Retain
ambiguity where the fabric is rotated, schematic, incomplete or conflicting.

Look for **RP = Reference Point**, with the circled RP marking described by the
supplied drafting convention. Inspect its symbol, RP label/identifier and nearby
coordinates, bearing/distance ties and evidence descriptions together. Distinguish
unrelated circles, legend samples and other point symbols. Record each candidate
with its page/view/region, exact label, point role and supported ties; retain
uncertain symbol-to-label or tie associations.

For CAD drawings using the supplied convention, inspect layer **`35`** for RP
entities and their associated blocks/text, and record the actual layer evidence.
Layer 35 is a drafting lookup clue, not a universal regulatory rule or a command
to relayer other evidence. A PDF can flatten or omit CAD layers: use visible RP
evidence when layers are unavailable and do not claim a layer inspection ran.
Different or missing layer names alone do not establish that RPs are absent.

Carry source-supported RP observations and ties into the private evidence/control
register for geometry work when relevant. A circled label, layer membership or
nearby coordinate text does not independently establish the point's coordinate
role, accepted control, quarter-corner identity or spatial alignment. Continue
supported finished-plan checks with unresolved items recorded; this reading
sequence does not require reconstruction or execute Octopus.

## Visually check the north arrow and scale bar

Run this pass on plan sheets when the host can see plan imagery. Use the
authorized original PDF's rendered pages or the supplied sheet images. If the
host only extracts PDF text, use local PDF rendering and image inspection when
available. Render a whole-sheet overview first, then zoom or render crops as
needed at readable resolution. Keep renders of private plans private. Never
report a visual check based on the extracted text, a guessed sheet location,
or a verbal description of an image you could not inspect.

- **North arrow:** Look for a directional arrow with identifying evidence such
  as an N, north label, or a recognizable compass symbol. Tie it to the main
  view it orients. Watch for leader arrows, flow arrows, legend samples, and
  arrows confined to insets. If visible, record the indicated direction on the
  sheet and the region where it appears.
- **Graphical scale bar:** Look for a drawn scale with divisions or tick marks
  and distance labels or units, including near the title block or main view.
  Record the readable divisions and units. A numeric ratio, line sample, or
  scale bar from an inset alone is insufficient evidence for the main view.
  Verify plotted scale separately when requested.

For each item, cite the page number, view (main, detail, or inset), and a
plain-language location. Use **Observed** for a clear match, **Not found after
visual review** only after inspecting the entire relevant sheet or view at
sufficient resolution, and **Unable to verify** when the image is unavailable,
cropped, illegible, or ambiguous. A narrow crop can establish presence but
cannot establish sheet-wide absence. Record a detail-only symbol in its own
view and keep the main-view status tied to the actual coverage.

Report these as drawing observations. Apply a requirement only after its source
and applicability are verified. Do not replace the offline CLI's mechanical
result with an AI observation. Include the visual finding alongside the CLI
result in the user-facing review.

## Ask for the information that changes the review

Collect missing facts into one concise question, using familiar words. Preserve
unknowns rather than supplying convenient defaults. Explain why the answer
matters. A disposition code does not identify its regulator, and unsurveyed land
does not independently establish Crown ownership.

- For an initial AER comparison, establish the exact application purpose and
  subactivity. An omitted subactivity is unknown; an explicitly empty string is
  usable only for a source row whose activity is genuinely blank.
- For an amendment, ask for the existing plan on file when its type is unknown.
  Request length or affected-quarter information only if it can change the
  unresolved route. At exactly 6,500 m, preserve the applicable direction gate;
  do not ask the user to change an already supplied measurement.
- For a renewal, establish whether the disposition changed, then the applicable
  plan-of-record and exact source-row facts. A changed disposition follows its
  amendment review; do not imply renewal eligibility.
- For mixed land, identify the Crown component. For out-of-scope land, explain
  the scope limit instead of requesting irrelevant Crown-only inputs.

Use the engine's `review_summary.input_requests` as intake guidance when
available. Its `context_question` groups known missing facts. It is not a reason
to repeat facts the conversation already resolves or to ask every optional
question in the dated workbook.

## Lead with a usable result

Begin with a short review status and four sections:

1. **What was checked:** name only the inspections or calculations that ran.
2. **What needs attention:** explain missing information, conflicting evidence
   and numerical differences in normal language, with source/page references
   where supported. A text element not found is not a proven missing feature.
3. **What remains unchecked:** list unavailable visual evidence, unverified
   current sources, blocked geometry or unexecuted Octopus work.
4. **Next steps:** give specific actions in priority order. Keep a current-source
   verification task once, rather than repeating it for every candidate clause.

Keep the full evidence ledger, citations, conditions and uncertainty below the
summary or available on request. Do not bury critical blockers in route codes.
An observed label, matching Table A2 row or successful numerical check is not a
regulatory PASS. Do not turn an invented fixture into a real approved example.

Distinguish review of supplied inventory from an executed PDF extraction.
Unsupported or unverified geometry may have been inspected without any boundary
measurements being computed. An unexecuted handoff is not reconstruction. A
cropped or pre-trimmed PDF does not by itself establish the original sheet size.

## Example request

> Review the plan I provided. Use the context already in this conversation,
> explain what needs attention in normal language, and ask together for any
> information you still need. Keep my PDF and project drawings out of GitHub.
