#!/usr/bin/env python3
"""Amaravati Digital Twin — full project report PDF"""
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, KeepTogether, PageBreak)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
import json, os, base64

W, H = A4
OUT = '/mnt/user-data/outputs/Amaravati_DigitalTwin_ProjectReport.pdf'

# ── colour palette (dark-twin-inspired) ──────────────────────────────
C_DARK   = colors.HexColor('#0c1a2e')
C_TEAL   = colors.HexColor('#5fe0d2')
C_CYAN   = colors.HexColor('#19C6F0')
C_AMBER  = colors.HexColor('#f5c542')
C_RED    = colors.HexColor('#ff5d5d')
C_GREEN  = colors.HexColor('#57d98a')
C_VIOLET = colors.HexColor('#a98bff')
C_DIM    = colors.HexColor('#9bb1c6')
C_INK    = colors.HexColor('#eaf2f9')
C_MID    = colors.HexColor('#1d3a57')
C_WHITE  = colors.white

# ── page template ──────────────────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    # header bar
    canvas.setFillColor(C_DARK)
    canvas.rect(0, H-18*mm, W, 18*mm, fill=1, stroke=0)
    canvas.setFillColor(C_TEAL)
    canvas.setFont('Helvetica-Bold', 8)
    canvas.drawString(15*mm, H-11*mm, 'KREAYOTOO SOLUTIONS (P) LTD  ·  AMARAVATI CAPITAL CITY DIGITAL TWIN')
    canvas.setFillColor(C_DIM)
    canvas.setFont('Helvetica', 8)
    canvas.drawRightString(W-15*mm, H-11*mm, 'CONFIDENTIAL  ·  PROJECT REPORT  ·  2026')
    # teal accent bar
    canvas.setFillColor(C_TEAL)
    canvas.rect(0, H-19.5*mm, W, 1.5*mm, fill=1, stroke=0)
    # footer
    canvas.setFillColor(C_DARK)
    canvas.rect(0, 0, W, 12*mm, fill=1, stroke=0)
    canvas.setFillColor(C_DIM)
    canvas.setFont('Helvetica', 7.5)
    canvas.drawString(15*mm, 4.5*mm, 'Engineering · Solutions · Innovation    kreayotoo.com')
    canvas.drawRightString(W-15*mm, 4.5*mm, f'Page {doc.page}')
    canvas.restoreState()

doc = BaseDocTemplate(OUT, pagesize=A4,
    leftMargin=18*mm, rightMargin=18*mm, topMargin=24*mm, bottomMargin=18*mm)
frame = Frame(doc.leftMargin, doc.bottomMargin,
    doc.width, doc.height, id='main')
doc.addPageTemplates([PageTemplate(id='std', frames=[frame], onPage=on_page)])

# ── styles ────────────────────────────────────────────────────────────
SS = getSampleStyleSheet()
def sty(name, **kw):
    return ParagraphStyle(name, **kw)

S_COVER_TITLE = sty('cover_title', fontName='Helvetica-Bold', fontSize=28,
    textColor=C_WHITE, spaceAfter=6, leading=34, alignment=TA_LEFT)
S_COVER_SUB   = sty('cover_sub',   fontName='Helvetica', fontSize=13,
    textColor=C_TEAL, spaceAfter=4, leading=17)
S_COVER_BODY  = sty('cover_body',  fontName='Helvetica', fontSize=10,
    textColor=C_DIM, spaceAfter=3, leading=14)
S_H1  = sty('h1',  fontName='Helvetica-Bold', fontSize=16,
    textColor=C_CYAN, spaceBefore=14, spaceAfter=4, leading=20, borderPad=0)
S_H2  = sty('h2',  fontName='Helvetica-Bold', fontSize=11,
    textColor=C_TEAL, spaceBefore=6, spaceAfter=2, leading=15, keepWithNext=1)
S_H3  = sty('h3',  fontName='Helvetica-Bold', fontSize=9.5,
    textColor=C_AMBER, spaceBefore=5, spaceAfter=2, leading=13, keepWithNext=1)
S_BODY = sty('body', fontName='Helvetica', fontSize=9,
    textColor=colors.HexColor('#2d3a4a'), spaceAfter=4, leading=14, alignment=TA_JUSTIFY)
S_BULLET = sty('bullet', fontName='Helvetica', fontSize=9,
    textColor=colors.HexColor('#2d3a4a'), spaceAfter=2, leading=13,
    leftIndent=12, bulletIndent=0)
S_CODE = sty('code', fontName='Courier', fontSize=8,
    textColor=colors.HexColor('#1a4060'), backColor=colors.HexColor('#e8f4f8'),
    spaceAfter=4, leading=12, leftIndent=8, rightIndent=8, borderPad=4)
S_CAPTION = sty('caption', fontName='Helvetica-Oblique', fontSize=8,
    textColor=C_DIM, spaceAfter=6, alignment=TA_CENTER)
S_LABEL = sty('label', fontName='Helvetica-Bold', fontSize=8.5,
    textColor=C_WHITE)
S_TAG_REAL = sty('tag_r', fontName='Helvetica-Bold', fontSize=8,
    textColor=colors.HexColor('#057a55'), backColor=colors.HexColor('#d1fae5'))
S_TAG_SIM  = sty('tag_s', fontName='Helvetica-Bold', fontSize=8,
    textColor=colors.HexColor('#92400e'), backColor=colors.HexColor('#fef3c7'))

def hr(): return HRFlowable(width='100%', thickness=0.7, color=C_MID, spaceAfter=4, spaceBefore=4)
def sp(h=4): return Spacer(1, h*mm)
def h1(t): return Paragraph(t, S_H1)
def h2(t): return Paragraph(t, S_H2)
def h3(t): return Paragraph(t, S_H3)
def p(t):  return Paragraph(t, S_BODY)
def b(t):  return Paragraph(f'<bullet>&bull;</bullet> {t}', S_BULLET)
def code(t): return Paragraph(t, S_CODE)

def section_heading(txt, colour=C_CYAN):
    return Paragraph(txt, ParagraphStyle('sh', fontName='Helvetica-Bold',
        fontSize=14, textColor=colour, leading=20, spaceBefore=4, spaceAfter=2,
        backColor=C_DARK, leftIndent=8, rightIndent=8, borderPad=6,
        borderWidth=0, keepWithNext=1))

