#!/usr/bin/env python3
"""Emit resources/img_src/section_databricks_layout_planning.drawio — Plate 01,
*Deployment Process Flow*.

Every recipe comes from kit.py. Only this plate's own copy, geometry and edges
live here.
"""
from __future__ import annotations
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from kit import *                                                       # noqa: F403
from kit import (PAPER, INK, MUTED, RULE, BAND, WHITE, WINE, ROSE, GREEN, SAGE,
                 HELVE, MONO, TXT, RAIL_PAD, CHIP_H, GUTTER, CX, CTOP, CBOT,
                 TITLE_H, cell, obj, edge, seg, label, out, push, pop,
                 store_style, OP_STYLE, ATT_STYLE, title_row, body, frame_style,
                 legend, rail, write, FLOW, TRIG, CEIL, FAIL, CONT,
                 text_w, lines, lh)

PAGE_W, M = 1436, 64
CONTENT_W = PAGE_W - 2 * M                 # 1308

# ============================================================ copy
US_BODY = 'Keep one boolean per query and per row, aggregated into hour bins'
TREE_CAP = 'bottom cut: ingestion time'
# leaf counts are drawn, never printed: A is balanced at 4, B is uneven at 3
TREE_SHAPE = {'tree_a': 4, 'tree_b': 3}
NODE_D, LEVEL_H = 14, 32
GLYPH_H = NODE_D + 2 * LEVEL_H
BOUNDS = ['resource monitor', 'complexity bound', 'partition-limit prune']
HE_BODY = 'Track underperforming decisions to help guide the next search iteration'
KN_BODY = ('Spend the table partition limit as a container budget, one container at a '
           'time, on every candidate tree')
HO_BODY = ('Replay the candidate trees against held-out queries under one global '
           'equal-size container policy')
GATE_Q = 'Does the skipping ratio hold on held-out queries?'
TF_BODY = 'Hand the tree that held up on holdout to the splitter on the write path'

# ============================================================ build
LEGEND_Y, LEGEND_H = 26, 48
ROW_A_Y = LEGEND_Y + LEGEND_H + 34

R1_X, R1_W = M, 520
R1_IN_X, R1_IN_W = R1_X + RAIL_PAD, R1_W - 2 * RAIL_PAD          # 472
R2_X = R1_X + R1_W + 20
R2_W = CONTENT_W - R1_W - 20                                      # 768
R2_IN_X, R2_IN_W = R2_X + RAIL_PAD, R2_W - 2 * RAIL_PAD           # 720
PILL_H = 22

# ---- usage_summary
COLS = ['record_id', 'hour_bin', 'q_01', 'q_02', 'q_03', '…']
ROWS = [['r_004171', '09:00', '1', '0', '1', '…'],
        ['r_004172', '09:00', '0', '0', '1', '…'],
        ['r_004173', '10:00', '1', '1', '0', '…'],
        ['r_004174', '10:00', '0', '1', '1', '…'],
        ['r_004175', '11:00', '1', '0', '0', '…']]
us_w = R1_IN_W
_base = [round(max([text_w(c, 10, mono=True)] + [text_w(r[i], 10, mono=True) for r in ROWS])) + 16
         for i, c in enumerate(COLS)]
_avail = us_w - 2 * CX
_share = (_avail - sum(_base)) // len(_base)
COLW = [b + _share for b in _base]
COLW[0] += _avail - sum(COLW)
TH, TR, TE = 24, 22, 20
TBL_H = TH + len(ROWS) * TR + TE

push()
cur = title_row('usage_summary', us_w, GREEN, 'usage_summary', 'DL Table', mono_name=True)
cur += CTOP
cur += body('usage_summary', us_w, 'SAMPLE ROWS · one boolean column per query', cur, 10, WINE, key='sample')
cur += 4
TBL_Y = cur
cell('us_tbl_head', '', f'rounded=0;fillColor={BAND};strokeColor={RULE};fontFamily={HELVE};fontSize=10;fontColor={INK};',
     CX, TBL_Y, _avail, TH, 'usage_summary')
