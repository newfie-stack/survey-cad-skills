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
