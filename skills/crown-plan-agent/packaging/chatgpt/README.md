# Crown Plan Agent for ChatGPT

This development preview packages the canonical public Crown Plan Agent skill,
its supporting Python source, dated catalogues and synthetic runtime tests.
Select Crown Plan Agent in ChatGPT, provide an authorized attachment or connected
file and ask for a review in plain language.

This is a skills-only package. It does not deploy an execution server or install
tools. Use the offline engine only when the host provides the required execution
environment and dependencies. Otherwise state that the engine did not run and
provide an assisted manual review, retaining all source and evidence gates.

Before native PDF work, use a fresh environment with the canonical skill's
hash-locked `requirements.txt`, preferably on Python 3.12.16 or a newer 3.12
patch, and run `python engine/runtime_security.py` from the skill folder.
The default dependency is official `pymupdf-lite==2.1`; it must not coexist with
the full PyMuPDF provider. Follow the
[dependency and runtime policy](https://github.com/newfie-stack/survey-cad-skills/blob/main/skills/crown-plan-agent/references/dependency-security.md),
including its unresolved native MuPDF advisory. A passed minimum-version check
is not security clearance. The package supplies Python source and locks, not
the interpreter or PDF runtime binaries.

Reconstruction requires separately authorized, reviewed Octopus code; it is not
bundled. Original plans, source PDFs, project drawings, private coordinates and
credentials must stay outside public repositories and this package.

`BUILD_MANIFEST.json` records the exact included file hashes. Original
contributions are covered by the
[repository license](https://github.com/newfie-stack/survey-cad-skills/blob/main/LICENSE);
external dependencies retain their own terms. The
[skill instructions](https://github.com/newfie-stack/survey-cad-skills/blob/main/skills/crown-plan-agent/SKILL.md)
and [release notes](https://github.com/newfie-stack/survey-cad-skills/blob/main/skills/crown-plan-agent/RELEASE_NOTES.md)
describe supported behavior and unfinished acceptance. These public links work
both in the source templates and in the built plugin.

## Rebuild from reviewed source

From the public repository root, choose a new ZIP path outside the skill folder:

```bash
python skills/crown-plan-agent/tools/build_chatgpt_plugin.py \
  --output /tmp/crown-plan-agent-chatgpt.zip
```

The builder uses only Python's standard library. It does not install, upload or
publish anything. It preserves canonical SKILL.md bytes, existing default prompts
and both reviewed icons. It rejects version mismatches, symlinks, unexpected
source artifacts, missing contained references and output overwrite. Repeated
builds of identical source produce identical bytes in the same Python/zlib
environment. Review confidentiality and distribution rights before uploading.
The reviewed icon profile uses non-interlaced 8-bit RGB/RGBA PNGs; compressed
pixel data is checked with an IHDR-derived decompression bound.

Development templates, build utilities, caches and
`tests/test_chatgpt_packaging.py` are excluded from the runtime package. All
runtime engine modules, references, skill instructions and runtime tests remain
included. Packaging tests run from the public source checkout; they require
the deliberately excluded build utility and templates.