_x = CX
for i, c in enumerate(COLS):
    label(f'us_col_{i}', c, _x + 7, TBL_Y, COLW[i] - 14, TH, 10, MUTED, bold=True, mono=True, parent='usage_summary')
    _x += COLW[i]
for j, r in enumerate(ROWS):
    ry = TBL_Y + TH + j * TR
    _x = CX
    for i, v in enumerate(r):
        label(f'us_r{j}c{i}', v, _x + 7, ry, COLW[i] - 14, TR, 10, INK, mono=True, parent='usage_summary')
        _x += COLW[i]
    cell(f'us_rule_{j}', '', f'rounded=0;fillColor={RULE};strokeColor=none;fontFamily={HELVE};fontSize=10;fontColor={INK};',
         CX, ry + TR - 1, _avail, 1, 'usage_summary')
_ey = TBL_Y + TH + len(ROWS) * TR
_x = CX
for i, c in enumerate(COLS):
    label(f'us_ell_{i}', '⋮', _x + 7, _ey, COLW[i] - 14, TE, 10, MUTED, mono=True, parent='usage_summary')
    _x += COLW[i]
cell('us_tbl_box', '', f'rounded=0;fillColor=none;strokeColor={RULE};fontFamily={HELVE};fontSize=10;fontColor={INK};',
     CX, TBL_Y, _avail, TBL_H, 'usage_summary')
cur = TBL_Y + TBL_H + 10
cur += body('usage_summary', us_w, US_BODY, cur, 10, MUTED, key='n1')
US_H = cur + CBOT
US_KIDS = pop()

# ---- search frame
sf_w = R2_IN_W
SF_HEAD, SF_PAD = 34, 18
sf_in_w = sf_w - 2 * SF_PAD
tree_w = (sf_in_w - 20) // 2

def tree_card(cid, letter):
    push()
    c = title_row(cid, tree_w, GREEN, letter, 'Split Tree Candidate')
    c += CTOP
    glyph_y = c
    c += GLYPH_H + 10
    label(cid + '_cap', TREE_CAP, CX, c, tree_w - 2 * CX, 14, 10, MUTED,
          align='center', parent=cid)
    c += 14
    return c + CBOT, glyph_y, pop()

TREE_H, GLYPH_Y, TREE_A_KIDS = tree_card('tree_a', 'A')
_, _, TREE_B_KIDS = tree_card('tree_b', 'B')

PILL_W = [round(text_w(b, 10)) + 34 for b in BOUNDS]
PILL_GAP = 12
sf_cur = SF_HEAD + SF_PAD
BEAM_LBL_Y = sf_cur
sf_cur += 20
TREE_Y = sf_cur
sf_cur += TREE_H + 20
BOUND_LBL_Y = sf_cur
sf_cur += 20
PILL_Y = sf_cur
SF_H = sf_cur + 28 + SF_PAD

# ---- heuristics
OUT_W = 520                      # the two objects the gate hands off to
he_w = OUT_W
push()
cur = title_row('heuristics', he_w, WINE, 'failed split trees', 'Dynamic Feedback', rounded=True)
cur += CTOP
cur += body('heuristics', he_w, HE_BODY, cur, 10, MUTED, key='b')
HE_H = cur + CBOT
HE_KIDS = pop()

RAIL1_H = CHIP_H + 18 + PILL_H + 10 + US_H + 18
RAIL2_H = CHIP_H + 18 + SF_H + 18
ROW_A_H = RAIL2_H
US_Y = ROW_A_Y + CHIP_H + 18 + PILL_H + 10
SF_Y = ROW_A_Y + CHIP_H + 18

# ---- rail 3
ROW_B_Y = ROW_A_Y + ROW_A_H + GUTTER
R3_IN_X, R3_IN_W = M + RAIL_PAD, CONTENT_W - 2 * RAIL_PAD          # 1260
kn_w, ov_w, ho_w = 380, 380, 360
kn_x = R3_IN_X
ov_x = kn_x + kn_w + 76
ho_x = ov_x + ov_w + 64

push()
cur = title_row('mckp', kn_w, WINE, 'Optimistic Knapsack Simulation (MCKP)', rounded=True)
cur += CTOP
cur += body('mckp', kn_w, KN_BODY, cur, 10, MUTED, key='b')
KN_H = cur + CBOT
KN_KIDS = pop()

