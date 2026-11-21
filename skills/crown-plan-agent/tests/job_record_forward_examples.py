"""Recreate original invented forward-review bundles; no work documents.

The two phases retain their independent authors' original layouts and text.
Published cases are now regressions, not fresh blind inputs. Expectations,
original byte hashes and separate historical attribution live in the truth file.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / 'engine'))
from runtime_security import load_pdf_runtime

fitz = None  # initialized only when original PDFs are actually generated/read
TRUTH_SHA256 = '2028dbcf02407a555cbe79da7a8a53534df2f9413e3b379a3e698652c6ba5dc5'
MAX_TRUTH_BYTES = 2 * 1024 * 1024
ORIGINAL_GENERATOR_SHA256 = 'c81088869af06c692f323e27238139a7b5b5ae459665387d5880c8a57a9e4f89'

DENSE_ORIGINAL_GENERATOR_SHA256 = '5d01f8676b42a8ae84ac982c14d1217328d480f3f8c80e5b25f19662bcf0775a'

INK = (0.12, 0.19, 0.24)

MUTED = (0.34, 0.40, 0.43)

BLUE = (0.13, 0.32, 0.46)

RULE = (0.60, 0.67, 0.70)

PALE = (0.94, 0.97, 0.98)

GREEN = (0.86, 0.94, 0.88)

GOLD = (0.99, 0.94, 0.76)

CASES = [
    dict(case='H4P7', job='NF-260847', stage='New LOC application', loc='NEW - application 26-LOC-48071',
         legal='NE 1/4 Sec. 14, Twp. 61, Rge. 17, W5M', applicant='Alderwake Passage Ltd.',
         client='9246810', operator='Cinderfen Energy Ltd.', operator_id='9372016',
         occupant='Latchmere Range Co-operative Ltd.', occupant_id='9287443',
         survey='Meridian Thistle Surveys Ltd.', survey_id='9514208',
         drawing='NF-260847-LOC-01', rev='B', date='2026-11-17', rotation=0,
         length='720.00', width='20.00', new='1.440', temp='0.240', total='1.680',
         plan_overrides={}, references=None),
    dict(case='M8R2', job='OR-261093', stage='LOC amendment application', loc='LOC 971462',
         legal='SE 1/4 Sec. 22, Twp. 67, Rge. 8, W6M', applicant='Brackenwake Access Ltd.',
         client='9183052', operator='Tarnquill Resources Ltd.', operator_id='9418872',
         occupant='Farwhistle Grazing Association Ltd.', occupant_id='9365074',
         survey='Juniper Meridian Surveys Ltd.', survey_id='9563021',
         drawing='OR-261093-LOC-02', rev='C', date='2026-11-17', rotation=180,
         existing='2.760', addition='0.420', removal='0.180', retained='2.580', post='3.000',
         temp='0.120', total='3.120', plan_overrides={},
         references=dict(approval='26-AR-3175', rev='B', date='2026-07-09', drawing='OR-261093-BASE-01',
                         area='2.760', supplied_rev='B', supplied_date='2026-07-09', current=True)),
    dict(case='Q6T9', job='FA-260526', stage='New LOC application', loc='NEW - application 26-LOC-50623',
         legal='SW 1/4 Sec. 9, Twp. 72, Rge. 12, W5M', applicant='Mossquay Passage Ltd.',
         client='9271054', operator='Hollowlark Energy Inc.', operator_id='9462781',
         occupant='Pineglass Range Co-operative Ltd.', occupant_id='9328085',
         survey='Cairnleaf Geomatics Ltd.', survey_id='9548103',
         drawing='FA-260526-LOC-01', rev='A', date='2026-11-16', rotation=90,
         length='620.00', width='20.00', new='1.240', temp='0.360', total='1.600',
         plan_overrides=dict(new='1.160', temp='0.440'), references=None),
    dict(case='V3K5', job='KL-261204', stage='New LOC application', loc='NEW - application 26-LOC-52786',
         legal='NW 1/4 Sec. 31, Twp. 58, Rge. 21, W5M', applicant='Twinfallow Crossing Ltd.',
         client='9196047', operator='Stoneglen Way Energy Ltd.', operator_id='9436705',
         occupant='Briarplateau Grazing Ltd.', occupant_id='9352019',
         survey='Willowcombe Surveys Ltd.', survey_id='9574086',
         drawing='KL-261204-LOC-01', rev='B', date='2026-11-18', rotation=180,
         length='660.00', width='20.00', new='1.320', temp='0.180', total='1.500',
         plan_overrides=dict(applicant='Stoneglen Way Energy Ltd.'), references=None),
    dict(case='X7N4', job='PE-260738', stage='LOC amendment application', loc='LOC 982357',
         legal='NE 1/4 Sec. 6, Twp. 64, Rge. 4, W6M', applicant='Reedharbour Route Ltd.',
         client='9256083', operator='Amberhollow Energy Ltd.', operator_id='9442197',
         occupant='Silverheath Range Association Ltd.', occupant_id='9304861',
         survey='Ironfern Geomatics Ltd.', survey_id='9581270',
         drawing='PE-260738-LOC-03', rev='D', date='2026-11-18', rotation=90,
         existing='2.480', addition='0.320', removal='0.140', retained='2.340', post='2.660',
         temp='0.100', total='2.760', plan_overrides=dict(retained='2.280'),
         references=dict(approval='26-AR-2846', rev='C', date='2026-06-24', drawing='PE-260738-BASE-02',
                         area='2.480', supplied_rev='C', supplied_date='2026-06-24', current=True)),
    dict(case='Z2C8', job='SV-261316', stage='LOC amendment application', loc='LOC 963814',
         legal='SW 1/4 Sec. 17, Twp. 69, Rge. 15, W5M', applicant='Fernquill Routes Ltd.',
         client='9227106', operator='Eastmorrow Energy Ltd.', operator_id='9481032',
         occupant='Greywren Grazing Co-operative Ltd.', occupant_id='9342758',
         survey='Aldercompass Surveys Ltd.', survey_id='9536049',
         drawing='SV-261316-LOC-04', rev='E', date='2026-11-18', rotation=0,
         existing='3.020', addition='0.180', removal='0.060', retained='2.960', post='3.140',
         temp='0.080', total='3.220', plan_overrides={},
         references=dict(approval='26-AR-6042', rev='D', date='2026-08-18', drawing='SV-261316-BASE-03',
                         area='2.900', supplied_rev='C', supplied_date='2025-09-04', current=False)),
]

def txt(page, x, y, value, size=10, font='helv', color=INK, rotate=0):
    page.insert_text((x, y), str(value), fontsize=size, fontname=font, color=color, rotate=rotate)

def wrapped(page, x, y, value, width, size=9.5, color=INK, leading=14):
    words = str(value).split()
    line = ''
    for word in words:
        cand = (line + ' ' + word).strip()
        if line and fitz.get_text_length(cand, fontname='helv', fontsize=size) > width:
            txt(page, x, y, line, size=size, color=color)
            y += leading
            line = word
        else:
            line = cand
    if line:
        txt(page, x, y, line, size=size, color=color)
        y += leading
    return y

def line(page, x1, y1, x2, y2, color=RULE, width=0.7):
    page.draw_line((x1, y1), (x2, y2), color=color, width=width)

def rect(page, x1, y1, x2, y2, fill=None, color=RULE, width=0.7):
    page.draw_rect(fitz.Rect(x1, y1, x2, y2), color=color, fill=fill, width=width)

def header(page, title, subtitle, job, doc_label):
    w, h = page.rect.width, page.rect.height
    rect(page, 18, 18, w - 18, h - 18, color=INK, width=1)
    rect(page, 18, 18, w - 18, 43, fill=PALE, color=PALE)
    txt(page, 30, 34, 'INVENTED EVALUATION MATERIAL - NO ACTUAL LAND OR COMPANY', 8.5, color=MUTED)
    txt(page, 32, 70, title, 18, 'hebo', BLUE)
    txt(page, 32, 89, subtitle, 10, color=MUTED)
    txt(page, 32, h - 31, f'{job} | {doc_label} | Page 1 of 1', 8, color=MUTED)
    txt(page, w - 230, h - 31, 'All areas in hectares unless stated', 8, color=MUTED)

def field(page, x, y, label, value, width=430, size=10.5):
    txt(page, x, y, label.upper(), 7.8, 'hebo', MUTED)
    # Each field value is deliberately one native text insertion / font span.
    txt(page, x, y + 15, value, size)
    line(page, x, y + 22, x + width, y + 22)

def area_rows(c, plan=False):
    values = dict(c)
    if plan:
        values.update(c['plan_overrides'])
    if c['references'] is None:
        return [
            ('New permanent LOC area', values['new']),
            ('Temporary workspace outside LOC', values['temp']),
            ('Total application footprint', values['total']),
        ]
    return [
        ('Approved LOC area before amendment', values['existing']),
        ('Area removed from LOC', values['removal']),
        ('Balance retained in LOC', values['retained']),
        ('Area added to LOC', values['addition']),
        ('Post-amendment permanent LOC area', values['post']),
        ('Temporary workspace outside LOC', values['temp']),
        ('Total application footprint', values['total']),
    ]

def area_table(page, x, y, width, rows, rowheight=27):
    rect(page, x, y, x + width, y + 27, fill=PALE)
    txt(page, x + 10, y + 18, 'AREA SCHEDULE', 10, 'hebo', BLUE)
    txt(page, x + width - 62, y + 18, 'AREA (ha)', 8.5, 'hebo', BLUE)
    y += 27
    for label, value in rows:
        rect(page, x, y, x + width, y + rowheight)
        txt(page, x + 10, y + 18, label, 9.2)
        txt(page, x + width - 58, y + 18, value, 10.4, 'hebo')
        y += rowheight
    return y

def save_doc(doc, path):
    doc.set_metadata({'title': path.stem, 'author': 'Invented Evaluation Fixtures',
                      'subject': 'Synthetic native PDF review input', 'creator': 'PyMuPDF fixture author',
                      'producer': 'PyMuPDF', 'creationDate': 'D:20261119090000Z',
                      'modDate': 'D:20261119090000Z'})
    doc.save(str(path), garbage=4, deflate=True, no_new_id=True)
    doc.close()

def plan(c, path):
    values = dict(c)
    values.update(c['plan_overrides'])
    doc = fitz.open()
    p = doc.new_page(width=1008, height=720)
    header(p, 'SKETCH PLAN - ACCESS ROAD', c['stage'] + ' | Alberta public land | Review issue', c['job'], 'PLAN')
    field(p, 34, 116, 'Project / drawing', c['job'] + ' / ' + c['drawing'], width=552)
    field(p, 610, 116, 'Plan revision and issue date', c['rev'] + ' / ' + c['date'], width=362)
    field(p, 610, 164, 'Applicant', values['applicant'], width=362)
    field(p, 610, 212, 'Applicant client identifier', c['client'], width=362)
    field(p, 610, 260, 'Disposition / application', c['loc'], width=362)
    field(p, 610, 308, 'Legal description', c['legal'], width=362, size=10)

    # Boundary sketch and symbols; reviewer task is records reconciliation, not closure.
    rect(p, 34, 158, 586, 494)
    txt(p, 46, 177, 'BOUNDARY DETAIL - DIAGRAMMATIC; DIMENSIONS GOVERN', 8.5, 'hebo', MUTED)
    txt(p, 495, 204, 'N', 12, 'hebo', BLUE)
    line(p, 499, 238, 499, 210, BLUE, 1.5)
    line(p, 499, 210, 493, 220, BLUE, 1.5)
    line(p, 499, 210, 505, 220, BLUE, 1.5)
    txt(p, 60, 210, 'Quarter-section boundary', 8.7, color=MUTED)
    for dash in range(62, 557, 20):
        line(p, dash, 222, min(dash + 12, 557), 222, RULE, 0.6)
    rect(p, 84, 289, 521, 315, fill=GREEN, color=BLUE, width=1)
    rect(p, 417, 315, 500, 359, fill=GOLD, color=BLUE, width=0.9)
    txt(p, 424, 336, 'TEMPORARY', 7.8, 'hebo')
    txt(p, 424, 349, 'WORKSPACE', 7.8, 'hebo')
    line(p, 84, 275, 521, 275, INK, 0.7)
    line(p, 84, 271, 84, 279, INK)
    line(p, 521, 271, 521, 279, INK)
    if c['references'] is None:
        txt(p, 103, 306, 'PERMANENT LOC CORRIDOR', 9.7, 'hebo', BLUE)
        txt(p, 226, 267, c['length'] + ' m  /  90 deg 00 min 00 sec', 9)
        txt(p, 65, 358, c['width'] + ' m corridor width', 8.8, rotate=90)
    else:
        rect(p, 84, 289, 162, 315, fill=(0.99, 0.89, 0.88), color=BLUE, width=0.9)
        rect(p, 521, 289, 556, 315, fill=(0.79, 0.89, 0.98), color=BLUE, width=0.9)
        txt(p, 187, 306, 'RETAINED LOC CORRIDOR', 9.7, 'hebo', BLUE)
        txt(p, 87, 304, 'REMOVAL', 7.5, 'hebo')
        txt(p, 524, 307, 'ADD', 7, 'hebo')
        txt(p, 213, 267, 'Existing corridor with amendment limits', 9)
        txt(p, 70, 356, 'Widths vary - see area schedule', 8, rotate=90)
    txt(p, 54, 389, 'Landowner: His Majesty the King in right of Alberta', 8.9)
    txt(p, 54, 410, 'Surface occupant / grazing lessee:', 7.8, 'hebo', MUTED)
    txt(p, 54, 426, c['occupant'], 9.8)
    if c['rotation'] == 180:
        txt(p, 554, 466, 'ADJOINING QUARTER - OUTSIDE APPLICATION LIMITS', 8, color=MUTED, rotate=180)
    elif c['rotation'] == 90:
        txt(p, 568, 457, c['legal'], 8.4, color=MUTED, rotate=90)
    else:
        txt(p, 54, 466, 'Quarter-section grid shown for location only', 8.5, color=MUTED)

    end = area_table(p, 610, 361, 362, area_rows(c, True), rowheight=24)
    notes_y = end + 15
    txt(p, 610, notes_y, 'Temporary workspace is outside the permanent LOC.', 8.1, color=MUTED)
    if c['references']:
        wrapped(p, 610, notes_y + 14, 'Balance retained = approved area less removal. Post-amendment LOC = retained plus addition.', 355, 8.1, MUTED, 11)
    else:
        wrapped(p, 610, notes_y + 14, 'Total application footprint = new permanent LOC plus temporary workspace.', 355, 8.1, MUTED, 11)

    field(p, 34, 516, 'Operator - operational contact only', c['operator'], width=552)
    field(p, 34, 564, 'Prepared by - survey firm', c['survey'], width=552)
    field(p, 34, 612, 'Issue purpose / units', 'AER LOC records review / metres and hectares', width=552)
    txt(p, 610, 658, 'LEGEND', 8.5, 'hebo', BLUE)
    rect(p, 659, 647, 673, 659, fill=GREEN, color=BLUE)
    txt(p, 680, 657, 'LOC corridor', 8)
    rect(p, 764, 647, 778, 659, fill=GOLD, color=BLUE)
    txt(p, 785, 657, 'Workspace outside LOC', 8)
    save_doc(doc, path)

def application(c, path):
    doc = fitz.open()
    p = doc.new_page(width=612, height=792)
    header(p, 'APPLICATION RECORD', c['stage'] + ' | submitted 2026-11-18', c['job'], 'APPLICATION')
    field(p, 34, 116, 'Job / requested drawing', c['job'] + ' / ' + c['drawing'] + ' Rev ' + c['rev'], width=544)
    field(p, 34, 164, 'Applicant legal name', c['applicant'], width=352)
    field(p, 410, 164, 'Applicant client ID', c['client'], width=168)
    field(p, 34, 212, 'Disposition / application', c['loc'], width=544)
    field(p, 34, 260, 'Legal description', c['legal'], width=544)
    txt(p, 34, 316, 'PROJECT AREA REQUEST', 10, 'hebo', BLUE)
    table_end = area_table(p, 34, 328, 544, area_rows(c), rowheight=23)
    y = table_end + 20
    if c['references']:
        refs = c['references']
        txt(p, 34, y, 'GOVERNING EXISTING-AREA RECORD IDENTIFIED BY APPLICANT', 8.2, 'hebo', MUTED)
        txt(p, 34, y + 16, refs['approval'] + ' / ' + refs['drawing'] + ' Rev ' + refs['rev'] + ' / signed ' + refs['date'], 9.5)
        y += 39
        y = wrapped(p, 34, y, 'Permanent area balance: retained = existing approved area less removal; post-amendment = retained plus addition. Workspace is outside the LOC and excluded from that balance.', 544, 8.5, INK, 12)
    else:
        y = wrapped(p, 34, y, 'Permanent LOC and temporary workspace are separate requested categories. The footprint total is their sum. No existing LOC area or prior approved plan is claimed for this new application.', 544, 8.5, INK, 12)
    y += 9
    txt(p, 34, y, 'ROLE CONTACTS (THESE DO NOT CHANGE THE APPLICANT)', 8.2, 'hebo', MUTED)
    txt(p, 34, y + 16, 'Operator: ' + c['operator'], 9.1)
    txt(p, 34, y + 32, 'Surface occupant: ' + c['occupant'], 9.1)
    txt(p, 34, y + 48, 'Survey firm: ' + c['survey'], 9.1)
    y += 68
    wrapped(p, 34, y, 'Landowner: His Majesty the King in right of Alberta. Role contacts and the registry extract are supplied to distinguish applicant identity from operating, occupancy and survey roles.', 544, 8.2, MUTED, 11)
    save_doc(doc, path)

def registry(c, path):
    doc = fitz.open()
    p = doc.new_page(width=612, height=792)
    header(p, 'CLIENT REGISTRY EXTRACT', 'Invented registry | extract issued 2026-11-19 | status as of 2026-11-19', c['job'], 'REGISTRY')
    txt(p, 34, 121, 'Related job: ' + c['job'], 11, 'hebo')
    wrapped(p, 34, 143, 'This extract confirms the current registered legal names for the four entities supplied with this job. Application roles come from the application record; registry inclusion alone does not establish the applicant role.', 544, 9.4, INK, 14)
    entities = [
        ('APPLICANT ENTITY', c['applicant'], c['client'], '2026-03-11'),
        ('OPERATOR ENTITY', c['operator'], c['operator_id'], '2025-11-06'),
        ('SURFACE OCCUPANT / GRAZING LESSEE', c['occupant'], c['occupant_id'], '2024-07-23'),
        ('SURVEY FIRM', c['survey'], c['survey_id'], '2025-02-19'),
    ]
    y = 211
    for role, name, ident, effective in entities:
        rect(p, 34, y, 578, y + 102)
        rect(p, 34, y, 578, y + 25, fill=PALE)
        txt(p, 45, y + 17, role, 9, 'hebo', BLUE)
        txt(p, 45, y + 46, name, 12, 'hebo')
        txt(p, 45, y + 66, 'Client identifier: ' + ident, 10)
        txt(p, 280, y + 66, 'Status: ACTIVE', 10)
        txt(p, 45, y + 86, 'Current legal-name record effective: ' + effective, 9, color=MUTED)
        y += 115
    wrapped(p, 34, 695, 'Landowner is the Crown in right of Alberta. None of the listed private entities is identified as the landowner. Names are invented and are not extracts from any live registry.', 544, 9, MUTED, 13)
    save_doc(doc, path)

def approved(c, path):
    refs = c['references']
    doc = fitz.open()
    p = doc.new_page(width=1008, height=720)
    header(p, 'APPROVED RECORD COPY', 'Invented public-land record | supplied for records comparison', c['job'], 'APPROVED RECORD')
    field(p, 34, 116, 'Disposition', c['loc'], width=440)
    field(p, 508, 116, 'Approval reference', refs['approval'], width=464)
    field(p, 34, 164, 'Legal description', c['legal'], width=938)
    field(p, 34, 212, 'Holder at record issue', c['applicant'], width=440)
    field(p, 508, 212, 'Client identifier', c['client'], width=464)
    field(p, 34, 260, 'Approved drawing', refs['drawing'], width=440)
    field(p, 508, 260, 'Record revision / signed date', refs['supplied_rev'] + ' / ' + refs['supplied_date'], width=464)
    txt(p, 34, 325, 'RECORD STATUS', 9, 'hebo', BLUE)
    if refs['current']:
        txt(p, 34, 348, 'CURRENT APPROVED BASELINE FOR THE PRESENT AMENDMENT', 13, 'hebo')
        wrapped(p, 34, 374, 'The approved permanent LOC extent recorded below is the existing-area baseline for the amendment application identified by this job. This record precedes the proposed additions and removals.', 924, 10, INK, 15)
    else:
        txt(p, 34, 348, 'ARCHIVE COPY - SUPERSEDED RECORD', 13, 'hebo')
        wrapped(p, 34, 374, 'This supplied copy is Revision ' + refs['supplied_rev'] + ' only. The controlled-record index identifies Revision ' + refs['rev'] + ', signed ' + refs['date'] + ', as the current approved baseline. Revision ' + refs['rev'] + ' is not included in this archive extract.', 924, 10, INK, 15)
    rect(p, 34, 430, 972, 501, fill=PALE)
    txt(p, 49, 452, 'PERMANENT LOC AREA APPROVED BY THIS RECORD', 9, 'hebo', MUTED)
    txt(p, 49, 482, refs['area'] + ' ha', 20, 'hebo', BLUE)
    txt(p, 340, 482, 'Temporary workspace: not part of this permanent-area record', 10)
    txt(p, 34, 542, 'Approved-record scope: existing LOC corridor only', 11, 'hebo')
    wrapped(p, 34, 565, 'No proposed amendment addition or removal is approved by this record copy. Application area values must be compared against a governing approved record whose disposition, drawing, revision and date match the current baseline identified in the application.', 924, 10, INK, 15)
    field(p, 34, 625, 'Record custodian / certification note', 'Invented Records Desk / evaluation copy; no real approval is represented', width=938)
    save_doc(doc, path)

COMMON_REVIEW = '''Review the supplied sketch plan at the AER LOC application stage. Reconcile its applicant and client identity, disposition or application identity, legal description, plan revision and each printed area category against the supplied job records. Treat operator, surface occupant/grazing lessee, landowner and survey firm as distinct roles. Use the application to determine the requested categories and the controlled-record identity; use the registry for current legal-name evidence. Check the printed areas using the category meanings and equations in the job brief. Where a governing current record is not established by the supplied files, state the unresolved point and the additional evidence needed. Boundary closure and professional certification are outside this exercise.'''

def brief(c):
    refs = c['references']
    scope = ('New permanent LOC area and temporary workspace outside the LOC are distinct application categories. Total application footprint is their sum.' if refs is None else 'Approved existing LOC, removal, retained balance, addition and post-amendment LOC are permanent-area categories. Retained = existing minus removal; post-amendment = retained plus addition. Temporary workspace lies outside the LOC; total footprint = post-amendment LOC plus workspace.')
    current = ('No existing disposition approval is relied on for this new application.' if refs is None else 'The application identifies the governing approved baseline by approval, drawing, revision and signed date. Establish that identity before using any supplied approved area as the current baseline.')
    return '\n'.join([
        '# Invented job brief', '',
        f'Bundle: {c["case"]}',
        f'Job reference: {c["job"]}',
        f'Plan in scope: {c["drawing"]}, Revision {c["rev"]}, issued {c["date"]}.',
        f'Application stage: {c["stage"]} for an Alberta AER LOC access-road sketch plan.',
        'Review date: 2026-11-19. All company names, job references, client identifiers, disposition identities and legal parcels in this bundle are invented.', '',
        '## Record use', '',
        'The application was submitted on 2026-11-18. The client registry extract is issued and current as of 2026-11-19; it lists separate entity records for the applicant, operator, surface occupant and survey firm. The landowner is the Crown in right of Alberta.',
        current, '',
        '## Area meanings', '', scope, '',
        '## Review instruction', '', COMMON_REVIEW, '',
        'All documents are local evaluation inputs. Do not publish their source PDFs. No external client search, live company lookup or real-land inference is needed.', '',
    ])

_DENSE_INK = (0.10, 0.16, 0.19)

_DENSE_GREY = (0.38, 0.43, 0.46)

_DENSE_BLUE = (0.10, 0.29, 0.42)

_DENSE_LINE = (0.62, 0.69, 0.72)

_DENSE_PALE = (0.94, 0.97, 0.98)

_DENSE_GREEN = (0.86, 0.93, 0.86)

_DENSE_YELLOW = (0.99, 0.94, 0.77)

_DENSE_CASES = [
    dict(case='B5J8', job='CW-261742', drawing='CW-261742-SK-02', rev='C',
         applicant='Sandquill Crossing Ltd.', client='9628704',
         operator='Ridgetern Energy Inc.', operator_id='9791640',
         occupant='Marshcopper Grazing Co-operative Ltd.', survey='Orchardstone Geomatics Ltd.',
         legal='NE 1/4 Sec. 18, Twp. 54, Rge. 19, W5M', disposition='Application 26-LOC-61847',
         permanent='0.864 ha', workspace='0.156 ha', total='1.020 ha', length='480.00 m', width='18.00 m',
         registry_names=['Sandquill Crossing Ltd.'], name_effective='2026-09-02', opposed=True),
    dict(case='R8D1', job='AN-261935', drawing='AN-261935-SK-01', rev='B',
         applicant='Cresswake Route Ltd.', client='9653041',
         operator='Bluffwillow Energy Ltd.', operator_id='9746208',
         occupant='Thistleplains Range Association Ltd.', survey='Bluecairn Meridian Surveys Ltd.',
         legal='SW 1/4 Sec. 28, Twp. 63, Rge. 11, W6M', disposition='Application 26-LOC-64720',
         permanent='1.152 ha', workspace='0.208 ha', total='1.360 ha', length='576.00 m', width='20.00 m',
         registry_names=['Cresswake Route Ltd.', 'Cresswake Passage Ltd.'], name_effective='', opposed=False),
]

def _dense_text(p, x, y, value, size=9.4, font='helv', color=_DENSE_INK, rotate=0):
    p.insert_text((x, y), value, fontsize=size, fontname=font, color=color, rotate=rotate)

def _dense_rule(p, x1, y1, x2, y2, width=0.65):
    p.draw_line((x1, y1), (x2, y2), color=_DENSE_LINE, width=width)

def _dense_box(p, x1, y1, x2, y2, fill=None, width=0.65):
    p.draw_rect(fitz.Rect(x1,y1,x2,y2), color=_DENSE_LINE, fill=fill, width=width)

def _dense_wrap(p,x,y,value,width,size=9,leading=13):
    words=value.split(); acc=''
    for word in words:
        cand=(acc+' '+word).strip()
        if acc and fitz.get_text_length(cand,fontname='helv',fontsize=size)>width:
            _dense_text(p,x,y,acc,size); y+=leading; acc=word
        else: acc=cand
    if acc: _dense_text(p,x,y,acc,size); y+=leading
    return y

def _dense_heading(p,title,job,kind):
    w,h=p.rect.width,p.rect.height
    _dense_box(p,18,18,w-18,h-18,width=1)
    _dense_box(p,18,18,w-18,38,fill=_DENSE_PALE)
    _dense_text(p,29,32,'INVENTED EVALUATION MATERIAL - NO ACTUAL LAND OR COMPANY',7.7,color=_DENSE_GREY)
    _dense_text(p,30,67,title,17,'hebo',_DENSE_BLUE)
    _dense_text(p,30,85,'AER LOC application stage / new access-road sketch / issue for review',9,color=_DENSE_GREY)
    _dense_text(p,30,h-29,job+' | '+kind+' | 1 of 1',7.7,color=_DENSE_GREY)
    _dense_text(p,w-254,h-29,'Review date 2026-11-21 / native PDF input',7.7,color=_DENSE_GREY)

def _dense_labelled(p,x,y,label,value,offset=81,size=9.5):
    _dense_text(p,x,y,label,8.1,'hebo',_DENSE_GREY)
    _dense_text(p,x+offset,y,value,size)

def _dense_identity(p,c,top=116,left=34,right=454,w=832):
    # Distinct adjacent labels deliberately share baseline rows.
    _dense_box(p,left-4,top-15,left+w,top+74)
    for y in [top+7,top+27,top+47]: _dense_rule(p,left-4,y,left+w,y)
    _dense_rule(p,right-14,top-15,right-14,top+74)
    _dense_labelled(p,left,top,'APPLICANT:',c['applicant'])
    _dense_labelled(p,right,top,'OPERATOR:',c['operator'])
    _dense_labelled(p,left,top+20,'CLIENT ID:',c['client'])
    _dense_labelled(p,right,top+20,'OPERATOR ID:',c['operator_id'])
    _dense_labelled(p,left,top+40,'LEGAL:',c['legal'],size=8.8)
    _dense_labelled(p,right,top+40,'DISPOSITION:',c['disposition'],size=9.2)
    _dense_labelled(p,left,top+60,'DRAWING:',c['drawing'])
    _dense_labelled(p,right,top+60,'REV / DATE:',c['rev']+' / 2026-11-20')

def _dense_quantity_table(p,c,x,y,width,row=31):
    _dense_box(p,x,y,x+width,y+26,fill=_DENSE_PALE)
    _dense_text(p,x+10,y+17,'REQUESTED AREA',9.4,'hebo',_DENSE_BLUE)
    _dense_text(p,x+width-100,y+17,'PRINTED QUANTITY',7.7,'hebo',_DENSE_BLUE)
    y+=26
    for label,val in [('Permanent LOC requested',c['permanent']),('Workspace outside LOC',c['workspace']),('Total application footprint',c['total'])]:
        _dense_box(p,x,y,x+width,y+row)
        _dense_text(p,x+10,y+20,label,8.8)
        # The amount, space and unit are one native font span / complete token.
        _dense_text(p,x+width-81,y+20,val,10.4,'hebo')
        y+=row
    return y

def _dense_save(d,path):
    d.set_metadata({'title':path.stem,'author':'Invented Evaluation Fixtures',
        'subject':'Fresh dense native PDF job records','creator':'PyMuPDF author',
        'producer':'PyMuPDF','creationDate':'D:20261121090000Z','modDate':'D:20261121090000Z'})
    d.save(str(path),garbage=4,deflate=True,no_new_id=True); d.close()

def _dense_plan(c,path):
    d=fitz.open(); p=d.new_page(width=900,height=640)
    _dense_heading(p,'SURFACE ACCESS SKETCH',c['job'],'PLAN')
    _dense_identity(p,c)
    _dense_box(p,30,210,556,462)
    _dense_text(p,42,229,'LOCATION DETAIL / DIAGRAMMATIC - DIMENSIONS GOVERN',8,'hebo',_DENSE_GREY)
    _dense_text(p,509,253,'N',11,'hebo',_DENSE_BLUE)
    p.draw_line((513,279),(513,257),color=_DENSE_BLUE,width=1.2)
    p.draw_line((513,257),(508,264),color=_DENSE_BLUE,width=1.2)
    p.draw_line((513,257),(518,264),color=_DENSE_BLUE,width=1.2)
    _dense_box(p,71,319,506,337,fill=_DENSE_GREEN)
    _dense_box(p,379,337,481,373,fill=_DENSE_YELLOW)
    _dense_text(p,159,332,'PERMANENT LOC CORRIDOR',8.8,'hebo',_DENSE_BLUE)
    _dense_text(p,387,352,'TEMPORARY',7.4,'hebo')
    _dense_text(p,387,365,'WORKSPACE',7.4,'hebo')
    _dense_rule(p,71,305,506,305)
    _dense_text(p,226,297,c['length'],9.4)
    _dense_text(p,61,360,c['width'],8.8,rotate=90)
    _dense_text(p,43,403,'Landowner: Crown in right of Alberta',9)
    _dense_text(p,43,427,'Quarter-section grid for location; no closure review requested.',8.4,color=_DENSE_GREY)
    _dense_quantity_table(p,c,574,210,292)
    _dense_wrap(p,584,354,'Permanent LOC and workspace are separate scopes. Total footprint is their sum. All printed area quantities include hectares.',272,8.5,12)
    _dense_box(p,30,478,440,568)
    _dense_text(p,42,497,'SURFACE OCCUPANT / GRAZING LESSEE',8,'hebo',_DENSE_GREY)
    _dense_text(p,42,518,c['occupant'],10)
    _dense_text(p,42,548,'Operational contact is the operator shown above.',8.4,color=_DENSE_GREY)
    _dense_box(p,454,478,866,568)
    if c['opposed']:
        _dense_text(p,850,541,'PREPARED BY / SURVEY FIRM',8,'hebo',_DENSE_GREY,rotate=180)
        _dense_text(p,850,519,c['survey'],10,rotate=180)
        _dense_text(p,850,493,'Native opposed field - read with the sheet rotated',8,color=_DENSE_GREY,rotate=180)
    else:
        _dense_text(p,466,497,'PREPARED BY / SURVEY FIRM',8,'hebo',_DENSE_GREY)
        _dense_text(p,466,518,c['survey'],10)
        _dense_text(p,466,548,'Review issue / survey professional certification out of scope',8.1,color=_DENSE_GREY)
    _dense_text(p,32,590,'Legend: pale green = permanent LOC; pale yellow = workspace outside LOC.',8.4,color=_DENSE_GREY)
    _dense_save(d,path)

def _dense_application(c,path):
    d=fitz.open(); p=d.new_page(width=900,height=640)
    _dense_heading(p,'APPLICATION - JOB RECORD',c['job'],'APPLICATION')
    _dense_identity(p,c,top=116)
    _dense_quantity_table(p,c,30,215,500,row=35)
    _dense_box(p,548,215,866,346)
    _dense_text(p,560,235,'CONTROLLED RECORDS',9,'hebo',_DENSE_BLUE)
    _dense_text(p,560,259,'Submitted: 2026-11-20',9.5)
    _dense_text(p,560,282,'Plan issue: 2026-11-20',9.5)
    _dense_text(p,560,305,'Registry extract: 2026-11-21',9.5)
    _dense_text(p,560,328,'Stage: NEW LOC / no existing approval',9.1)
    _dense_text(p,30,379,'APPLICATION SCOPE AND AREA DEFINITIONS',9.2,'hebo',_DENSE_BLUE)
    _dense_wrap(p,30,401,'The permanent LOC request covers the access-road corridor. Temporary workspace is outside the permanent LOC and is a separate application category. The footprint total is the permanent request plus workspace. No retained area, removal, addition or prior approved baseline is relied on for this new application.',826,9.5,15)
    _dense_box(p,30,468,866,558)
    _dense_labelled(p,42,489,'OCCUPANT:',c['occupant'],offset=99)
    _dense_labelled(p,42,513,'SURVEY FIRM:',c['survey'],offset=99)
    _dense_labelled(p,42,537,'LANDOWNER:','Crown in right of Alberta',offset=99)
    _dense_text(p,30,584,'Applicant role is identified above. Operator, occupant, landowner and survey firm are separate roles.',9,color=_DENSE_GREY)
    _dense_save(d,path)

def _dense_registry(c,path):
    d=fitz.open(); p=d.new_page(width=900,height=640)
    _dense_heading(p,'CLIENT REGISTRY - JOB EXTRACT',c['job'],'REGISTRY')
    _dense_text(p,30,111,'Extract issued / status as of: 2026-11-21',10,'hebo')
    _dense_labelled(p,30,133,'LEGAL:',c['legal'],offset=81,size=9)
    _dense_labelled(p,454,133,'DISPOSITION:',c['disposition'],offset=81,size=9)
    _dense_text(p,30,158,'Role index comes from the application. Names below reproduce the registry name cells for those entities.',9,color=_DENSE_GREY)
    cols=[30,179,297,672,866]
    for a,b in zip(cols,cols[1:]): _dense_box(p,a,181,b,214,fill=_DENSE_PALE)
    for x,label in [(40,'APPLICATION ROLE'),(189,'CLIENT IDENTIFIER'),(307,'REGISTERED NAME - SOURCE CELL'),(682,'STATUS / NAME EFFECTIVE')]:
        _dense_text(p,x,201,label,7.6,'hebo',_DENSE_BLUE)
    rows=[('Applicant',c['client'],c['registry_names'],c['name_effective']),
          ('Operator',c['operator_id'],[c['operator']],'2026-02-04'),
          ('Surface occupant','9674102' if c['case']=='B5J8' else '9661927',[c['occupant']],'2025-08-12'),
          ('Survey firm','9782305' if c['case']=='B5J8' else '9771409',[c['survey']],'2025-10-07')]
    y=214
    for role,ident,names,effective in rows:
        h=68
        for a,b in zip(cols,cols[1:]): _dense_box(p,a,y,b,y+h)
        _dense_text(p,40,y+24,role,9.6,'hebo')
        _dense_text(p,189,y+24,ident,9.6)
        for i,name in enumerate(names):
            # Deliberate source line breaks are retained verbatim, without ranking.
            _dense_text(p,307,y+24+i*18,name,10)
        _dense_text(p,682,y+24,'ACTIVE',9.4)
        if effective: _dense_text(p,682,y+44,effective,9.1)
        y+=h
    _dense_text(p,30,514,'EXPORT CONVENTIONS',8.6,'hebo',_DENSE_BLUE)
    _dense_wrap(p,30,535,'Embedded line breaks in a registry name cell are preserved. Empty effective-date cells are blank in the supplied extract. No name-history subrecords accompany this job extract. The extract date identifies when the record was supplied.',826,9,14)
    _dense_text(p,30,590,'Landowner: Crown in right of Alberta. Private entities above are role contacts, not the landowner.',8.7,color=_DENSE_GREY)
    _dense_save(d,path)

def _dense_brief(c):
    return '\n'.join([
        '# Invented job brief','',f'Bundle: {c["case"]}',f'Job: {c["job"]}',
        f'Plan: {c["drawing"]}, Revision {c["rev"]}, issue date 2026-11-20.',
        'Scope: new AER LOC application for an Alberta public-land access-road sketch. Review date: 2026-11-21.',
        'All companies, job references, client identifiers, application identities and legal parcels are invented.','',
        'The application identifies the applicant and separate operator. The occupant/grazing lessee, Crown landowner and survey firm have separate roles. The client registry extract was issued and is current as of 2026-11-21; any name-effective dates are shown in its source cells. No prior approved disposition is relied on for this new application.','',
        'Permanent LOC request and temporary workspace outside the LOC are separate area categories. Total application footprint is their sum. A quantity includes both the printed amount and the unit.','',
        'Review the plan against the application and registry for applicant/client identity, application identity, legal description, revision, and each printed area category. Use each distinct field label to associate its value with the correct role or scope. Where the supplied records cannot establish a governing current value, record the unresolved point and what evidence is required. Boundary closure and professional certification are outside scope.','',
        'These are local evaluation inputs. Do not publish their source PDFs or search for real companies or land records.',''
    ])

INITIAL_CASE_IDS = tuple(case['case'] for case in CASES)
DENSE_CASE_IDS = tuple(case['case'] for case in _DENSE_CASES)
CASE_IDS = INITIAL_CASE_IDS + DENSE_CASE_IDS


def _runtime():
    global fitz
    if fitz is None:
        fitz = load_pdf_runtime()
    return fitz


def load_forward_truth(path: str | Path | None = None) -> dict:
    """Return only the immutable portable record; changed oracles are rejected."""
    source = Path(path) if path is not None else Path(__file__).with_name('fixtures') / 'job_record_forward_truth.json'
    with source.open('rb') as handle:
        raw = handle.read(MAX_TRUTH_BYTES + 1)
    if len(raw) > MAX_TRUTH_BYTES or sha256(raw).hexdigest() != TRUTH_SHA256:
        raise ValueError('Forward fixture truth SHA-256 does not match the preserved record')
    result = json.loads(raw.decode('utf-8'))
    if result.get('schema_version') != 1 or result.get('classification') != 'INVENTED_FORWARD_INPUTS_NOW_KNOWN_REGRESSIONS':
        raise ValueError('Unsupported forward fixture record')
    return result


def _fresh_output(folder: str | Path) -> Path:
    output = Path(folder).resolve()
    if output.is_relative_to(SKILL):
        raise ValueError('Generated original PDFs must stay outside the installed skill')
    for parent in SKILL.parents:
        if (parent / '.git').exists() and output.is_relative_to(parent):
            raise ValueError('Generated original PDFs must stay outside the source repository')
    output.mkdir(parents=True, exist_ok=False)
    return output


def make_forward_example(folder: str | Path, case_id: str) -> dict[str, Path | None]:
    """Write one authored bundle into a new directory outside the skill/repo."""
    if case_id not in CASE_IDS:
        raise ValueError('Unknown invented forward case')
    _runtime()
    dense = case_id in DENSE_CASE_IDS
    choices = _DENSE_CASES if dense else CASES
    case = deepcopy(next(value for value in choices if value['case'] == case_id))
    output = _fresh_output(folder)
    paths = {name: output / (name + '.pdf') for name in ('plan', 'application', 'registry')}
    writers = (_dense_plan, _dense_application, _dense_registry) if dense else (plan, application, registry)
    for name, writer in zip(('plan', 'application', 'registry'), writers):
        writer(case, paths[name])
    paths['approved'] = output / 'approved.pdf' if case.get('references') else None
    if paths['approved'] is not None:
        approved(case, paths['approved'])
    paths['brief'] = output / 'job-brief.md'
    paths['brief'].write_text((_dense_brief if dense else brief)(case), encoding='utf-8')
    return paths


def rebind_recorded_preparation(case_id: str, generated_paths: dict[str, Path | None]) -> tuple[dict, dict[str, Path]]:
    """Replay the original reviewed selectors on faithfully recreated originals.

    Byte-identical inputs retain original hashes. Where native serialization
    differs, the original complete native-text hash binds the same authored
    input before hashes are updated. This is test-fixture rebinding, never a
    way to borrow synthetic job/currentness declarations for arbitrary inputs.
    No region, role, currentness or expected value is changed.
    """
    truth = load_forward_truth()
    if case_id not in truth['cases']:
        raise ValueError('Unknown recorded forward preparation')
    recorded = truth['cases'][case_id]
    available = {path.name: Path(path) for path in generated_paths.values() if path is not None}
    expected = recorded['original_inputs']
    if set(available) != set(expected):
        raise ValueError('Forward fixture source set differs from the original bundle')
    for filename, path in available.items():
        if path.stat().st_size > 1_000_000:
            raise ValueError('Forward fixture input exceeds its bounded test size')
        raw = path.read_bytes()
        digest = sha256(raw).hexdigest()
        if digest == expected[filename]['sha256']:
            continue
        if filename.endswith('.pdf'):
            runtime = _runtime()
            with runtime.open(stream=raw, filetype='pdf') as document:
                if len(document) != 1:
                    raise ValueError('Forward fixture PDF page count differs')
                text = '\n'.join(page.get_text() for page in document)
            if sha256(text.encode()).hexdigest() != expected[filename]['native_text_sha256']:
                raise ValueError('Forward fixture native source content differs from its preserved input')
        else:
            raise ValueError('Forward fixture brief SHA-256 differs from its preserved input')
    spec = deepcopy(recorded['original_preparation'])
    files = {}
    for source_id, filename in recorded['source_file_bindings'].items():
        if filename is None:
            continue
        path = available[filename]
        spec['records']['sources'][source_id]['source_sha256'] = sha256(path.read_bytes()).hexdigest()
        if source_id != 'plan':
            files[source_id] = path
    return spec, files


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='Fresh private directory outside the repository/skill')
    parser.add_argument('--case', choices=CASE_IDS)
    args = parser.parse_args(argv)
    if args.case:
        make_forward_example(args.output, args.case)
    else:
        output = _fresh_output(args.output)
        for case_id in CASE_IDS:
            make_forward_example(output / case_id, case_id)
    print('Invented original job bundles generated:', args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
