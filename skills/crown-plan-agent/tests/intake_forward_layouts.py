"""Regenerate four preserved synthetic forward-review input packets.

Only plan.pdf and the original neutral job-brief.md are written. These
published inputs are known regressions, not fresh blind-review material.
The native drawings and image-only notes are reconstructed from invented
source data; no PDF or PNG binary is stored in the repository. Original
metadata and the absent PDF trailer /ID are retained for byte identity on
the recorded runtime and font files. Other maintained runtimes may serialize
or rasterize differently. The label directions are test data, not an angular
drafting standard.
"""
from hashlib import sha256
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from runtime_security import load_pdf_runtime

fitz = load_pdf_runtime()


INK = (0.08, 0.12, 0.16)


MUTED = (0.26, 0.31, 0.34)


PALE = (0.94, 0.96, 0.97)


WHITE = (1, 1, 1)


FONT_FILE = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


BOLD_FILE = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def text(p, x, y, s, size=10, bold=False, color=INK, angle=0):
    fontname = 'freshbold' if bold else 'fresh'
    p.insert_font(fontname=fontname, fontfile=BOLD_FILE if bold else FONT_FILE)
    point = fitz.Point(x, y)
    kwargs = dict(fontname=fontname, fontsize=size, color=color, overlay=True)
    if angle:
        kwargs['morph'] = (point, fitz.Matrix(angle))
    p.insert_text(point, s, **kwargs)


def line(p, x1, y1, x2, y2, width=.65, color=INK, dashes=None):
    p.draw_line((x1, y1), (x2, y2), color=color, width=width, dashes=dashes, overlay=True)


def box(p, r, fill=None, width=.65):
    p.draw_rect(fitz.Rect(r), color=INK, fill=fill, width=width, overlay=True)


def heading(p, r, s, size=11):
    box(p, r, PALE)
    text(p, r[0] + 9, r[1] + 18, s, size, True)


def lines(p, x, y, values, size=10.2, leading=16):
    for i, s in enumerate(values):
        text(p, x, y + i * leading, s, size)


def footer(p, sheet, total):
    y = p.rect.height - 27
    line(p, 35, y-12, p.rect.width-35, y-12, .55)
    text(p, 40, y, 'SYNTHETIC REVIEW EXERCISE ONLY — no legal, field, or regulatory reliance.', 8.3)
    text(p, p.rect.width-140, y, f'SHEET {sheet} OF {total}', 8.3, True)


def frame(p, title, subtitle, sheet, total):
    w, h = p.rect.width, p.rect.height
    box(p, (25, 25, w-25, h-48), None, 1)
    text(p, 40, 54, title, 19, True)
    text(p, 40, 75, subtitle, 10.3)
    footer(p, sheet, total)


def field(p, x, y, w, label, value):
    # 13.2 pt normal visible leading; font metric boxes can touch at adjacent rows.
    box(p, (x, y, x+w, y+45))
    text(p, x+9, y+15, label.upper(), 8.4, True, MUTED)
    text(p, x+9, y+30, value, 11)


def fieldtwo(p, x, y, w, label, first, second):
    box(p, (x, y, x+w, y+45))
    text(p, x+9, y+12, label.upper(), 8.0, True, MUTED)
    text(p, x+9, y+27, first, 11.5)
    text(p, x+9, y+40, second, 11.5)


def dot(p, x, y, label, dx=8, dy=-7):
    p.draw_circle((x, y), 3, color=INK, fill=WHITE, width=.85)
    text(p, x+dx, y+dy, label, 10.2, True)


def north(p, x, y, length=51):
    line(p, x, y+length, x, y, 1.1)
    line(p, x, y, x-5, y+12, 1)
    line(p, x, y, x+5, y+12, 1)
    text(p, x-4, y-10, 'N', 12, True)


def scale_bar(p, x, y, max_m, segments, denom):
    pts = max_m * 1000 / denom * 72 / 25.4
    step = pts / segments
    for i in range(segments):
        box(p, (x+i*step, y, x+(i+1)*step, y+6), INK if i%2==0 else WHITE, .5)
        text(p, x+i*step-4, y+19, str(round(max_m*i/segments)), 8)
    text(p, x+pts-8, y+19, str(max_m)+' m', 8)