def kv_table(rows, col_w=None):
    if col_w is None: col_w = [55*mm, doc.width-55*mm]
    data = [[Paragraph(f'<b>{k}</b>', ParagraphStyle('kk', fontName='Helvetica-Bold',
                fontSize=8.5, textColor=C_DARK)),
             Paragraph(v, ParagraphStyle('kv', fontName='Helvetica', fontSize=8.5,
                textColor=colors.HexColor('#1a3a5c')))] for k,v in rows]
    t = Table(data, colWidths=col_w)
    t.setStyle(TableStyle([
        ('BACKGROUND',   (0,0), (0,-1), colors.HexColor('#e8f4fb')),
        ('BACKGROUND',   (1,0), (1,-1), colors.white),
        ('GRID',         (0,0), (-1,-1), 0.4, colors.HexColor('#c5dce8')),
        ('LEFTPADDING',  (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING',   (0,0), (-1,-1), 4),
        ('BOTTOMPADDING',(0,0), (-1,-1), 4),
        ('VALIGN',       (0,0), (-1,-1), 'TOP'),
    ]))
    return t

def status_table(rows, headers=None):
    HSTYLE = ParagraphStyle('th', fontName='Helvetica-Bold', fontSize=8, textColor=C_WHITE)
    RSTYLE = ParagraphStyle('td', fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#1a3a5c'))
    col_ws = [8*mm, 80*mm, 35*mm, doc.width - 8*mm - 80*mm - 35*mm]
    data = []
    if headers: data.append([Paragraph(h, HSTYLE) for h in headers])
    for r in rows:
        icon, name, status, note = r
        sc = {'REAL':colors.HexColor('#d1fae5'),'BUILT':colors.HexColor('#dbeafe'),
              'PARTIAL':colors.HexColor('#fef3c7'),'PENDING':colors.HexColor('#fee2e2'),
              'FUTURE':colors.HexColor('#ede9fe')}.get(status.upper(), colors.white)
        tc = {'REAL':colors.HexColor('#065f46'),'BUILT':colors.HexColor('#1e40af'),
              'PARTIAL':colors.HexColor('#92400e'),'PENDING':colors.HexColor('#991b1b'),
              'FUTURE':colors.HexColor('#5b21b6')}.get(status.upper(), C_DARK)
        stbl = Table([[Paragraph(status, ParagraphStyle('s', fontName='Helvetica-Bold',
            fontSize=7.5, textColor=tc))]],
            colWidths=[30*mm])
        stbl.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),sc),
            ('LEFTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),2),
            ('BOTTOMPADDING',(0,0),(-1,-1),2),('ROUNDEDCORNERS',[3])]))
        data.append([Paragraph(icon, RSTYLE), Paragraph(f'<b>{name}</b>', RSTYLE),
                     stbl, Paragraph(note, RSTYLE)])
    t = Table(data, colWidths=col_ws)
    ts = [('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#c5dce8')),
          ('VALIGN',(0,0),(-1,-1),'TOP'),
          ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
          ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]
    if headers: ts += [('BACKGROUND',(0,0),(-1,0),C_DARK)]
    t.setStyle(TableStyle(ts))
    return t

def two_col(left_items, right_items):
    lw = rw = (doc.width - 6*mm) / 2
    def wrap(items): return ''.join(f'• {x}<br/>' for x in items)
    tbl = Table([[Paragraph(wrap(left_items), ParagraphStyle('lc', fontName='Helvetica',
                    fontSize=8.5, textColor=colors.HexColor('#1a3a5c'), leading=14)),
                  Paragraph(wrap(right_items), ParagraphStyle('rc', fontName='Helvetica',
                    fontSize=8.5, textColor=colors.HexColor('#1a3a5c'), leading=14))]],
                colWidths=[lw, rw])
    tbl.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f0f9ff')),
        ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#c5dce8')),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
    ]))
    return tbl

def phase_table(phases):
    PS = ParagraphStyle('pt', fontName='Helvetica', fontSize=8.5,
        textColor=colors.HexColor('#1a3a5c'), leading=13)
    PH = ParagraphStyle('ph', fontName='Helvetica-Bold', fontSize=8.5, textColor=C_WHITE)
    cols = [18*mm, 45*mm, doc.width-18*mm-45*mm]
    data = [[Paragraph(h, PH) for h in ['Phase','Title','Deliverables / milestones']]]
    bgs = [colors.HexColor('#1e3a5f'),colors.HexColor('#164e63'),colors.HexColor('#065f46'),
           colors.HexColor('#7c2d12'),colors.HexColor('#4c1d95'),colors.HexColor('#1f2937')]
    for i,(num,title,items) in enumerate(phases):
        bg = bgs[i % len(bgs)]
        data.append([
            Paragraph(num, ParagraphStyle('pn', fontName='Helvetica-Bold', fontSize=10,
                textColor=C_WHITE, alignment=TA_CENTER)),
            Paragraph(title, ParagraphStyle('pt2', fontName='Helvetica-Bold', fontSize=8.5,
                textColor=C_TEAL if i>0 else C_AMBER)),
            Paragraph('  '.join(f'• {x}' for x in items), PS)])
        t = Table(data[-1:], colWidths=cols)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(0,0),bg),('BACKGROUND',(1,0),(-1,0),
            colors.HexColor('#f8fafc') if i%2==0 else colors.white)]))
    t = Table(data, colWidths=cols)
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),C_DARK),
        ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#c5dce8')),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
        *[('BACKGROUND',(0,i+1),(0,i+1),bgs[i%len(bgs)]) for i in range(len(phases))],
        *[('BACKGROUND',(1,i+1),(-1,i+1),
           colors.HexColor('#f0f9ff') if i%2==0 else colors.white) for i in range(len(phases))],
    ]))
    return t

# ═══════════════════════════════════════════════════════════════════════
# BUILD STORY
# ═══════════════════════════════════════════════════════════════════════
story = []

# ── COVER PAGE ────────────────────────────────────────────────────────
cover_bg = Table([['']], colWidths=[doc.width], rowHeights=[80*mm])
cover_bg.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(-1,-1),C_DARK),
    ('ROUNDEDCORNERS',[6]),
]))
story.append(cover_bg)
story.append(sp(-84))   # overlay text on background

story.append(Paragraph('<font color="#19C6F0">▌</font> KREAYOTOO SOLUTIONS (P) LTD', sty('tag',
    fontName='Helvetica-Bold', fontSize=9, textColor=C_TEAL, spaceBefore=6, spaceAfter=3)))
story.append(Paragraph('Amaravati Capital City', S_COVER_TITLE))
story.append(Paragraph('Underground Utility Digital Twin', sty('cs2', fontName='Helvetica-Bold',
    fontSize=22, textColor=C_CYAN, spaceAfter=3, leading=28)))
story.append(Paragraph('Project Report — What We Built, How It Works &amp; Where We Are Going',
    S_COVER_SUB))
story.append(sp(4))
story.append(Paragraph('Andhra Pradesh Capital Region Development Authority (APCRDA) · Amaravati, Andhra Pradesh',
    S_COVER_BODY))
story.append(Paragraph('Report Date: July 2026  ·  Classification: Confidential', S_COVER_BODY))
story.append(sp(10))

# ── KEY NUMBERS ───────────────────────────────────────────────────────
kn = Table([
    [Paragraph('<b>78,053</b><br/>pipes', ParagraphStyle('kn', fontName='Helvetica-Bold',
        fontSize=14, textColor=C_CYAN, alignment=TA_CENTER, leading=18)),
     Paragraph('<b>43,685</b><br/>chambers', ParagraphStyle('kn2', fontName='Helvetica-Bold',
        fontSize=14, textColor=C_TEAL, alignment=TA_CENTER, leading=18)),
     Paragraph('<b>95,935</b><br/>plots', ParagraphStyle('kn3', fontName='Helvetica-Bold',
        fontSize=14, textColor=C_AMBER, alignment=TA_CENTER, leading=18)),
     Paragraph('<b>21</b><br/>blocks', ParagraphStyle('kn4', fontName='Helvetica-Bold',
        fontSize=14, textColor=C_VIOLET, alignment=TA_CENTER, leading=18)),
     Paragraph('<b>6</b><br/>zones', ParagraphStyle('kn5', fontName='Helvetica-Bold',
        fontSize=14, textColor=C_GREEN, alignment=TA_CENTER, leading=18)),
     Paragraph('<b>5</b><br/>utilities', ParagraphStyle('kn6', fontName='Helvetica-Bold',
        fontSize=14, textColor=C_RED, alignment=TA_CENTER, leading=18)),
    ]
], colWidths=[doc.width/6]*6)
kn.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(-1,-1),C_DARK),
    ('GRID',(0,0),(-1,-1),0.5,C_MID),
    ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
    ('ROUNDEDCORNERS',[4]),
]))
story += [kn, sp(8), PageBreak()]

