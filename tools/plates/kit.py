"""The Lakehouse Plate System, as code.

One drawing kit for the three Go Live on Databricks Lakehouse plates, so a
recipe changes in one place and all three plates change with it. The rules this
file implements are stated in
`project_metadata/instructions/lakehouse-plate-system.md`; read that first.

Card heights are measured from the text each card holds (metrics.py), never
typed.
"""
from __future__ import annotations
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from metrics import text_w, lines, lh                                  # noqa: E402

PAPER, INK, MUTED, RULE, BAND, WHITE = '#FCFCFB', '#0B0B0B', '#52514E', '#DEDEDE', '#F3F3F3', '#FFFFFF'
WINE, ROSE, GREEN, SAGE = '#7A1F2B', '#F8EEF0', '#1B4D3E', '#EEF4F0'
ONGREEN, ROSED = '#C9DAD2', '#E8C6CB'   # subordinate type on a green / wine band
HELVE, MONO = 'Helvetica', 'Courier New'
TXT = 'text;html=0;strokeColor=none;fillColor=none;whiteSpace=wrap;overflow=hidden;'

_stack: list[list[str]] = [[]]
def out(): return _stack[-1]
def push(): _stack.append([])
def pop(): return _stack.pop()

def esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
             .replace('"', '&quot;').replace('\n', '&#10;'))

def cell(cid, value, style, x, y, w, h, parent='1'):
    out().append(
        f'<mxCell id="{cid}" value="{esc(value)}" style="{style}" vertex="1" parent="{parent}">\n'
        f'  <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>\n</mxCell>')

def obj(cid, lbl, cat, style, x, y, w, h, parent='1'):
    out().append(
        f'<object id="{cid}" label="{esc(lbl)}" spec_id="{cid}" spec_category="{cat}">\n'
        f'  <mxCell style="{style}" vertex="1" parent="{parent}">\n'
        f'    <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/>\n'
        f'  </mxCell>\n</object>')

def edge(cid, lbl, cat, style, src, tgt, points=None, lpos=None):
    pts = ''
    lp = f' x="{lpos}"' if lpos is not None else ''
    if points:
        inner = ''.join(f'<mxPoint x="{px}" y="{py}"/>' for px, py in points)
        pts = f'      <Array as="points">{inner}</Array>\n'
    out().append(
        f'<object id="{cid}" label="{esc(lbl)}" spec_id="{cid}" spec_category="{cat}">\n'
        f'  <mxCell style="{style}" edge="1" parent="1" source="{src}" target="{tgt}">\n'
        f'    <mxGeometry{lp} relative="1" as="geometry">\n{pts}    </mxGeometry>\n'
        f'  </mxCell>\n</object>')

def seg(cid, style, x1, y1, x2, y2, pts=None):
    arr = ''
    if pts:
        arr = '    <Array as="points">' + ''.join(f'<mxPoint x="{a}" y="{b}"/>' for a, b in pts) + '</Array>\n'
    out().append(
        f'<mxCell id="{cid}" style="{style}" edge="1" parent="1">\n'
        f'  <mxGeometry relative="1" as="geometry">\n{arr}'
        f'    <mxPoint x="{x1}" y="{y1}" as="sourcePoint"/>\n'
        f'    <mxPoint x="{x2}" y="{y2}" as="targetPoint"/>\n'
        f'  </mxGeometry>\n</mxCell>')

def label(cid, s, x, y, w, h, size=10, color=INK, bold=False, italic=False,
          align='left', mono=False, track=0, parent='1', valign='middle'):
    st = (TXT + f'align={align};verticalAlign={valign};'
          f'fontFamily={MONO if mono else HELVE};fontSize={size};fontColor={color};')
    fs = (1 if bold else 0) + (2 if italic else 0)
    if fs: st += f'fontStyle={fs};'
    if track: st += f'letterSpacing={track};'
    cell(cid, s, st, x, y, w, h, parent)

# ------------------------------------------------------------------ grid
# Plate-specific: PAGE_W, M, CONTENT_W are set by each plate.
RAIL_PAD, CHIP_H, GUTTER = 24, 34, 40
CX, CTOP, CBOT = 14, 12, 12

def store_style(accepted=False):
    return (f'rounded=0;fillColor={SAGE if accepted else WHITE};strokeColor={GREEN};'
            f'strokeWidth={2.4 if accepted else 1.6};fontFamily={HELVE};fontSize=12;fontColor={INK};')

