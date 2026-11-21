"""Drawing constructors and original job briefs from synthetic trial author B.

No private authoring, oracle, preflight or renderer entry point is retained.
"""
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from runtime_security import load_pdf_runtime

fitz = load_pdf_runtime()

INK = (0.10, 0.16, 0.20)
MUTED = (0.34, 0.40, 0.43)
LINE = (0.24, 0.32, 0.36)
PALE = (0.94, 0.96, 0.96)
BLUE = (0.12, 0.34, 0.44)
WHITE = (1, 1, 1)


def box(p, r, fill=None, width=0.7):
    p.draw_rect(fitz.Rect(r), color=LINE, fill=fill, width=width)


def text(p, r, value, size=10, bold=False, color=INK, align=0):
    r = fitz.Rect(r)
    font = "hebo" if bold else "helv"
    if "\n" not in value:
        tw = fitz.get_text_length(value, fontname=font, fontsize=size)
        if tw > r.width + 0.01 or size * 1.38 > r.height + 0.01:
            raise ValueError(f"Single line does not fit {r}: {value!r}; width {tw}")
        x = r.x0 + (r.width-tw) / 2 if align == 1 else (r.x1-tw if align == 2 else r.x0)
        p.insert_text(fitz.Point(x,r.y0+size*1.075), value, fontname=font, fontsize=size, color=color)
        return
    remaining = p.insert_textbox(r, value, fontname=font,
                                fontsize=size, color=color, align=align, lineheight=1.20)
    if remaining < -0.01:
        raise ValueError(f"Text does not fit {r}: {value!r}; {remaining}")


def line(p, a, b, width=0.8, color=LINE, dash=None):
    p.draw_line(fitz.Point(a), fitz.Point(b), color=color, width=width, dashes=dash)


def north(p, x, y):
    line(p, (x, y+44), (x, y+8), 1.3)
    p.draw_polyline([fitz.Point(x-6,y+20),fitz.Point(x,y+8),fitz.Point(x+6,y+20)],color=INK,width=1.3)
    text(p,(x-12,y-10,x+12,y+8),"N",11,True,align=1)


def scale(p, x, y, segment=30, units="0        20        40 m"):
    box(p,(x,y,x+segment,y+5),INK)
    box(p,(x+segment,y,x+2*segment,y+5),WHITE)
    text(p,(x-5,y+9,x+5,y+25),"0",8,align=1)
    text(p,(x+segment-8,y+9,x+segment+8,y+25),"20",8,align=1)
    text(p,(x+2*segment-13,y+9,x+2*segment+13,y+25),"40 m",8,align=1)


def frame(p, w, h, small=False):
    box(p,(18,18,w-18,h-18),width=1)
    text(p,(25,h-16,w-25,h-3),"SYNTHETIC REVIEW ONLY - FICTIONAL ALBERTA DRAWING - NO LEGAL OR REGULATORY STATUS",6.3 if small else 7.3,align=1,color=MUTED)


def caption(p,r,label):
    box(p,r,PALE)
    text(p,(r[0]+7,r[1]+5,r[2]-7,r[3]-3),label,9,True)


