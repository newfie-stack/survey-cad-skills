# PDF dependency and runtime policy

Checked **November 19, 2026**. This is a dated maintenance policy and advisory
record. Version floors, hashes, tests and package scanners do not certify that a
PDF runtime is free of vulnerabilities.

The [native MuPDF signing advisory](#remaining-native-advisory) and findings in
[interpreter-native libraries](#interpreter-native-libraries) remain unresolved
for the reviewed runtime. The normal maintenance route is reviewed, published
vendor updates and synthetic compatibility tests; this distribution does not
require custom native patch builds or vulnerability reproductions.

## Interpreter and installation

Prefer a fresh virtual environment on **Python 3.12.16 or a newer 3.12 patch**.
The engine accepts final releases at these branch-specific minimum patch levels:

| Python branch | Minimum release |
|---|---|
| 3.11 | 3.11.18 |
| 3.12 | 3.12.16 |
| 3.13 | 3.13.18 |
| 3.14 | 3.14.10 |
| 3.15 | 3.15.2 |

Other branches and prereleases fail the runtime gate. Check the
[Python 3.12.16 release](https://www.python.org/downloads/release/python-31216/)
and the [coordinated Python security releases](https://blog.python.org/2026/10/python-3152-31410-31318-31216-31118/)
when refreshing this policy; a listed minimum is not a promise that no later
security release is needed.

The default [runtime lock](../requirements.txt) pins official
**`pymupdf-lite==2.1`**, permits binary wheels only and records all eleven wheel
SHA-256 hashes from the reviewed
[official PyPI release metadata](https://pypi.org/pypi/pymupdf-lite/2.1/json).
That release declares no `Requires-Dist` dependencies. Its smaller dependency
surface does not remove the native MuPDF library or clear native advisories.
See the [publisher's Lite description](https://github.com/pymupdf/PyMuPDF/blob/main/README-lite.md).

Install in a new environment with `python -m pip install --require-hashes -r requirements.txt`
from the skill folder. Do not relax hashes or build from a
source distribution when a platform lacks a reviewed wheel. Repository CI also
bootstraps the installer from the
[audited pip lock](https://github.com/newfie-stack/survey-cad-skills/blob/main/.github/bootstrap-pip.txt),
pinning pip 26.3 by its reviewed wheel hash. Installation and audit-tool locks
must be refreshed and reviewed together.

The canonical import is `pymupdf`. The gate requires exactly one provider:
official Lite or the full `PyMuPDF` distribution. Full PyMuPDF 2.1 is allowed
alone, but is not the default locked installation. Stable newer 2.x versions
still require advisory and compatibility review. Installing both providers,
using an older binding or loading a module that disagrees with its distribution
metadata fails the check. Create a fresh environment rather than trying to
repair overlapping providers in place.

## Pre-PDF runtime check

From the skill folder, run:

```bash
python engine/runtime_security.py
```

This checks the actual Python patch, provider metadata, canonical binding and
native MuPDF version without opening a PDF. Engine PDF entry points call the
same gate before native opening. The binding floor is 2.1 and the native floor
is **MuPDF 1.28.6**. A successful result explicitly covers minimum runtime
versions only and leaves advisory review required.

If the gate fails, the engine must remain unexecuted. Use the host's available
authorized evidence for an assisted manual review and state which operations
did not run. Do not bypass the check or substitute an older PDF provider.

## Reviewed package advisories

| Advisory | Dated finding |
|---|---|
| [CVE-2026-3029 / GHSA-cxqh-p2w9-fmr7](https://github.com/advisories/GHSA-cxqh-p2w9-fmr7) | PyMuPDF 1.26.6 is affected; the package fix is 1.26.7. The old development runtime is not an acceptable current baseline. |
| CVE-2026-82035 | The CLI font-path issue extends through PyMuPDF 1.28.2; the package fix is 2.0. See the [publisher's change log](https://pymupdf.readthedocs.io/en/latest/changes.html). |
| [CVE-2026-120752 / GHSA-x2mr-6hpr-g257](https://github.com/advisories/GHSA-x2mr-6hpr-g257) | The annotation-callout overflow package fix is 2.0. The advisory/package mapping was unreviewed or absent from the scanner mapping during this audit; a clean scan alone cannot establish coverage. |

The PyPI-based scans of the runtime lock and the complete pinned `pip-audit`
tool graph reported **zero mapped findings** on this date. That describes the
scanner's package mapping, not zero risk or clearance of native MuPDF. Review
upstream release notes and native advisories as well as scanner results.

## Remaining native advisory

**CVE-2026-112036 remains unresolved for the reviewed vanilla MuPDF 1.28.6
baseline.** The signing-related double-free fix is upstream commit
[`3984925b660afb8a781ddf504021e91be1bc671e`](https://github.com/ArtifexSoftware/mupdf/commit/3984925b660afb8a781ddf504021e91be1bc671e).
The reviewed `source/pdf/pdf-xref.c` in the vanilla 1.28.6 tag lacks the reset
introduced by that fix. Do not describe this issue as fixed by the native version
floor or by a zero-finding Python package scan.

Crown Plan Agent does not expose PDF signing or the upstream CLI embedded-file
and font-extraction features. Independent review identified no signing or upstream CLI extraction route in
the exposed Crown operations. It did not prove exhaustive native-callgraph
safety or establish a read-only exploit. These observations do not clear the
advisory or prove supported operations unaffected. Recheck native advisories and
the actual downstream build before any signing extension.

Use isolated environments and resource limits for untrusted PDFs. The engine's
file, page and span limits mitigate accidental resource exhaustion but do not
sandbox native parsing. Unit tests and benchmarks use invented fixtures. A separate public-plan
calibration remains outside the repository; no private project plan was used
or published in this hardening pass.

## Interpreter-native libraries

Python patch numbers do not identify every bundled native-library version. The
validated current interpreter build uses Expat 2.10.0; an earlier build of the
same Python 3.12.16 release still contained Expat 2.9.0. The
[Expat 2.10.0 security release](https://blog.hartwork.org/posts/expat-2-10-0-released/)
addresses four named advisories, not every known issue. Further review identified:

| Expat record | Disposition for the reviewed interpreter |
|---|---|
| [CVE-2026-124317](https://github.com/libexpat/libexpat/pull/1492) | Affects the library through 2.10.0. A fix is merged upstream, but was not in a released version at this check. Requires a verified interpreter/vendor build containing the fix. |
| [CVE-2025-66382](https://github.com/libexpat/libexpat/issues/1076) | The maintainer still describes an unfixed issue affecting all releases; structured CVE data stops at 2.7.5. Applicability to 2.10.0 remains unresolved. No verified public fix was found; do not infer clearance from the scanner range. |
| [CVE-2026-128241](https://github.com/libexpat/libexpat/pull/1502) | Concerns the separate `xmlwf` command. That command was absent from the exact reviewed Python installation. This scoped component-absence result does not clear the embedded library or other hosts. |

The maintainer also tracks [non-public and unvalidated reports](https://github.com/libexpat/libexpat/issues/1160).
These are not individually classified as affecting Crown without supporting
evidence. No untrusted XML input interface is exposed by the current Crown
engine; that observation does not remove Expat or clear its advisories.
Reassess the boundary before adding XML/GIS ingestion.

OpenSSL 3.5.9 remains the latest published 3.5 LTS build on this date, but its
[November 10](https://openssl-library.org/news/secadv/20261110.txt) and
[November 17 advisories](https://openssl-library.org/news/secadv/20261117.txt)
include outstanding Low-severity issues, with release fixes scheduled for
December 1, 2026. The eight tracked records are CVE-2026-35190,
CVE-2026-88822, CVE-2026-88823, CVE-2026-95691, CVE-2026-95692,
CVE-2026-107493, CVE-2026-107496 and CVE-2026-124709. Planned fixed releases
3.5.10, 4.0.4 and 4.1.1 were not yet published at this check; moving to the
currently released 4.0 or 4.1 branch does not avoid these findings.
Current Crown interfaces do not expose QUIC servers, custom CMS/PEM
or the other affected specialized APIs. This is scoped interface evidence, not
clearance of the linked native component. Track upstream fixes and maintain the
host build independently; neither pip-audit nor the Python patch-floor table
patches or fully audits these libraries.

In the reviewed Python builds, SSL and Expat were built into the interpreter.
Installing a newer system `openssl` command, a pip package or a system Expat
package does not establish replacement of those embedded copies. Replace the
actual interpreter with a verified maintained build when fixes become
available. Managed ChatGPT host libraries require provider updates; updating
the skill does not replace them.

## Maintained updates and PDF reader alternatives

Keep the published runtime lock and ordinary synthetic tests as the default
maintenance path. Review actual released artifacts, their native-library
provenance and compatibility before changing pins. Keep findings open when no
suitable verified release is available; do not suppress them or label the
current release fully patched. No custom native binary is distributed here.

MuPDF is an implementation choice, not a requirement of Crown-plan review.
Switching to PDFium is possible but is a separate migration: current code uses
rotated-text geometry, vector paths, table detection, popup annotations,
Unicode review-note layout and internal links. Text-only extraction libraries
cannot replace that complete contract. A replacement must pass synthetic
conformance cases and the existing review suite before it becomes the default.

The latest reviewed [pypdfium2 release metadata](https://pypi.org/pypi/pypdfium2/json)
was 5.15.2, uploaded November 9, with PDFium build 8138 in its
[release record](https://github.com/pypdfium2-team/pypdfium2/blob/main/autorelease/record.json).
The separate [PDFium binary distributor](https://github.com/bblanchon/pdfium-binaries/releases)
already listed build 8165 on November 16. Thus a current Python wrapper can
still bundle an older native library; changing engines is not automatic
security clearance.

[Debian sid](https://security-tracker.debian.org/tracker/CVE-2026-112036) and
[openSUSE Tumbleweed](https://www.suse.com/security/cve/CVE-2026-112036.html)
document fixed native MuPDF packages. They are unstable/rolling channels, and a
compatible patched Python/native stack for this deployment was not verified.
Installing system MuPDF does not patch Lite's bundled library. Do not mix
unverified native and Python packages or lower the runtime gate to force them
to work.

For the current preview, retain the existing reader and use the normal
reviewed-release update path. No reader migration, custom native build or
native-advisory clearance is implied by this documentation follow-up.

## Ongoing maintenance and audit boundary

CI runs the locked runtime tests and package audits on relevant changes and a
weekly schedule. The scanner reads the fully resolved locks directly without
creating a temporary pip resolver environment. Its report must contain every
expected package and exact version, with no silent skips. Installation steps
verify artifact hashes; the advisory scanner checks package metadata and does
not independently verify installed binary bytes. The audit job scans both the application lock and the complete
audit-tool/installer lock (29 unique tool packages; 30 together with the PDF
runtime in this dated snapshot). CI actions use immutable commit revisions; Dependabot
checks the runtime, audit toolchain and GitHub Actions weekly. Updates require
review and tests, with no automatic merging enabled.

Hashes establish artifact identity, not trust or vulnerability absence. A lock
update needs upstream/advisory review, all supported-operation tests and package
verification before release. Python, native libraries and host isolation must
be maintained separately from the package scanner.

External Octopus, CAD/ezdxf and GIS environments remain separate audit boundaries.
The Crown runtime lock and its scanner results do not automatically cover those
dependencies. Official minimal PyMuPDF Lite retains PyMuPDF's AGPL/commercial
licensing terms and is installed separately; no PDF runtime binaries are bundled
in the skill or ChatGPT package.