# ══════════════════════════════════════════════════════════════════════
# 1. PROJECT OVERVIEW
# ══════════════════════════════════════════════════════════════════════
story += [section_heading('1. PROJECT OVERVIEW'), sp(3)]
story += [p('Kreayotoo Solutions (P) Ltd (KSPL) has built a <b>Digital Twin of Amaravati Capital '
  'City\'s underground utility infrastructure</b> for the Andhra Pradesh Capital Region Development '
  'Authority (APCRDA). The twin covers the complete underground network — water supply, sewerage, '
  'storm-water drainage, reuse water and power — across 21 blocks in 6 zones of the planned capital city.'), sp(2)]
story += [p('The deliverable is a <b>single offline HTML application</b> (double-click to run, no '
  'server needed) that provides 3D visualisation, GIS mapping, BIM building integration, live '
  'weather and storm simulation, and an AI-assisted decision support system driven by a virtual '
  'SCADA sensor network. The platform is designed to evolve from a visualisation tool into a '
  'full operational system as real IoT sensors and SCADA are connected.'), sp(4)]

story += [h2('Project Objectives'), hr()]
story += [two_col(
    ['Provide a unified 3D+GIS view of all underground utilities across Amaravati\'s 21 blocks',
     'Enable zone-by-zone and city-wide network analysis',
     'Integrate real BIM building data (Revit IFC) with the infrastructure',
     'Simulate storm-water network response to live rainfall',
     'Build an alert-driven decision support system with real GIS buffer analysis'],
    ['Establish a foundation ready for live SCADA/IoT sensor integration',
     'Demonstrate the SIWA-style operational capability (Siemens benchmark)',
     'Ensure honest labelling: real data vs simulated always distinguished',
     'Create a reusable platform engine for other cities and airports',
     'Deliver a fully self-contained offline package (no internet needed for core)']
), sp(6)]

story += [h2('Project Scope — What Is Covered'), hr(),
kv_table([
    ('Area',           'Amaravati Capital City — 21 blocks across 6 zones (Zone 1B, 5A, 5C, 5D, 10, 12)'),
    ('Utilities',      'Water supply  ·  Sewerage  ·  Storm-water drainage  ·  Reuse water  ·  Power/electrical conduits'),
    ('Network scale',  '78,053 pipes  ·  43,685 manholes/chambers  ·  2,131+ km of utility mains  ·  117 km trunk main'),
    ('BIM',            'WTP Admin Building — 16-storey Revit IFC4 (architectural + structural), real materials, 89 rooms'),
    ('Masterplan',     '95,935 plots from the APCRDA masterplan shapefile with full landuse zoning (35 zone types)'),
    ('Weather',        'Live rainfall (Open-Meteo) + Windy.com radar, driving simulated storm-water network response'),
    ('Decision Support','Alert-driven with real GIS buffer (95,935 plots + 78,053 pipes), 5 scenarios, virtual SCADA sensors'),
]), sp(6), PageBreak()]

# ══════════════════════════════════════════════════════════════════════
# 2. WHAT WE BUILT
# ══════════════════════════════════════════════════════════════════════
story += [section_heading('2. WHAT WE BUILT — MODULES'), sp(3)]

modules = [
    ('3D Network Twin', 'BUILT', 'Dark SCADA-style 3D viewer — individual block / zone / entire city views. '
     'Free pan/orbit/zoom. Click any pipe or manhole to see its attributes.'),
    ('GIS Map', 'BUILT', 'Interactive Leaflet map with satellite basemap, all 5 utility layers '
     'coloured by type, trunk main polylines, block markers, and tap-to-locate.'),
    ('Landuse Zoning Overlay', 'BUILT', 'All 95,935 masterplan plots rendered as a georeferenced colour '
     'image (QML colours) — toggleable on both the overview and per-block maps, with a 35-zone legend.'),
    ('Trunk Main', 'BUILT', 'Dedicated 3D + GIS view of the 117 km trunk water main network across all zones.'),
    ('WTP Admin Building — BIM', 'BUILT', '16-storey Revit IFC4 in 3D — real Revit material colours (24 colours, 0% black), '
     'floor-by-floor isolation, 89 clickable room labels with area and level, X-ray/ghost/edges modes.'),
    ('Building Georeferencing', 'BUILT', 'IfcProjectedCRS + IfcMapConversion injected into the IFC — EPSG:32644 (UTM 44N), '
     'placed at the network centre. Any GIS/BIM tool will now read the correct position.'),
    ('Live Weather + Storm', 'BUILT', 'Open-Meteo live rainfall (current, 24h, 7-day) + Windy.com animated '
     'radar map. Rolling-window intensity + antecedent wetness drive a real Manning capacity model per zone. '
     'Demand and raw-water outlook also updated.'),
    ('Decision Support', 'BUILT', 'Alert-driven: 5 scenarios (pipe burst, contamination, power failure, '
     'heavy rain, fire). Real GIS buffer on 95,935 plots + 78,053 pipes. Impact tab, Network tab, '
     'Actions checklist, Timeline chart, Sensors tab, Audit Log. Generates a full incident report.'),
    ('Virtual SCADA Sensor Network', 'BUILT', '~50 virtual sensors (pressure transmitters, DMA flow meters, '
     'chlorine analysers, pump monitors) across 21 blocks. Readings evolve every 20 s with real diurnal '
     'patterns and noise. Faults spawn, escalate and clear. Every alert is a real threshold breach.'),
    ('Continuous Alert Engine', 'BUILT', 'Feed re-checked every 20 s. New/escalated alerts trigger toasts, '
     'auto-follow re-runs impact analysis. ACK button, audit log, export. Sidebar badge reflects live count.'),
    ('Zone 10 Invert Fix', 'BUILT', '6,784 manholes in Zone 10 (blocks B3, B7, B8) had zero invert levels '
     '(data gap) — derived from connected pipe inverts. Depths now 1.2–5.8 m (median 2.0 m).'),
    ('Manning Capacity per Zone', 'BUILT', 'Real storm-drain outfall capacity per zone computed from Civil 3D '
     'pipe diameters and invert-derived slopes (Manning\'s equation, n=0.014).'),
    ('Isolation Points', 'BUILT', 'Scenario-aware: valve chambers for burst/contamination, power chambers '
     'for power failure, storm chambers for flood, hydrant points for fire.'),
    ('DMA Leak Detection', 'REMOVED', 'Minimum Night Flow + mass-balance panel built and tested — '
     'removed at client request, ready to reinstate when needed.'),
]