push()
cur = title_row('holdout', ho_w, WINE, 'Experiment Simplified Assignment On Holdout', rounded=True)
cur += CTOP
cur += body('holdout', ho_w, HO_BODY, cur, 10, MUTED, key='b')
HO_H = cur + CBOT
HO_KIDS = pop()

OV_HEAD, OV_PLOT, OV_AXISBLK, OV_KEY = 33, 104, 46, 18
OV_H = OV_HEAD + 22 + OV_PLOT + OV_AXISBLK + 2 * OV_KEY + 6
CARD_Y = ROW_B_Y + CHIP_H + 18
ROW_B_INNER = max(OV_H, KN_H, HO_H)
KN_Y = CARD_Y + (ROW_B_INNER - KN_H) // 2
HO_Y = CARD_Y + (ROW_B_INNER - HO_H) // 2
OV_Y = CARD_Y + (ROW_B_INNER - OV_H) // 2
CEIL_LANE = CARD_Y + ROW_B_INNER + 24
ROW_B_H = CHIP_H + 18 + ROW_B_INNER + 24 + 20

# ---- rail 4
ROW_C_Y = ROW_B_Y + ROW_B_H + GUTTER
R4_IN_X, R4_IN_W = M + RAIL_PAD, CONTENT_W - 2 * RAIL_PAD
GATE_W, GATE_H = 400, 204
GATE_TXT_W = 236
gate_x = R4_IN_X
tf_w = OUT_W
tf_x = gate_x + GATE_W + 280
push()
cur = title_row('tree_frozen', tf_w, GREEN, 'Pre-Built', 'Split Tree', tag='FROZEN')
cur += CTOP
cur += body('tree_frozen', tf_w, TF_BODY, cur, 10, MUTED, key='b')
TF_H = cur + CBOT
TF_KIDS = pop()

OUT_GAP = 26
OUT_STACK = TF_H + OUT_GAP + HE_H
ROW_C_INNER = max(GATE_H, OUT_STACK)
ROW_C_H = CHIP_H + 18 + ROW_C_INNER + 18
_c4 = ROW_C_Y + CHIP_H + 18
GATE_Y = _c4 + (ROW_C_INNER - GATE_H) // 2
TF_Y = _c4 + (ROW_C_INNER - OUT_STACK) // 2
HE_Y = TF_Y + TF_H + OUT_GAP

LANE_R = PAGE_W - 22
PAGE_H = ROW_C_Y + ROW_C_H + 40

# ============================================================ emit
def _tree_key(kid, sw, sh):
    cell(kid + '_int', '', f'ellipse;fillColor={WHITE};strokeColor={GREEN};strokeWidth=1.4;'
         f'fontFamily={HELVE};fontSize=10;fontColor={INK};', 0, 5, 12, 12, kid)
    cell(kid + '_br', '', f'rounded=0;fillColor={GREEN};strokeColor={GREEN};'
         f'fontFamily={HELVE};fontSize=10;fontColor={INK};', 12, 10, 14, 1.3, kid)
    cell(kid + '_leaf', '', f'rounded=0;fillColor={GREEN};strokeColor={GREEN};strokeWidth=1.4;'
         f'fontFamily={HELVE};fontSize=10;fontColor={PAPER};', 26, 5, 12, 12, kid)


def _frozen_key(kid, sw, sh):
    label(kid + '_tag', 'FROZEN', 0, 8, sw, 13, 7, GREEN, bold=True, align='center', parent=kid)


