# Octopus reconstruction provider

Use **actual Octopus code** for reconstruction. Read the available checkout's
`SKILL.md`, verify its commit and protected-source lock, then select the supported
route below. The [geometry handoff](geometry-handoff.md) still governs source,
control, CAD and acceptance evidence. The Crown offline CLI does not invoke this
provider automatically.

Octopus is a separately maintained implementation requiring authorized access;
this public preview does not include its source, dependencies or a public
download entitlement. Obtain an authorized reviewed checkout before using the
routes below. The offline PDF review and synthetic example can run without it.
If access is unavailable, retain `BLOCKED_MISSING_TOOL` for reconstruction.

| Reviewed input | Existing Octopus route |
| --- | --- |
| Partial courses, sketch diagnostics or unresolved registration | Load the checkout's `registered_plan/geometry.py` directly; call its existing functions without constructing a registered-plan payload. Output remains provisional and partial. |
| Source-backed registered target, with a faithful reviewed construction | Use `survey_geometry_engine.reconstruct_cli` with supplied observations, construction and a bound review ledger. |
| Missing provider, dependencies or unsupported construction | Report `BLOCKED_MISSING_TOOL` or the specific representation/source blocker; retain the evidence register. Do not write parallel COGO or copy the Octopus engine into Crown. |

This reference was inspected against Octopus commit
`eb2efb9e22cfa2e091ed09d1c83ccfe98b88017c`. Before execution, run
`python scripts/check_registered_plan_lock.py` from the reviewed checkout. A
different revision needs a fresh code/contract review; do not refresh its lock to
make a check pass.

## Reviewed partial-course diagnostics

The existing `course_end(start, bearing, distance_m, factor=1.0, reverse=False)`
and `bearing_azimuth(bearing)` preserve explicit course direction. The same
module supplies `intersection` and `constant_width_offset` for independently
reviewed constraint models. Calling an offset does not establish its source
width, side, terminal or boundary role. Validate finite coordinates and positive,
finite distances/widths before calling these functions. `intersection` uses
infinite lines; separately verify any required segment/ray limits.

Load this single module by file location: normal package import also loads the
full tool and its dependency/binding initialization. The example below executes
the hash-checked Octopus module, uses invented evidence, and writes a fresh
private diagnostic with input/provider hashes. Replace the absolute checkout
argument with the reviewed clone. Its diagnostic request is **not** a
`RegisteredPlanInput` or an admissible full-tool construction.

```bash
python - /absolute/path/to/reviewed-octopus-checkout <<'PY'
import hashlib, importlib.util, json, os, subprocess, sys, tempfile
from pathlib import Path
os.umask(0o077)
checkout = Path(sys.argv[1]).resolve(strict=True)
commit = "eb2efb9e22cfa2e091ed09d1c83ccfe98b88017c"
actual = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
if actual != commit:
    raise RuntimeError("Review the changed Octopus revision before execution")
subprocess.run([sys.executable, "scripts/check_registered_plan_lock.py"], cwd=checkout, check=True)
module_path = checkout / "registered_plan/geometry.py"
module_hash = hashlib.sha256(module_path.read_bytes()).hexdigest()
if module_hash != "63fcb81ae198ec6f2809758d14400dde6b7ed01429c87cd886d815e822683b45":
    raise RuntimeError("Octopus geometry source differs from the reviewed module")
spec = importlib.util.spec_from_file_location("octopus_geometry", module_path)
if spec is None or spec.loader is None:
    raise RuntimeError("Octopus geometry provider unavailable")
geometry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry)
def fingerprint(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()
source = b"INVENTED: P0 to P1, azimuth 90d00m00s, 12.50 m; no actual plan.\n"
observations = [{"id": "INVENTED-01", "bearing": '90\u00b000\'00"', "distance_m": 12.5,
                 "from": "P0", "to": "P1", "source_id": "INVENTED", "locator": "source.txt:1"}]
construction = {"mode": "PARTIAL_COURSE_ONLY", "origin": [0.0, 0.0], "factor": 1.0, "reverse": False}
request = {"observations": observations, "construction": construction}
end = geometry.course_end(tuple(construction["origin"]), observations[0]["bearing"],
                          observations[0]["distance_m"], factor=construction["factor"], reverse=construction["reverse"])
ledger = {"status": "REVIEW_REQUIRED", "scope": "INVENTED_PARTIAL_COURSE_ONLY",
          "provider_commit": commit, "module_path": str(module_path), "module_sha256": module_hash, "call": "course_end",
          "source_sha256": hashlib.sha256(source).hexdigest(), "request_sha256": fingerprint(request),
          "observations_sha256": fingerprint(observations), "construction_sha256": fingerprint(construction)}
folder = Path(tempfile.mkdtemp(prefix="crown-octopus-", dir="/tmp"))
(folder / "source.txt").write_bytes(source)
(folder / "review.json").write_text(json.dumps({"request": request, "ledger": ledger, "end": end}, indent=2))
print(folder)
PY
```