for i in range(0, len(modules), 3):
    rows = modules[i:i+3]
    tdata = []
    for name, status, desc in rows:
        sc = {'BUILT':colors.HexColor('#dbeafe'),'REMOVED':colors.HexColor('#fee2e2'),
              'PARTIAL':colors.HexColor('#fef3c7')}.get(status,colors.white)
        tc = {'BUILT':colors.HexColor('#1e40af'),'REMOVED':colors.HexColor('#991b1b'),
              'PARTIAL':colors.HexColor('#92400e')}.get(status,C_DARK)
        cell = [Paragraph(f'<b>{name}</b>', ParagraphStyle('mn', fontName='Helvetica-Bold',
                    fontSize=8.5, textColor=C_DARK, spaceAfter=2)),
                Paragraph(f'<font color="{tc.hexval() if hasattr(tc,"hexval") else "#1e40af"}"><b>{status}</b></font>',
                    ParagraphStyle('ms', fontName='Helvetica-Bold', fontSize=7.5)),
                Paragraph(desc, ParagraphStyle('md', fontName='Helvetica', fontSize=8,
                    textColor=colors.HexColor('#374151'), leading=12))]
        tdata.append(cell)
    for c in tdata:
        t = Table([[c[0]],[c[1]],[c[2]]], colWidths=[(doc.width-10*mm)/3])
        t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f8fafc')),
            ('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#c5dce8')),
            ('LEFTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),
            ('BOTTOMPADDING',(0,0),(-1,-1),5),
        ]))
    cw = [(doc.width-10*mm)/3]*min(3,len(rows))
    grid = Table([[t] for t in [Table([[c[0]],[c[1]],[c[2]]], colWidths=cw) for c in tdata]],
                 colWidths=[doc.width])
    # simpler: one row table
    cells = []
    for name, status, desc in rows:
        tc_hex = {'BUILT':'#1e40af','REMOVED':'#991b1b','PARTIAL':'#92400e'}.get(status,'#1e40af')
        cells.append(
            Table([[Paragraph(f'<b>{name}</b>',
                       ParagraphStyle('mn2',fontName='Helvetica-Bold',fontSize=8.5,textColor=C_DARK))],
                   [Paragraph(f'<font color="{tc_hex}"><b>● {status}</b></font>',
                       ParagraphStyle('ms2',fontName='Helvetica-Bold',fontSize=7.5))],
                   [Paragraph(desc,
                       ParagraphStyle('md2',fontName='Helvetica',fontSize=8,
                       textColor=colors.HexColor('#374151'),leading=12))],
                  ], colWidths=[(doc.width-12*mm)/len(rows)]))
    row_tbl = Table([cells], colWidths=[(doc.width-12*mm)/len(rows)]*len(rows),
                    spaceBefore=4, spaceAfter=0)
    row_tbl.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f8fafc')),
        ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#c5dce8')),
        ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
    ]))
    story += [row_tbl, sp(2)]

story += [sp(4), PageBreak()]

# ══════════════════════════════════════════════════════════════════════
# 3. HOW IT WORKS
# ══════════════════════════════════════════════════════════════════════
story += [section_heading('3. HOW IT WORKS — ARCHITECTURE & DATA FLOW'), sp(3)]
story += [p('The platform is a <b>single offline HTML file</b> (~33 MB) embedding all data, '
  '3D geometry, maps, dashboards and application code. It runs by double-clicking — no server, '
  'no installation. Internet is needed only for the live basemap tiles, weather API and Windy radar. '
  'The architecture has five layers:'), sp(3)]

arch_rows = [
    ('Layer 1 — Source data', 'Civil 3D pipe networks (xlsx quantities), Revit IFC4 building, '
     'APCRDA masterplan shapefile, QGIS QML zoning styles, ECW ortho imagery (pending conversion)'),
    ('Layer 2 — Build pipeline', 'Python scripts: parse xlsx → compact JSON per block; tessellate IFC '
     'via ifcopenshell → Draco-compressed glTF (building.glb); render shapefile → georeferenced PNG; '
     'extract IfcSpace rooms; fix invert levels; compute Manning capacity. Output: one set of data files.'),
    ('Layer 3 — make_app.py', 'Assembles the single HTML file: embeds the dashboard template, '
     'all 21 block networks, trunk main, building GLB+floors+rooms, landuse PNG, weather dashboard, '
     'decision dashboard (with 95k plots + 78k pipes), weather/storm params, zone storm capacity. '
     'All tokens replaced at build time.'),
    ('Layer 4 — Browser runtime', 'Three.js (3D), Leaflet + Esri Leaflet (GIS), DRACOLoader (compressed '
     'building geometry), Open-Meteo fetch (live weather), virtual sensor simulator (20s tick), '
     'real-time GIS buffer query (spatial loop over 95,935 plots + 78,053 pipes — runs in <1s in-browser).'),
    ('Layer 5 — Live feeds (future)', 'SCADA/IoT endpoint (ALERT_FEED_URL), Windy Point Forecast '
     'API (key needed), DEM for flood depth, EPANET hydraulic model, consumer connection database.'),
]
story += [kv_table(arch_rows, col_w=[48*mm, doc.width-48*mm]), sp(6)]

story += [h2('Data Flow: Source → App'), hr()]
flow_items = [
    ('Civil 3D / xlsx', '→', 'build_block.py', '→', 'Block network JSON\n(pipes, manholes, dims)'),
    ('Revit IFC4',      '→', 'ifc_to_glb.py + build_ar_floors.py + build_st_combine.py', '→', 'building_real_draco.glb\n(floors + colours + rooms)'),
    ('Masterplan shp',  '→', 'render_landuse.py + build_incident_data.py', '→', 'landuse.png + plots.json\n+ incident_net.json'),
    ('make_app.py',     '→', 'Assembles all of the above', '→', 'Amaravati_Twins_App.html'),
]
for src, a1, proc, a2, out in flow_items:
    ft = Table([[
        Paragraph(src, ParagraphStyle('ft1',fontName='Helvetica-Bold',fontSize=8,
            textColor=C_WHITE,alignment=TA_CENTER)),
        Paragraph('→', ParagraphStyle('arr',fontName='Helvetica-Bold',fontSize=12,
            textColor=C_TEAL,alignment=TA_CENTER)),
        Paragraph(proc, ParagraphStyle('ft2',fontName='Helvetica',fontSize=7.5,
            textColor=colors.HexColor('#374151'),alignment=TA_CENTER)),
        Paragraph('→', ParagraphStyle('arr2',fontName='Helvetica-Bold',fontSize=12,
            textColor=C_TEAL,alignment=TA_CENTER)),
        Paragraph(out, ParagraphStyle('ft3',fontName='Helvetica-Bold',fontSize=8,
            textColor=colors.HexColor('#065f46'),alignment=TA_CENTER)),
    ]], colWidths=[30*mm, 8*mm, 80*mm, 8*mm, doc.width-126*mm])
    ft.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(0,0),C_DARK),
        ('BACKGROUND',(2,0),(2,0),colors.HexColor('#f0f9ff')),
        ('BACKGROUND',(4,0),(4,0),colors.HexColor('#d1fae5')),
        ('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#c5dce8')),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
        ('LEFTPADDING',(0,0),(-1,-1),5),
    ]))
    story += [ft, sp(1)]
story += [sp(4), PageBreak()]

# ══════════════════════════════════════════════════════════════════════
# 4. SIMULATION METHODS
# ══════════════════════════════════════════════════════════════════════
story += [section_heading('4. SIMULATION METHODS — HOW EACH NUMBER IS CALCULATED'), sp(3)]

story += [h2('4.1  Virtual Sensor Network (demo SCADA)'), hr()]
story += [p('The twin runs approximately 50 virtual sensors across the 21 blocks — pressure '
  'transmitters (PT), DMA flow meters (FM), chlorine analysers (CL) and pump monitors (PU). '
  'Readings are recalculated every 20 seconds following a real diurnal demand pattern with noise. '
  'Faults spawn randomly, ramp up over 2–8 minutes and clear after 8–35 minutes. Every alert in '
  'the feed is a threshold breach on a moving sensor reading — exactly how real SCADA alerting works.'), sp(2)]