MICA_BRIEF = '''# Synthetic job brief — Mica Ridge Corridor

Synthetic review exercise only. All names, dates, references, dimensions, and survey marks are invented. No current regulation, real parcel, legal survey control, or legal entitlement is represented.

Prepare a two-sheet portrait plan for Practice Talus Ltd. (fictional), job MR-813. The subject file is SYN-MR-813, the practice locality is Mica Ridge Practice Block, and the drawing revision is 2 dated 2026-10-06. Use simulated local grid MR-LG; bearings are clockwise from the page north arrow. This is a self-contained drafting consistency review using the following job facts.

The proposed 30.00 m corridor follows centreline A–B–C. Line A–B has bearing 345°00′00″ and length 1,250.10 m. Line B–C has bearing 355°00′00″ and length 2,000.20 m. The total centreline length is 3,250.30 m. Use main-view scale 1:12,500 at the supplied page size. Lettering may reverse reading direction on separate segments; the printed bearings are the line bearings. There is no job-specified angular cutoff for a label-direction change.

Show the subject corridor solid and the historical trail HT-4 dashed. HT-4 is context only and is not adopted as the corridor centreline. Point A is station 0+000.00; B is 1+250.10; C is 3+250.30. Width is 15.00 m each side of the centreline. A practice culvert at station 2+110.00 is context only. Use evidence marks A, B and C as schematic practice symbols; no field or legal control claim is made.

The title/notes sheet should carry subject identity, line schedule, length summary, and normal drafting notes. The second sheet should carry the main view with its line labels, north arrow, legend, station schedule, and scale bar. Distances are in metres. Review the supplied plan and state any concrete inconsistencies with these job facts or within the plan.
'''


BENCH_BRIEF = '''# Synthetic job brief — Willow Bench Access Strip

Synthetic review exercise only. All names, dates, references, dimensions, and survey marks are invented. No current regulation, real parcel, legal survey control, or legal entitlement is represented.

Prepare a wide sheet for Practice Meridian Ltd. (fictional), job WB-624, subject file SYN-WB-624, revision 1 dated 2026-09-18. The subject is a proposed 18.00 m access strip between points S1–S4 with a centreline length of 230.00 m and an area of 0.414 ha. Show the main view at 1:2500 and the culvert crossing inset at 1:500.

Use simulated NAD83(CSRS) / UTM Zone 12N for subject coordinates. Historical sketch H-17 uses a simulated Zone 11N reference and is context only; do not adopt it as subject control. Identify the subject with solid boundary lines and show historical information dashed. Dimensions are metres unless otherwise stated. Field-note reference is FN-A, dated 2026-09-14.

The inset centres on practice culvert C1 at centreline station 0+145.00. Width is 9.00 m each side of the centreline. Centreline points CL1 and CL2 carry invented local display coordinates only; the coordinate-system note is the subject spatial-reference statement. Point S1 is the southwest corner, S2 southeast, S3 northeast, and S4 northwest. Review the supplied plan and state any concrete inconsistencies with these job facts or within the plan.
'''