BRIEFS = {
"portrait_pla": """# Synthetic drawing review request\n\nPlease check the complete supplied plan, including its diagram, schedules, notes, references and title information, for ordinary drafting mistakes and inconsistencies. Report clear issues with page locations and evidence; distinguish uncertainty from an observed mistake. This is a fictional review exercise, not a regulatory compliance assessment.\n\nRedwillow Materials Ltd. is preparing the Alder Spur extraction and access sketch, job RWM-26-418, drawing RM-418-PLA, current revision 2 dated 2026-10-28. The work is an initial illustrative PLA sketch for aggregate extraction and access on fictional Alberta Crown land at SW 14-052-16 W4M. Work instruction WI-326 is the authorized operating reference for this issue. The proposal includes extraction block Q-2 and the separate stockpile block S-1; those block identifiers are intentionally different. Historical revision rows remain part of the document record.\n\nUse the printed drawing and these job facts as the review basis. The diagram is illustrative and supplies no surveyed control network or boundary closure. No real site, owner, public requirement, approval or professional certification is represented.\n""",
"route_rtf": """# Synthetic drawing review request\n\nPlease review both complete sheets together for ordinary drafting mistakes and inconsistencies. Include the route views, schedules, notes, cross-references and sheet information. Locate supported findings and retain uncertainty where the supplied material is insufficient. This is a fictional drawing-quality exercise, not a regulatory compliance assessment.\n\nBlue Tamarack Projects Ltd. has commissioned the Clearfen temporary route sketch, job BTP-26-579, drawing BT-579-RTF. This issue is revision 1 dated 2026-10-30 and consists of two current sheets. It illustrates an initial RTF temporary water-transfer route on fictional Alberta Crown land. The west route segment lies in SE 24-064-09 W5M and the east route segment lies in NE 24-064-09 W5M. Crossing identifiers C-04 and C-05 refer to separate crossings. A superseded alignment reference remains in the historical revision entry.\n\nUse these job facts and all printed sheet information as the review basis. Chainages and scheduled distances are supplied for a schematic route; no surveyed control network, legal boundary reconstruction or current regulatory authority is provided. All names and project information are invented.\n""",
"wide_loc": """# Synthetic drawing review request\n\nPlease check the entire supplied drawing for ordinary drafting mistakes and inconsistencies, including native text in the oblique plan view and the notes at both page edges. State the page locations and evidence for clear findings, and distinguish unsupported interpretation. This is a fictional drawing-quality exercise, not a regulatory compliance assessment.\n\nNorthspoke Utility Services Ltd. is preparing the Larch Hollow water-transfer line sketch, job NUS-26-207, drawing NU-207-LOC. The authorized issue is revision 3 dated 2026-11-02, for an illustrative initial LOC proposal on fictional Alberta Crown land in NW and NE 08-047-19 W4M. The proposal uses an 18.00 m standard corridor. The stated spatial basis for this issue is NAD83(CSRS), UTM Zone 12N, with bearings referenced to illustrative Grid North. Parcels P-6 and P-7 are distinct adjoining parcels, and Detail B is intentionally enlarged. Historical revision information is retained.\n\nUse the printed drawing and these job facts as the review basis. The diagram supplies no independently accepted survey control or legal geometry. No real site, public requirement, approval or certification is represented.\n"""
}