story += [kv_table([
    ('Pressure',  'value = base × (1.08 − 0.10 × diurnal_factor) + noise(±0.06 bar).\n'
                  'Fault: value × (1 − 0.62 × magnitude × ramp_progress).\n'
                  'Alert threshold: below 2.35 bar.'),
    ('Flow',      'value = base × diurnal_factor + noise(±5%).\n'
                  'Fault: value × (1 + 1.25 × magnitude × ramp_progress) — inlet flow spikes as a leak develops.\n'
                  'Alert threshold: above +45% of base.'),
    ('Chlorine',  'value = base + noise(±0.03 mg/L).\n'
                  'Fault: value × (1 − 0.80 × magnitude × ramp_progress).\n'
                  'Alert threshold: below 0.20 mg/L (WHO minimum).'),
    ('Pump',      'value = base × (0.85 + 0.20 × diurnal) + noise(±4 kW).\n'
                  'Fault: value × (1 − magnitude × ramp_progress) — pump draws less power as it fails.\n'
                  'Alert threshold: below 35% of base load.'),
], col_w=[28*mm, doc.width-28*mm]), sp(4)]

story += [h2('4.2  GIS Buffer Analysis (real spatial query)'), hr()]
story += [p('When you tap the map, the twin runs a real point-in-circle query against all 95,935 '
  'plot centroids and 78,053 pipe mid-points stored as integer metre offsets. No external GIS '
  'server is involved — the full computation runs in the browser in under one second.'), sp(2)]
story += [kv_table([
    ('Plot query',   'for each plot: distance² = (plot.dx − mx)² + (plot.dy − my)²; if < radius² → include'),
    ('Population',   'Population = Σ (plot_area_ha × planning_density_of_zone)\ne.g. R3 zone = 250 persons/ha  ·  R4 = 400  ·  Parks = 2  ·  Roads = 0'),
    ('Demand',       'Water demand at risk (MLD) = Population × 135 LPCD ÷ 1,000,000'),
    ('Road length',  'Road reserve area (from zoning) ÷ 12 m assumed width'),
    ('Risk score',   'score = pop/220 + 4×(hospitals×3 + schools×1.5 + govt) + 1.4×(total km in buffer)\n× 1.25 for contamination/fire  ·  capped at 100'),
], col_w=[32*mm, doc.width-32*mm]), sp(4)]

story += [h2('4.3  Storm-water Response (live rainfall → real capacity)'), hr()]
story += [kv_table([
    ('Live rainfall input',   'Open-Meteo hourly precipitation (past 48 h + next 24 h). '
                              'Peak intensity = worst of peak-1h and rolling 3-hour average.'),
    ('Antecedent wetness',    'C_effective = min(0.95,  0.70 + min(rain_48h / 60, 1) × 0.22)\n'
                              'Saturated ground raises the runoff coefficient from 0.70 toward 0.95.'),
    ('Runoff (rational method)', 'Q_peak = C_eff × intensity (mm/hr) × catchment_area (m²) ÷ 3,600,000   [m³/s]'),
    ('Outfall capacity',      'Q_cap = (1/n) × A × R^(2/3) × S^0.5   [Manning, n=0.014]\n'
                              'Computed from <b>real Civil 3D pipe diameters and invert-derived slopes</b>.\n'
                              'e.g. Zone 12 (1500 mm) = 1,367 m³/s  ·  Zone 10 (200 mm) = 62 m³/s'),
    ('Utilisation',           'Utilisation (%) = Q_peak / Q_cap × 100\nAlert: ≥50% = medium, ≥70% = watch, >100% = overflow risk'),
], col_w=[40*mm, doc.width-40*mm]), sp(4)]

story += [h2('4.4  Rule Engine — Recommended Actions'), hr()]
story += [p('The decision engine is a transparent deterministic rule set — not a trained AI model. '
  'Every card shows its formula and assumption. Key formulae:'), sp(2)]
story += [kv_table([
    ('Burst discharge',      'Q = Cd × A × √(2gH)  where Cd=0.62, bore fraction=20%, H=30 m (assumed head)\n'
                             'e.g. 600 mm main → Q ≈ 270 L/s ≈ 972 m³/hr'),
    ('Contaminant travel',   'Speed = 0.9 m/s = 3.2 km/hr  ·  time to buffer edge = radius ÷ 3,200 (min)'),
    ('Power / storage',      'Storage time = 8 hrs (CPHEEO standard)  ·  with 25% demand cut → 10.7 hrs'),
    ('Fire flow',            'Required: 30–60 L/s at 2 bar residual. A 300 mm main can deliver; <300 mm may not.'),
    ('Repair time estimate', 'Isolation 25 min  ·  Excavation + repair: 3–5 hrs (<600 mm), 6–10 hrs (≥600 mm)\n'
                             'Recharge + flush: 1 hr  →  Total: 5–7 hrs or 8–12 hrs'),
], col_w=[42*mm, doc.width-42*mm]), sp(4), PageBreak()]

# ══════════════════════════════════════════════════════════════════════
# 5. TECHNOLOGY STACK
# ══════════════════════════════════════════════════════════════════════
story += [section_heading('5. TECHNOLOGY STACK'), sp(3)]
story += [p('The entire platform is built on open-source and free-tier tools — no proprietary '
  'middleware or licences required for the core twin. Live API services are free/key-free.'), sp(3)]

tech = [
    ['Category', 'Technology / Library', 'Version / Notes', 'Role'],
    ['3D Viewer',   'Three.js',            'r128, CDN',     'WebGL 3D rendering for pipe networks and building'],
    ['3D Viewer',   'DRACOLoader',         'Three.js addon','Decompress Draco-compressed building GLB in browser'],
    ['GIS Map',     'Leaflet',             '1.9.4, CDN',    'Interactive map — layers, markers, popups'],
    ['GIS Map',     'Esri Leaflet',        '3.0.x, CDN',    'Satellite basemap (Imagery + ImageryLabels)'],
    ['Weather',     'Open-Meteo API',      'Free, no key',  'Live temperature, rainfall, 7-day forecast for Amaravati'],
    ['Weather',     'Windy.com embed',     'Free embed',    'Animated radar map — rain/wind/temp/cloud layers'],
    ['BIM/IFC',     'ifcopenshell',        '0.8.5, Python', 'Parse IFC4, tessellate geometry, extract rooms'],
    ['BIM/IFC',     'trimesh',             '4.x, Python',   'Build scene, export GLB, apply transforms'],
    ['BIM/IFC',     'gltf-pipeline',       'npm, Node.js',  'Draco compression of building GLB (872 KB from 14 MB)'],
    ['GIS process', 'pyshp (shapefile)',   'Python',        'Read masterplan shapefile (95,935 plots)'],
    ['GIS process', 'pyproj',             'Python',        'CRS transforms: EPSG:32644 ↔ EPSG:4326'],
    ['GIS process', 'Pillow (PIL)',        'Python',        'Render landuse colour image (4200×3757 px PNG)'],
    ['Build',       'Python 3.12',         'Build-time',    'All data processing, build pipeline, PDF report'],
    ['Build',       'ReportLab',           'Python',        'This project report PDF'],
    ['Compression', 'Draco (Google)',      'Via gltf-pipeline', 'Building GLB: 14.5 MB → 872 KB (16× smaller)'],
    ['Coord system','EPSG:32644',          'UTM Zone 44N',  'Native CRS for Amaravati — all network data'],
    ['Coord system','EPSG:4326',           'WGS84',        'Web map display, building georeferencing'],
    ['Standards',   'IFC4 (ISO 16739)',    'Revit export',  'Open BIM standard for the Admin building'],
    ['Standards',   'IfcMapConversion',    'IFC4',          'Georeferencing: local coords → UTM 44N'],
    ['Standards',   'Manning\'s equation', 'Engineering',   'Storm-drain outfall capacity from real pipe data'],
    ['Standards',   'CPHEEO guidelines',   'India water',   'Storage norms, demand planning (135 LPCD)'],
]
col_ws = [30*mm, 40*mm, 38*mm, doc.width-108*mm]
tdata = []
for i, row in enumerate(tech):
    if i==0:
        tdata.append([Paragraph(c, ParagraphStyle('th',fontName='Helvetica-Bold',fontSize=8,
            textColor=C_WHITE)) for c in row])
    else:
        tdata.append([Paragraph(c, ParagraphStyle('td2',fontName='Helvetica',fontSize=8,
            textColor=colors.HexColor('#1a3a5c'))) for c in row])
