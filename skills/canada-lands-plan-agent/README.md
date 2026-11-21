# Canada Lands Plan Agent — development preview

Independent Canada Lands survey/land-interest plan-review skill focused first on **First Nation reserve oil-and-gas drawings administered by IOGC**. It complements Alberta's Crown Plan Agent; it does not use PLAR Table A2 as a default rule source.

## Typical tasks
- Explain which CLSR and LTO numbers refer to which survey documents and flag unresolved agreement status.
- Review an existing wellsite, pipeline ROW, access road and road allowance without collapsing different rights into one boundary.
- Triage off-lease TWS for remediation: possible Surface Permit vs formal lease amendment, without claiming approval.
- Review IOGC Application Survey Plan vs CLSR survey plan vs temporary Surface Permit sketch.
- Check whether an Incidental Activities table applies and whether hectare totals are internally consistent.
- Review draft PDFs and CAD-derived exports for observable omissions with a citation-based issue register.
- Flag approvals and disturbance/clearing issues for the CLS, First Nation and IOGC to resolve.

## Use
Read [SKILL.md](SKILL.md), [sources](references/source-hierarchy.md), [route matrix](references/route-matrix.md) and [review checklist](references/review-checklist.md).

For optional **synthetic-only** CLI smoke tests from repository root:

```sh
python -m unittest discover -s skills/canada-lands-plan-agent/tests -v
```

For private offline JSON routing (no drawing parsing):

```sh
python skills/canada-lands-plan-agent/engine/triage.py /path/to/private-case.json
```

Example schema, with *fictional* information only:

```json
{
  "land_class": "first_nation_reserve",
  "iogc_confirmed": true,
  "purpose": "off_lease_remediation",
  "document_type": "surface_permit_sketch",
  "workspace_area": {
    "total_ha": "0.4800",
    "within_row_ha": "0.0600",
    "outside_row_ha": "0.4200"
  }
}
```

No external dependencies. Test values are synthetic bookkeeping quantities, **not a real site or a survey tolerance**. The helper only suggests a process and checks independently supplied area arithmetic; it cannot read plans, validate source currency or decide legal permissions.

**Not production accepted:** additional federal/region/First Nation scopes, parser automation, live official-source change detection and independent real-world validation remain future work. Do not upload confidential jobs to GitHub.
