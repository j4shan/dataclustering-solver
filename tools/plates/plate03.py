#!/usr/bin/env python3
"""Emit resources/img_src/section_databricks_query.drawio — Plate 03,
*Query Time Integration*.

Every recipe comes from kit.py. Only this plate's own copy, geometry and edges
live here. This plate carries no drawn title: the pane it sits in prints one.
"""
from __future__ import annotations
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from kit import *                                                       # noqa: F403
from kit import (PAPER, INK, MUTED, RULE, BAND, WHITE, WINE, ROSE, GREEN, SAGE,
                 HELVE, MONO, TXT, RAIL_PAD, CHIP_H, CX, CTOP, CBOT,
                 TITLE_H, cell, obj, edge, seg, label, out, push, pop,
                 store_style, OP_STYLE, ATT_STYLE, title_row, body, frame_style,
                 schema, legend, rail, write, FLOW, TRIG, text_w, lines, lh)

PAGE_W, M = 1560, 64
CONTENT_W = PAGE_W - 2 * M
IN_X, IN_W = M + RAIL_PAD, CONTENT_W - 2 * RAIL_PAD      # 88, 1384

# breathing room between layers, as on Plate 02
PAD, GUT, STACK = 26, 60, 44

# ============================================================ instance data
# Placeholder column names. No figure prints a term from the dataset example.
INDEX_COLUMNS = ['predicate_1', 'predicate_2', 'partition_id']
PSINK_COLUMNS = ['predicate_1', 'predicate_2', 'attribute_1', 'attribute_2',
                 'partition_id', 'record_id']
DRIVER_SHARE, WORKERS_SHARE = 0.60, 0.40
WORKERS = ['w1', 'w2']
DRIVER_NODE = 'rgd-class driver, 256 GB or more'
BROADCAST_THRESHOLD = 'autoBroadcastJoinThreshold 256 MB'
assert set(INDEX_COLUMNS) <= set(PSINK_COLUMNS)
assert 'partition_id' in INDEX_COLUMNS and 'partition_id' in PSINK_COLUMNS
assert 'record_id' not in INDEX_COLUMNS
assert len(WORKERS) == 2
assert DRIVER_SHARE + WORKERS_SHARE == 1.0

# ============================================================ copy
INDEX_B = ('Carry the query predicate features and partition_id only, so a prescan never '
           'opens the event table')
PSINK_B = 'Hold the full event attributes under their finalized container assignment'
DRIVER_B = ('Prescan the narrow index and broadcast the matching partition_id set to every '
            'worker')
WORKER_B = 'Fetch only the activated containers and write its share of the result'
QOUT_B = 'Hold the query result on durable storage for anything downstream to read'
COLL_B = 'Read the durable result and aggregate one boolean flag per query and per row'
USAGE_B = 'Keep one boolean per query and per row, aggregated into hour bins'


# ============================================================ card builders
def op_card(cid, w, name, text, ink=WINE, type_label=None, tag=None, rounded=True):
    push()
    cur = title_row(cid, w, ink, name, type_label, tag=tag, rounded=rounded)
    cur += CTOP
    cur += body(cid, w, text, cur)
    return cur + CBOT, pop()


def store_card(cid, w, type_label, name, text, cols=None, tag=None, accepted=False):
    push()
    cur = title_row(cid, w, GREEN, name, type_label, mono_name=True, tag=tag)
    cur += CTOP
    if cols:
        cur += schema(cid, w, cols, cur) + 10
    cur += body(cid, w, text, cur)
    return cur + CBOT, pop()


def place(cid, cat, style, x, y, w, h, kids, parent='1'):
    obj(cid, '', cat, style, x, y, w, h, parent)
    out().extend(kids)


def bus(cid, x, y):
    """The shared node a one-to-many hand-off passes through before it fans out."""
    obj(cid, '', 'chrome',
        f'ellipse;fillColor={INK};strokeColor={INK};strokeWidth=1.4;'
        f'fontFamily={HELVE};fontSize=10;fontColor={INK};', x - 7, y - 7, 14, 14)