tech_tbl = Table(tdata, colWidths=col_ws)
tech_tbl.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(-1,0),C_DARK),
    ('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#c5dce8')),
    ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f0f9ff')]),
    ('VALIGN',(0,0),(-1,-1),'TOP'),
    ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
    ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
]))
story += [tech_tbl, sp(4), PageBreak()]

# ══════════════════════════════════════════════════════════════════════
# 6. DATA — REAL VS SIMULATED
# ══════════════════════════════════════════════════════════════════════
story += [section_heading('6. DATA — REAL vs SIMULATED'), sp(3)]
story += [p('A fundamental principle of this platform is honest, unambiguous labelling of data '
  'quality. The interface uses colour-coded tags: <b>● REAL</b> (green) for data from your actual '
  'Civil 3D / GIS / Revit sources, and <b>◐ SIMULATED</b> (amber) for modelled or demonstration '
  'values that will be replaced by live sensor data as the SCADA system is deployed.'), sp(3)]

ds_rows = [
    ('●', 'Pipe geometry, diameters, lengths, connectivity', 'REAL', 'Civil 3D xlsx quantities → build_block.py'),
    ('●', 'Manhole positions, rim levels, invert levels', 'REAL', 'Civil 3D. Zone 10 zero-inverts derived from connected pipes.'),
    ('●', 'Storm drain capacity per zone', 'REAL', 'Manning\'s equation on real diameters + invert-derived slopes'),
    ('●', 'Masterplan plot positions, zoning, areas', 'REAL', 'APCRDA shapefile — 95,935 plots, 35 zone types'),
    ('●', 'Landuse zoning colours', 'REAL', 'QML colour scheme from QGIS'),
    ('●', 'Building geometry, floors, materials', 'REAL', 'Revit IFC4 tessellated via ifcopenshell'),
    ('●', 'Building room names and areas', 'REAL', 'IfcSpace objects from Revit'),
    ('●', 'Rainfall / temperature / 7-day forecast', 'REAL', 'Open-Meteo live API (free, no key, auto-refreshed)'),
    ('●', 'Windy live radar map', 'REAL', 'Windy.com embed (free, no key)'),
    ('●', 'GIS buffer spatial query', 'REAL', 'In-browser point-in-circle on real plot + pipe data'),
    ('◐', 'Sensor readings (pressure, flow, chlorine, pump)', 'PARTIAL', 'Virtual simulator — real diurnal pattern, noise and fault model. Replaced by SCADA.'),
    ('◐', 'Population in the buffer', 'PARTIAL', 'Plot area × HMDA planning density — not census data'),
    ('◐', 'Burst discharge', 'PARTIAL', 'Orifice equation — assumed 30 m head, 20% bore. Replaced by live pressure.'),
    ('◐', 'Contaminant travel speed', 'PARTIAL', 'Assumed 0.9 m/s. Replaced by live flow meter.'),
    ('◐', 'Tank storage / drawdown', 'PARTIAL', 'CPHEEO standard 8 hrs. Replaced by live tank level.'),
    ('◐', 'Repair times', 'PARTIAL', 'Engineering estimates. Replaced by historical asset maintenance log.'),
    ('✗', 'Flood depth', 'PENDING', 'Needs a DEM (terrain model) + SWMM hydraulic routing'),
    ('✗', 'Pump station locations', 'PENDING', 'Needs the electrical asset register'),
    ('✗', 'Valve register', 'PENDING', 'Needed for true minimum-valve-set isolation'),
    ('✗', 'Consumer connections', 'PENDING', 'Needed for exact population count and NRW'),
]
story += [status_table(ds_rows,
    headers=['','Data / Parameter','Status','Source / Notes']), sp(4), PageBreak()]

# ══════════════════════════════════════════════════════════════════════
# 7. DELIVERABLES
# ══════════════════════════════════════════════════════════════════════
story += [section_heading('7. DELIVERABLES'), sp(3)]
story += [kv_table([
    ('Amaravati_Twins_App.html',   '~33 MB single-file offline application. Double-click to run. '
                                   'Contains all networks, building, landuse, dashboards and code. '
                                   'Internet needed only for map tiles and live weather.'),
    ('Amaravati_WTP_Admin_Building.html', '~1.3 MB standalone BIM viewer — full building with '
                                   'floor isolation, X-ray, edges, ghost, 89 room labels.'),
    ('WTP-ADMIN-AR_09_georeferenced.ifc', '~32 MB georeferenced architectural IFC4 — '
                                   'IfcProjectedCRS + IfcMapConversion (EPSG:32644) injected. '
                                   'Opens in any GIS or BIM tool at the correct Amaravati location.'),
    ('DECISION_SUPPORT.md',        'Full documentation of the decision support system: data flow, '
                                   'all formulae, real-vs-modelled table, 16-module status, '
                                   'alert payload schema, and next-data-needed list.'),
    ('Amaravati_DigitalTwin_FullPackage.zip', '~77 MB complete package:\n'
                                   '• build_pipeline/ — all Python scripts + HTML templates + logo\n'
                                   '• datasets/ — all data JSON, building source, landuse, decision datasets\n'
                                   '• webapp/ — hosted version (Vercel-deployable)\n'
                                   '• docs/ — DECISION_SUPPORT.md + workflow\n'
                                   '• README.txt — complete guide'),
], col_w=[60*mm, doc.width-60*mm]), sp(4)]

story += [h2('Package Contents Detail'), hr()]
story += [two_col(
    ['21 block network HTMLs (individual twin files)',
     'Zone combined HTMLs (6 zones)',
     'City and trunk combined views',
     'manifest.json (block metadata)',
     'combined.json (zone+city data)',
     'Trunk_Main_network.json',
     'plots.json (95,935 plot centroids + zoning)',
     'incident_net.json (78,053 pipes + 43,685 chambers)',
     'blocks_ll.json (21 block lat/lon)',
     'landuse.png + landuse_bounds.json + legend'],
    ['building_real_draco.glb (Draco-compressed building)',
     'floors.json + floor_order.json + spaces.json',
     'elem_color.json (real Revit material colours)',
     'recenter.json (model origin offset)',
     'bldg_loc.json (georeferenced position)',
     'Landuse_Styles.qml (original QGIS style)',
     'Source xlsx workbooks (all 21 blocks)',
     'Trunk_Model.dxf',
     'build_*.py, make_*.py, render_*.py scripts',
     'dashboard_template.html + all dashboard HTMLs']
), sp(6), PageBreak()]