def mica_pdf(defective):
    d = fitz.open()
    p = d.new_page(width=842, height=1191)
    frame(p, 'MICA RIDGE CORRIDOR', 'Practice plan • title, schedules and drafting notes • invented data', 1, 2)
    text(p, 40, 106, 'PROPOSED ACCESS CORRIDOR  |  MICA RIDGE PRACTICE BLOCK', 12, True)
    field(p, 40, 124, 381, 'Client', 'Practice Talus Ltd. (fictional)')
    field(p, 421, 124, 381, 'Subject file', 'SYN-MR-831' if defective else 'SYN-MR-813')
    field(p, 40, 169, 381, 'Job / drawing', 'MR-813 / MR-813-PL-02')
    field(p, 421, 169, 381, 'Revision / date', '2 / 2026-10-06')
    field(p, 40, 214, 381, 'Reference frame', 'Simulated local grid MR-LG')
    field(p, 421, 214, 381, 'Main view / width', '1:12,500 / 30.00 m corridor')
    heading(p, (40, 280, 802, 308), 'LINE AND STATION SCHEDULE')
    cols = [40, 123, 327, 495, 648, 802]
    for x in cols: line(p, x, 308, x, 424)
    for y in [308, 341, 382, 424]: line(p, 40, y, 802, y)
    for x, s in zip([49,132,336,504,657], ['LINE', 'BEARING', 'LENGTH', 'FROM STATION', 'TO STATION']): text(p, x, 329, s, 9, True)
    for y, vals in [(367, ['A–B','345°00′00″','1,250.10 m.','0+000.00','1+250.10']), (408, ['B–C','355°00′00″','2,000.20 m.','1+250.10','3+250.30'])]:
        for x, s in zip([49,132,336,504,657], vals): text(p, x, y, s, 10.4)
    heading(p, (40, 448, 802, 476), 'LENGTH SUMMARY')
    box(p, (40, 476, 802, 548))
    text(p, 53, 500, 'Centreline A–B + B–C', 10.4, True)
    text(p, 53, 525, '1,250.10 m. + 2,000.20 m. = '+('3,150.30 m.' if defective else '3,250.30 m.'), 13)
    heading(p, (40, 572, 802, 600), 'GENERAL DRAFTING NOTES')
    box(p, (40, 600, 802, 850))
    notes = [
        '1. Dimensions are metres. Bearings are clockwise from the page north arrow.',
        '2. All identifiers, marks and coordinates are synthetic practice data.',
        '3. Proposed corridor: 30.00 m wide, 15.00 m each side of A–B–C.',
        '4. The centreline stations are carried continuously through point B.',
        '5. Historical trail HT-4 is dashed context and is not adopted as centreline.',
        '6. Point labels A, B and C identify schematic practice evidence symbols.',
        '7. Culvert at station 2+110.00 is context only; no structure dimensions adopted.',
        '8. Segment labels retain their printed line bearings where reading direction changes.',
        '9. No field survey, legal boundary, approval, tenure or real control is represented.',
        '10. Read this sheet with the main view and legend on sheet 2.'
    ]
    lines(p, 53, 624, notes, 10.3, 21.2)
    # Adjacent normal-leading fields deliberately exercise font metric overlap, not visible collisions.
    heading(p, (40, 873, 802, 901), 'DRAWING RECORD')
    fieldtwo(p, 40, 901, 381, 'Drawing team', 'Prepared: Draft Practice', 'Checked: Review Practice')
    fieldtwo(p, 421, 901, 381, 'Source / display', 'Source: invented job facts', 'Display: supplied page size')
    field(p, 40, 946, 381, 'Historical reference', 'HT-4 • context only')
    field(p, 421, 946, 381, 'Plan purpose', 'Synthetic drafting consistency review')
    box(p, (40, 1014, 802, 1109))
    lines(p, 53, 1038, [
        'SHEET REGISTER: 1 — identity, schedules and notes; 2 — main view and legend.',
        'The subject file identifies the current corridor. Historical references are separate.',
        'Page-size scale applies only to the supplied PDF at 100% print size.',
        'SYNTHETIC REVIEW ONLY • All information was invented for this exercise.'
    ], 10.1, 18.4)

    p = d.new_page(width=842, height=1191)
    frame(p, 'MICA RIDGE CORRIDOR', 'Practice plan • main view and line labels • invented data', 2, 2)
    text(p, 40, 105, 'MAIN VIEW — SCALE 1:12,500 AT SUPPLIED PAGE SIZE', 11.4, True)
    north(p, 755, 147, 60)
    heading(p, (40, 138, 269, 166), 'VIEW NOTES')
    box(p, (40, 166, 269, 338))
    lines(p, 51, 187, ['Simulated local grid MR-LG.', 'Subject centreline: A–B–C.', 'Corridor width: 30.00 m.', '15.00 m each side.', 'HT-4: historical context only.', 'Marks are schematic practice', 'symbols, not survey control.'], 9.6, 20)
    a = fitz.Point(420, 1005)
    ppm = 1000 / 12500 * 72 / 25.4
    def advance(o, bearing, length):
        r = math.radians(bearing)
        return fitz.Point(o.x + math.sin(r)*length*ppm, o.y - math.cos(r)*length*ppm)
    b = advance(a, 345, 1250.10)
    c = advance(b, 355, 2000.20)
    # A narrow surveyed strip around each straight segment; change-of-direction join is schematic.
    for start, end in [(a,b),(b,c)]:
        dx,dy = end.x-start.x,end.y-start.y
        mag=math.hypot(dx,dy); off=15*ppm
        ox,oy=-dy/mag*off,dx/mag*off
        line(p,start.x+ox,start.y+oy,end.x+ox,end.y+oy,1.0)
        line(p,start.x-ox,start.y-oy,end.x-ox,end.y-oy,1.0)
        line(p,start.x,start.y,end.x,end.y,.6,dashes='[5 3] 0')
    line(p, a.x-3.4,a.y+.9,a.x+3.4,a.y-.9,1)
    line(p, c.x-3.4,c.y+.3,c.x+3.4,c.y-.3,1)
    dot(p,a.x,a.y,'A',12,4)
    dot(p,b.x,b.y,'B',-25,0)
    dot(p,c.x,c.y,'C',13,-1)
    text(p, b.x+22, b.y+13, '345°00′00″   1,250.10 m.', 10.8, angle=285)
    text(p, b.x-14, b.y-34, '355°00′00″   2,000.20 m.', 10.8, angle=95)
    # Historical trail deliberately separate and visibly dashed.
    hist=[(510,1025),(550,885),(523,750),(562,603),(547,417),(585,286)]
    for u,v in zip(hist,hist[1:]): line(p,*u,*v,.8,MUTED,'[9 5] 0')
    text(p, 610, 462, 'HT-4 — historical trail', 10.3, angle=90)
    text(p, 588, 662, 'Context only', 9.4, angle=90)
    # Station 2+110 lies on B–C.
    cu=advance(b,355,2110-1250.10)
    line(p,cu.x-12,cu.y-5,cu.x+12,cu.y+5,1.1)
    text(p, 459, 532, 'Practice culvert', 9.8)
    text(p, 459, 548, 'Sta. 2+110.00 • context', 9.5)
    line(p, cu.x+13,cu.y,452,539,.6)
    heading(p, (40, 383, 266, 411), 'STATION REGISTER')
    box(p, (40,411,266,551))
    lines(p,52,434,['A      0+000.00','B      1+250.10','C      3+250.30','Total  3,250.30 m.'],10.4,27)
    heading(p, (40, 600, 266, 628), 'LEGEND')
    box(p,(40,628,266,772))
    line(p,53,650,92,650,1)
    text(p,104,654,'Subject boundary',9.5)
    line(p,53,678,92,678,.6,dashes='[5 3] 0')
    text(p,104,682,'Subject centreline',9.5)
    line(p,53,706,92,706,.8,dashes='[9 5] 0')
    text(p,104,710,'Historical trail HT-4',9.5)
    p.draw_circle((72,737),3,color=INK,fill=WHITE,width=.85)
    text(p,104,741,'Practice evidence mark',9.1)
    box(p,(633,820,802,1027))
    lines(p,644,844,['CURRENT SUBJECT','SYN-MR-813','Job MR-813','Revision 2','2026-10-06','','No legal or field','reliance.'],9.4,22)
    scale_bar(p, 49, 1070, 500, 5, 12500)
    text(p, 49, 1111, 'MAIN VIEW 1:12,500  •  dimensions govern', 9.1)
    return d


