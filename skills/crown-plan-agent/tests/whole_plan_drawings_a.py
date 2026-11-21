"""Drawing constructors and original job briefs from synthetic trial author A.

No private authoring, oracle, preflight or renderer entry point is retained.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from runtime_security import load_pdf_runtime

fitz = load_pdf_runtime()

INK = (0.10, 0.16, 0.19)
BLUE = (0.13, 0.32, 0.43)
PALE = (0.93, 0.96, 0.97)
GRAY = (0.42, 0.45, 0.47)
WHITE = (1, 1, 1)


def rect(p, box, fill=None, width=0.8, color=INK):
    p.draw_rect(fitz.Rect(box), color=color, fill=fill, width=width)


def line(p, a, b, width=0.8, color=INK, dashes=None):
    p.draw_line(fitz.Point(*a), fitz.Point(*b), color=color, width=width, dashes=dashes)


def poly(p, pts, fill=None, width=1.2, color=INK, close=True):
    sh = p.new_shape()
    for a, b in zip(pts, pts[1:]):
        sh.draw_line(fitz.Point(*a), fitz.Point(*b))
    if close:
        sh.draw_line(fitz.Point(*pts[-1]), fitz.Point(*pts[0]))
    sh.finish(color=color, fill=fill, width=width, closePath=close)
    sh.commit()


def txt(p, box, text, size=11, bold=False, color=INK, align=0):
    r = fitz.Rect(box)
    out = p.insert_textbox(r, text, fontsize=size, fontname='hebo' if bold else 'helv',
                           color=color, align=align, lineheight=1.2)
    if out < -0.01:
        raise RuntimeError(f'Text does not fit page {p.number + 1}: {text!r} in {box}: {out}')


def label(p, x, y, text, size=11, bold=False, width=300, color=INK):
    txt(p, (x, y, x + width, y + size * (1.5 + 1.3 * len(text.splitlines()))), text, size, bold, color)


def heading(p, box, text):
    rect(p, box, fill=BLUE, color=BLUE)
    txt(p, (box[0] + 10, box[1] + 5, box[2] - 8, box[3] - 1), text, 12, True, WHITE)


def north(p, x, y, size=37, name='GRID N', angle=0):
    # All views in these conceptual drawings have the same upright orientation.
    label(p, x - 27, y - 20, name, 9, True, 80)
    poly(p, [(x, y), (x - 7, y + size), (x, y + size - 9), (x + 7, y + size)], fill=INK, width=0.8)
    line(p, (x, y), (x, y + size + 8), width=0.8)


def scale(p, x, y, denominator, interval, label_text=None):
    # A physical bar at the declared printed scale, independent of diagram geometry.
    half = interval * 1000 / denominator / 25.4 * 72
    rect(p, (x, y, x + half, y + 5), fill=INK)
    rect(p, (x + half, y, x + 2 * half, y + 5), fill=WHITE)
    for k, s in enumerate(('0', str(interval), f'{interval * 2} m')):
        label(p, x + k * half - (2 if k else 0), y + 9, s, 8.5, width=80)
    label(p, x, y - 19, label_text or f'SCALE 1:{denominator:,}', 9, True, 210)


def dot(p, x, y, name, dx=9, dy=-12):
    p.draw_circle(fitz.Point(x, y), 3, color=INK, fill=WHITE, width=1)
    label(p, x + dx, y + dy, name, 9, width=155)


def footer(p, case_id):
    h, w = p.rect.height, p.rect.width
    label(p, 30, h - 21, 'SYNTHETIC REVIEW EXERCISE - FICTIONAL DATA - NO LEGAL OR REGULATORY STATUS', 8, width=w - 200, color=GRAY)
    txt(p, (w - 145, h - 21, w - 30, h - 5), f'CASE {case_id}', 8, color=GRAY, align=2)


def top(p, case_id, title, subtitle):
    label(p, 30, 20, title, 20, True, p.rect.width - 200)
    label(p, 31, 49, subtitle, 10, width=p.rect.width - 100, color=GRAY)
    line(p, (30, 70), (p.rect.width - 30, 70), width=1.8, color=BLUE)


def simple_rows(p, box, rows, col=0.64, size=10.5, header=None):
    x0, y0, x1, y1 = box
    rect(p, box)
    rh = (y1 - y0) / len(rows)
    sx = x0 + (x1 - x0) * col
    line(p, (sx, y0), (sx, y1), width=0.5)
    for i, (left, right) in enumerate(rows):
        yy = y0 + i * rh
        if i:
            line(p, (x0, yy), (x1, yy), width=0.4)
        txt(p, (x0 + 8, yy + 6, sx - 7, yy + rh - 2), left, size, bold=i == 0 and header is not None)
        txt(p, (sx + 8, yy + 6, x1 - 8, yy + rh - 2), right, size, bold=i == 0 and header is not None)


def a_title(p, sheet, defective):
    # Four-column complete titleblock shared by the two issued sheets.
    y0, y1 = 650, 815
    xs = [30, 445, 755, 970, 1160]
    rect(p, (30, y0, 1160, y1), fill=PALE)
    for x in xs[1:-1]:
        line(p, (x, y0), (x, y1), width=0.8)
    label(p, 43, 660, 'BIRCH LANTERN FIELD SERVICES', 15, True, 390)
    label(p, 43, 687, 'Hollow Creek instrument access', 15, True, 390)
    txt(p, (43, 719, 432, 799), 'Two-sheet Crown-land planning sketch\nPrepared for: Lumen Vale Research Cooperative\nPurpose: seasonal monitoring access\nConceptual geometry; no survey-control acceptance', 10.5)
    legal = 'NE 14-56-8 W5M' if not (defective and sheet == 2) else 'NE 14-58-8 W5M'
    txt(p, (458, 662, 742, 808), f'LOCATION\n{legal}\nAlberta - fictional Hollow Creek area\nBASIS\nNAD83(CSRS), UTM Zone 11\nGrid bearings; metres unless stated', 11)
    doc = 'HV-6027' if not (defective and sheet == 2) else 'HV-5882'
    txt(p, (768, 662, 958, 808), f'CURRENT ISSUE\nDrawing: {doc}\nRevision: C\nIssued: 2026-11-18\nJob: BL-26074\nDrawn: SD   Checked: MK', 11)
    txt(p, (983, 662, 1148, 808), f'SHEET {sheet} OF 2\n' + ('Route overview' if sheet == 1 else 'Crossing details') + '\n\nSheet size: A3\nScales: as shown\nReview issue only', 11, bold=False)


def family_a(case_id, defective):
    d = fitz.open()
    p = d.new_page(width=1190, height=842)
    top(p, case_id, 'HOLLOW CREEK / ACCESS PACKAGE', 'Route overview with separate crossing details on Sheet 2')
    heading(p, (30, 87, 775, 117), 'MAIN VIEW - MONITORING ACCESS')
    rect(p, (30, 117, 775, 625))
    # Contiguous fictional quarter outline and access route with deliberately roomy labels.
    poly(p, [(84, 176), (640, 176), (685, 495), (116, 555)], fill=(0.98, 0.985, 0.98), width=1.1)
    label(p, 113, 138, 'Adjoining: NW 14-56-8 W5M', 10, width=300)
    label(p, 417, 191, 'NE 14-56-8 W5M', 11, True, width=220)
    label(p, 132, 520, 'Adjacent parcel: SE 15-56-8 W5M', 10, width=350)
    # Corridor polygons and a genuine detail reference, not an independent missing graphic.
    poly(p, [(130, 434), (298, 424), (444, 342), (567, 343), (567, 367), (450, 366), (306, 448), (132, 458)], fill=(0.84, 0.91, 0.94))
    line(p, (131, 446), (302, 436), width=0.6, dashes='[5 3]')
    line(p, (302, 436), (449, 354), width=0.6, dashes='[5 3]')
    line(p, (449, 354), (567, 355), width=0.6, dashes='[5 3]')
    label(p, 140, 472, '10.0 m proposed access', 10, width=245)
    label(p, 448, 382, 'Monitoring station HC-04', 11, True, width=265)
    rect(p, (567, 333, 616, 382), fill=(0.94, 0.90, 0.78))
    dot(p, 132, 446, 'RP-A', dx=-22, dy=17)
    dot(p, 302, 436, 'RP-B', dx=-34, dy=-27)
    # Creek drawn as paired curves, labelled with generous clearance.
    for off in (0, 8):
        poly(p, [(403 + off, 239), (383 + off, 281), (399 + off, 325), (385 + off, 371), (407 + off, 418), (399 + off, 483)], close=False, color=(0.25, 0.49, 0.62), width=1.3)
    label(p, 418, 259, 'Hollow Creek', 10, width=180, color=BLUE)
    p.draw_circle(fitz.Point(395, 385), 33, color=INK, width=0.8)
    label(p, 430, 424, 'C-1 / see Sheet 2', 10, width=230)
    north(p, 716, 159)
    scale(p, 76, 583, 2500, 50)
    heading(p, (800, 87, 1160, 117), 'ISSUE RECORD - HISTORICAL ENTRIES RETAINED')
    simple_rows(p, (800, 117, 1160, 284), [
        ('2026-08-21 / A', 'Preliminary'),
        ('2026-10-09 / B', 'Route shift'),
        ('2026-11-18 / C', 'Current issue'),
        ('Archived drawing', 'HV-5882')], col=0.59, size=10.5)
    heading(p, (800, 302, 1160, 332), 'NOTES')
    txt(p, (814, 346, 1145, 463), '1. Current package comprises Drawing HV-6027, Sheets 1 and 2, Revision C.\n2. Archived Drawing HV-5882 is retained in the history only.\n3. The route is within NE 14-56-8 W5M.\n4. Diagram geometry is illustrative; do not set out from this exercise.', 10.5)
    heading(p, (800, 480, 1160, 510), 'LOCATION INSET - WIDER CONTEXT')
    rect(p, (800, 510, 1160, 625))
    line(p, (832, 546), (1021, 546), width=1.1)
    line(p, (917, 526), (917, 592), width=0.7)
    label(p, 837, 522, 'Range Road 82', 8.5, width=170)
    rect(p, (951, 553, 974, 569), fill=BLUE, color=BLUE)
    label(p, 987, 554, 'Site', 9, width=65)
    north(p, 1115, 533, size=25)
    scale(p, 826, 596, 10000, 200)
    a_title(p, 1, defective)
    footer(p, case_id)

    p = d.new_page(width=1190, height=842)
    top(p, case_id, 'HOLLOW CREEK / CROSSING DETAILS', 'Detail references correspond to the route overview on Sheet 1')
    heading(p, (30, 87, 735, 117), 'DETAIL C-1 - CREEK CROSSING')
    rect(p, (30, 117, 735, 401))
    # Cross creek and access drawn as generic illustrative detail.
    poly(p, [(93, 239), (635, 239), (635, 279), (93, 279)], fill=(0.84, 0.91, 0.94))
    for off in (0, 20):
        poly(p, [(329 + off, 147), (315 + off, 194), (330 + off, 238), (317 + off, 283), (332 + off, 337)], close=False, color=(0.25, 0.49, 0.62), width=1.2)
    label(p, 98, 202, '10.0 m access corridor', 11, width=230)
    label(p, 375, 297, 'C-1 / conceptual span', 11, width=255)
    label(p, 405, 155, 'Hollow Creek', 10, width=175, color=BLUE)
    north(p, 685, 155, size=30)
    scale(p, 76, 368, 500, 10)
    heading(p, (30, 422, 735, 452), 'DETAIL S-1 - STATION APPROACH')
    rect(p, (30, 452, 735, 625))
    poly(p, [(97, 510), (402, 510), (402, 541), (97, 541)], fill=(0.84, 0.91, 0.94))
    rect(p, (402, 487, 506, 568), fill=(0.94, 0.90, 0.78))
    label(p, 534, 502, 'HC-04\nStation pad', 10.5, width=140)
    north(p, 685, 477, size=27)
    scale(p, 76, 594, 1000, 25)
    heading(p, (760, 87, 1160, 117), 'NOTES / DETAIL INTERPRETATION')
    txt(p, (775, 135, 1145, 314), '1. Read this sheet with the current route overview.\n2. Detail C-1 is the creek crossing identified on Sheet 1.\n3. Detail S-1 shows the HC-04 approach.\n4. Grid north applies independently to each view.\n5. Access corridor width is 10.0 m.\n6. Insets use their own stated scales.\n7. No construction or legal boundary authority is conveyed.', 11)
    heading(p, (760, 340, 1160, 370), 'REFERENCE KEY')
    p.draw_circle(fitz.Point(787, 397), 3, color=INK, fill=WHITE)
    label(p, 803, 386, 'Reference marker (diagram only)', 10.5, width=335)
    rect(p, (779, 434, 795, 446), fill=(0.84, 0.91, 0.94))
    label(p, 803, 428, 'Proposed access corridor', 10.5, width=330)
    rect(p, (779, 473, 795, 485), fill=(0.94, 0.90, 0.78))
    label(p, 803, 467, 'Monitoring station pad', 10.5, width=330)
    txt(p, (775, 532, 1145, 614), 'Package identity is recorded in the current-issue titleblock below. Historical references on Sheet 1 describe earlier work and are not current sheet identifiers.', 10.5)
    a_title(p, 2, defective)
    footer(p, case_id)
    return d


def raster_notes(zone):
    nd = fitz.open()
    np = nd.new_page(width=735, height=178)
    rect(np, (0, 0, 735, 178), fill=(0.97, 0.97, 0.94))
    txt(np, (14, 10, 721, 169), f'NOTES\n1. Coordinate reference: NAD83(CSRS), UTM Zone {zone}.\n2. All stated distances are metres. Main view and locator inset use separate scales.\n3. Bearings refer to grid north; each view is independently oriented.\n4. Proposed cabin and access are schematic review features, not accepted boundaries.\n5. Review issue dated 2026-11-16 supersedes the preliminary issue of 2026-09-24.\n6. Fictional project; no legal, regulatory or construction authority is conveyed.', 11)
    pix = np.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False)
    data = pix.tobytes('png')
    nd.close()
    return data


def family_b(case_id, defective):
    d = fitz.open()
    p = d.new_page(width=842, height=1190)
    top(p, case_id, 'MOTH RIDGE / FIELD CABIN', 'Rooklight Survey Studio - Draft planning sketch')
    heading(p, (30, 89, 550, 119), 'MAIN VIEW - CABIN AND ACCESS')
    rect(p, (30, 119, 550, 660))
    poly(p, [(83, 205), (460, 182), (487, 526), (111, 553)], fill=(0.97, 0.98, 0.95))
    line(p, (87, 365), (477, 338), width=0.5, color=GRAY, dashes='[4 4]')
    label(p, 105, 221, 'SE 23-62-11 W5M', 11, True, width=240)
    label(p, 120, 513, 'NE 14-62-11 W5M (adjoining)', 10, width=300)
    # One bent corridor leading into a cabin occupation; labels are kept outside shapes.
    poly(p, [(130, 463), (228, 455), (327, 356), (341, 370), (239, 475), (132, 483)], fill=(0.84, 0.91, 0.94))
    rect(p, (302, 294, 393, 360), fill=(0.94, 0.90, 0.78))
    label(p, 291, 267, 'Proposed field cabin', 10.5, True, width=230)
    label(p, 135, 391, '8.0 m access', 10.5, width=170)
    dot(p, 130, 473, 'RP-1', dx=-15, dy=19)
    dot(p, 337, 360, 'RP-2', dx=16, dy=7)
    line(p, (88, 580), (480, 580), width=1.5)
    label(p, 122, 551, 'Fictional Ridge Trail - existing travelway', 10, width=360)
    if not defective:
        north(p, 493, 159, size=37)
    scale(p, 76, 620, 2000, 50)
    heading(p, (575, 89, 812, 119), 'LOCATOR INSET')
    rect(p, (575, 119, 812, 421))
    # Inset has a valid independent north arrow; it cannot orient the main view by proxy.
    line(p, (607, 193), (773, 346), width=1.5)
    line(p, (610, 329), (768, 195), width=0.8)
    label(p, 594, 152, 'Moth Ridge\nlocal context', 10.5, True, width=140)
    rect(p, (687, 246, 707, 262), fill=BLUE)
    label(p, 711, 259, 'Site', 9, width=70)
    label(p, 592, 342, 'Adjoining blocks\nnot part of request', 9, width=180)
    north(p, 777, 150, size=30)
    scale(p, 596, 391, 8000, 200)
    heading(p, (575, 442, 812, 472), 'LEGEND')
    rect(p, (575, 472, 812, 660))
    rect(p, (590, 491, 609, 505), fill=(0.94, 0.90, 0.78))
    txt(p, (620, 488, 800, 527), 'Cabin occupation', 10)
    rect(p, (590, 535, 609, 549), fill=(0.84, 0.91, 0.94))
    txt(p, (620, 532, 800, 572), 'Proposed access', 10)
    p.draw_circle(fitz.Point(599, 586), 3, color=INK, fill=WHITE)
    txt(p, (620, 578, 800, 618), 'Reference marker', 10)
    # A raster panel is intentionally used in both members of the pair.
    p.insert_image(fitz.Rect(30, 684, 812, 874), stream=raster_notes('12' if defective else '11'))
    # Bottom title block is vertical and information-rich; all text is native here.
    rect(p, (30, 896, 812, 1157), fill=PALE)
    line(p, (440, 896), (440, 1157), width=0.8)
    txt(p, (45, 910, 424, 1012), 'ROOKLIGHT SURVEY STUDIO\nMoth Ridge seasonal field cabin\nPrepared for: Ember Finch Ecology Group\nPlanning sketch - initial review issue', 13, True)
    txt(p, (45, 1026, 424, 1141), 'LOCATION\nSE 23-62-11 W5M, Alberta\nFictional Moth Ridge area\nPurpose: seasonal wildlife monitoring\nConceptual geometry only', 11)
    txt(p, (456, 910, 798, 1142), 'DRAWING MR-7316\nJob RL-26109\nCurrent revision: 2\nIssue date: 2026-11-16\nHistory: Rev 1 / 2026-09-24 / preliminary\nSheet 1 of 1 - A3 portrait\nScales: main 1:2,000; locator 1:8,000\nPrepared: AJ     Checked: ER\nSynthetic review exercise', 11)
    footer(p, case_id)
    return d


def c_title(p):
    rect(p, (30, 658, 1160, 815), fill=PALE)
    line(p, (455, 658), (455, 815), width=0.8)
    line(p, (790, 658), (790, 815), width=0.8)
    txt(p, (43, 670, 442, 800), 'COPPER WREN GEOMATICS\nJuniper Bench materials staging\nFor: Lantern Field Utilities Association\nFictional Crown-land planning sketch\nConceptual areas; no certified boundary survey', 12, True)
    txt(p, (469, 670, 777, 800), 'LOCATION\nSW 31-49-17 W5M, Alberta\nFictional Juniper Bench area\nBASIS\nNAD83(CSRS), UTM Zone 11\nGrid north; distances in metres', 10.5)
    txt(p, (803, 670, 1146, 800), 'DRAWING JB-4208 / JOB CW-26093\nCurrent revision B / 2026-11-17\nHistory: A / 2026-08-28 / concept only\nSheet 1 of 1 - A3 landscape\nScales: main 1:1,500; detail 1:750\nPrepared: NL     Checked: HT', 10.5)


def family_c(case_id, defective):
    d = fitz.open()
    p = d.new_page(width=1190, height=842)
    top(p, case_id, 'JUNIPER BENCH / OCCUPATION AREAS', 'Activity areas and excluded overlap are stated separately throughout the drawing')
    heading(p, (30, 88, 747, 118), 'MAIN VIEW - ACTIVITY COMPONENTS')
    rect(p, (30, 118, 747, 495))
    poly(p, [(80, 189), (640, 189), (640, 420), (80, 420)], fill=(0.98, 0.98, 0.96))
    label(p, 95, 155, 'SW 31-49-17 W5M', 11, True, width=250)
    label(p, 95, 431, 'Neighbour: SE 36-49-18 W5M', 10, width=330)
    # Main occupation components shown as named conceptual blocks, without dimensional claims.
    rect(p, (408, 228, 578, 346), fill=(0.94, 0.89, 0.76))
    txt(p, (420, 252, 568, 321), 'STAGING PAD\n0.620 ha', 12, True, align=1)
    poly(p, [(134, 351), (385, 351), (408, 316), (408, 344), (396, 375), (134, 375)], fill=(0.84, 0.91, 0.94))
    label(p, 185, 311, 'NEW ACCESS\n0.420 ha', 11, True, width=190)
    rect(p, (405, 367, 529, 417), fill=(0.87, 0.91, 0.82))
    txt(p, (414, 375, 521, 415), 'BORROW\n0.220 ha', 10.5, True, align=1)
    rect(p, (85, 210, 120, 420), fill=(0.89, 0.89, 0.89))
    label(p, 133, 234, 'Existing shared track\n0.140 ha excluded', 10, width=220)
    line(p, (115, 247), (131, 247), width=0.7)
    north(p, 690, 153, size=32)
    scale(p, 76, 466, 1500, 25)
    heading(p, (30, 514, 747, 544), 'DETAIL RA-1 - ROAD ALLOWANCE OVERLAP')
    rect(p, (30, 544, 747, 635))
    rect(p, (76, 559, 314, 585), fill=(0.90, 0.90, 0.90))
    poly(p, [(156, 550), (192, 550), (192, 591), (156, 591)], fill=(0.84, 0.91, 0.94))
    txt(p, (333, 560, 581, 619), 'Road allowance overlap\n0.080 ha - excluded\nShown separately from activity subtotal', 9.5)
    north(p, 695, 576, size=24)
    scale(p, 77, 613, 750, 10)
    heading(p, (773, 88, 1160, 118), 'AREA SCHEDULE - HECTARES')
    access, borrow = ('0.480', '0.160') if defective else ('0.420', '0.220')
    rows = [
        ('Activity component', 'Area (ha)'),
        ('Staging pad', '0.620'),
        ('New access', access),
        ('Borrow', borrow),
        ('ACTIVITY SUBTOTAL', '1.260'),
        ('Existing shared track / excluded', '0.140'),
        ('Road allowance / excluded', '0.080'),
        ('GROSS ENVELOPE', '1.480'),
        ('NET CROWN REQUEST', '1.260')]
    simple_rows(p, (773, 118, 1160, 423), rows, col=0.75, size=10.5, header=True)
    heading(p, (773, 445, 1160, 475), 'NOTES / AREA SCOPE')
    ra = '0.100' if defective else '0.080'
    txt(p, (787, 490, 1146, 635), f'1. Net Crown request is the activity subtotal of pad, new access and borrow.\n2. Gross envelope also includes 0.140 ha of existing shared track and {ra} ha of road allowance overlap; both are excluded from the request.\n3. All hectare figures describe separate stated scopes. Detail RA-1 identifies the road overlap.\n4. Areas are synthetic planning values, not legal survey results.', 10.5)
    c_title(p)
    footer(p, case_id)
    return d


PRESENTATION = '''Please review the complete supplied plan package for ordinary drafting mistakes, omissions and internal contradictions against these job facts. Read every sheet, titleblock, note, view and schedule. The current sheets are expected to identify the same job, site and issue consistently. Every main, detail and locator view is expected to provide its own north orientation and stated scale. Labels, notes and schedules are expected to communicate consistent quantities and area scopes. Treat clearly identified history, adjoining parcels and differing view scales in their stated roles. Report observations with page and location evidence, and distinguish a demonstrated contradiction from an uncertainty. This is drawing QA only; no legal, regulatory or survey-control acceptance is requested.'''


def brief(case_id, fam):
    facts = {
        'A': '''Project: Hollow Creek instrument access\nClient: Lumen Vale Research Cooperative\nPrepared by: Birch Lantern Field Services\nJob: BL-26074\nCurrent drawing package: HV-6027, Sheets 1 and 2, Revision C, issued 2026-11-18\nIntended activity: seasonal monitoring access to station HC-04\nLocation: NE 14-56-8 W5M, fictional Hollow Creek area, Alberta\nCoordinate reference: NAD83(CSRS), UTM Zone 11\nExpected package: route overview and separate crossing/approach details''',
        'B': '''Project: Moth Ridge seasonal field cabin\nClient: Ember Finch Ecology Group\nPrepared by: Rooklight Survey Studio\nJob: RL-26109\nCurrent drawing: MR-7316, Revision 2, issued 2026-11-16, one sheet\nIntended activity: seasonal wildlife monitoring, with cabin and 8.0 m access\nLocation: SE 23-62-11 W5M, fictional Moth Ridge area, Alberta\nCoordinate reference: NAD83(CSRS), UTM Zone 11\nExpected package: cabin/access main view and wider locator inset''',
        'C': '''Project: Juniper Bench materials staging\nClient: Lantern Field Utilities Association\nPrepared by: Copper Wren Geomatics\nJob: CW-26093\nCurrent drawing: JB-4208, Revision B, issued 2026-11-17, one sheet\nIntended activity: staging pad, new access and borrow\nLocation: SW 31-49-17 W5M, fictional Juniper Bench area, Alberta\nCoordinate reference: NAD83(CSRS), UTM Zone 11\nArea scope: net request covers the three activity components; the existing shared track and road allowance overlap remain excluded. Gross envelope also includes those exclusions.\nExpected package: activity main view, road overlap detail and area schedule'''
    }
    return f'''# Synthetic job brief - {case_id}\n\nAll names, activities, locations and quantities in this packet are invented for a private review exercise. Nothing here represents an approved plan, actual project, legal interest or current regulatory requirement.\n\n{facts[fam]}\n\n{PRESENTATION}\n'''