# ============================================================ measure
IDX_W, CL_W, PSK_W = 280, 700, 300
IDX_X, CL_X, PSK_X = IN_X, IN_X + 340, IN_X + 1084
assert PSK_X + PSK_W == IN_X + IN_W

H_IDX, K_IDX = store_card('index_table', IDX_W, 'Index Table', 'index_table', INDEX_B, INDEX_COLUMNS)
H_PSK, K_PSK = store_card('partitioned_sink', PSK_W, 'Event Table', 'partitioned_sink',
                          PSINK_B, PSINK_COLUMNS)

# ---- the cluster frame: driver compartment, dashed rule, workers stacked
FHEAD, FPAD, CAP_H = 34, 24, 22
CL_IN_W = CL_W - 2 * FPAD
SPLIT_X = FPAD + round(CL_IN_W * DRIVER_SHARE)
DRV_W, DRV_X = 300, FPAD + 20
WK_W, WK_X = 200, SPLIT_X + 35
assert WK_X + WK_W <= CL_W - FPAD
H_DRV, K_DRV = op_card('driver', DRV_W, 'Driver', DRIVER_B)
H_W1, K_W1 = op_card('w1', WK_W, 'Worker w1', WORKER_B)
H_W2, K_W2 = op_card('w2', WK_W, 'Worker w2', WORKER_B)

PILLS = [('driver_node', DRIVER_NODE), ('broadcast_threshold', BROADCAST_THRESHOLD)]
PILL_H, PILL_GAP = 26, 10
PILL_W = max(round(text_w(t, 10)) + 34 for _, t in PILLS)
assert PILL_W <= DRV_W

DRV_COL_H = H_DRV + 20 + 16 + len(PILLS) * (PILL_H + PILL_GAP) - PILL_GAP
WK_COL_H = H_W1 + STACK + H_W2
CL_BODY_H = max(DRV_COL_H, WK_COL_H)
CL_H = FHEAD + FPAD + CAP_H + CL_BODY_H + FPAD
ROW1_H = max(CL_H, H_IDX, H_PSK)

# ---- rail 2, the feedback lane, read right to left
US_W, COLL_W, QO_W = 440, 440, 336
US_X, COLL_X = IN_X, IN_X + 524
QO_X = IN_X + IN_W - QO_W
H_US, K_US = store_card('usage_summary', US_W, 'DL Table', 'usage_summary', USAGE_B)
H_COLL, K_COLL = op_card('usage_collector', COLL_W, 'Usage Statistics Collector', COLL_B)
H_QO, K_QO = store_card('query_output', QO_W, 'Query Result', 'query_output', QOUT_B, tag='DURABLE')
ROW2_H = max(H_US, H_COLL, H_QO)

# ============================================================ grid
LEGEND_Y, LEGEND_H = 26, 48
ROW1_Y = LEGEND_Y + LEGEND_H + 34
RAIL1_H = CHIP_H + PAD + ROW1_H + PAD
CARD1_Y = ROW1_Y + CHIP_H + PAD
CL_Y = CARD1_Y + (ROW1_H - CL_H) // 2

ROW2_Y = ROW1_Y + RAIL1_H + GUT
RAIL2_H = CHIP_H + PAD + ROW2_H + PAD
CARD2_Y = ROW2_Y + CHIP_H + PAD
PAGE_H = ROW2_Y + RAIL2_H + 40