OP_STYLE = (f'rounded=1;absoluteArcSize=1;arcSize=14;fillColor={ROSE};strokeColor={WINE};'
            f'strokeWidth=1.8;fontFamily={HELVE};fontSize=12;fontColor={INK};')
ATT_STYLE = (f'rounded=1;absoluteArcSize=1;arcSize=14;fillColor={ROSE};strokeColor={WINE};'
             f'strokeWidth=1.8;dashed=1;dashPattern=7 4;fontFamily={HELVE};fontSize=12;fontColor={INK};')

TITLE_H = 32

# subordinate type set on a filled band, one clear step below `paper`
DIM = {GREEN: ONGREEN, WINE: ROSED, MUTED: RULE}


def title_row(cid, w, ink, name, type_label=None, mono_name=False, tag=None,
              rounded=False):
    """The one title row every node opens with: a band filled in the node's own
    ink, reversed type on it, left-aligned, any tag beside the name."""
    dim = DIM[ink]
    bar = f'fillColor={ink};strokeColor={ink};fontFamily={HELVE};fontSize=12;fontColor={PAPER};'
    if rounded:
        # square the band's foot so only its top corners follow the card's arc
        cell(cid + '_bar', '', 'rounded=1;absoluteArcSize=1;arcSize=14;' + bar, 0, 0, w, TITLE_H, cid)
        cell(cid + '_bar_foot', '', 'rounded=0;' + bar, 0, 14, w, TITLE_H - 14, cid)
    else:
        cell(cid + '_bar', '', 'rounded=0;' + bar, 0, 0, w, TITLE_H, cid)
    x = CX
    if type_label:
        t = type_label + ':'
        tw = round(text_w(t, 11)) + 3
        label(cid + '_type', t, x, 0, tw, TITLE_H, 11, dim, parent=cid)
        x += tw + 6
    tgw = round(text_w(tag, 10, bold=True) + 2 * (len(tag) - 1)) + 10 if tag else 0
    label(cid + '_name', name, x, 0, w - x - CX - tgw, TITLE_H, 12, PAPER,
          bold=True, mono=mono_name, parent=cid)
    if tag:
        nx = x + round(text_w(name, 12, bold=True, mono=mono_name)) + 12
        label(cid + '_tag', tag, nx, 0, tgw, TITLE_H, 10, dim, bold=True, track=2, parent=cid)
    return TITLE_H + 2


def body(cid, w, text, y, size=10, color=MUTED, key='b'):
    avail = w - 2 * CX
    h = lines(text, size, avail) * lh(size)
    label(cid + '_' + key, text, CX, y, avail, h, size, color, parent=cid, valign='top')
    return h



# ------------------------------------------------------------------ edge lexicon
FLOW = (f'edgeStyle=orthogonalEdgeStyle;rounded=1;arcSize=10;jettySize=auto;html=0;'
        f'strokeColor={INK};strokeWidth=1.8;endArrow=blockThin;endFill=1;endSize=8;'
        f'labelBackgroundColor={BAND};verticalAlign=middle;fontFamily={HELVE};fontSize=10;fontColor={INK};')
TRIG = (f'edgeStyle=orthogonalEdgeStyle;rounded=1;arcSize=10;jettySize=auto;html=0;'
        f'strokeColor={WINE};strokeWidth=1.8;dashed=1;dashPattern=2 3;endArrow=blockThin;endFill=1;endSize=8;'
        f'labelBackgroundColor={BAND};verticalAlign=middle;fontFamily={HELVE};fontSize=10;fontColor={WINE};fontStyle=1;')
CEIL = (f'edgeStyle=orthogonalEdgeStyle;rounded=1;arcSize=10;jettySize=auto;html=0;'
        f'strokeColor={WINE};strokeWidth=1.6;dashed=1;dashPattern=6 4;endArrow=blockThin;endFill=1;endSize=8;'
        f'labelBackgroundColor={BAND};verticalAlign=middle;fontFamily={HELVE};fontSize=10;fontColor={WINE};fontStyle=1;')
FAIL = (f'edgeStyle=orthogonalEdgeStyle;rounded=1;arcSize=10;jettySize=auto;html=0;'
        f'strokeColor={WINE};strokeWidth=2.2;endArrow=blockThin;endFill=1;endSize=8;'
        f'labelBackgroundColor={PAPER};verticalAlign=middle;fontFamily={HELVE};fontSize=10;fontColor={WINE};fontStyle=1;')