# ══════════════════════════════════════════════════════════════════════
# 8. COMPARISON WITH SIEMENS SIWA
# ══════════════════════════════════════════════════════════════════════
story += [section_heading('8. BENCHMARK — SIEMENS SIWA vs AMARAVATI TWIN'), sp(3)]
story += [p('The Siemens SIWA platform (used in Spain at Servicios de Txingudi and Malaga) '
  'is an AI-powered water network analytics suite. Kreayotoo reviewed the SIWA case study to '
  'benchmark the Amaravati twin and map a realistic roadmap to that capability level.'), sp(3)]

compare = [
    ['Capability', 'SIWA (Spain)', 'Amaravati Twin (current)', 'Gap / Next step'],
    ['Network model', '285 km pipes modelled', '2,131+ km pipes in Civil 3D data', 'EPANET hydraulic model to build'],
    ['Leak detection', 'Real MNF on live DMA meters\nAI pre-locates to 45 m', 'MNF logic built — needs real flow meters', 'Install DMA inlet flow meters'],
    ['Sensor network', 'Flow, pressure, quality, AMI', '~50 virtual sensors (demo)', 'Install PT/FM/CL sensors + SCADA'],
    ['Customer meters', '238,000 AMI meters (Malaga)', 'None yet', 'Smart meter rollout (Phase 3)'],
    ['AI / ML', 'Trained on 3+ years of data', 'Rule engine (transparent, no training data)', 'ML possible after 1+ year of SCADA data'],
    ['SCADA historian', 'InfluxDB / time series', 'Not yet', 'InfluxDB + data pipeline (Phase 2)'],
    ['NRW accounting', 'Per-DMA mass balance, live', 'Framework built, needs live meters', 'DMA meters (Phase 1)'],
    ['3D / GIS twin', 'Not the SIWA focus', 'Full 3D + GIS + BIM (built)', 'AHEAD of SIWA in this dimension'],
    ['Offline / portable', 'Server-hosted', 'Full offline single-file HTML', 'AHEAD — unique advantage'],
    ['GIS buffer analysis','Not in SIWA', '95,935 plots + 78,053 pipes, real-time', 'AHEAD — unique to this twin'],
]
col_ws2 = [38*mm, 38*mm, 55*mm, doc.width-131*mm]
c_tdata = []
for i, row in enumerate(compare):
    if i==0:
        c_tdata.append([Paragraph(c, ParagraphStyle('th2',fontName='Helvetica-Bold',
            fontSize=8,textColor=C_WHITE)) for c in row])
    else:
        bg3 = colors.HexColor('#d1fae5') if 'AHEAD' in row[2] else colors.white
        c_tdata.append([Paragraph(c, ParagraphStyle('td3',fontName='Helvetica',
            fontSize=8,textColor=colors.HexColor('#1a3a5c'),leading=12,
            backColor=bg3 if j==2 else colors.white)) for j,c in enumerate(row)])
c_tbl = Table(c_tdata, colWidths=col_ws2)
c_tbl.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(-1,0),C_DARK),
    ('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#c5dce8')),
    ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f0f9ff')]),
    ('VALIGN',(0,0),(-1,-1),'TOP'),
    ('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
    ('LEFTPADDING',(0,0),(-1,-1),5),
]))
story += [c_tbl, sp(3)]
story += [p('<b>Key insight:</b> The Amaravati twin is <b>ahead of SIWA</b> in 3D/GIS visualisation, '
  'offline portability and spatial decision support. SIWA is ahead in live sensor analytics and AI. '
  'The gap is instrumentation — once SCADA and DMA meters are connected, the same analytical '
  'framework already built in this twin runs on real data with no redesign.'), sp(4), PageBreak()]

# ══════════════════════════════════════════════════════════════════════
# 9. FUTURE ROADMAP
# ══════════════════════════════════════════════════════════════════════
story += [section_heading('9. FUTURE ROADMAP'), sp(3)]
story += [p('The roadmap is structured in six phases. Phases 0–1 require no new software — only '
  'data. Phases 2–6 progressively close the gap to full operational AI-level capability.'), sp(3)]

phases = [
    ('Phase 0', 'Foundation (DONE)',
     ['All 21 blocks + 6 zones + city + trunk in the twin',
      'WTP Admin Building BIM (16 floors + 89 rooms + real materials)',
      'Landuse zoning overlay (95,935 plots)',
      'Live weather + storm-water simulation',
      'Alert-driven decision support + GIS buffer analysis',
      'Virtual SCADA sensor network (demo)',
      'Georeferenced IFC (EPSG:32644)']),
    ('Phase 1', 'Real Data Integration (now → 6 months)',
     ['ECW ortho imagery: convert to GeoTIFF in QGIS → drop into Zone 5D overlay',
      'WTP Admin Building: surveyed Easting/Northing → exact map placement',
      'Valve / hydrant register → true minimum-valve-set isolation',
      'Electrical asset register → pump stations, substations, DG sets',
      'DEM (terrain model) → flood depth + evacuation routing',
      'Consumer connection database → exact population, NRW per zone']),
    ('Phase 2', 'DMA Instrumentation (6–18 months)',
     ['Install DMA inlet electromagnetic flow meters (one per block entry)',
      'Install pressure loggers at zone inlets and network extremities',
      'Install water-quality sensors (chlorine, turbidity, pH) at WTP outlet + key points',
      'Connect to SCADA / IoT platform (MQTT or REST) → set ALERT_FEED_URL',
      'Time-series database (InfluxDB or TimescaleDB) + historian',
      'Leak detection dashboard reinstated on real Minimum Night Flow data']),
    ('Phase 3', 'Smart Meters + NRW (18–36 months)',
     ['Smart meter (AMI) rollout — per-connection daily consumption',
      'NRW panel: produced vs billed vs metered per DMA, live mass balance',
      'Demand forecasting: temperature + holiday + historical pattern → next-day peak',
      'EPANET hydraulic model: pressure heatmap, valve operation simulation, pipe failure modelling',
      'Automated supply interruption notification (SMS / app) from the decision engine']),
    ('Phase 4', 'AI Analytics (after 1+ year of SCADA data)',
     ['Leak pre-location: ML on pressure/flow patterns → narrowed to 45 m (SIWA level)',
      'Predictive maintenance: pump bearing failure prediction from current + vibration',
      'Burst risk model: pipe age + material + pressure history + break history',
      'Water quality prediction: contamination spread direction + concentration + time',
      'Seasonal demand model trained on accumulated consumption data']),
    ('Phase 5', 'Conversational AI + Automation (36+ months)',
     ['AI chat assistant: "Why is pressure low in Zone 5A?" → real answer from live data',
      'Automated valve control recommendation with one-click approval',
      'Digital twin time-travel: replay any historical incident with measured data',
      'Risk map: city-wide colour heatmap updated hourly from sensor health',
      'Full SIWA-level operational capability: leak finder + meter analytics + NRW + quality']),
    ('Phase 6', 'Platform Reuse (parallel track)',
     ['Separate the engine (3D/GIS/dashboards) from the project config (CRS, utilities, data paths)',
      'Config-driven project scaffolder: new city = one config file + data folder',
      'Airport variant: apron/taxiway/terminal zones, fuel lines, BMS/HVAC feeds, gates',
      'SaaS hosting: multi-project dashboard with project switcher',
      'First reuse project: existing city or airport client onboarded on the same engine']),
]
story += [phase_table(phases), sp(4), PageBreak()]

