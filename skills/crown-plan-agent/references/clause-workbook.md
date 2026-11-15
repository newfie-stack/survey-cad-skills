# Dated-source clause workbook

Use the workbook to organize manual review against one explicitly selected
publication and edition. It keeps applicability questions, source citations,
exemptions and replacement requirements visible beside the existing PDF evidence
report. It does not establish current authority, inspect every drawing element or
produce a compliance verdict.

The supplied [dated catalogue](../engine/dated_clause_catalogue.json) represents
the May 30, 2024 *Content Requirements for Survey Plans and Sketches for
Dispositions on Crown Lands*. It contains **144 clause paths, 323 atomic manual
review checks containing 326 question prompts, 105 fact definitions and four
override controllers**. These are counts of the selected data, not 323 automated
compliance checks or proof that every current obligation has been implemented.
Consult the [source verification record](../SOURCE_VERIFICATION.md) separately.

All workbook results remain `REVIEW_REQUIRED`, with source status
`UNVERIFIED_CURRENT`. Even a fully populated fact file or a matching inventory
cannot promote the workbook to `PASS`, `FAIL` or verified current authority.

## Run the optional workbook

Run from the complete `crown-plan-agent` folder, with its Python dependencies
installed. Keep the authorized PDF, scenario, facts and report in a private
working folder outside both the repository and the installed skill. Replace
`/path/to/private-review` below with that directory; it is an illustrative
placeholder, not a supplied project path.

```bash
python engine/review_cli.py /path/to/private-review/plan.pdf \
  --scenario /path/to/private-review/scenario.json \
  --clause-catalogue engine/dated_clause_catalogue.json \
  --clause-facts /path/to/private-review/clause-facts.json \
  --clause-inventory engine/requirement_coverage.json \
  --reference-cache /path/to/private-review/empty-cache \
  --offline --output /path/to/private-review/review-with-clauses.md
```

Use a new output filename; existing reports are not overwritten. This command
adds a **Dated-source clause workbook** section. The ordinary observation report
and Table A2 checks remain separate. The workbook needs no regulator PDF to
prepare its manual questions; Table A2 verification still requests an appropriate
local source when none is supplied or cached. `--offline` is the default and
does not initiate a download. The example uses an empty reference-cache path.

| Option | Meaning |
| --- | --- |
| `--clause-catalogue PATH` | Explicitly selects and enables the workbook. There is no inferred default. |
| `--clause-facts PATH` | Supplies typed applicability facts and their provenance. Omit it to start with an empty fact map and inspect unresolved questions. |
| `--clause-inventory PATH` | Explicitly supplies a matching dated clause universe for coverage accounting. |
| `--catalogue PATH` | Selects the existing observation checklist; it does not enable or select a clause workbook. |

The facts and inventory options are rejected without `--clause-catalogue`.
Matching filenames, observation IDs or citation titles never activate a workbook
or bind observations automatically.

## Inspect definitions before supplying facts

Use the same scenario contract as the PDF review: declare `land_class`, regulator,
disposition, stage and proposed plan type. Crown scope is a declaration requiring
supporting evidence, not an inference from an LOC code or unsurveyed-territory
annotation. Mixed land requires the explicitly identified Alberta Crown component.

Open the catalogue's `facts` list to inspect each ID, scalar type, unit, bounds,
allowed values, purpose and provenance requirement. For example, from the skill
folder:

```bash
python - <<'PY'
import json
from pathlib import Path

catalogue = json.loads(Path("engine/dated_clause_catalogue.json").read_text(encoding="utf-8"))
for definition in catalogue["facts"]:
    if definition["id"] in {"has_details", "existing_length_m"}:
        print(json.dumps(definition, indent=2))
PY
```

The following is an **invented format example**, not evidence for a real plan:

```json
{
  "has_details": {
    "value": false,
    "provenance": {
      "source_id": "INVENTED-PLAN-001",
      "locator": "Page 1, independently reviewed invented view inventory"
    }
  },
  "existing_length_m": {
    "value": null,
    "provenance": null
  }
}
```

Here `false` asserts that the invented plan has no details. `null` says the
existing length is unknown; it does not assert zero length or make a condition
false. Do not fill the other definitions with guessed values merely to remove
blockers. Supply the facts relevant to the review and retain genuine unknowns.

| Fact type | Accepted value |
| --- | --- |
| Boolean | JSON `true` or `false`; strings such as `"false"` are not converted. |
| Integer | An integer JSON number within the declared domain; booleans are excluded. |
| Decimal | A plain decimal string such as `"7000.00"`, within the declared bounds; exponent notation, commas, NaN, infinity and unquoted numeric scalars are invalid. |
| Enum | An exact member of the definition's `allowed_values` list. |

Each supplied record has exactly `value` and `provenance`. Provenance is either
`null` or an object with nonempty `source_id` and `locator` strings identifying
the private evidence register. A provenance entry records an assertion and where
to review it; the engine does not independently verify its truth. A
`manual_applicability` fact requires provenance for the recorded interpretation
or direction, rather than inferring it from a drawing keyword.

For a fact used by a condition, the primary unresolved reason is:

