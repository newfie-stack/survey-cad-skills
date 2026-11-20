"""Generate invented office-review drawings with PyMuPDF, entirely offline.

These drawings, names and job briefs were authored for this synthetic study.
No material was taken from work plans. The initial and reserved cases are now
published for regression testing.

write_case(output_dir, case_id) writes the three reviewer inputs directly
into a new directory at the caller's explicit path.
"""
from hashlib import sha256
from pathlib import Path

import pymupdf as pdf


CASE_IDS = tuple(f"{n:02d}" for n in range(1, 9))
INITIAL_CASE_IDS = CASE_IDS[:6]
RESERVED_CASE_IDS = CASE_IDS[6:]
INK = (0.12, 0.18, 0.22)
TEAL = (0.10, 0.34, 0.35)
PALE = (0.91, 0.95, 0.94)
GRAY = (0.35, 0.40, 0.42)
WHITE = (1, 1, 1)
MARK = "INVENTED DRAWING  /  NOT A REAL PLAN"
REVIEW = """# Drawing review

Review the supplied drawing against its job brief and its own printed information.
Identify each discrepancy with its sheet, view or field, and the observed and
expected content. Mention any material limits on what you could read or check.
If the material agrees, say so. All names, identifiers and records are invented.
"""


def txt(p, x, y, value, size=12, *, bold=False, color=INK):
    font = "hebo" if bold else "helv"
    if x + pdf.get_text_length(value, fontname=font, fontsize=size) > p.rect.width - 5:
        raise ValueError(f"Text beyond page boundary: {value}")
    p.insert_text((x, y), value, fontsize=size, fontname=font, color=color)


def lines(p, x, y, values, *, size=11, step=17):
    for i, value in enumerate(values):
        txt(p, x, y + step * i, value, size)


def box(p, x, y, w, h, *, fill=None, color=TEAL, width=0.9):
    p.draw_rect(pdf.Rect(x, y, x + w, y + h), color=color, fill=fill, width=width)


def path(p, pts, *, color=TEAL, width=1.5):
    p.draw_polyline(pts, color=color, width=width)


def arrow(p, x, y, dx=0, dy=-36):
    """Tip is anchored at the specified point and rotated with the shaft."""
    tip = (x + dx, y + dy)
    length = (dx * dx + dy * dy) ** 0.5
    ux, uy = dx / length, dy / length
    path(p, [(x, y), tip], width=2.3)
    path(p, [(tip[0] - 9 * ux - 4 * uy, tip[1] - 9 * uy + 4 * ux),
             tip, (tip[0] - 9 * ux + 4 * uy, tip[1] - 9 * uy - 4 * ux)], width=2.3)
    txt(p, tip[0] - 3, tip[1] - 5, "N", 12, bold=True)


def band(p, x, y, w, label):
    box(p, x, y, w, 27, fill=PALE)
    txt(p, x + 9, y + 18, label, 12, bold=True, color=TEAL)


def bytes_of(doc):
    doc.set_metadata({"title": "Invented drawing", "author": "Synthetic Drafting Office"})
    return doc.tobytes(garbage=4, deflate=True, no_new_id=True)


LOC_BRIEF = """# Reedglass route issue instruction

This invented LOC corridor at Reedglass Reach uses project RG-17, route LOC-RG-417
and issue R2 throughout. Issue one long sheet. The main view carries the issued
scale 1:5,000. The plan-specific crossing record is utility register UR-59184,
at crossing C1. Carry the utility register identifier into the crossing note.
Station references at the two route terminals are 0+000 and 0+800. The office
sketch depicts the route and the crossing symbolically. No external records are
needed for this review.
"""


