# Crown Plan Agent — Test 2: synthetic defect detection

## Status
Synthetic fixture and offline test harness. These tests **do not inspect a real PDF** and do not establish compliance with current Alberta requirements.

## Synthetic defects
The fictional survey plan intentionally lacks a legal description and north arrow. The synthetic input has no geometry area, CAD/DXF, shapefile, or monument evidence. Current AER Table A2 plan-type applicability and regulator bulletins are marked unverified.

## Expected outcomes
- Detect the two deliberately absent plan elements as **fixture defects**.
- Preserve REVIEW_REQUIRED for area, monument evidence, declaration, GIS schema and current plan-type authority.
- Reject a fixture that claims to have no plan artifact.
- Ensure the fixture contains no real plan, employer or client identifiers.

## Limitations
The offline harness checks a **structured synthetic observation record**, not image extraction or actual regulatory source clause verification. A true end-to-end Test 2 still requires a generated synthetic PDF and a separate evaluator that independently extracts observations, verifies current requirements, and compares findings with this frozen answer key.

Run: `python -m unittest discover -s skills/crown-plan-agent/tests -p 'test_*.py' -v`

## Scope of this historical report

The limitations above describe the original structured `synthetic_plan_test2.json` fixture only. The current suite also includes generated-PDF extraction and PDF-to-report integration tests, plus a standalone `smoke_review.py` example. Their verification status is tracked in the [master checklist](../MASTER_CHECKLIST.md). Those synthetic PDF tests do not provide real-plan validation or current regulatory authority verification.

## Execution evidence — November 14, 2026
A local mirror of the fixture's classifier was executed with Python 3. Three assertions passed: expected synthetic classifications, missing-plan rejection, and preservation of regulatory uncertainty. **The GitHub-hosted test file itself was not executed through CI**, so a repository checkout/CI run is still required. This does not demonstrate source retrieval, visual PDF inspection, independent review, or real regulatory compliance.