legend([
    ('legend_key_persisted', 'persisted table',
     f'rounded=0;fillColor={WHITE};strokeColor={GREEN};strokeWidth=1.6;', GREEN),
    ('legend_key_frozen', 'frozen output',
     f'rounded=0;fillColor={SAGE};strokeColor={GREEN};strokeWidth=2.4;', GREEN),
    ('legend_key_operation', 'operation',
     f'rounded=1;absoluteArcSize=1;arcSize=10;fillColor={ROSE};strokeColor={WINE};strokeWidth=1.8;', WINE),
    ('legend_key_heuristics', 'dynamic feedback',
     f'rounded=1;absoluteArcSize=1;arcSize=10;fillColor={ROSE};strokeColor={WINE};strokeWidth=1.8;'
     f'dashed=1;dashPattern=7 4;', WINE),
    ('legend_key_decision', 'decision gate',
     f'rhombus;fillColor={ROSE};strokeColor={WINE};strokeWidth=1.8;', None),
    ('legend_key_tree', 'split point · leaf container',
     f'rounded=0;fillColor=none;strokeColor=none;', None),
    ('legend_key_ceiling', 'dashed = ceiling only',
     f'shape=line;strokeColor={WINE};strokeWidth=1.8;dashed=1;dashPattern=6 4;', None),
], M, LEGEND_Y, CONTENT_W, LEGEND_H,
    extra={'legend_key_tree': _tree_key, 'legend_key_frozen': _frozen_key})

for _r in [('rail_1', '1', 'COLLECT', R1_X, ROW_A_Y, R1_W, RAIL1_H),
           ('rail_2', '2', 'SEARCH', R2_X, ROW_A_Y, R2_W, ROW_A_H),
           ('rail_3', '3', 'SPEND & CHECK', M, ROW_B_Y, CONTENT_W, ROW_B_H),
           ('rail_4', '4', 'GATE', M, ROW_C_Y, CONTENT_W, ROW_C_H)]:
    rail(*_r)

cell('only_input', 'ONLY RAW INPUT',
     f'rounded=1;arcSize=50;fillColor={WHITE};strokeColor={MUTED};align=center;verticalAlign=middle;'
     f'fontFamily={HELVE};fontSize=10;fontColor={MUTED};fontStyle=1;letterSpacing=2;',
     R1_IN_X, ROW_A_Y + CHIP_H + 18, us_w, PILL_H)
obj('usage_summary', '', 'data_persisted', store_style(), R1_IN_X, US_Y, us_w, US_H)
out().extend(US_KIDS)

obj('search', 'OPTIMIZE SPLIT DECISION TREES', 'group',
    f'swimlane;startSize={SF_HEAD};container=1;collapsible=0;recursiveResize=0;'
    f'fillColor={RULE};swimlaneFillColor={WHITE};strokeColor={MUTED};strokeWidth=1.4;'
    f'align=right;spacingRight=16;verticalAlign=middle;whiteSpace=wrap;overflow=hidden;'
    f'fontFamily={HELVE};fontSize=14;fontColor={INK};fontStyle=1;letterSpacing=2;',
    R2_IN_X, SF_Y, sf_w, SF_H)
obj('tree_a', '', 'data_persisted', store_style(), SF_PAD, TREE_Y, tree_w, TREE_H, 'search')
out().extend(TREE_A_KIDS)
obj('tree_b', '', 'data_persisted', store_style(), SF_PAD + tree_w + 20, TREE_Y, tree_w, TREE_H, 'search')
out().extend(TREE_B_KIDS)
label('beam_lbl', 'BEAM', SF_PAD, BEAM_LBL_Y, sf_in_w, 16, 10, MUTED, bold=True, track=2, parent='search')
label('bounded_by', 'BOUNDED BY', SF_PAD, BOUND_LBL_Y, sf_in_w, 16, 10, MUTED, bold=True, track=2, parent='search')
_px = SF_PAD
for bid, btxt, bw in zip(['bound_resource', 'bound_complexity', 'bound_partitions'], BOUNDS, PILL_W):
    obj(bid, btxt, 'chrome',
        f'rounded=1;arcSize=50;fillColor={BAND};strokeColor={MUTED};align=center;'
        f'verticalAlign=middle;whiteSpace=wrap;overflow=hidden;fontFamily={HELVE};fontSize=10;fontColor={INK};',
        _px, PILL_Y, bw, 28, 'search')
    _px += bw + PILL_GAP

# ---- mini split trees: internal nodes are circles, leaves are filled containers
NODE_INT = (f'ellipse;fillColor={WHITE};strokeColor={GREEN};strokeWidth=1.4;'
            f'fontFamily={HELVE};fontSize=10;fontColor={INK};')