def loc(fault):
    d = pdf.open()
    p = d.new_page(width=1000, height=500)
    box(p, 20, 20, 960, 460)
    txt(p, 33, 44, MARK, 12, color=TEAL, bold=True)
    txt(p, 34, 78, "Reedglass Reach", 26, bold=True)
    txt(p, 34, 99, "LOC corridor   /   station and crossing sheet", 12)
    box(p, 34, 115, 715, 178)
    txt(p, 47, 137, "MAIN ROUTE   /   1:5,000", 12, bold=True)
    path(p, [(72, 254), (243, 232), (437, 199), (666, 188)], width=3)
    path(p, [(72, 246), (243, 224), (437, 191), (666, 180)], width=1)
    path(p, [(72, 262), (243, 240), (437, 207), (666, 196)], width=1)
    path(p, [(417, 163), (454, 241)], color=GRAY)
    txt(p, 73, 278, "0+000", 11)
    txt(p, 624, 214, "0+800", 11)
    txt(p, 454, 241, "C1", 11, bold=True)
    arrow(p, 701, 191, -9, -28)
    band(p, 34, 311, 346, "Route notes")
    lines(p, 45, 360, ["1. Twin lines mark the corridor limits.", "2. Terminal labels are station references.",
                        "3. Stationing increases toward the east."])
    band(p, 397, 311, 352, "Crossing notes")
    reg = "UR-59148" if fault else "UR-59184"
    lines(p, 408, 360, [f"4. C1 crosses utility register {reg}.", "5. Single oblique line marks the crossing.",
                         "6. Crossing position is diagrammatic."])
    txt(p, 36, 458, "Drawing index   /   route plan and crossing notes", 11, color=GRAY)
    box(p, 767, 32, 201, 432)
    band(p, 767, 32, 201, "ISSUE REGISTER")
    fields = [("PROJECT", "RG-17"), ("ROUTE ID", "LOC-RG-471" if fault else "LOC-RG-417"),
              ("ISSUE", "R2"), ("SHEET", "1 of 1"), ("MAIN VIEW", "1:5,000")]
    for i, (label, value) in enumerate(fields):
        y = 91 + i * 71
        txt(p, 782, y, label, 10, color=GRAY)
        txt(p, 782, y + 23, value, 17, bold=True)
    return bytes_of(d)


MSL_BRIEF = """# Hollowfen lease drawing instruction

Issue all three portrait sheets for invented MSL-HF-296 at revision C3. Keep
the C2 entry in the issue history. The site view is issued at 1:2,000 and the
gate detail at 1:250. The lease area schedule gives gross 4.800 ha and excluded
0.650 ha. Print the net lease area as gross less exclusion. The separate
reference parcel has gross 1.400 ha and no exclusion. Issue sheets in this order:
site overview, gate detail, area schedule. Only the lease schedule contributes to
the net lease area.
"""


def msl(fault):
    d = pdf.open()
    titles = ["Site overview", "Gate detail", "Area schedule"]
    for i, title in enumerate(titles):
        p = d.new_page(width=460, height=635)
        box(p, 17, 17, 426, 601)
        txt(p, 30, 40, MARK, 11, color=TEAL, bold=True)
        txt(p, 30, 86, title, 26, bold=True)
        txt(p, 30, 109, "Hollowfen   /   lease drawing series", 12, color=GRAY)
        if i == 0:
            band(p, 30, 135, 399, "SITE VIEW   /   1:2,000")
            box(p, 30, 162, 399, 207)
            path(p, [(80, 330), (63, 238), (287, 202), (319, 290), (80, 330)])
            txt(p, 145, 270, "Lease site", 14, bold=True)
            path(p, [(268, 299), (315, 324), (360, 324)])
            txt(p, 285, 345, "Gate; see sheet 2", 11)
            arrow(p, 385, 239, -8, -33)
            lines(p, 32, 406, ["The outer line identifies the lease site.",
                               "Sheet 3 records the office area schedule."])
        elif i == 1:
            band(p, 30, 135, 399, "GATE DETAIL   /   1:250")
            box(p, 30, 162, 399, 207)
            path(p, [(55, 288), (176, 260)], width=2)
            path(p, [(243, 245), (390, 211)], width=2)
            path(p, [(176, 260), (217, 207)], width=2)
            for x, y in [(176, 260), (243, 245)]:
                p.draw_circle((x, y), 3, color=TEAL, fill=TEAL)
            txt(p, 180, 291, "Gate opening", 12)
            lines(p, 32, 404, ["Circles mark the gate posts.", "The detail shows the opening in the site fence."])
        else:
            band(p, 30, 135, 399, "LEASE AREA   /   hectares")
            net = "4.250" if fault else "4.150"
            for j, (name, val) in enumerate([("Gross lease", "4.800"), ("Excluded", "0.650"), ("Net lease", net)]):
                y = 192 + j * 39
                txt(p, 47, y, name, 14)
                txt(p, 324, y, val, 14, bold=True)
                path(p, [(43, y + 7), (412, y + 7)], width=0.5)
            band(p, 30, 316, 399, "REFERENCE PARCEL   /   hectares")
            lines(p, 46, 369, ["Gross  1.400      Excluded  0.000      Net  1.400", "Shown for reference only."])
        txt(p, 31, 467, "Issue history", 12, color=TEAL, bold=True)
        txt(p, 31, 488, "C2     Earlier office issue", 12)
        box(p, 29, 518, 401, 81, fill=PALE)
        txt(p, 41, 541, "PLAN", 10, color=GRAY)
        txt(p, 41, 569, "MSL-HF-296", 17, bold=True)
        txt(p, 207, 541, "CURRENT REV", 10, color=GRAY)
        txt(p, 207, 569, "C2" if fault and i == 1 else "C3", 17, bold=True)
        txt(p, 336, 541, "SHEET", 10, color=GRAY)
        txt(p, 336, 569, f"{i+1} of 3", 15)
    return bytes_of(d)