def portrait_pla(bad):
    d=fitz.open(); p=d.new_page(width=595,height=842); frame(p,595,842)
    text(p,(34,30,561,55),"ALDER SPUR | EXTRACTION + ACCESS",17,True)
    text(p,(34,59,561,78),"REDWILLOW MATERIALS LTD.    /    PLA SKETCH    /    ALBERTA",10,color=BLUE)
    caption(p,(32,88,563,113),"DRAWING NOTES")
    notes=[
        "1. Location: SW 14-052-16 W4M. All project information is fictional.",
        "2. Proposed extraction block Q-2 and stockpile block S-1 have separate uses.",
        f"3. Stockpile operating limits follow work instruction {'WI-263' if bad else 'WI-326'}.",
        "4. Distances in metres. Diagram geometry is illustrative; use the printed schedule.",
        "5. Bearings are illustrative Grid North. No accepted survey control is supplied."
    ]
    for i,n in enumerate(notes): text(p,(40,120+i*19,554,137+i*19),n,9.1)
    caption(p,(32,223,563,248),"MAIN DIAGRAM - SCHEMATIC")
    box(p,(76,284,286,442),(0.91,0.95,0.91),1.2)
    text(p,(90,315,272,338),"EXTRACTION BLOCK Q-2",11,True,align=1)
    text(p,(105,342,257,366),"Proposed aggregate site",10,align=1)
    box(p,(315,300,430,376),(0.96,0.95,0.90),1.0)
    text(p,(323,315,422,335),"STOCKPILE S-1",10,True,align=1)
    text(p,(323,341,422,361),"Separate block",8.7,align=1)
    line(p,(286,402),(365,402),8,color=(0.77,0.83,0.85))
    line(p,(365,402),(490,472),8,color=(0.77,0.83,0.85))
    line(p,(286,402),(365,402),0.8); line(p,(365,402),(490,472),0.8)
    text(p,(297,383,413,400),"A - 124.50 m",9)
    text(p,(395,397,525,415),"B - 86.25 m",9)
    text(p,(399,477,533,497),"Existing access track",9)
    line(p,(56,493),(516,493),1.0,dash="[6 4]")
    text(p,(68,501,400,520),"Illustrative road allowance - not a reconstructed boundary",8.7)
    north(p,510,280)
    # Deliberately different detail scale, clearly labelled.
    box(p,(45,548,216,629),WHITE)
    text(p,(53,554,207,575),"DETAIL A - ENLARGED VIEW",8.7,True)
    line(p,(64,604),(188,604),7,color=(0.77,0.83,0.85))
    line(p,(126,595),(126,610),0.8)
    text(p,(54,578,206,594),"Gate and track junction",8.5)
    text(p,(55,612,205,626),"Detail schematic; no scale",7.8)
    box(p,(230,548,550,629),PALE)
    text(p,(240,556,541,575),"ACCESS LENGTH CALCULATION",10,True)
    text(p,(240,580,541,600),"A 124.50 m  +  B 86.25 m",10)
    text(p,(240,604,541,623),f"TOTAL ACCESS LENGTH = {'211.75' if bad else '210.75'} m",10,True)
    # Horizontal bottom title block gives this family a distinct reading order.
    box(p,(32,646,563,805))
    line(p,(32,676),(563,676)); line(p,(32,718),(563,718));line(p,(32,764),(563,764))
    line(p,(345,676),(345,805))
    text(p,(41,653,553,673),"ALDER SPUR - EXTRACTION AND ACCESS SKETCH",11,True)
    text(p,(41,684,336,714),"Job RWM-26-418\nDrawing RM-418-PLA",9)
    text(p,(355,684,553,714),"Revision 2  |  2026-10-28\nSheet 1 of 1",9)
    text(p,(41,726,335,757),"CURRENT ISSUE: INITIAL ILLUSTRATIVE PLA\nPrepared by: Redwillow drafting group",8.7)
    text(p,(355,726,552,757),"Units: metres\nSpatial basis: illustrative only",8.7)
    text(p,(41,772,335,799),"REVISION RECORD (HISTORICAL)\nRev 1, 2026-09-18: WI-281 retained in archive",8)
    text(p,(355,772,553,799),"Rev 2, 2026-10-28\nCurrent issue authorized for QA exercise",8)
    return d