NODE_LEAF = (f'rounded=0;fillColor={GREEN};strokeColor={GREEN};strokeWidth=1.4;'
             f'fontFamily={HELVE};fontSize=10;fontColor={PAPER};')
BRANCH = (f'html=0;endArrow=none;strokeColor={GREEN};strokeWidth=1.3;'
          f'fontFamily={HELVE};fontSize=10;fontColor={INK};')
R = NODE_D // 2

def mini_tree(cid, ax, ay, w, leaves):
    """Draw a binary split tree of `leaves` leaves, centred in (ax, ay, w, GLYPH_H)."""
    cx = ax + w // 2
    ly = [ay + R, ay + LEVEL_H + R, ay + 2 * LEVEL_H + R]   # node centres per level
    if leaves == 4:                      # balanced: root, two cuts, four containers
        internal = [(cx, ly[0]), (cx - 62, ly[1]), (cx + 62, ly[1])]
        leaf = [(cx - 92, ly[2]), (cx - 32, ly[2]), (cx + 32, ly[2]), (cx + 92, ly[2])]
        branches = [(0, 1), (0, 2), (1, 3), (1, 4), (2, 5), (2, 6)]
    else:                                # uneven: one branch is cut again, one is not
        internal = [(cx, ly[0]), (cx - 62, ly[1])]
        leaf = [(cx - 92, ly[2]), (cx - 32, ly[2]), (cx + 62, ly[2])]
        branches = [(0, 1), (0, 4), (1, 2), (1, 3)]
    pts = internal + leaf
    for i, (bx, by) in enumerate(pts):
        style = NODE_INT if i < len(internal) else NODE_LEAF
        cell(f'{cid}_n{i}', '', style, bx - R, by - R, NODE_D, NODE_D)
    for k, (a, b) in enumerate(branches):
        seg(f'{cid}_e{k}', BRANCH, pts[a][0], pts[a][1] + R, pts[b][0], pts[b][1] - R)

for cid, off in (('tree_a', 0), ('tree_b', tree_w + 20)):
    mini_tree(cid, R2_IN_X + SF_PAD + off, SF_Y + TREE_Y + GLYPH_Y, tree_w, TREE_SHAPE[cid])

obj('mckp', '', 'operation', OP_STYLE, kn_x, KN_Y, kn_w, KN_H)
out().extend(KN_KIDS)
obj('holdout', '', 'operation', OP_STYLE, ho_x, HO_Y, ho_w, HO_H)
out().extend(HO_KIDS)

# ---- overlay chart panel
obj('overlay', '', 'overlay_panel',
    f'rounded=0;fillColor={WHITE};strokeColor={MUTED};strokeWidth=1.4;fontFamily={HELVE};fontSize=12;fontColor={INK};',
    ov_x, OV_Y, ov_w, OV_H)
title_row('overlay', ov_w, MUTED, 'Skipping Gain Against Metadata Cost', 'Chart')
PL_X0, PL_X1 = ov_x + 22, ov_x + ov_w - 22
PL_Y0 = OV_Y + OV_HEAD + 22
PL_Y1 = PL_Y0 + OV_PLOT
LIMIT_X = PL_X0 + round((PL_X1 - PL_X0) * 0.62)
cell('ov_past', '', f'rounded=0;fillColor={BAND};strokeColor=none;fontFamily={HELVE};fontSize=10;fontColor={INK};',
     LIMIT_X, PL_Y0, PL_X1 - LIMIT_X, PL_Y1 - PL_Y0)
label('ov_past_t', 'HEADROOM', LIMIT_X, PL_Y1 - 18, PL_X1 - LIMIT_X, 12,
      8, MUTED, bold=True, track=1, align='center')
