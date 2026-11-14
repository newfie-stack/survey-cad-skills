---
name: survey-boundary-topology
description: Resolve survey boundary connections, feature membership, sides and legal terminal relationships.
version: 1.0.0
---
# Survey Intent & Boundary Topology
Before COGO, assign each observation to a feature and role: SUBJECT_BOUNDARY, EXISTING_BOUNDARY, TIE, CONTROL, TRAVERSE, OFFSET, CAP, TERMINAL or UNRESOLVED. Use stable side identifiers until direction is established. Require supported endpoint identity and same-feature/same-side membership for chaining. Keep existing surveyed boundaries and physical tracks distinct from new survey limits. A right-of-way may terminate at an established surveyed boundary, not merely the nearest line. Found monuments and calculated points carry different evidence states; neither alone determines legal intent. Preserve disconnected evidence rather than inserting an unsupported segment. Record each proposed edge's source, endpoint identity, role and review state.

## Supporting references
- [edge role decision md](references/edge-role-decision.md)

Read the applicable supporting reference before carrying out the corresponding technical workflow. Do not assume a regulatory rule is current without checking the official source.
- [terminal and feature roles md](references/terminal-and-feature-roles.md)

## Feature-identity gate
Before constructing subject boundaries, read [feature topology and lineweight](../registered-plan-reconstruction/references/feature-topology-and-lineweight.md). Verify subject plan identity, same-side continuity and endpoint identity independently; do not chain an existing corridor into the new subject.