def route_rtf(bad):
    d=fitz.open()
    for sn in (1,2):
        p=d.new_page(width=842,height=595); frame(p,842,595)
        box(p,(30,30,812,115))
        box(p,(30,30,176,115),PALE)
        text(p,(40,40,168,61),"BLUE TAMARACK",13,True)
        text(p,(40,67,168,104),"PROJECTS LTD.\nALBERTA / RTF",10)
        text(p,(192,39,639,64),"CLEARFEN TEMPORARY ROUTE",17,True)
        text(p,(192,71,635,94),"WEST SEGMENT" if sn==1 else "EAST SEGMENT",11,color=BLUE)
        job="BTP-26-597" if bad and sn==2 else "BTP-26-579"
        text(p,(660,39,803,104),f"Job {job}\nBT-579-RTF\nRev 1 / 2026-10-30",9.3)
        text(p,(33,124,804,146),"LOCATION: " + ("SE 24-064-09 W5M" if sn==1 else "NE 24-064-09 W5M") + "    |    Synthetic Crown-land route illustration",10,True)
        # Route enters/exits page margins, with explicit cross-sheet match-line names.
        line(p,(70,202),(770,202),0.8,dash="[6 4]")
        text(p,(75,180,590,198),"Illustrative section context line - no cadastral boundary reconstruction",8.8)
        pts=([(75,324),(260,324),(458,278),(758,278)] if sn==1 else [(75,278),(286,278),(489,324),(762,324)])
        p.draw_polyline([fitz.Point(v) for v in pts],color=(0.77,0.85,0.87),width=17)
        p.draw_polyline([fitz.Point(v) for v in pts],color=INK,width=0.8)
        cp=260 if sn==1 else 489
        cy=324
        line(p,(cp,cy-54),(cp,cy+50),1.3)
        text(p,(cp-63,cy+57,cp+78,cy+77),"Crossing C-04" if sn==1 else "Crossing C-05",9,True)
        stations=[("0+000",75,324),("0+075",458,278),("0+150",758,278)] if sn==1 else [("0+150",75,278),("0+225",286,278),("0+300",762,324)]
        for lab,x,y in stations:
            p.draw_circle(fitz.Point(x,y),3.5,color=INK,fill=WHITE)
            if sn==2 and lab=="0+150":
                text(p,(x+8,y-27,x+80,y-7),lab,9,True)
            else:
                text(p,(x-30,y-27,x+42,y-7),lab,9,True)
        mx=777 if sn==1 else 60
        line(p,(mx,230),(mx,360),1,dash="[4 3]")
        if sn==1:
            text(p,(587,365,806,397),"MATCH A at 0+150\nContinues on Sheet 2",9,True,align=2)
        else:
            text(p,(36,366,256,397),"MATCH A at 0+150\nContinued from Sheet 1",9,True)
        north(p,727,152)
        caption(p,(34,414,401,438),"DISTANCE SCHEDULE - EXPLICIT CHAINAGE INTERVALS")
        box(p,(34,438,401,502))
        rows=[("0+000 to 0+075","75.00 m"),("0+075 to 0+150","75.00 m"),("SHEET SEGMENT TOTAL","150.00 m")] if sn==1 else [("0+150 to 0+225","75.00 m"),("0+225 to 0+300","75.00 m"),("SHEET SEGMENT TOTAL","150.00 m")]
        for i,(a,b) in enumerate(rows):
            text(p,(43,444+i*18,298,460+i*18),a,8.6,bold=(i==2))
            text(p,(303,444+i*18,392,460+i*18),b,8.6,bold=(i==2),align=2)
        box(p,(416,414,807,502),PALE)
        text(p,(425,422,798,495),"NOTES\nDistances in metres; route geometry is schematic.\nIllustrative Grid North; no accepted control supplied.\nDifferent crossing IDs designate separate crossings.",9)
        box(p,(33,516,808,563))
        line(p,(557,516),(557,563))
        text(p,(42,523,547,557),"HISTORY: Rev 0, 2026-09-23 - alignment CF-A superseded.\nCURRENT ISSUE: Rev 1 - alignment CF-B, route total 300.00 m.",8.6)
        sheetnum=1 if bad and sn==2 else sn
        text(p,(568,523,799,555),f"DRAWING BT-579-RTF  |  RTF\nSheet {sheetnum} of 2  |  QA issue 2026-10-30",8.6,True)
    return d


def rot_text(p,xy,value,angle=14.5,size=10,bold=False):
    pt=fitz.Point(xy)
    p.insert_text(pt,value,fontname="hebo" if bold else "helv",fontsize=size,color=INK,morph=(pt,fitz.Matrix(angle)))


