# Official checklist coverage for independent pre-checking

**Verified for source routing:** 2026-11-24 (official public IOGC and MyCLSS web pages). These are original review prompts paraphrasing the public checklists, not a statement that the private on-project MyCLSS checklist or the survey instructions were reviewed. Check for later amendments and applicability at each actual review.

## Core principle

A reviewer MUST select jurisdiction, `document_type` and actual `transaction` before activating any rule. Review all visible content, but label a question as `REVIEW_REQUIRED` if source applicability or plan evidence is unresolved. For an as-built exhibit or Surface Permit sketch, do **not** silently apply statutory CLSR requirements. This matrix does not replace project-specific instructions.

## Surveyor General Branch (MyCLSS survey document plan-check)

Official source: https://www.myclss.ca/myclss/index/pc/ (Plan check, published public checklist items 1–27).

For a formal SGB survey document, reviewer checks include:
- [ ] Returned documents and applicable required format identified; legibility, document type, land descriptions, plan designators and surveyor/land-administrator endorsement blocks reviewed.
- [ ] CLSR **and** LTO registration blocks checked for applicability, no invented or assumed recording number.
- [ ] Lands dealt with, compiled/comprising statements where applicable, parcel remainders and access as applicable reviewed.
- [ ] Each underlying parcel/plan number and affected *limited right* inspected separately, not silently overwritten by newer survey geometry. Registered rights verified against appropriate land records; map display alone insufficient.
- [ ] Dimensions/curves, areas, monumentation, found evidence, connection to existing survey, georeferencing and digital returns reviewed only with supporting observations and data.
- [ ] Plan compared with the project's actual SGB instructions and land-registry/LTO records where supplied. The public list does **not** establish the individual project's survey instructions or approvals.

## IOGC requirements: choose one applicable survey-plan subtype

Official source: https://www.iogc-pgic.gc.ca/eng/1472575186371/1472575275357 (Survey Plan Requirements; distinguish Application Survey Plan and CLSR Survey Plan).
Supplementary official source: https://www.myclss.ca/myclss/index/iogc-pgic/ (Checklist for IOGC).

**IOGC Surface Lease Application Survey Plan** (only if applicable):
- [ ] Title matches each relevant facility and parcel; reserve name/number, descriptions, legal subdivision and well identification properly shown.
- [ ] Surface and bottomhole well locations present; if directional/horizontal, wellbore path; if horizontal, intermediate casing point.
- [ ] Applicable facility/parcel areas in hectares, subtotal/total, and supplemental square-metre entry when required by the applicable IOGC threshold.
- [ ] Incidental Activities (TWS, temporary access, log decks as applicable) in a separate activity-type table and shown separately from permanent lands dealt with; reconcile area without duplicate counting.
- [ ] Applicable access route table, surroundings/topography/drainage and environmental features; formal-plan content not automatically transferred to as-built or Surface Permit sketch.
- [ ] Existing/pending agreements, recorded survey references, relevant roads and road-allowance jurisdiction addressed; exclusive-use surface-disposition overlap reviewed as a *legal-interest* question, not just geometry.

**IOGC Right-of-Way Application Survey Plan** (only if applicable):
- [ ] From/To pipeline locations, projected route, endpoints/tie-in, pipeline particulars and every affected parcel/road allowance where required.
- [ ] Applicable **crossing table** and **access route table** checked for completeness.
- [ ] Length/width, hectares/area subdivisions, IA table, existing interests and watercourses/topographic context reviewed with actual evidence and source.
- [ ] Endpoint connection and legal overlap with surface-lease/tie-in agreement verified, not inferred from a pipe crossing on a picture.

**IOGC CLSR Survey Plan** (only if applicable):
- [ ] Separate IOGC CLSR Surface Lease or ROW checklist selection; confirm hectare/IA table, pertinent wellbore or pipeline content, LSDs, dimensions and statutory signatures as applicable.
- [ ] Do not assume all application-only topographic layers appear on the CLSR plotting version.
- [ ] Appropriate Surveyor General Branch plan-check requirements still evaluated.

**IOGC Surface Permit sketch**:
- [ ] Current IOGC guidance identifies a sketch route to applicable provincial standards. Determine actual scope and approving authority.
- [ ] Do not automatically require a formal IOGC CLSR survey plan, statutory survey signatures, IA table, or CLSR recording for the sketch without applicable evidence.
- [ ] Check proposed temporary occupancy/clearing limits, area, existing interests and applicable authorization independently, noting any unverified approvals.

**Reclamation / remediation / amendment / surrender**:
- [ ] Classify the environmental purpose separately from land-tenure changes; reclamation alone is not proof of an amendment.
- [ ] For an amendment with **no change** to lands dealt with, check IOGC's stated exception to CLSR recording as it applies to the actual transaction.
- [ ] For changed permanent lands or partial surrender, flag appropriate CLSR survey and retained/surrendered parcel identity; do not assume one route without contracts/instructions.

## First Nation approvals and changes

Official source: https://www.myclss.ca/myclss/index/fna/.
- [ ] For a formal section 31 reserve survey creating new parcels/rights, check whether First Nation approval is applicable and evidenced, with correct plan identity, authorized approving party and date.
- [ ] A change to parcel shape/size or title-block after approval may require reapproval or documented acceptance. Never treat a changed plan as automatically covered by an old approval.
- [ ] A pre-check report is **not** an approval and does not itself submit anything to First Nation, IOGC, SGB or MyCLSS.

## What counts as tested?

| Check class | Needed evidence | Permissible conclusion without that evidence |
|---|---|---|
| Visual symbol/annotation | Readable whole-sheet source image and inspected locations | REVIEW_REQUIRED |
| Text/label consistency | Actual page text with coordinates or readable region image | REVIEW_REQUIRED |
| Area arithmetic | Reliable distinct tabulated values | REVIEW_REQUIRED |
| Area topology/closure | Actual valid CAD/GIS polygons and reviewed computation | REVIEW_REQUIRED |
| Recorded interests | Relevant recorded plan *and* active agreement/registry evidence | REVIEW_REQUIRED |
| Normative applicability | Applicable current source edition, plan-type selection and actual SGB instructions where required | REVIEW_REQUIRED |
| Whole-plan readiness | All applicable mandatory checks and significant uncertainty closed | INSUFFICIENT EVIDENCE |

Never turn a successful document scan, text detection or math check into a legal/registry `PASS`.