# ══════════════════════════════════════════════════════════════════════
# 10. WHAT DATA IS NEEDED NEXT
# ══════════════════════════════════════════════════════════════════════
story += [section_heading('10. WHAT DATA IS NEEDED NEXT'), sp(3)]
story += [p('The following data items, in order of impact on the platform\'s accuracy and '
  'capability, are either already in KSPL\'s possession or can be obtained from APCRDA/project '
  'records without new surveying or instrumentation:'), sp(3)]

next_data = [
    ('Immediate — no new work needed',
     ['WTP Admin Building surveyed Easting/Northing (from site-layout drawing) → exact building position on map',
      'ECW ortho for Zone 5D → convert to GeoTIFF in QGIS (File → Export → Save As, EPSG:32644, JPEG, ~6000 px) → send the .tif',
      'Remaining zone ortho files → same conversion',
      'Any additional block xlsx workbooks not yet in the package']),
    ('Short term — from existing records',
     ['Valve and hydrant register (location, type, size, status) → true isolation-point optimisation',
      'Electrical asset register (pump stations, substations, DG set locations, ratings)',
      'DEM / terrain model for Amaravati (even a 5 m resolution SRTM or LiDAR extract)',
      'Consumer connection database (plot ID, meter ID, monthly consumption)']),
    ('Medium term — from instrumentation',
     ['SCADA: DMA inlet flow meters + pressure loggers per block',
      'Water quality sensors: chlorine residual, turbidity, pH at WTP + key network points',
      'Tank level sensors + pump telemetry (flow, kW, status)',
      'Any existing SCADA data extracts (even CSV) from temporary monitoring campaigns']),
    ('For SCADA integration',
     ['Set ALERT_FEED_URL in decision_dashboard.html to your SCADA REST/MQTT endpoint',
      'Payload: id, type, severity, lat, lon, ts, source, msg, value, unit, radius',
      'The twin polls every 20 s and re-runs the full decision analysis on every new alert',
      'No other code changes needed — the integration hook is already built']),
]
for cat, items in next_data:
    story += [h3(cat)]
    for item in items: story.append(b(item))
    story.append(sp(2))
story += [sp(4), PageBreak()]

# ══════════════════════════════════════════════════════════════════════
# 11. HONEST LIMITATIONS
# ══════════════════════════════════════════════════════════════════════
story += [section_heading('11. HONEST LIMITATIONS'), sp(3)]
story += [p('The platform is designed to be transparent. The following limitations are known '
  'and clearly labelled in the interface:'), sp(2)]
lims = [
    ('Network geometry is schematic', 'Pipe positions are from Civil 3D plan-view drawings — '
     'horizontal alignment is accurate but vertical depth uses the invert/rim levels, not '
     'true survey coordinates. The 3D height exaggeration is intentional for visibility.'),
    ('Trunk main is schematic (~23 m grid)', 'The trunk main is modelled from the DXF plan — '
     'it is accurate in route but may not reflect as-built final positions.'),
    ('Population is planning-density based', 'Population in the buffer is computed as plot area '
     'times an HMDA planning density per zone type. It is not census data and will overestimate '
     'in not-yet-built areas.'),
    ('Burst discharge assumes 30 m head', 'The orifice equation uses an assumed 30 m static head. '
     'The true discharge depends on the actual operating pressure, which requires a live pressure sensor.'),
    ('Sensor readings are virtual', 'All ~50 sensors are simulated. They follow real diurnal patterns '
     'and fault physics but produce no real operational information. Labelled ◐ SIM throughout.'),
    ('Flood depth not modelled', 'A DEM is required for true flood depth simulation. The current '
     'storm module assesses drain capacity and surcharge risk but cannot predict water depth.'),
    ('Building position is approximate', 'The WTP Admin Building is placed at the network centre '
     'as a georeferenced placeholder. The exact position requires the surveyed Easting/Northing from the site plan.'),
    ('ECW ortho not integrated', 'The Zone 5D ortho image is in ECW (proprietary Hexagon format) '
     'which cannot be decoded without the Hexagon SDK. Conversion to GeoTIFF in QGIS is required first.'),
    ('Internet required for map + weather', 'The 3D viewer and core analysis run offline. '
     'The Esri satellite basemap, Open-Meteo weather and Windy radar require an internet connection.'),
    ('Decision engine is not trained AI', 'The recommended actions come from deterministic engineering '
     'rules, not a machine-learning model. Confidence levels are rule-based, not statistical. '
     'ML is possible after approximately one year of accumulated SCADA sensor history.'),
]
for title, desc in lims:
    story += [KeepTogether([h3(f'⚠  {title}'), p(desc), sp(1)])]
story += [sp(4), PageBreak()]

# ══════════════════════════════════════════════════════════════════════
# 12. CREDITS & CONTACT
# ══════════════════════════════════════════════════════════════════════
story += [section_heading('12. CREDITS & CONTACT'), sp(3)]
story += [kv_table([
    ('Client',           'Andhra Pradesh Capital Region Development Authority (APCRDA)\nAmaravati, Andhra Pradesh, India'),
    ('Platform developer','Kreayotoo Solutions (P) Ltd (KSPL)\nHyderabad, Telangana — Engineering · Solutions · Innovation'),
    ('Data sources',     'Civil 3D utility network quantities (APCRDA/contractor workbooks)\n'
                         'Revit IFC4 architectural + structural models (WTP Admin Building)\n'
                         'APCRDA Masterplan shapefile (95,935 plots, landuse zoning)\n'
                         'Open-Meteo (weather API) · Windy.com (radar embed)\n'
                         'Esri World Imagery (satellite basemap)'),
    ('Standards & references','IFC4 (ISO 16739) · EPSG:32644 (UTM Zone 44N) · EPSG:4326 (WGS84)\n'
                         'Manning\'s equation (n=0.014) · Rational Method (Q=CiA)\n'
                         'CPHEEO Manual on Water Supply · HMDA Planning Norms\n'
                         'WHO Guidelines for Drinking-water Quality (chlorine 0.2–0.5 mg/L)\n'
                         'Siemens SIWA (operational benchmark reference)'),
    ('Report generated', 'July 2026 · Kreayotoo Solutions (P) Ltd'),
], col_w=[42*mm, doc.width-42*mm]), sp(4)]

# closing banner
footer_tbl = Table([[Paragraph(
    'This report documents the Amaravati Capital City Digital Twin built by Kreayotoo Solutions (P) Ltd. '
    'All data from APCRDA sources is used solely for this project. The simulated sensor data is clearly '
    'labelled and does not represent actual operational readings. This document is confidential.',
    ParagraphStyle('disc', fontName='Helvetica-Oblique', fontSize=8, textColor=C_DIM,
        leading=13, alignment=TA_JUSTIFY))]], colWidths=[doc.width])
footer_tbl.setStyle(TableStyle([
    ('BACKGROUND',(0,0),(-1,-1),C_DARK),
    ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),
    ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),
    ('ROUNDEDCORNERS',[4]),
]))
story += [footer_tbl]

# ── BUILD ─────────────────────────────────────────────────────────────
doc.build(story)
sz = os.path.getsize(OUT)/1024/1024
print(f"PDF written: {OUT}  ({sz:.1f} MB)")