CONT = (f'edgeStyle=orthogonalEdgeStyle;rounded=0;html=0;strokeColor={MUTED};strokeWidth=1.4;'
        f'dashed=1;dashPattern=4 4;endArrow=diamondThin;endFill=1;endSize=12;'
        f'labelBackgroundColor={BAND};fontFamily={HELVE};fontSize=10;fontColor={MUTED};')


def frame_style(head_h=34, align='right'):
    """A group frame: card body, rule header bar, heading at whichever end of the bar
    no lane crosses."""
    spacing = 'spacingRight=16;' if align == 'right' else 'spacingLeft=16;'
    return (f'swimlane;startSize={head_h};container=1;collapsible=0;recursiveResize=0;'
            f'fillColor={RULE};swimlaneFillColor={WHITE};strokeColor={MUTED};strokeWidth=1.4;'
            f'align={align};{spacing}verticalAlign=middle;whiteSpace=wrap;overflow=hidden;'
            f'fontFamily={HELVE};fontSize=14;fontColor={INK};fontStyle=1;letterSpacing=2;')


# ------------------------------------------------------------------ plate chrome
def plate_title(text, x, y, w):
    obj('title', text, 'chrome',
        TXT + f'align=left;verticalAlign=middle;fontFamily={HELVE};fontSize=20;fontColor={INK};fontStyle=1;',
        x, y, w, 30)


def legend(keys, x, y, w, h=48, extra=None):
    """One horizontal row under the title. Each swatch is the real recipe."""
    obj('legend', '', 'chrome',
        f'rounded=0;fillColor={BAND};strokeColor={RULE};fontFamily={HELVE};fontSize=12;fontColor={INK};',
        x, y, w, h)
    label('legend_t', 'LEGEND', 16, 0, 70, h, 10, MUTED, bold=True, track=2, parent='legend')
    kx, sw, sh = 96, 38, 22
    for kid, ktxt, kstyle, band_ink in keys:
        obj(kid, '', 'chrome', kstyle + f'fontFamily={HELVE};fontSize=12;fontColor={INK};',
            kx, (h - sh) // 2, sw, sh, parent='legend')
        if extra and kid in extra:
            extra[kid](kid, sw, sh)
        if band_ink:
            cell(kid + '_bar', '', f'rounded=0;fillColor={band_ink};strokeColor={band_ink};'
                 f'fontFamily={HELVE};fontSize=10;fontColor={PAPER};', 0, 0, sw, 7, kid)
        tw = round(text_w(ktxt, 11)) + 4
        label(kid + '_t', ktxt, kx + sw + 9, 0, tw, h, 11, INK, parent='legend')
        kx += sw + 9 + tw + 26
    assert kx < w, f'legend overflows: {kx} > {w}'


def rail(rid, num, name, x, y, w, h, name_w=230):
    """A numbered band. The name is capped so a lane can cross the rail head."""
    cell(rid, '', f'rounded=0;fillColor={BAND};strokeColor={RULE};fontFamily={HELVE};fontSize=12;fontColor={INK};',
         x, y, w, h)
    cell(rid + '_badge', num,
         f'rounded=1;absoluteArcSize=1;arcSize=6;fillColor={WINE};strokeColor={WINE};'
         f'align=center;verticalAlign=middle;fontFamily={MONO};fontSize=13;fontColor={PAPER};fontStyle=1;',
         x + 18, y + 5, 24, 24)
    label(rid + '_name', name, x + 50, y + 5, min(w - 68, name_w), 24, 14, INK, bold=True, track=2)


def schema(cid, w, cols, y, key='sc'):
    """A store card's column list: one identifier per row, mono."""
    for i, c in enumerate(cols):
        label(f'{cid}_{key}{i}', c, CX + 2, y + i * 17, w - 2 * CX - 4, 17, 10, INK, mono=True, parent=cid)
    return len(cols) * 17


def write(dest, page_w, page_h):
    doc = (f'<mxGraphModel dx="1400" dy="900" grid="0" gridSize="10" guides="1" tooltips="1" '
           f'connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{page_w}" '
           f'pageHeight="{page_h}" math="0" shadow="0" background="{PAPER}">\n'
           f'  <root>\n    <mxCell id="0"/>\n    <mxCell id="1" parent="0"/>\n'
           + '\n'.join(_stack[0]) + '\n  </root>\n</mxGraphModel>\n')
    p = pathlib.Path(dest)
    p.write_text(doc)
    print(f'{p}  {page_w}x{page_h}')