def wide_loc(bad):
    d=fitz.open();p=d.new_page(width=1100,height=520);frame(p,1100,520)
    # A wide folded-sheet arrangement: information runs across both long edges.
    box(p,(31,29,1069,123))
    line(p,(343,29),(343,123));line(p,(750,29),(750,123))
    text(p,(42,38,333,63),"LARCH HOLLOW",18,True)
    text(p,(42,71,333,114),"WATER-TRANSFER LINE / LOC\nNORTHSPOKE UTILITY SERVICES LTD.",10.3)
    text(p,(354,38,740,114),"LOCATION: NW and NE 08-047-19 W4M\nStandard corridor: 18.00 m\nBasis: NAD83(CSRS), UTM Zone 12N\nBearings: illustrative Grid North",10)
    text(p,(761,38,1059,114),"Job NUS-26-207  |  NU-207-LOC\nRev 3  |  2026-11-02  |  Sheet 1 of 1\nSynthetic Crown-land proposal\nInitial issue for drawing-quality review",10)
    text(p,(44,136,659,158),"OBLIQUE MAIN PLAN VIEW - NATIVE LABELS FOLLOW THE CORRIDOR",10,True,color=BLUE)
    # Oblique schematic corridor, full width is 18m at nominal scale 1:1500.
    a=(269,335);length_pt=300*72/(1500*0.0254);theta=math.radians(14.5)
    b=(a[0]+length_pt*math.cos(theta),a[1]-length_pt*math.sin(theta))
    v=(b[0]-a[0],b[1]-a[1]);l=math.hypot(*v);half_width=18*72/(1500*0.0254)/2
    n=(-v[1]/l*half_width,v[0]/l*half_width)
    poly=[(a[0]+n[0],a[1]+n[1]),(b[0]+n[0],b[1]+n[1]),(b[0]-n[0],b[1]-n[1]),(a[0]-n[0],a[1]-n[1]),(a[0]+n[0],a[1]+n[1])]
    p.draw_polyline([fitz.Point(x) for x in poly],color=BLUE,fill=(0.90,0.95,0.97),width=1.1,closePath=True)
    line(p,a,b,0.7,dash="[7 4]")
    # Parcel divider and clearly different parcel identifiers are legitimate.
    line(p,(590,157),(590,351),0.8,dash="[3 3]")
    rot_text(p,(334,260),"PARCEL P-6 / NW 08",14.5,10)
    rot_text(p,(654,175),"PARCEL P-7 / NE 08",14.5,10)
    rot_text(p,(411,341),"Larch Hollow transfer line",14.5,11,True)
    rot_text(p,(257,376),"START 0+000",14.5,9)
    rot_text(p,(749,247),"END 0+300",14.5,9)
    # A transverse dimension is repeated from the authorized standard width.
    cx,cy=645,238
    line(p,(cx+n[0],cy+n[1]),(cx-n[0],cy-n[1]),0.9)
    line(p,(cx+n[0]-5,cy+n[1]+1),(cx+n[0]+5,cy+n[1]-1),0.9)
    line(p,(cx-n[0]-5,cy-n[1]+1),(cx-n[0]+5,cy-n[1]-1),0.9)
    rot_text(p,(664,230),"1.80 m" if bad else "18.00 m",14.5,10,True)
    north(p,1005,158)
    scale(p,907,235,20*72/(1500*0.0254),"0         20         40 m")
    text(p,(905,265,1045,285),"Nominal view scale 1:1500",8.5)
    # Detail is intentionally shown at a distinct, explicitly stated nominal scale.
    box(p,(41,191,213,336),WHITE)
    text(p,(50,200,204,221),"DETAIL B / 1:300",10,True)
    line(p,(64,272),(185,272),24,color=(0.9,0.95,0.97));line(p,(64,260),(185,260));line(p,(64,284),(185,284))
    p.draw_circle(fitz.Point(123,272),7,color=INK,fill=WHITE)
    text(p,(52,295,204,327),"Valve protection detail\nEnlarged, independent view",8.7)
    box(p,(31,393,1069,485))
    line(p,(401,393),(401,485));line(p,(773,393),(773,485))
    zone="11N" if bad else "12N"
    text(p,(42,403,391,477),f"PLAN NOTES\n1. Basis of bearings: NAD83(CSRS), UTM Zone {zone}.\n2. Bearings refer to illustrative Grid North.\n3. Drawing geometry is illustrative; no closure supplied.",9)
    text(p,(412,403,762,477),"REFERENCE / USE NOTES\n4. T-14 is a tie-only reference; it is not accepted control.\n5. Units: metres. Different parcel identifiers are intentional.\n6. All site, company and project facts are fictional.",9)
    text(p,(784,403,1057,477),"REVISION RECORD\nRev 2, 2026-09-29: valve detail expanded.\nRev 3, 2026-11-02: current QA issue.\nNU-207-LOC  /  Initial LOC illustration",9)
    return d

