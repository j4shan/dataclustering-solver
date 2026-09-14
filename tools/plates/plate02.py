#!/usr/bin/env python3
"""Emit resources/img_src/section_databricks_ingestion.drawio — Plate 02,
*Ingestion Time Integration*.

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

PAGE_W, M = 1436, 64
CONTENT_W = PAGE_W - 2 * M
IN_X, IN_W = M + RAIL_PAD, CONTENT_W - 2 * RAIL_PAD      # 88, 1260

# breathing room between layers: rail padding, rail to rail, row to row, card to card
PAD, GUT, SUBGAP, STACK = 26, 60, 68, 44

# ============================================================ instance data
# Placeholder column names. No figure prints a term from the dataset example.
INDEX_COLUMNS = ['predicate_1', 'predicate_2', 'partition_id']
PSINK_COLUMNS = ['predicate_1', 'predicate_2', 'attribute_1', 'attribute_2',
                 'partition_id', 'record_id']
GROUP_KEYS = ['predicate_1', 'predicate_2']
assert set(INDEX_COLUMNS) <= set(PSINK_COLUMNS)
assert 'partition_id' in INDEX_COLUMNS and 'partition_id' in PSINK_COLUMNS
assert 'record_id' not in INDEX_COLUMNS
assert GROUP_KEYS == INDEX_COLUMNS[:2]

# ============================================================ copy
STREAM_B = 'Carry events as they arrive, under no layout of their own'
LOADER_B = 'Persist the arriving stream and hand each micro-batch to the stream writer'
SWRITER_B = 'Append every micro-batch to the landing table as it arrives'
SSINK_B = ('Hold the landing copy unsplit, so high-frequency arrivals never fragment '
           'the container layout')
CRON_B = 'Fire the consistency checker and the consolidation optimizer on one schedule'
CHECKER_B = 'Read the write-ahead log, clear any partial ingest state, then launch the writer'
WAL_B = 'Record every multi-table write so a repeated fan-out stays idempotent'
TREE_B = 'Carry the split decision that held up on holdout into the splitter'
SPLIT_B = ('Divide each batch into logical groupings with a conditional group-by built '
           'from the frozen tree')
ALLOC_B = 'Read container fill from the tracker and finalize a partition_id for every record'
FANOUT_B = 'Write the assigned batch to the index, the tracker and the event table, then commit'
TRACKER_B = 'Keep one row for every grouping, recording how full its open container is'
INDEX_B = ('Carry the query predicate features and partition_id only, so a prescan never '
           'opens the event table')
PSINK_B = 'Hold the full event attributes under their finalized container assignment'
OPT_B = 'Rewrite each partition back to one file on disjoint commits, without Z-order'


# ============================================================ card builders
def op_card(cid, w, name, text, ink=WINE, type_label=None, tag=None, rounded=True):
    push()
    cur = title_row(cid, w, ink, name, type_label, tag=tag, rounded=rounded)
    cur += CTOP
    cur += body(cid, w, text, cur)
    return cur + CBOT, pop()


def store_card(cid, w, type_label, name, text, cols=None):
    push()
    cur = title_row(cid, w, GREEN, name, type_label, mono_name=True)
    cur += CTOP
    if cols:
        cur += schema(cid, w, cols, cur) + 10
    cur += body(cid, w, text, cur)
    return cur + CBOT, pop()


def place(cid, cat, style, x, y, w, h, kids, parent='1'):
    obj(cid, '', cat, style, x, y, w, h, parent)
    out().extend(kids)


# ============================================================ measure
# ---- rail 1, the landing path
L1 = [('stream', 230), ('auto_loader', 320), ('stream_writer', 240), ('streaming_sink', 330)]
L1X, _x = {}, IN_X
for _cid, _w in L1:
    L1X[_cid] = _x
    _x += _w + 46
assert _x - 46 <= IN_X + IN_W

H_STREAM, K_STREAM = op_card('stream', 230, 'an event stream', STREAM_B,
                             type_label='Data Source')
H_LOADER, K_LOADER = op_card('auto_loader', 320, 'Spark Structured Streaming / Auto Loader', LOADER_B)
H_SWRITER, K_SWRITER = op_card('stream_writer', 240, 'Stream Writer', SWRITER_B)
H_SSINK, K_SSINK = store_card('streaming_sink', 330, 'Landing Table', 'streaming_sink', SSINK_B)
ROW1_H = max(H_STREAM, H_LOADER, H_SWRITER, H_SSINK)

# ---- rail 2 sub-row A, the schedule
CRON_W, CHECKER_W, WAL_W = 240, 400, 300
CRON_X, CHECKER_X, WAL_X = IN_X, IN_X + 300, IN_X + 760
LAND_LANE = IN_X + 730                     # the free column between checker and checkpoint
H_CRON, K_CRON = op_card('cron', CRON_W, 'CRON Scheduler', CRON_B)
H_CHECKER, K_CHECKER = op_card('consistency_checker', CHECKER_W, 'Consistency Checker', CHECKER_B)
H_WAL, K_WAL = store_card('checkpoint', WAL_W, 'Write-Ahead Log', 'checkpoint', WAL_B)
ROWA_H = max(H_CRON, H_CHECKER, H_WAL)
assert WAL_X + WAL_W <= IN_X + IN_W

# ---- rail 2 sub-row B: inputs, the writer stacked vertically, the destinations
TREE_W, TREE_X = 280, IN_X
FRAME_X, FRAME_W = IN_X + 340, 400
FHEAD, FPAD = 34, 24
STAGE_W = FRAME_W - 2 * FPAD
H_SPLIT, K_SPLIT = op_card('data_splitter', STAGE_W, 'Data Splitter', SPLIT_B)
H_ALLOC, K_ALLOC = op_card('container_allocator', STAGE_W, 'Container Allocator', ALLOC_B)
H_FANOUT, K_FANOUT = op_card('fanout_distributor', STAGE_W, 'Fanout Distributor', FANOUT_B)
STAGE_Y = [FHEAD + FPAD]
STAGE_Y.append(STAGE_Y[0] + H_SPLIT + STACK)
STAGE_Y.append(STAGE_Y[1] + H_ALLOC + STACK)
FRAME_H = STAGE_Y[2] + H_FANOUT + FPAD
H_TREE, K_TREE = op_card('tree_frozen', TREE_W, 'Pre-Built', TREE_B, ink=GREEN,
                         type_label='Split Tree', tag='FROZEN', rounded=False)

DEST_W, DEST_X = 400, IN_X + 860
H_IDX, K_IDX = store_card('index_table', DEST_W, 'Index Table', 'index_table', INDEX_B, INDEX_COLUMNS)
H_TRK, K_TRK = store_card('container_tracker', DEST_W, 'Assignment Tracker', 'container_tracker', TRACKER_B)
H_PSK, K_PSK = store_card('partitioned_sink', DEST_W, 'Event Table', 'partitioned_sink', PSINK_B, PSINK_COLUMNS)
assert DEST_X + DEST_W == IN_X + IN_W
DEST_STACK = H_IDX + STACK + H_TRK + STACK + H_PSK
ROWB_H = max(FRAME_H, DEST_STACK)

# ---- rail 3, consolidation
H_OPT, K_OPT = op_card('optimizer', DEST_W, 'Continuous Consolidation Optimizer', OPT_B)

# ============================================================ grid
LEGEND_Y, LEGEND_H = 26, 48
ROW1_Y = LEGEND_Y + LEGEND_H + 34
RAIL1_H = CHIP_H + PAD + ROW1_H + PAD
CARD1_Y = ROW1_Y + CHIP_H + PAD

RAIL2_Y = ROW1_Y + RAIL1_H + GUT
ROWA_Y = RAIL2_Y + CHIP_H + PAD
ROWB_Y = ROWA_Y + ROWA_H + SUBGAP
RAIL2_H = ROWB_Y + ROWB_H + PAD - RAIL2_Y
TREE_Y = ROWB_Y + STAGE_Y[0] + (H_SPLIT - H_TREE) // 2

IDX_Y = ROWB_Y
TRK_Y = IDX_Y + H_IDX + STACK
PSK_Y = TRK_Y + H_TRK + STACK

RAIL3_X, RAIL3_W = DEST_X - RAIL_PAD, DEST_W + 2 * RAIL_PAD
RAIL3_Y = RAIL2_Y + RAIL2_H + GUT
RAIL3_H = CHIP_H + PAD + H_OPT + PAD
OPT_Y = RAIL3_Y + CHIP_H + PAD
PAGE_H = RAIL3_Y + RAIL3_H + 40

LANE_L = M - 20                                    # CRON trigger, outside the rails
LANE_CRON = ROWA_Y + ROWA_H + 24                   # its lane under the schedule row
GUT1_Y = ROW1_Y + RAIL1_H + GUT // 2
BOT_Y = RAIL2_Y + RAIL2_H + GUT // 2
FANOUT_Y = ROWB_Y + STAGE_Y[2] + H_FANOUT // 2
READ_LANE = FRAME_X + FRAME_W + 30                 # tracker -> allocator
COMMIT_LANE = FRAME_X + FRAME_W + 60               # fan-out -> checkpoint
BUS_X = FRAME_X + FRAME_W + 90                     # the shared node and its trunk

# ============================================================ emit
legend([
    ('legend_key_persisted', 'persisted table',
     f'rounded=0;fillColor={WHITE};strokeColor={GREEN};strokeWidth=1.6;', GREEN),
    ('legend_key_frozen', 'frozen input',
     f'rounded=0;fillColor={SAGE};strokeColor={GREEN};strokeWidth=2.4;', GREEN),
    ('legend_key_operation', 'operation',
     f'rounded=1;absoluteArcSize=1;arcSize=10;fillColor={ROSE};strokeColor={WINE};strokeWidth=1.8;', WINE),
    ('legend_key_transient', 'transient source',
     f'rounded=1;absoluteArcSize=1;arcSize=10;fillColor={ROSE};strokeColor={WINE};strokeWidth=1.8;'
     f'dashed=1;dashPattern=7 4;', WINE),
    ('legend_key_assembly', 'assembly line frame',
     f'rounded=0;fillColor={WHITE};strokeColor={MUTED};strokeWidth=1.4;', RULE),
    ('legend_key_dash', 'dotted = CRON trigger',
     f'shape=line;strokeColor={WINE};strokeWidth=1.8;dashed=1;dashPattern=2 3;', None),
], M, LEGEND_Y, CONTENT_W, LEGEND_H)

rail('rail_1', '1', 'LAND', M, ROW1_Y, CONTENT_W, RAIL1_H)
rail('rail_2', '2', 'WRITE', M, RAIL2_Y, CONTENT_W, RAIL2_H)
rail('rail_3', '3', 'COMPACT', RAIL3_X, RAIL3_Y, RAIL3_W, RAIL3_H)

for _cid, _w, _h, _k, _st, _cat in [
        ('stream', 230, H_STREAM, K_STREAM, ATT_STYLE, 'data_transient'),
        ('auto_loader', 320, H_LOADER, K_LOADER, OP_STYLE, 'operation'),
        ('stream_writer', 240, H_SWRITER, K_SWRITER, OP_STYLE, 'operation'),
        ('streaming_sink', 330, H_SSINK, K_SSINK, store_style(), 'data_persisted')]:
    place(_cid, _cat, _st, L1X[_cid], CARD1_Y + (ROW1_H - _h) // 2, _w, _h, _k)

place('cron', 'operation', OP_STYLE, CRON_X, ROWA_Y + (ROWA_H - H_CRON) // 2,
      CRON_W, H_CRON, K_CRON)
place('consistency_checker', 'operation', OP_STYLE, CHECKER_X,
      ROWA_Y + (ROWA_H - H_CHECKER) // 2, CHECKER_W, H_CHECKER, K_CHECKER)
place('checkpoint', 'data_persisted', store_style(), WAL_X,
      ROWA_Y + (ROWA_H - H_WAL) // 2, WAL_W, H_WAL, K_WAL)

place('tree_frozen', 'data_accepted', store_style(True), TREE_X, TREE_Y, TREE_W, H_TREE, K_TREE)
obj('specialized_writer', 'SPECIALIZED WRITER', 'group', frame_style(FHEAD, align='left'),
    FRAME_X, ROWB_Y, FRAME_W, FRAME_H)
for _i, (_cid, _h, _k) in enumerate([('data_splitter', H_SPLIT, K_SPLIT),
                                     ('container_allocator', H_ALLOC, K_ALLOC),
                                     ('fanout_distributor', H_FANOUT, K_FANOUT)]):
    obj(_cid, '', 'operation', OP_STYLE, FPAD, STAGE_Y[_i], STAGE_W, _h, 'specialized_writer')
    out().extend(_k)

place('index_table', 'data_persisted', store_style(), DEST_X, IDX_Y, DEST_W, H_IDX, K_IDX)
place('container_tracker', 'data_persisted', store_style(), DEST_X, TRK_Y, DEST_W, H_TRK, K_TRK)
place('partitioned_sink', 'data_persisted', store_style(), DEST_X, PSK_Y, DEST_W, H_PSK, K_PSK)
place('optimizer', 'operation', OP_STYLE, DEST_X, OPT_Y, DEST_W, H_OPT, K_OPT)

# the shared node every write passes through before it fans out
obj('fanout_bus', '', 'chrome',
    f'ellipse;fillColor={INK};strokeColor={INK};strokeWidth=1.4;'
    f'fontFamily={HELVE};fontSize=10;fontColor={INK};',
    BUS_X - 7, FANOUT_Y - 7, 14, 14)

# ============================================================ edges
SIDE = 'exitX=1;exitY=0.5;exitDx=0;exitDy=0;exitPerimeter=1;entryX=0;entryY=0.5;entryDx=0;entryDy=0;entryPerimeter=1;'
DOWN = 'exitX=0.5;exitY=1;exitDx=0;exitDy=0;exitPerimeter=1;entryX=0.5;entryY=0;entryDx=0;entryDy=0;entryPerimeter=1;'
edge('e_stream_loader', '', 'data_flow', FLOW + SIDE, 'stream', 'auto_loader')
edge('e_loader_writer', '', 'data_flow', FLOW + SIDE, 'auto_loader', 'stream_writer')
edge('e_writer_sink', 'write', 'data_flow', FLOW + SIDE, 'stream_writer', 'streaming_sink')

edge('e_cron_checker', 'schedule', 'trigger', TRIG + SIDE, 'cron', 'consistency_checker')
edge('e_checker_wal', 'read', 'data_flow',
     FLOW + 'exitX=1;exitY=0.32;exitDx=0;exitDy=0;exitPerimeter=1;entryX=0;entryY=0.32;entryDx=0;entryDy=0;entryPerimeter=1;',
     'consistency_checker', 'checkpoint')
edge('e_wal_checker', 'offsets', 'data_flow',
     FLOW + 'exitX=0;exitY=0.72;exitDx=0;exitDy=0;exitPerimeter=1;entryX=1;entryY=0.72;entryDx=0;entryDy=0;entryPerimeter=1;',
     'checkpoint', 'consistency_checker')

edge('e_checker_writer', 'launch', 'trigger',
     TRIG + 'exitX=0.45;exitY=1;exitDx=0;exitDy=0;exitPerimeter=1;entryX=0.45;entryY=0;entryDx=0;entryDy=0;entryPerimeter=1;',
     'consistency_checker', 'data_splitter')
edge('e_sink_splitter', 'landed rows', 'data_flow',
     FLOW + 'exitX=0.5;exitY=1;exitDx=0;exitDy=0;exitPerimeter=1;'
     'entryX=0.86;entryY=0;entryDx=0;entryDy=0;entryPerimeter=1;',
     'streaming_sink', 'data_splitter',
     points=[(L1X['streaming_sink'] + 165, GUT1_Y), (LAND_LANE, GUT1_Y),
             (LAND_LANE, ROWB_Y - 34),
             (FRAME_X + FPAD + round(STAGE_W * 0.86), ROWB_Y - 34)], lpos=-0.78)
edge('e_tree_splitter', 'grouping rule', 'data_flow', FLOW + SIDE, 'tree_frozen', 'data_splitter')

edge('e_splitter_alloc', 'groupings', 'data_flow', FLOW + DOWN, 'data_splitter', 'container_allocator')
edge('e_alloc_fanout', 'partition_id', 'data_flow', FLOW + DOWN, 'container_allocator', 'fanout_distributor')

edge('e_tracker_alloc', 'read fill', 'data_flow',
     FLOW + 'jumpStyle=arc;jumpSize=8;exitX=0;exitY=0.72;exitDx=0;exitDy=0;exitPerimeter=1;'
     'entryX=1;entryY=0.72;entryDx=0;entryDy=0;entryPerimeter=1;',
     'container_tracker', 'container_allocator',
     points=[(READ_LANE, TRK_Y + round(H_TRK * 0.72)),
             (READ_LANE, ROWB_Y + STAGE_Y[1] + round(H_ALLOC * 0.72))], lpos=-0.4)

# one edge out of the writer into the shared node, then three out of it
edge('e_fanout_bus', 'assigned batch', 'data_flow',
     FLOW + 'exitX=1;exitY=0.5;exitDx=0;exitDy=0;exitPerimeter=1;entryX=0;entryY=0.5;entryDx=0;entryDy=0;entryPerimeter=1;',
     'fanout_distributor', 'fanout_bus', lpos=-0.25)
for _eid, _tgt, _ty, _th in [('e_fanout_index', 'index_table', IDX_Y, H_IDX),
                             ('e_fanout_tracker', 'container_tracker', TRK_Y, H_TRK),
                             ('e_fanout_psink', 'partitioned_sink', PSK_Y, H_PSK)]:
    edge(_eid, '', 'data_flow',
         FLOW + 'exitX=0.5;exitY=0.5;exitDx=0;exitDy=0;exitPerimeter=1;entryX=0;entryY=0.3;entryDx=0;entryDy=0;entryPerimeter=1;',
         'fanout_bus', _tgt, points=[(BUS_X, _ty + round(_th * 0.3))])

edge('e_fanout_wal', 'commit', 'data_flow',
     FLOW + 'exitX=1;exitY=0.22;exitDx=0;exitDy=0;exitPerimeter=1;entryX=0.6;entryY=1;entryDx=0;entryDy=0;entryPerimeter=1;',
     'fanout_distributor', 'checkpoint',
     points=[(COMMIT_LANE, ROWB_Y + STAGE_Y[2] + round(H_FANOUT * 0.22)),
             (COMMIT_LANE, ROWB_Y - 34), (WAL_X + round(WAL_W * 0.6), ROWB_Y - 34)], lpos=0.8)

edge('e_cron_optimizer', 'schedule', 'trigger',
     TRIG + 'exitX=0.14;exitY=1;exitDx=0;exitDy=0;exitPerimeter=1;entryX=0;entryY=0.5;entryDx=0;entryDy=0;entryPerimeter=1;',
     'cron', 'optimizer',
     points=[(CRON_X + 34, LANE_CRON), (LANE_L, LANE_CRON), (LANE_L, BOT_Y),
             (RAIL3_X - 34, BOT_Y), (RAIL3_X - 34, OPT_Y + H_OPT // 2)], lpos=0.66)

edge('e_psink_opt', 'read', 'data_flow',
     FLOW + 'exitX=0.25;exitY=1;exitDx=0;exitDy=0;exitPerimeter=1;entryX=0.25;entryY=0;entryDx=0;entryDy=0;entryPerimeter=1;',
     'partitioned_sink', 'optimizer')
edge('e_opt_psink', 'compact', 'data_flow',
     FLOW + 'exitX=0.75;exitY=0;exitDx=0;exitDy=0;exitPerimeter=1;entryX=0.75;entryY=1;entryDx=0;entryDy=0;entryPerimeter=1;',
     'optimizer', 'partitioned_sink')

write(sys.argv[1], PAGE_W, PAGE_H)
print(f'rail1={RAIL1_H} rail2={RAIL2_H} rail3={RAIL3_H} | rowA={ROWA_H} frame={FRAME_H} '
      f'dest_stack={DEST_STACK} stage_w={STAGE_W}')