ROT_BRIEF = """# Aster foldout issue instruction

The invented Aster Spur sketch AS-62 is issued as a single foldout, revision F1.
Use main index scale 1:3,000 and a diagrammatic key. The two run lengths from
the office sketch are 180 and 95. Include the drawing-wide note "Run lengths
are in metres." The main index needs its own north arrow. The office sketch
places north diagonally toward the upper left when the foldout title is upright.
The coloured key marks the junction and the spur limit. No coordinates or
ground measurements are supplied.
"""


def ribbon(fault):
    d = pdf.open()
    p = d.new_page(width=321, height=61)
    box(p, 1, 1, 319, 59, fill=PALE)
    txt(p, 12, 21, "PRINTED NOTE STRIP", 11, bold=True, color=TEAL)
    txt(p, 12, 44, "Junction symbols follow the key." if fault else "Run lengths are in metres.", 14)
    return p.get_pixmap(matrix=pdf.Matrix(2, 2), alpha=False).tobytes("png")


def rotated(fault):
    canvas = pdf.open()
    p = canvas.new_page(width=700, height=430)
    box(p, 16, 16, 668, 398)
    txt(p, 30, 39, MARK, 11, bold=True, color=TEAL)
    txt(p, 31, 78, "Aster Spur foldout", 25, bold=True)
    txt(p, 486, 44, "AS-62    /    REV F1", 14, bold=True)
    txt(p, 486, 69, "Sheet 1 of 1", 11)
    band(p, 30, 98, 417, "MAIN INDEX   /   1:3,000")
    box(p, 30, 125, 417, 209)
    path(p, [(70, 296), (229, 231), (371, 191)], width=3)
    p.draw_circle((229, 231), 5, color=TEAL, fill=WHITE, width=1.8)
    box(p, 367, 187, 8, 8, fill=TEAL)
    txt(p, 119, 256, "180", 13)
    txt(p, 292, 201, "95", 13)
    if not fault:
        arrow(p, 115, 209, -30, -43)
    band(p, 462, 98, 208, "SYMBOL KEY")
    p.draw_circle((480, 159), 5, color=TEAL, fill=WHITE, width=1.8)
    txt(p, 498, 164, "Junction", 12)
    box(p, 476, 184, 8, 8, fill=TEAL)
    txt(p, 498, 194, "Spur limit", 12)
    txt(p, 474, 227, "Diagrammatic key", 11, color=GRAY)
    p.insert_image(pdf.Rect(30, 343, 351, 404), stream=ribbon(fault))
    txt(p, 471, 381, "Office foldout series", 12, color=GRAY)
    # Counter-rotate the visible page contents onto a portrait MediaBox.
    doc = pdf.open()
    physical = doc.new_page(width=430, height=700)
    physical.show_pdf_page(physical.rect, canvas, 0, rotate=90)
    physical.set_rotation(90)
    return bytes_of(doc)