AX = f'html=0;endArrow=none;strokeColor={MUTED};strokeWidth=1.2;fontFamily={HELVE};fontSize=10;fontColor={INK};'
seg('ov_y', AX, PL_X0, PL_Y0, PL_X0, PL_Y1)
seg('ov_x', AX, PL_X0, PL_Y1, PL_X1, PL_Y1)
_sp = PL_X1 - PL_X0
seg('ov_skip', f'html=0;curved=1;endArrow=none;strokeColor={GREEN};strokeWidth=2.4;fontFamily={HELVE};fontSize=10;fontColor={INK};',
    PL_X0 + 2, PL_Y1 - 6, PL_X1 - 4, PL_Y0 + 12,
    pts=[(PL_X0 + round(_sp * .2), PL_Y0 + 52), (PL_X0 + round(_sp * .45), PL_Y0 + 22),
         (PL_X0 + round(_sp * .72), PL_Y0 + 14)])
seg('ov_meta', f'html=0;curved=1;endArrow=none;strokeColor={WINE};strokeWidth=2.4;dashed=1;dashPattern=7 4;fontFamily={HELVE};fontSize=10;fontColor={INK};',
    PL_X0 + 2, PL_Y1 - 2, PL_X1 - 4, PL_Y0 + 34,
    pts=[(PL_X0 + round(_sp * .3), PL_Y1 - 12), (PL_X0 + round(_sp * .6), PL_Y0 + 66),
         (PL_X0 + round(_sp * .84), PL_Y0 + 46)])
obj('partition_limit', 'partition limit', 'chrome',
    f'rounded=0;fillColor=none;strokeColor={WINE};strokeWidth=1.4;dashed=1;dashPattern=4 4;'
    f'verticalLabelPosition=top;verticalAlign=bottom;labelPosition=center;align=center;'
    f'fontFamily={HELVE};fontSize=10;fontColor={WINE};',
    LIMIT_X, PL_Y0, 1, PL_Y1 - PL_Y0)
label('ov_axis', 'containers per table, log scale, continued past the limit\neach curve on its own vertical scale',
      ov_x + 8, PL_Y1 + 6, ov_w - 16, 30, 10, MUTED, align='center', valign='top')
KY = PL_Y1 + OV_AXISBLK
for i, (kid, ktxt, kcol, kdash) in enumerate([
        ('ov_k1', 'skipping performance', GREEN, ''),
        ('ov_k2', 'table metadata overhead', WINE, 'dashed=1;dashPattern=7 4;')]):
    ky = KY + i * OV_KEY
    seg(kid, f'html=0;endArrow=none;strokeColor={kcol};strokeWidth=2.4;{kdash}fontFamily={HELVE};fontSize=10;fontColor={INK};',
        ov_x + 16, ky, ov_x + 46, ky)
    label(kid + '_t', ktxt, ov_x + 54, ky - 8, ov_w - 70, 16, 10, kcol)

obj('gate', '', 'decision',
    f'rhombus;fillColor={ROSE};strokeColor={WINE};strokeWidth=1.8;whiteSpace=wrap;overflow=hidden;'
    f'fontFamily={HELVE};fontSize=12;fontColor={INK};',
    gate_x, GATE_Y, GATE_W, GATE_H)
_qh = lines(GATE_Q, 13, GATE_TXT_W, bold=True) * lh(13)
label('gate_tag', 'DECISION', (GATE_W - GATE_TXT_W) // 2, GATE_H // 2 - _qh // 2 - 20, GATE_TXT_W, 14,
      10, WINE, bold=True, track=2, align='center', parent='gate')
label('gate_q', GATE_Q, (GATE_W - GATE_TXT_W) // 2, GATE_H // 2 - _qh // 2, GATE_TXT_W, _qh,
      13, INK, bold=True, align='center', parent='gate')

obj('tree_frozen', '', 'data_accepted', store_style(True), tf_x, TF_Y, tf_w, TF_H)
out().extend(TF_KIDS)
obj('heuristics', '', 'data_carried', ATT_STYLE, tf_x, HE_Y, he_w, HE_H)
out().extend(HE_KIDS)

# ---- edges
edge('e_usage_search', '', 'data_flow',
     FLOW + 'exitX=1;exitY=0.35;exitDx=0;exitDy=0;exitPerimeter=1;entryX=0;entryY=0.3;entryDx=0;entryDy=0;entryPerimeter=1;',
     'usage_summary', 'search')