GUT_Y = ROW1_Y + RAIL1_H + GUT // 2
WK_ABS_X = CL_X + WK_X
W1_Y = CL_Y + FHEAD + FPAD + CAP_H + (CL_BODY_H - WK_COL_H) // 2
W2_Y = W1_Y + H_W1 + STACK
BCAST_X = CL_X + SPLIT_X - 16                      # just inside the driver compartment
BCAST_Y = (W1_Y + H_W1 // 2 + W2_Y + H_W2 // 2) // 2
W1_LANE, W2_LANE = WK_ABS_X + WK_W + 24, WK_ABS_X + WK_W + 46
JOIN_X, JOIN_Y = QO_X + QO_W // 2, GUT_Y

# ============================================================ emit
legend([
    ('legend_key_persisted', 'persisted table, schema only',
     f'rounded=0;fillColor={WHITE};strokeColor={GREEN};strokeWidth=1.6;', GREEN),
    ('legend_key_durable', 'durable output',
     f'rounded=0;fillColor={SAGE};strokeColor={GREEN};strokeWidth=2.4;', GREEN),
    ('legend_key_operation', 'operation',
     f'rounded=1;absoluteArcSize=1;arcSize=10;fillColor={ROSE};strokeColor={WINE};strokeWidth=1.8;', WINE),
    ('legend_key_cluster', 'cluster frame',
     f'rounded=0;fillColor={WHITE};strokeColor={MUTED};strokeWidth=1.4;', RULE),
    ('legend_key_split', 'dashed = driver / workers split',
     f'shape=line;direction=north;strokeColor={MUTED};strokeWidth=1.4;dashed=1;dashPattern=6 4;', None),
], M, LEGEND_Y, CONTENT_W, LEGEND_H)

rail('rail_1', '1', 'ACTIVATE & FETCH', M, ROW1_Y, CONTENT_W, RAIL1_H)
rail('rail_2', '2', 'FEED THE NEXT LAYOUT', M, ROW2_Y, CONTENT_W, RAIL2_H, name_w=300)

place('index_table', 'data_persisted', store_style(), IDX_X,
      CARD1_Y + (ROW1_H - H_IDX) // 2, IDX_W, H_IDX, K_IDX)
place('partitioned_sink', 'data_persisted', store_style(), PSK_X,
      CARD1_Y + (ROW1_H - H_PSK) // 2, PSK_W, H_PSK, K_PSK)

obj('cluster', 'DATABRICKS CLUSTER', 'group', frame_style(FHEAD), CL_X, CL_Y, CL_W, CL_H)
obj('cluster_split', '', 'chrome',
    f'rounded=0;fillColor=none;strokeColor={MUTED};strokeWidth=1.4;dashed=1;dashPattern=6 4;'
    f'fontFamily={HELVE};fontSize=10;fontColor={MUTED};',
    SPLIT_X, FHEAD, 1, CL_H - FHEAD, 'cluster')
label('cap_driver', f'DRIVER {round(DRIVER_SHARE * 100)}%', FPAD, FHEAD + FPAD,
      SPLIT_X - FPAD - 12, CAP_H, 10, MUTED, bold=True, track=2, parent='cluster')
label('cap_workers', f'WORKERS {round(WORKERS_SHARE * 100)}%', WK_X, FHEAD + FPAD,
      CL_W - WK_X - FPAD, CAP_H, 10, MUTED, bold=True, track=2, parent='cluster')

_drv_y = FHEAD + FPAD + CAP_H + (CL_BODY_H - DRV_COL_H) // 2
place('driver', 'operation', OP_STYLE, DRV_X, _drv_y, DRV_W, H_DRV, K_DRV, parent='cluster')
label('driver_req', 'REQUIRES', DRV_X, _drv_y + H_DRV + 16, DRV_W, 16, 10, MUTED,
      bold=True, track=2, parent='cluster')
_py = _drv_y + H_DRV + 20 + 16
for _pid, _txt in PILLS:
    obj(_pid, _txt, 'chrome',
        f'rounded=1;arcSize=50;fillColor={BAND};strokeColor={MUTED};align=center;'
        f'verticalAlign=middle;whiteSpace=wrap;overflow=hidden;fontFamily={HELVE};fontSize=10;fontColor={INK};',
        DRV_X, _py, PILL_W, PILL_H, 'cluster')
    _py += PILL_H + PILL_GAP

place('w1', 'operation', OP_STYLE, WK_X, W1_Y - CL_Y, WK_W, H_W1, K_W1, parent='cluster')
place('w2', 'operation', OP_STYLE, WK_X, W2_Y - CL_Y, WK_W, H_W2, K_W2, parent='cluster')

place('usage_summary', 'data_persisted', store_style(), US_X,
      CARD2_Y + (ROW2_H - H_US) // 2, US_W, H_US, K_US)
place('usage_collector', 'operation', OP_STYLE, COLL_X,
      CARD2_Y + (ROW2_H - H_COLL) // 2, COLL_W, H_COLL, K_COLL)
place('query_output', 'data_durable', store_style(True), QO_X,
      CARD2_Y + (ROW2_H - H_QO) // 2, QO_W, H_QO, K_QO)

bus('broadcast_bus', BCAST_X, BCAST_Y)             # one broadcast, then both workers
bus('write_bus', JOIN_X, JOIN_Y)                   # both shares, then one durable result

# ============================================================ edges
SIDE = 'exitX=1;exitY=0.5;exitDx=0;exitDy=0;exitPerimeter=1;entryX=0;entryY=0.5;entryDx=0;entryDy=0;entryPerimeter=1;'
BACK = 'exitX=0;exitY=0.5;exitDx=0;exitDy=0;exitPerimeter=1;entryX=1;entryY=0.5;entryDx=0;entryDy=0;entryPerimeter=1;'

edge('e_index_driver', 'scan', 'data_flow', FLOW + SIDE, 'index_table', 'driver')
edge('e_driver_bus', 'activate', 'data_flow', FLOW + SIDE, 'driver', 'broadcast_bus', lpos=-0.1)
for _eid, _tgt, _y, _h in [('e_driver_w1', 'w1', W1_Y, H_W1), ('e_driver_w2', 'w2', W2_Y, H_W2)]:
    edge(_eid, '', 'data_flow',
         FLOW + 'exitX=0.5;exitY=0.5;exitDx=0;exitDy=0;exitPerimeter=1;entryX=0;entryY=0.5;entryDx=0;entryDy=0;entryPerimeter=1;',
         'broadcast_bus', _tgt, points=[(BCAST_X, _y + _h // 2)])

edge('e_w1_psink', 'fetch', 'data_flow',
     FLOW + 'exitX=0;exitY=0.34;exitDx=0;exitDy=0;exitPerimeter=1;entryX=1;entryY=0.3;entryDx=0;entryDy=0;entryPerimeter=1;',
     'partitioned_sink', 'w1')
edge('e_w2_psink', 'fetch', 'data_flow',
     FLOW + 'exitX=0;exitY=0.66;exitDx=0;exitDy=0;exitPerimeter=1;entryX=1;entryY=0.3;entryDx=0;entryDy=0;entryPerimeter=1;',
     'partitioned_sink', 'w2')

for _eid, _src, _y, _h, _lane, _jump in [
        ('e_w1_qout', 'w1', W1_Y, H_W1, W1_LANE, 'jumpStyle=arc;jumpSize=8;'),
        ('e_w2_qout', 'w2', W2_Y, H_W2, W2_LANE, '')]:
    edge(_eid, '', 'data_flow',
         FLOW + _jump + 'exitX=1;exitY=0.78;exitDx=0;exitDy=0;exitPerimeter=1;'
         'entryX=0.5;entryY=0.5;entryDx=0;entryDy=0;entryPerimeter=1;',
         _src, 'write_bus',
         points=[(_lane, _y + round(_h * 0.78)), (_lane, JOIN_Y)])
edge('e_bus_qout', 'write', 'data_flow',
     FLOW + 'exitX=0.5;exitY=0.5;exitDx=0;exitDy=0;exitPerimeter=1;entryX=0.5;entryY=0;entryDx=0;entryDy=0;entryPerimeter=1;',
     'write_bus', 'query_output', lpos=0.2)

edge('e_qout_collector', '', 'data_flow', FLOW + BACK, 'query_output', 'usage_collector')
edge('e_collector_usage', 'persist', 'data_flow', FLOW + BACK, 'usage_collector', 'usage_summary')

write(sys.argv[1], PAGE_W, PAGE_H)
print(f'rail1={RAIL1_H} rail2={RAIL2_H} | cluster={CL_H} idx={H_IDX} psk={H_PSK} '
      f'drv={H_DRV} wk={H_W1} qo={H_QO}')