def raster_notes(defective):
    d=fitz.open();p=d.new_page(width=506,height=235)
    box(p,(0,0,506,235),WHITE,.8)
    box(p,(0,0,506,31),PALE,.6)
    text(p,12,21,'SITE REFERENCE / GENERAL NOTES',12,True)
    n=[
        '1. Subject reference: simulated NAD83(CSRS) /',
        '   UTM Zone '+('11N.' if defective else '12N.'),
        '2. H-17 historical reference: simulated UTM Zone 11N.',
        '   Context only; not adopted as subject control.',
        '3. Dimensions are metres; strip width is 18.00 m.',
        '4. Subject area is 0.414 ha; centreline is 230.00 m.',
        '5. C1 crossing station is 0+145.00; see inset.',
        '6. Synthetic review only; no legal or field reliance.'
    ]
    lines(p,12,52,n,11.4,22.2)
    return p.get_pixmap(matrix=fitz.Matrix(3,3),alpha=False).tobytes('png')


def bench_pdf(defective, note_image):
    d=fitz.open();p=d.new_page(width=1191,height=842)
    frame(p,'WILLOW BENCH ACCESS STRIP','Practice plan • main view, culvert inset and field notes • invented data',1,1)
    heading(p,(40,98,709,127),'MAIN VIEW')
    heading(p,(732,98,1151,127),'CULVERT CROSSING INSET')
    box(p,(40,127,709,478))
    box(p,(732,127,1151,478))
    text(p,53,151,'Scale 1:2,50' if defective else 'Scale 1:2500',12,True)
    text(p,745,151,'Scale 1:500',12,True)
    text(p,53,170,'Subject strip S1–S4 • 18.00 m width • 230.00 m centreline',9.6)
    north(p,658,183,48);north(p,1104,183,48)
    ppm=1000/2500*72/25.4
    x0,y0=126,315;length=230*ppm;width=18*ppm
    # Actual nominal scale dimensions for the subject rectangle.
    box(p,(x0,y0-width,x0+length,y0),None,1.1)
    line(p,x0,y0-width/2,x0+length,y0-width/2,.65,dashes='[5 3] 0')
    for x,y,lab,dx,dy in [(x0,y0,'S1',-23,17),(x0+length,y0,'S2',6,17),(x0+length,y0-width,'S3',6,-8),(x0,y0-width,'S4',-23,-8)]:dot(p,x,y,lab,dx,dy)
    text(p,x0+49,y0-width-17,'090°00′00″  230.00 m.',10.1)
    text(p,x0+56,y0+47,'18.00 m proposed access strip',10.1)
    line(p,88,225,484,225,.8,MUTED,'[9 5] 0')
    text(p,95,212,'H-17 — historical sketch alignment (context only)',9.3)
    cx=x0+145*ppm
    line(p,cx-4,y0-width-15,cx+4,y0+15,1.3)
    text(p,cx-14,y0+67,'C1',10.2,True)
    text(p,470,291,'Centreline',9.2)
    text(p,470,308,'0+000.00 to 0+230.00',9.2)
    line(p,x0+length+5,y0-width/2,463,300,.5)
    scale_bar(p,60,420,100,4,2500)
    text(p,315,442,'Solid: subject     Dashed: historical context',9.3)
    # Inset: 18 m strip scales to 102.05 pt high.
    wi=18*1000/500*72/25.4
    yi=301;xi=942
    line(p,763,yi-wi/2,1117,yi-wi/2,1.1)
    line(p,763,yi+wi/2,1117,yi+wi/2,1.1)
    line(p,763,yi,1117,yi,.65,dashes='[5 3] 0')
    line(p,xi-12,205,xi+12,396,1.5)
    line(p,xi-4,205,xi+20,396,.75)
    text(p,974,230,'C1 practice culvert',9.4)
    text(p,974,246,'Sta. 0+145.00',9.4)
    text(p,774,284,'9.00 m',9.3)
    text(p,774,333,'9.00 m',9.3)
    text(p,975,377,'Subject strip',9.4)
    scale_bar(p,761,420,20,4,500)
    heading(p,(40,500,626,528),'FIELD NOTES — FN-A / 2026-09-14')
    box(p,(40,528,626,735))
    # Dense native text elsewhere cannot establish coverage of the separate image-only note panel.
    for y in [556,585,614,643,672]:line(p,40,y,626,y,.5)
    for x in [111,246,432]:line(p,x,528,x,672,.5)
    for x,s in [(51,'REF.'),(122,'STATION'),(257,'OBSERVATION'),(443,'DISPLAY / NOTE')]:text(p,x,547,s,8.5,True)
    rows=[['CL1','0+000.00','Start centreline','500,000.00 / 5,900,000.00'],['C1','0+145.00','Culvert crossing','Context feature only'],['CL2','0+230.00','End centreline','500,230.00 / 5,900,000.00'],['H-17','—','Historical sketch','Simulated Zone 11N; context']]
    for y,vals in zip([576,605,634,663],rows):
        for x,s in zip([51,122,257,443],vals):text(p,x,y,s,8.5)
    lines(p,51,695,['Display coordinates above are invented local display values only.', 'Subject spatial reference is stated in the site reference notes.', 'No field survey, legal boundary, approval or real survey control is represented.'],9.0,15.5)
    p.insert_image(fitz.Rect(645,500,1151,735),stream=note_image,overlay=True)
    # Title block intentionally has no redundant numeric view-scale value.
    for x,w,label,value in [(40,279,'Client / job','Practice Meridian Ltd. / WB-624'),(319,279,'Subject file / revision','SYN-WB-624 / 1'),(598,279,'Date / scale','2026-09-18 / AS SHOWN'),(877,274,'Drawing / purpose','WB-624-PL-01 / Practice review')]:
        field(p,x,748,w,label,value)
    return d