GUT_AB = ROW_A_Y + ROW_A_H + GUTTER // 2
LANE_MID = (R1_X + R1_W + R2_X) // 2
LANE_BEAM = M + CONTENT_W + 10
edge('e_search_mckp', 'every candidate', 'data_flow',
     FLOW + 'exitX=0;exitY=0.88;exitDx=0;exitDy=0;exitPerimeter=1;entryX=0.75;entryY=0;entryDx=0;entryDy=0;entryPerimeter=1;',
     'search', 'mckp',
     points=[(LANE_MID, SF_Y + round(SF_H * 0.88)), (LANE_MID, GUT_AB), (kn_x + round(kn_w * 0.75), GUT_AB)])
edge('e_search_holdout', 'beam', 'data_flow',
     FLOW + 'exitX=1;exitY=0.88;exitDx=0;exitDy=0;exitPerimeter=1;entryX=0.5;entryY=0;entryDx=0;entryDy=0;entryPerimeter=1;',
     'search', 'holdout',
     points=[(LANE_BEAM, SF_Y + round(SF_H * 0.88)), (LANE_BEAM, GUT_AB), (ho_x + ho_w // 2, GUT_AB)])

edge('e_overlay_mckp', 'panel on', 'containment',
     CONT + 'exitX=0;exitY=0.5;exitDx=0;exitDy=0;exitPerimeter=1;entryX=1;entryY=0.5;entryDx=0;entryDy=0;entryPerimeter=1;',
     'overlay', 'mckp')

edge('e_mckp_holdout', 'a ceiling, not an assignment', 'data_flow_ceiling',
     CEIL + 'exitX=0.85;exitY=1;exitDx=0;exitDy=0;exitPerimeter=1;entryX=0.25;entryY=1;entryDx=0;entryDy=0;entryPerimeter=1;',
     'mckp', 'holdout',
     points=[(kn_x + round(kn_w * 0.85), CEIL_LANE), (ho_x + round(ho_w * 0.25), CEIL_LANE)])

GUT_BC = ROW_B_Y + ROW_B_H + GUTTER // 2
edge('e_holdout_gate', 'weighted-average skipping ratio', 'data_flow',
     FLOW + 'exitX=0.5;exitY=1;exitDx=0;exitDy=0;exitPerimeter=1;entryX=0.5;entryY=0;entryDx=0;entryDy=0;entryPerimeter=1;',
     'holdout', 'gate',
     points=[(ho_x + ho_w // 2, GUT_BC), (gate_x + GATE_W // 2, GUT_BC)])

edge('e_gate_tree', 'Yes', 'data_flow',
     FLOW.replace('fontSize=10', 'fontSize=13') + 'fontStyle=1;exitX=0.75;exitY=0.25;exitDx=0;exitDy=0;exitPerimeter=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;entryPerimeter=1;',
     'gate', 'tree_frozen',
     points=[(gate_x + round(GATE_W * 0.88), TF_Y + TF_H // 2)])

edge('e_gate_heuristics', 'No', 'data_flow',
     FAIL.replace('fontSize=10', 'fontSize=13') + 'exitX=0.75;exitY=0.75;exitDx=0;exitDy=0;exitPerimeter=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;entryPerimeter=1;',
     'gate', 'heuristics',
     points=[(gate_x + round(GATE_W * 0.88), HE_Y + HE_H // 2)])

edge('e_heuristics_search', 'read before the next pass', 'data_flow',
     FLOW + 'exitX=0.9;exitY=0;exitDx=0;exitDy=0;exitPerimeter=1;entryX=1;entryY=0.62;entryDx=0;entryDy=0;entryPerimeter=1;',
     'heuristics', 'search',
     points=[(tf_x + round(he_w * 0.9), HE_Y - OUT_GAP // 2), (LANE_R, HE_Y - OUT_GAP // 2),
             (LANE_R, SF_Y + round(SF_H * 0.62))], lpos=-0.55)

write(sys.argv[1], PAGE_W, PAGE_H)
print(f'rowA={ROW_A_H} rowB={ROW_B_H} rowC={ROW_C_H} | us={US_H} sf={SF_H} he={HE_H} '
      f'kn={KN_H} ho={HO_H} ov={OV_H} tf={TF_H} gate={GATE_H}')