1. `MISSING_FACT` when the ID was omitted.
2. `UNKNOWN_FACT` when its value is explicitly `null`.
3. `INVALID_FACT_VALUE` when the scalar, domain or range is wrong.
4. `MISSING_PROVENANCE` when a valid value lacks required provenance.

These reasons remain distinct. Unknown IDs, malformed record keys and malformed
provenance are input errors, including for outside-scope scenarios. A known false
branch may resolve a condition without another missing fact becoming a blocker;
the nonblocking issue remains in its trace.

## Read selections, questions and overrides

Explicit private, municipal, federal and other excluded land yields `OUT_OF_SCOPE`.
Missing or invalid core context leaves every path `UNRESOLVED_APPLICABILITY`.
Those gates stop condition, override and evidence selection; they do not bypass
basic input validation or silently select conventional-plan rules.

Within resolved scope, inspect each clause's citation, condition trace and atomic
check selection:

| Selection | How to use it |
| --- | --- |
| `CANDIDATE_REVIEW` | Answer the selected manual review requests using the relevant source and artifacts. |
| `UNRESOLVED_APPLICABILITY` | Resolve the named fact/context/override blockers; the questions remain pending, not active deficiency findings. |
| `NOT_SELECTED_FOR_REVIEW` | The condition or a cited override did not select this path. This is not a normative `NOT_APPLICABLE` verdict. |
| `OUT_OF_SCOPE` | The declared land scope excludes the Crown review paths. |

Required checks, optional or permitted guidance, and exemption controls have
separate counts and labels. For example, the dated detail-view clause separates
its required scale review from an optional scale bar; absence of that optional
bar does not become a missing mandatory element. Selected manual questions are
not automatically satisfied by a nearby text span.

The supplied catalogue has these four controllers:

| Dated clause | Effect when its applicability is established |
| --- | --- |
| `3.6.1.1` | Excludes the compiled plan's ordinary heading, `3.2.1` monumentation and `3.3` amendment paths. It does not exempt unrelated general content. |
| `3.6.1.3` | Replaces the ordinary `3.1.2` declaration path with compiled Appendix D declaration/signature review. |
| `4.3.1.5` | Excludes the eight `1.3.6.4` timber-damage-area breakdown checks for the cited SME/RME non-peat branch. |
| `4.3.2.3` | Excludes the same eight `1.3.6.4` timber-damage-area breakdown checks for the cited SME/RME peat-related branch. |

Those two SME/RME controllers do not remove the independent area requirements
under `1.3.6.2` and `1.3.6.3`.

Controller truth is determined before artifact review. Missing replacement
evidence never restores the old requirement. An unknown controller can keep a
target unresolved; competing possible or established overrides are reported as
`POTENTIAL_OVERRIDE_CONFLICT` or `CONFLICTING_OVERRIDES`, with their citations.
Resolve those source/applicability questions rather than choosing the more
convenient route.

## Coverage and observation limits

Without an explicit inventory, `coverage.universe_status` is `NOT_SUPPLIED` and
the expected clause count and unmapped IDs are unknown. The catalogue's own path
count is not an independently established source universe.

With `engine/requirement_coverage.json` explicitly supplied for the dated
catalogue, the workbook checks the source title, version, page count and every
catalogued section/page before reporting `MATCHED` and listing inventory IDs
without a path. A mismatch is an error. Even zero unmapped paths leaves
`atomic_obligation_completeness: NOT_ASSESSED`: path coverage does not prove
complete interpretation of every bullet, exception or external standard.

The CLI supplies no automatic observation availability to this workbook. The
existing PDF checklist may contain an observation while the related workbook
question still requires manual review. Programmatic callers may explicitly
declare available IDs for a catalogue's supported adapter links. Those are
references only: the workbook executes no adapter, reads no drawing, constructs
no geometry and confirms no requirement satisfaction.

## Programmatic use

From the skill folder, after preparing authorized local scenario/fact files and
replacing the illustrative private directory:

```python
from pathlib import Path
import sys

sys.path.insert(0, str(Path("engine").resolve()))
from clause_schema import load_bounded_json, load_clause_catalogue
from clause_workbook import prepare_clause_workbook
from clause_workbook_markdown import render_clause_workbook

catalogue = load_clause_catalogue("engine/dated_clause_catalogue.json")
scenario = load_bounded_json("/path/to/private-review/scenario.json")
facts = load_bounded_json("/path/to/private-review/clause-facts.json")
inventory = load_bounded_json("engine/requirement_coverage.json")
workbook = prepare_clause_workbook(
    catalogue, scenario, facts,
    available_observation_ids=(),
    coverage_inventory=inventory,
)
print(render_clause_workbook(workbook))
```

`prepare_clause_workbook` takes the explicitly loaded catalogue and performs no
PDF/CAD inspection, adapter execution, network access or file mutation.
`render_clause_workbook` validates nested statuses, selections, traces, references
and counts before rendering. The loaders read bounded local JSON. These APIs
accept no normative verified status; current-source, professional and actual
artifact acceptance remain separate decisions. Follow the
[geometry handoff](geometry-handoff.md) when reconstruction evidence is needed.