_CASES = {"L38": ("mica", True), "P72": ("bench", False),
          "R46": ("mica", False), "U91": ("bench", True)}
CASE_IDS = tuple(sorted(_CASES))
_METADATA = {
    "title": "Synthetic review plan",
    "author": "Practice Drafting Studio (fictional)",
    "subject": "Synthetic drafting review exercise",
    "keywords": "synthetic; review only",
    "creator": "Private synthetic plan generator",
    "producer": "Private synthetic plan generator",
    "creationDate": "D:20261121090000Z",
    "modDate": "D:20261121090000Z",
}


def write_case(output_dir: Path, case_id: str) -> dict:
    """Write the original two review inputs into a new caller-owned directory.

    Unknown IDs and existing destinations are rejected without modification.
    The return value contains input names and actual SHA256 hashes only.
    """
    if not isinstance(case_id, str) or case_id not in _CASES:
        raise ValueError(f"Unknown case ID: {case_id!r}")
    output_dir = Path(output_dir)
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"Destination already exists: {output_dir}")
    family, defective = _CASES[case_id]
    drawing = mica_pdf(defective) if family == "mica" else bench_pdf(defective, raster_notes(defective))
    with drawing as document:
        document.set_metadata(_METADATA)
        plan = document.tobytes(garbage=4, deflate=True, no_new_id=True)
    brief = MICA_BRIEF if family == "mica" else BENCH_BRIEF
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
