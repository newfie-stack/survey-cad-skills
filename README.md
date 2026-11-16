# Survey & CAD Skills

Open-source, general-purpose skills for survey evidence interpretation, cadastral reasoning, registered-plan reconstruction and deterministic CAD geometry.

## Skills
- [Registered Plan Reconstruction](skills/registered-plan-reconstruction/SKILL.md)
- [Survey Plan Evidence Interpretation](skills/survey-plan-evidence-interpretation/SKILL.md)
- [Survey Boundary Topology](skills/survey-boundary-topology/SKILL.md)
- [Survey DXF & CAD Construction](skills/survey-dxf-cad-construction/SKILL.md)
- [Alberta Cadastral Reasoning](skills/alberta-cadastral-reasoning/SKILL.md)
- [Survey Evidence Plotting & Labeling](skills/survey-evidence-plotting-labeling/SKILL.md)
- [Field Note Observation Extraction](skills/field-note-observation-extraction/SKILL.md)

- [Shapefile Validator](skills/shapefile-validator/SKILL.md)
- [Quarter Completeness & Encumbrance Research](skills/quarter-completeness-encumbrance/SKILL.md)
- [Counsel — General Decision Review](skills/counsel/SKILL.md) (general-purpose AI advisory skill)

- [AER OneStop Guide](skills/aer-onestop-guide/SKILL.md) — public-source regulatory research only
- [Crown Plan Agent](skills/crown-plan-agent/SKILL.md) — development preview with summary-first evidence reports, private marked-up PDF copies, targeted intake questions, dated requirement workbooks and an Octopus reconstruction handoff
- [CAD/GIS Object Inspection](skills/cad-gis-object-inspection/SKILL.md)
- [Skill Evaluation & Regression Testing](skills/skill-evaluation-regression/SKILL.md)
- [Interactive Artifact Review](skills/interactive-artifact-review/SKILL.md)
- [Code Review](skills/code-review/SKILL.md)
- [Drafting Agent Pressure Test](skills/drafting-agent-pressure-test/SKILL.md)
- [Checking Station Review](skills/checking-station-review/SKILL.md)

## Intended use
Most skills provide workflow guidance and synthetic regression specifications. Crown Plan Agent also includes an executable offline review engine and synthetic tests; its [setup guide](skills/crown-plan-agent/engine/README.md) explains installation. Reconstruction requires separately available, reviewed Octopus code, which is not bundled here. Verify control, bearing basis, source evidence, topology, closure, area and CAD outputs. Professional survey judgment and current regulatory requirements take precedence; the development preview does not establish production or regulatory acceptance.

## Privacy and contributions
No actual survey-plan files, client information, private coordinates, employer procedures or proprietary source materials are included. Do not contribute them. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## Installation
This repository includes a Claude plugin manifest under `.claude-plugin/`. Consult your host's current plugin installation documentation. Individual `SKILL.md` files may also be used as standalone guidance where supported.

Crown Plan Agent also has a
[reproducible ChatGPT package](skills/crown-plan-agent/packaging/chatgpt/README.md)
built from the same skill instructions. The package supplies instructions and
supporting source; automated operations depend on the host's available tools.

## License
Original repository contributions are MIT licensed. See [LICENSE](LICENSE).
Crown Plan Agent installs PyMuPDF separately; its AGPL/commercial terms and any
external reconstruction provider's terms remain separate. See the skill's
[distribution notes](skills/crown-plan-agent/RELEASE_NOTES.md#distribution-boundary).
