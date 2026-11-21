"""Regenerate twelve preserved synthetic whole-plan review input packets.

Only the drawing and its original neutral brief are written. These published
cases are known regressions, not a fresh blind or assisted-review experiment.
PDF byte identity is recorded on the study runtime; other maintained PDF
versions can produce different bytes. Original randomly assigned trailer IDs
are retained to reproduce the frozen input binding on that runtime.
"""
from hashlib import sha256
from pathlib import Path

import whole_plan_drawings_a as author_a
import whole_plan_drawings_b as author_b


# Constructor, original brief, and original trailer /ID. These identifiers are
# PDF serialization data, not an oracle or a reviewer-visible answer field.
_CASES = {
    "K27": (author_a.family_b, False, author_a.brief("K27", "B"),
            "[<1B651E1DC29B72724FC39403485CC289><EDF1C4D195BB5A10451928601B00AE90>]"),
    "M84": (author_a.family_a, True, author_a.brief("M84", "A"),
            "[<C3983BC3AF0438C3BFC28E39C2A20066><1AF262F312EEDA32B1719DCE74EE3AC1>]"),
    "Q19": (author_a.family_a, False, author_a.brief("Q19", "A"),
            "[<3CC39E667736C2BDC2BFC29B45C385C2><F5272D78A87AC14EB5F13E3BFA0B3B2C>]"),
    "S63": (author_a.family_c, True, author_a.brief("S63", "C"),
            "[<49C2BD293DC2B837C28AC3AAC38902C3><4C4E8B2C50F798363B946B2D021CA22E>]"),
    "V42": (author_a.family_c, False, author_a.brief("V42", "C"),
            "[<35C282164DC28A55C29E2A6C6C2936C2><E8EE6AB0CD3F56E679EEF13C92AA446F>]"),
    "X95": (author_a.family_b, True, author_a.brief("X95", "B"),
            "[<51C29E3F681CC397C3B7C2B94FC39467><AE46AD878F50585465302FC89862694E>]"),
    "B76": (author_b.wide_loc, False, author_b.BRIEFS["wide_loc"],
            "[<C2AC26786723C29B41C2AD52C3920E12><AC2429A7284EA7511C6B5FF1CCAC9356>]"),
    "D31": (author_b.route_rtf, True, author_b.BRIEFS["route_rtf"],
            "[<1AC28AC29C3C617BC2B6C2A2C3A458C2><26DD4DA2C6A87986840C029174CE3C69>]"),
    "F58": (author_b.route_rtf, False, author_b.BRIEFS["route_rtf"],
            "[<C28050C28A41C284C2B455C386C2A9C2><6BA41A046469EAB15131F9A3A3EA3D61>]"),
    "H90": (author_b.wide_loc, True, author_b.BRIEFS["wide_loc"],
            "[<28C3993350C292C3B675C3AF35C297C3><E2D48AA9B7A1BF05548406C668144E87>]"),
    "N24": (author_b.portrait_pla, False, author_b.BRIEFS["portrait_pla"],
            "[<2BC38D34C2B2392FC3B0363B0E7E31C2><98A6929FA028368CB2A940F0314A847F>]"),
    "T67": (author_b.portrait_pla, True, author_b.BRIEFS["portrait_pla"],
            "[<14C3B2407CC3BDC3B541C2B53CC38CC3><D4DB6744DABB996DDDBD431503278C06>]"),
}
CASE_IDS = tuple(sorted(_CASES))


def write_case(output_dir: Path, case_id: str) -> dict:
    """Write plan.pdf and job-brief.md into a new caller-owned directory.

    Reject unknown case IDs and existing destinations without modifying them.
    Return input names and actual SHA256 values, without answer-key fields.
    """
    if not isinstance(case_id, str) or case_id not in _CASES:
        raise ValueError(f"Unknown case ID: {case_id!r}")
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f"Destination already exists: {output_dir}")
    draw, variant, brief, trailer_id = _CASES[case_id]
    is_author_a = draw.__module__ == author_a.__name__
    with draw(case_id, variant) if is_author_a else draw(variant) as document:
        metadata = ({
            "title": f"Synthetic review plan {case_id}",
            "author": "Fictional drafting exercise",
            "subject": "Private synthetic whole-plan drafting review; no legal or regulatory status",
            "creator": "Private trial authoring",
        } if is_author_a else {
            "title": "Synthetic Alberta drawing - whole-plan review",
            "author": "Fictional project drafting group",
            "subject": "Private synthetic drawing-quality exercise",
            "creator": "Synthetic drawing author",
        })
        document.set_metadata(metadata)
        document.xref_set_key(-1, "ID", trailer_id)
        plan = document.tobytes(garbage=4, deflate=True, no_new_id=True)
    contents = {"plan.pdf": plan, "job-brief.md": brief.encode("utf-8")}
    output_dir.mkdir(parents=True, exist_ok=False)
    try:
        for name, data in contents.items():
            (output_dir / name).write_bytes(data)
    except OSError:
        for name in contents:
            (output_dir / name).unlink(missing_ok=True)
        output_dir.rmdir()
        raise
    return {"case_id": case_id, "inputs": list(contents),
            "sha256": {name: sha256(data).hexdigest() for name, data in contents.items()}}


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path, help="new directory for the two inputs")
    parser.add_argument("case_id", choices=CASE_IDS)
    args = parser.parse_args()
    print(json.dumps(write_case(args.output_dir, args.case_id), indent=2))