TAB_BRIEF = """# Brindlemere index drawing instruction

For invented drawing BI-34, issue T4, identify the west plot and the service
plot. The index is issued at 1:2,500 and the service detail at 1:500. The west
plot is 6.250 ha and the service plot is 1.750 ha. The index must label the west
plot area. The hectare schedule includes both plots and their combined total;
the service detail repeats the service area in square metres. Use
1 hectare = 10,000 square metres. The office outlines are schematic.
"""


def table(fault):
    doc = pdf.open()
    p = doc.new_page(width=630, height=620)
    box(p, 18, 18, 594, 584)
    txt(p, 33, 41, MARK, 11, bold=True, color=TEAL)
    txt(p, 33, 82, "Brindlemere plot index", 23, bold=True)
    txt(p, 448, 70, "BI-34    /    T4", 15, bold=True)
    txt(p, 449, 91, "Sheet 1 of 1", 11)
    band(p, 33, 110, 564, "LAND SCHEDULE")
    for j, (name, area) in enumerate([("West plot", "6.250 ha"), ("Service plot", "1.750 ha"), ("Combined", "8.000 ha")]):
        y = 161 + 30 * j
        txt(p, 48, y, name, 13)
        txt(p, 454, y, area, 13, bold=True)
        path(p, [(47, y + 7), (582, y + 7)], width=0.5)
    band(p, 33, 255, 330, "INDEX   /   1:2,500")
    box(p, 33, 282, 330, 174)
    path(p, [(59, 419), (80, 323), (244, 306), (275, 405), (59, 419)])
    path(p, [(244, 306), (301, 297), (332, 397), (275, 405)])
    txt(p, 93, 351, "West plot", 13, bold=True)
    txt(p, 93, 375, "6.520 ha" if fault else "6.250 ha", 13)
    txt(p, 272, 353, "Service", 10)
    band(p, 377, 255, 220, "SERVICE DETAIL   /   " + ("1:750" if fault else "1:500"))
    box(p, 377, 282, 220, 174)
    path(p, [(402, 424), (419, 322), (554, 302), (572, 402), (402, 424)])
    txt(p, 429, 367, "17,500 sq m", 13, bold=True)
    txt(p, 34, 502, "Office notes", 14, bold=True, color=TEAL)
    lines(p, 34, 530, ["1. Areas in the land schedule are hectares.", "2. The service outline is repeated in the detail.",
                       "3. The index labels serve the plot schedule."], size=11)
    return bytes_of(doc)


def write_case(output_dir: Path, case_id: str) -> dict:
    """Write neutral inputs. The return value contains no answer-key fields."""
    mapping = {
        "01": (MSL_BRIEF, msl, False), "02": (ROT_BRIEF, rotated, True),
        "03": (LOC_BRIEF, loc, True), "04": (MSL_BRIEF, msl, True),
        "05": (LOC_BRIEF, loc, False), "06": (ROT_BRIEF, rotated, False),
        "07": (TAB_BRIEF, table, False), "08": (TAB_BRIEF, table, True),
    }
    if case_id not in mapping:
        raise ValueError(f"Unknown case ID: {case_id!r}")
    brief, draw, fault = mapping[case_id]
    brief += ("\nThe office uses schematic linework in these invented drawings. "
              "Issued scale fields identify views. Ground geometry is outside this desk review.\n")
    contents = {"plan.pdf": draw(fault), "job-brief.md": brief.encode(), "REVIEW.md": REVIEW.encode()}
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    hashes = {}
    try:
        for name, data in contents.items():
            (output_dir / name).write_bytes(data)
            hashes[name] = sha256(data).hexdigest()
    except OSError:
        for name in contents:
            (output_dir / name).unlink(missing_ok=True)
        output_dir.rmdir()
        raise
    return {"case_id": case_id, "phase": "initial" if case_id in INITIAL_CASE_IDS else "reserved",
            "inputs": list(contents), "sha256": hashes}