Use printed distances and widths unchanged with **factor `1.0`**, as required by
the current Octopus skill and registered workflow. Retain printed combined/scale
factors as evidence; do not rescale this output or silently mix provisional local
coordinates with accepted grid control. A partial chain does not supply a cap,
closed parcel, full-area comparison, accepted CRS or alignment.

## Full supplied-observation tool

After source and construction admission, run the existing offline entrypoint
from the reviewed checkout in a controlled runtime with network denied:

```bash
cd /absolute/path/to/reviewed-octopus-checkout
python -m survey_geometry_engine.reconstruct_cli \
  /absolute/path/to/private-job/request.json \
  /absolute/path/to/private-job/review-ledger.json
```

Use `registered_plan.models.RegisteredPlanInput` and its actual nested models:

- Supply a job-relative `source_file`, private `job_root`, **nonempty supplied
  `observations`** and an explicit reviewed `construction` object. Use a fresh,
  nonexistent job-relative `output_dir`; keep all job files outside both clones.
- Each observation needs `kind`, `label`, `printed_text` and `citation` with
  `page` and `text`; construction uses need stable `observation_id`s and the
  appropriate original values/endpoints.
- Construction requires a legitimate source-backed `target_plan_number`,
  `feature_type: "constant_width_corridor"`, nonempty components and `confidence`.
  The model must faithfully represent the source. Preserve
  course IDs, directed endpoints, widths, offset sides, terminals and complete
  control/tie uses. Unknown registration, a disposition code, drawing number or
  referenced background plan cannot become a fabricated registered target/tag.
  An instrument attachment still needs that legitimate source-backed target
  relationship to use this adapter; without it, use provisional pure-module
  diagnostics and retain the unresolved identity.
- Do not pass `construction=None` to the underlying tool as an evidence-only
  fallback: that legacy path can sequentially join courses and offset them.
  `topology: "open"` is also not a partial diagnostic mode; the full builder may
  close a corridor ring. Keep arbitrary partial cuts on the pure-module route.
- Set `ground_to_grid_factor: 1.0`; retain original factor notes externally.
  Leave `ats_points_csv` and `alignment_transform_json` absent/null at this
  adapter, whose binding does not admit those auxiliary files.
- The separate ledger requires nonempty `author` and `statement`, plus
  `request_sha256`, `source_sha256`, `observations_sha256` and
  `construction_sha256`. Source hash covers original file bytes; JSON hashes use
  the adapter's `fingerprint` convention shown above. Hash the complete raw
  request, including paths/options, after its source associations are reviewed.

This adapter invokes `RegisteredPlanTool(extractor=NoExtraction())`; extraction
and API calls are outside this route. Do **not** substitute
`python -m survey_geometry_engine`, which invokes a separate prototype. A review
result normally exits **2**; inspect structured status and fresh artifacts before
retrying. A matching hash ledger proves input binding, not reviewer authenticity,
source completeness or plan acceptance.

## Provenance and attribution

Retain original text/decimal lexemes, source hashes, page/detail/bbox locators,
feature/side identities, control roles and reviewed constraint decisions in the
private source graph/register. The tool model does not carry all of that
provenance. Record the executed provider path, commit/module hashes, actual call,
dependency versions, input ledger and fresh output hashes alongside its report.

Earlier handwritten COGO artifacts are historical custom diagnostics, not
Octopus output. Preserve their original attribution; after a fresh Octopus run,
mark them superseded for reconstruction/provider claims. Do not relabel old files
or cite a skill read as proof of Octopus execution. All original plans, source
audit images and derived project artifacts remain private. Numerical checks,
successful execution and artifact availability remain review evidence; accepted
boundary, control, alignment and regulatory readiness require their own checks.
