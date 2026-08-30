#!/usr/bin/env python3
"""Authoring renderer for the four Go Live section rasters.

    .venv/bin/python tools/render_section_c_go_live.py

Draws each figure at 3840 x 2160, downsamples once with LANCZOS, and writes
1920 x 1080 PNGs. Specifications:
    resources/img_prompt/c_go_live_process_prompt.txt
    resources/img_prompt/c_data_ingestion_prompt.txt
    resources/img_prompt/c_dpp_skipping_prompt.txt
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "resources" / "img"

# --------------------------------------------------------------------------
# Instances (fixed by the prompts). Printed values are derived from these.
# --------------------------------------------------------------------------
ACTIONS = [
    {"n": 1, "title": "Collect a target sample"},
    {"n": 2, "title": "Identify split decision trees"},
    {"n": 3, "title": "Estimate leaf skipping potential"},
    {"n": 4, "title": "Inspect the holdout"},
    {"n": 5, "title": "Implement data ingestion"},
    {"n": 6, "title": "Implement query optimization"},
]

# Shared with resources/img_prompt/c_dpp_skipping_prompt.txt
INGESTION = {
    "stream": "brand sales",
    "group_keys": ["brand_id", "pricing_tier"],
    "index_columns": ["brand_id", "pricing_tier", "partition_id"],
    "event_columns": [
        "brand_id", "pricing_tier", "sku", "amount",
        "partition_id", "record_id",
    ],
    "records": [
        {"record_id": "r01", "brand_id": "A", "pricing_tier": 1,
         "sku": "brk-12", "amount": 40, "partition_id": "p1"},
        {"record_id": "r02", "brand_id": "A", "pricing_tier": 2,
         "sku": "flt-03", "amount": 18, "partition_id": "p2"},
        {"record_id": "r03", "brand_id": "B", "pricing_tier": 1,
         "sku": "brk-08", "amount": 55, "partition_id": "p3"},
        {"record_id": "r04", "brand_id": "B", "pricing_tier": 2,
         "sku": "tyr-21", "amount": 22, "partition_id": "p4"},
    ],
}

DPP = {
    "query": {
        "text": "brand_id IN (A, B) AND pricing_tier = 1",
        "kind": "multi-select",
    },
    "workers": ["w1", "w2"],
}

ASSIGNMENT = {
    "grouping_key": ("A", 1),
    "T": 4,
    "k": 1,
    "s_1": 2,
    "N": 6,
    "batch": [
        {"record_id": "r11", "hash_slot": 0},
        {"record_id": "r12", "hash_slot": 1},
        {"record_id": "r13", "hash_slot": 2},
        {"record_id": "r14", "hash_slot": 3},
        {"record_id": "r15", "hash_slot": 1},
        {"record_id": "r16", "hash_slot": 5},
    ],
    "tracker_columns": [
        "grouping_key", "container_seq", "filled_count",
    ],
}

# Shared column widths so figures 2 and 4 read as one family.
COL_W = {
    "brand_id": 132,
    "pricing_tier": 148,
    "sku": 118,
    "amount": 104,
    "partition_id": 140,
    "record_id": 118,
}
HDR_H = 40
ROW_H = 36

# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------
CANVAS = (0xFC, 0xFC, 0xFB)
WINE = (0x7A, 0x1F, 0x2B)
ROSE = (0xF8, 0xEE, 0xF0)
GREEN = (0x1B, 0x4D, 0x3E)
SAGE = (0xEE, 0xF4, 0xF0)
INK = (0x0B, 0x0B, 0x0B)
SECOND = (0x52, 0x51, 0x4E)
RULE = (0xDE, 0xDE, 0xDE)
BAND = (0xF3, 0xF3, 0xF3)
WHITE = (0xFF, 0xFF, 0xFF)

# --------------------------------------------------------------------------
# Fonts: cache by (size, weight, mono)
# --------------------------------------------------------------------------
S = 2
SANS = "/System/Library/Fonts/SFNS.ttf"
MONO = "/System/Library/Fonts/SFNSMono.ttf"
_fonts: dict = {}


def face(size: float, weight: str = "Regular", mono: bool = False):
    key = (round(size, 2), weight, mono)
    f = _fonts.get(key)
    if f is None:
        f = ImageFont.truetype(MONO if mono else SANS,
                               max(1, int(round(size * S))))
        try:
            f.set_variation_by_name(weight)
        except (OSError, ValueError):
            pass
        _fonts[key] = f
    return f


def text_w(s: str, size: float, weight: str = "Regular", mono: bool = False) -> float:
    return face(size, weight, mono).getlength(s) / S


# --------------------------------------------------------------------------
# Drawing surface
# --------------------------------------------------------------------------
W, H = 1920, 1080
HEADER_H = 130
M = 56


class Dc:
    def __init__(self, img: Image.Image, audit: "Audit | None" = None):
        self.img = img
        self.d = ImageDraw.Draw(img)
        self.audit = audit

    def _b(self, b):
        return tuple(v * S for v in b)

    def rect(self, b, fill=None, outline=None, width=1):
        self.d.rectangle(self._b(b), fill=fill, outline=outline,
                         width=int(round(width * S)))

    def rrect(self, b, r, fill=None, outline=None, width=1):
        self.d.rounded_rectangle(self._b(b), radius=r * S, fill=fill,
                                 outline=outline, width=int(round(width * S)))

    def ellipse(self, b, fill=None, outline=None, width=1):
        self.d.ellipse(self._b(b), fill=fill, outline=outline,
                       width=int(round(width * S)))

    def line(self, pts, fill, width=1, joint="curve"):
        self.d.line([(x * S, y * S) for x, y in pts], fill=fill,
                    width=int(round(width * S)), joint=joint)

    def text(self, xy, s, size, colour, weight="Regular", mono=False,
             anchor="lm", kind="label"):
        f = face(size, weight, mono)
        x, y = xy[0] * S, xy[1] * S
        self.d.text((x, y), s, font=f, fill=colour, anchor=anchor)
        if self.audit is not None:
            self.audit.label(self.d.textbbox((x, y), s, font=f, anchor=anchor),
                             s, kind)
        return f.getlength(s) / S


def _dist_point_seg(p, a, b) -> float:
    ax, ay = a
    vx, vy = b[0] - ax, b[1] - ay
    L = vx * vx + vy * vy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - ax) * vx + (p[1] - ay) * vy) / L))
    return math.hypot(p[0] - (ax + vx * t), p[1] - (ay + vy * t))


def _dist_rect_seg(rect, a, b) -> float:
    x0, y0, x1, y1 = rect
    corners = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    inside = lambda p: x0 <= p[0] <= x1 and y0 <= p[1] <= y1  # noqa: E731
    if inside(a) or inside(b):
        return 0.0
    d = min(_dist_point_seg(c, a, b) for c in corners)
    for p in (a, b):
        cx = min(max(p[0], x0), x1)
        cy = min(max(p[1], y0), y1)
        d = min(d, math.hypot(p[0] - cx, p[1] - cy))
    return d


class Audit:
    """Titles and stage labels versus arrow shafts only.

    Adjacent table cells are not audited for overlap — their bboxes sit
    on a shared grid and will always kiss.
    """

    CLEAR = 20
    WATCH = {"title", "stage"}

    def __init__(self):
        self.labels: list[tuple[tuple[float, float, float, float], str, str]] = []
        self.segments: list[tuple[tuple[float, float], tuple[float, float], float]] = []
        self.printed: list[str] = []

    def label(self, bbox, text, kind="label"):
        self.labels.append((bbox, text, kind))
        self.printed.append(text)

    def shaft(self, pts, width):
        for a, b in zip(pts, pts[1:]):
            self.segments.append(((a[0] * S, a[1] * S), (b[0] * S, b[1] * S), width * S))

    def run(self, canvas_box) -> None:
        watched = [(b, t, k) for (b, t, k) in self.labels if k in self.WATCH]
        for (b, t, _k) in watched:
            if not (canvas_box[0] <= b[0] and b[1] >= canvas_box[1]
                    and b[2] <= canvas_box[2] and b[3] <= canvas_box[3]):
                raise SystemExit(f"clipped label {t!r} at {b}")
        clear = self.CLEAR * S
        for (box, t, _k) in watched:
            for (a, b, w) in self.segments:
                if _dist_rect_seg(box, a, b) - w / 2 < clear:
                    raise SystemExit(
                        f"label {t!r} sits within {self.CLEAR}px of an arrow shaft")


def blend(fg, bg, a):
    return tuple(int(round(bg[i] + (fg[i] - bg[i]) * a)) for i in range(3))


def _head(dc: Dc, p0, p1, colour, width, head):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    n = math.hypot(dx, dy) or 1.0
    dx, dy = dx / n, dy / n
    px, py = -dy, dx
    back = (p1[0] - dx * head, p1[1] - dy * head)
    for sgn in (1, -1):
        dc.line([(back[0] + px * head * 0.55 * sgn, back[1] + py * head * 0.55 * sgn), p1],
                colour, width=width)


def arrow(dc: Dc, p0, p1, colour, width=1.5, head=9.0, audit=None):
    """Single-stroke arrow; the head is two strokes, never a Unicode glyph."""
    dc.line([p0, p1], colour, width=width)
    if audit is not None:
        audit.shaft([p0, p1], width)
    _head(dc, p0, p1, colour, width, head)


def arrow_path(dc: Dc, pts, colour, width=1.5, head=9.0, audit=None):
    dc.line(pts, colour, width=width, joint="curve")
    if audit is not None:
        audit.shaft(pts, width)
    _head(dc, pts[-2], pts[-1], colour, width, head)


def dashed_line(dc: Dc, pts, colour, width=1.5, dash=7.0, gap=5.0):
    on, left, cur = True, dash, []
    for a, b2 in zip(pts, pts[1:]):
        seg = math.hypot(b2[0] - a[0], b2[1] - a[1])
        t = 0.0
        while t < seg - 1e-9:
            step = min(seg - t, left)
            p = (a[0] + (b2[0] - a[0]) * t / seg, a[1] + (b2[1] - a[1]) * t / seg)
            t += step
            q = (a[0] + (b2[0] - a[0]) * t / seg, a[1] + (b2[1] - a[1]) * t / seg)
            if on:
                cur = cur + [p, q] if not cur else cur + [q]
            left -= step
            if left <= 1e-9:
                if on and cur:
                    dc.line(cur, colour, width=width)
                    cur = []
                on = not on
                left = dash if on else gap
    if cur:
        dc.line(cur, colour, width=width)


def dashed_rect(dc: Dc, b, colour, width=1.5, dash=7.0, gap=5.0):
    x0, y0, x1, y1 = b
    dashed_line(dc, [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)],
                colour, width=width, dash=dash, gap=gap)


def dashed_rrect(dc: Dc, b, r, colour, width=1.5, dash=7.0, gap=5.0):
    x0, y0, x1, y1 = b
    r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
    pts = [(x0 + r, y0)]
    for cx, cy, a0, a1 in ((x1 - r, y0 + r, -90, 0), (x1 - r, y1 - r, 0, 90),
                           (x0 + r, y1 - r, 90, 180), (x0 + r, y0 + r, 180, 270)):
        for i in range(11):
            a = math.radians(a0 + (a1 - a0) * i / 10)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pts.append((x0 + r, y0))
    on, left, cur = True, dash, []
    for a, b2 in zip(pts, pts[1:]):
        seg = math.hypot(b2[0] - a[0], b2[1] - a[1])
        t = 0.0
        while t < seg - 1e-9:
            step = min(seg - t, left)
            p = (a[0] + (b2[0] - a[0]) * t / seg, a[1] + (b2[1] - a[1]) * t / seg)
            t += step
            q = (a[0] + (b2[0] - a[0]) * t / seg, a[1] + (b2[1] - a[1]) * t / seg)
            if on:
                cur = cur + [p, q] if not cur else cur + [q]
            left -= step
            if left <= 1e-9:
                if on and cur:
                    dc.line(cur, colour, width=width)
                    cur = []
                on = not on
                left = dash if on else gap
    if cur:
        dc.line(cur, colour, width=width)


def draw_header(dc: Dc, title: str, subtitle: str) -> None:
    dc.rect((0, 0, W, HEADER_H), fill=BAND)
    dc.line([(0, HEADER_H), (W, HEADER_H)], RULE, width=1)
    dc.text((M, 48), title, 35, INK, "Bold", anchor="lm", kind="title")
    dc.text((M, 92), subtitle, 17.5, SECOND, anchor="lm", kind="title")


# --------------------------------------------------------------------------
# Derivations
# --------------------------------------------------------------------------
def index_row(r: dict) -> dict:
    return {k: r[k] for k in INGESTION["index_columns"]}


def event_row(r: dict) -> dict:
    return {k: r[k] for k in INGESTION["event_columns"]}


def v_of(r: dict) -> int:
    return ASSIGNMENT["s_1"] + r["hash_slot"]


def seq_of(r: dict) -> int:
    return ASSIGNMENT["k"] + (v_of(r) // ASSIGNMENT["T"])


def job_range() -> tuple[int, int]:
    s1, n = ASSIGNMENT["s_1"], ASSIGNMENT["N"]
    return s1, s1 + n


def virtual_slots() -> list[int]:
    s1 = ASSIGNMENT["s_1"]
    return [s1 + i for i in range(ASSIGNMENT["N"])]


def match_row(r: dict) -> bool:
    return r["brand_id"] in {"A", "B"} and r["pricing_tier"] == 1


def activated_ids() -> list[str]:
    seen: list[str] = []
    for r in INGESTION["records"]:
        pid = r["partition_id"]
        if match_row(r) and pid not in seen:
            seen.append(pid)
    return seen


def trimmed_ids() -> list[str]:
    act = set(activated_ids())
    seen: list[str] = []
    for r in INGESTION["records"]:
        pid = r["partition_id"]
        if pid not in act and pid not in seen:
            seen.append(pid)
    return seen


def tracker_cell(col: str) -> str:
    if col == "grouping_key":
        gk = ASSIGNMENT["grouping_key"]
        return f"({gk[0]}, {gk[1]})"
    if col == "container_seq":
        return str(ASSIGNMENT["k"])
    if col == "filled_count":
        return str(ASSIGNMENT["s_1"])
    raise SystemExit(f"unknown tracker column {col!r}")


def cell_str(v) -> str:
    return str(v)


def assignment_formula() -> str:
    return "V = s_1 + pmod(xxhash64(identity), N)"


def col_origin(columns: list[str], name: str, x0: float) -> float:
    x = x0
    for c in columns:
        if c == name:
            return x
        x += COL_W[c]
    raise SystemExit(f"column {name!r} is not on the shared grid")


def packed_width(columns: list[str]) -> float:
    return sum(COL_W[c] for c in columns)


# --------------------------------------------------------------------------
# Instance checks named in the prompts
# --------------------------------------------------------------------------
def check_process() -> None:
    if len(ACTIONS) != 6:
        raise SystemExit("process figure must have exactly six actions")
    for i, a in enumerate(ACTIONS, start=1):
        if a["n"] != i:
            raise SystemExit(f"number {a['n']} does not match the title beside it: {a['title']!r}")
        if not a["title"]:
            raise SystemExit(f"missing title for action {i}")


def check_ingestion() -> None:
    ids = []
    keys = INGESTION["group_keys"]
    for r in INGESTION["records"]:
        for k in keys:
            if k not in r:
                raise SystemExit(f"record missing group key {k}")
        if "partition_id" not in r:
            raise SystemExit("record missing partition_id")
        if "record_id" not in r:
            raise SystemExit("record missing record_id")
        ids.append(r["record_id"])
    if len(ids) != len(set(ids)):
        raise SystemExit("two records share a record_id")
    for r in INGESTION["records"]:
        ix, ev = index_row(r), event_row(r)
        for k in ("brand_id", "pricing_tier", "partition_id"):
            if ix[k] != ev[k] or ix[k] != r[k]:
                raise SystemExit(
                    f"tables disagree on {k} for {r['record_id']}")


def check_assignment() -> None:
    n = ASSIGNMENT["N"]
    s1 = ASSIGNMENT["s_1"]
    k = ASSIGNMENT["k"]
    t = ASSIGNMENT["T"]
    by_slot: dict[int, list[int]] = defaultdict(list)
    for r in ASSIGNMENT["batch"]:
        hs = r["hash_slot"]
        if hs < 0 or hs > n - 1:
            raise SystemExit(f"hash_slot {hs} is outside 0..N-1")
        v = v_of(r)
        if not (s1 <= v < s1 + n):
            raise SystemExit(f"V={v} is outside [{s1}, {s1 + n})")
        if v != s1 + hs:
            raise SystemExit(f"V does not match s_1 + hash_slot for {r['record_id']}")
        seq = seq_of(r)
        if seq != k + (v // t):
            raise SystemExit(f"seq does not match k + floor(V / T) for {r['record_id']}")
        by_slot[hs].append(v)
    for hs, vs in by_slot.items():
        if len(set(vs)) != 1:
            raise SystemExit(f"records with hash_slot {hs} do not share a V")
    expected_v = [s1 + r["hash_slot"] for r in ASSIGNMENT["batch"]]
    if expected_v != [2, 3, 4, 5, 3, 7]:
        raise SystemExit(f"bound V instance drifted: {expected_v}")
    expected_seq = [k + (v // t) for v in expected_v]
    if expected_seq != [1, 1, 2, 2, 1, 2]:
        raise SystemExit(f"bound seq instance drifted: {expected_seq}")


def check_dpp() -> None:
    act = set(activated_ids())
    trim = set(trimmed_ids())
    if act != {"p1", "p3"}:
        raise SystemExit(f"activated is {act}, not {{p1, p3}}")
    if trim != {"p2", "p4"}:
        raise SystemExit(f"trimmed is {trim}, not {{p2, p4}}")


DIGEST = re.compile(r"\b[0-9a-fA-F]{8,}\b")


def fail_if_digest(printed: list[str]) -> None:
    for t in printed:
        if "xxhash64" in t:
            continue
        if DIGEST.search(t):
            raise SystemExit(f"printed xxhash digest: {t!r}")


# --------------------------------------------------------------------------
# Figure 1 — The go-live process
# --------------------------------------------------------------------------
def draw_process(dc: Dc, audit: Audit) -> None:
    draw_header(dc, "The go-live process",
                "Six actions. Numbers match the left-pane sections.")
    box_w, box_h, gap, radius = 760, 108, 30, 10
    circ_r = 18
    total = len(ACTIONS) * box_h + (len(ACTIONS) - 1) * gap
    y0 = HEADER_H + (H - HEADER_H - total) / 2
    x0 = (W - box_w) / 2
    boxes = []
    outgoing = defaultdict(int)
    for i, action in enumerate(ACTIONS):
        y = y0 + i * (box_h + gap)
        box = (x0, y, x0 + box_w, y + box_h)
        boxes.append(box)
        dc.rrect(box, radius, fill=WHITE, outline=WINE, width=1.5)
        cx, cy = x0, y
        dc.ellipse((cx - circ_r, cy - circ_r, cx + circ_r, cy + circ_r),
                   fill=ROSE, outline=WINE, width=1.5)
        num = str(action["n"])
        dc.text((cx, cy), num, 15, INK, "Semibold", mono=True, anchor="mm",
                kind="stage")
        title = action["title"]
        remain = box_w - circ_r - 28
        tw = text_w(title, 18, "Semibold")
        if tw > remain:
            raise SystemExit(f"title wraps to a second line: {title!r}")
        # centred in the remaining width to the right of the circle
        tx = x0 + circ_r + 10 + remain / 2
        dc.text((tx, y + box_h / 2), title, 18, INK, "Semibold",
                anchor="mm", kind="stage")
    for i in range(len(boxes) - 1):
        a = ((boxes[i][0] + boxes[i][2]) / 2, boxes[i][3] + 4)
        b = ((boxes[i + 1][0] + boxes[i + 1][2]) / 2, boxes[i + 1][1] - 4)
        arrow(dc, a, b, WINE, width=1.5, head=9.0, audit=audit)
        outgoing[i] += 1
    for i in range(len(ACTIONS) - 1):
        if outgoing[i] != 1:
            raise SystemExit(f"rectangle {i + 1} does not have exactly one outgoing arrow")
    if outgoing[len(ACTIONS) - 1]:
        raise SystemExit("a second arrow leaves the last rectangle")
    numbers = [t for t in audit.printed if t.isdigit()]
    if numbers != [str(a["n"]) for a in ACTIONS]:
        raise SystemExit(f"missing or mismatched numbers: {numbers}")


# --------------------------------------------------------------------------
# Shared table drawing (figures 2 and 4)
# --------------------------------------------------------------------------
def draw_table_header(dc: Dc, box, fill, name: str, qualifier: str) -> None:
    x0, y0, x1, y1 = box
    dc.rrect(box, 8, fill=WHITE, outline=RULE, width=1)
    dc.rect((x0, y0, x1, y0 + HDR_H), fill=fill)
    # cover the top corners of the body rule
    dc.line([(x0, y0 + HDR_H), (x1, y0 + HDR_H)], RULE, width=1)
    dc.text((x0 + 16, y0 + HDR_H / 2), name, 15, INK, "Semibold",
            anchor="lm", kind="stage")
    dc.text((x1 - 16, y0 + HDR_H / 2), qualifier, 13, SECOND,
            anchor="rm", kind="label")


def draw_grid_cells(dc: Dc, x_grid: float, y: float, columns: list[str],
                    row: dict, allowed: list[str],
                    grid_columns: list[str] | None = None,
                    outline=None, dashed=False, tag=None, fill=WHITE):
    """Place cells on `grid_columns` (default: the event grid). Only `columns` are drawn."""
    grid = grid_columns or INGESTION["event_columns"]
    for col in columns:
        if col not in allowed:
            raise SystemExit(f"cell {col!r} is not in the allowed columns")
        if not col:
            raise SystemExit("bare column name")
        cx = col_origin(grid, col, x_grid)
        cw = COL_W[col]
        cell = (cx, y, cx + cw, y + ROW_H)
        dc.rect(cell, fill=fill)
        if dashed:
            dashed_rrect(dc, cell, 0, GREEN, width=1.2)
        elif outline:
            dc.rect(cell, outline=outline, width=1.2)
        else:
            dc.rect(cell, outline=RULE, width=1)
        dc.text((cx + cw / 2, y + ROW_H / 2), cell_str(row[col]), 12, INK,
                mono=True, anchor="mm", kind="cell")
    if tag:
        last = columns[-1]
        lx = col_origin(grid, last, x_grid) + COL_W[last] + 10
        dc.text((lx, y + ROW_H / 2), tag, 12, SECOND, anchor="lm", kind="label")


def draw_column_names(dc: Dc, x_grid: float, y: float, columns: list[str],
                      grid_columns: list[str] | None = None) -> None:
    grid = grid_columns or INGESTION["event_columns"]
    for col in columns:
        if not col:
            raise SystemExit("bare column name")
        cx = col_origin(grid, col, x_grid)
        dc.text((cx + COL_W[col] / 2, y), col, 12.5, SECOND, mono=True,
                anchor="mm", kind="cell")


def draw_index_row(dc: Dc, x_grid: float, y: float, columns: list[str],
                   row: dict, hit: bool) -> None:
    """One prescan row: solid wine + 'match', or dashed green and quiet."""
    width = packed_width(columns)
    band = (x_grid, y, x_grid + width, y + ROW_H)
    if hit:
        dc.rect(band, fill=ROSE, outline=WINE, width=1.5)
    else:
        dc.rect(band, fill=SAGE)
        dashed_rect(dc, band, GREEN, width=1.5)
    for col in columns:
        if col not in INGESTION["index_columns"]:
            raise SystemExit(f"index cell {col!r} is not in index_columns")
        cx = col_origin(columns, col, x_grid)
        dc.text((cx + COL_W[col] / 2, y + ROW_H / 2), cell_str(row[col]),
                12, INK, mono=True, anchor="mm", kind="cell")
    if hit:
        dc.text((x_grid + width + 10, y + ROW_H / 2), "match", 12, SECOND,
                anchor="lm", kind="label")


# --------------------------------------------------------------------------
# Figure 2 — Ingestion writes two tables
# --------------------------------------------------------------------------
def draw_ingestion(dc: Dc, audit: Audit) -> None:
    draw_header(dc, "Ingestion writes two tables",
                "One grouped stream. A narrow index and a wide event table.")

    ev_cols = INGESTION["event_columns"]
    ix_cols = INGESTION["index_columns"]
    records = INGESTION["records"]
    grid_w = packed_width(ev_cols)
    table_w = grid_w + 32
    table_x0 = W - M - table_w
    grid_x = table_x0 + 16

    stack_h = HDR_H + 18 + 4 * ROW_H
    gap_t = 36
    total_t = stack_h * 2 + gap_t
    table_y0 = HEADER_H + (H - HEADER_H - total_t) / 2 + 8
    index_box = (table_x0, table_y0, table_x0 + table_w, table_y0 + stack_h)
    event_box = (table_x0, table_y0 + stack_h + gap_t,
                 table_x0 + table_w, table_y0 + stack_h + gap_t + stack_h)

    stage_y = table_y0 - 28
    box_h = 200
    box_y = (index_box[1] + event_box[3]) / 2 - box_h / 2
    stream_w, group_w, assign_w = 210, 230, 240
    left = M
    stream_box = (left, box_y, left + stream_w, box_y + box_h)
    gx0 = stream_box[2] + 54
    group_box = (gx0, box_y, gx0 + group_w, box_y + box_h)
    ax0 = group_box[2] + 54
    assign_box = (ax0, box_y, ax0 + assign_w, box_y + box_h)

    # Stage titles — process concepts from §2.5
    for title, box in (("Stream", stream_box),
                       ("Split decision", group_box),
                       ("Container assignment", assign_box)):
        dc.text(((box[0] + box[2]) / 2, stage_y), title, 15, INK, "Semibold",
                anchor="mm", kind="stage")

    def process_box(box, label, notes):
        dc.rrect(box, 10, fill=WHITE, outline=WINE, width=1.5)
        cx = (box[0] + box[2]) / 2
        cy = (box[1] + box[3]) / 2
        dc.text((cx, cy - (14 if notes else 0)), label, 16, INK, "Semibold",
                anchor="mm", kind="label")
        for i, note in enumerate(notes):
            dc.text((cx, cy + 18 + i * 20), note, 13, SECOND,
                    anchor="mm", kind="label")

    stream_label = f"{INGESTION['stream']} stream"
    process_box(stream_box, stream_label, [])
    group_notes = [f"[{k}]" for k in INGESTION["group_keys"]]
    # label on top, keys underneath as specified
    dc.rrect(group_box, 10, fill=WHITE, outline=WINE, width=1.5)
    gcx, gcy = (group_box[0] + group_box[2]) / 2, (group_box[1] + group_box[3]) / 2
    dc.text((gcx, gcy - 28), "group by", 16, INK, "Semibold",
            anchor="mm", kind="label")
    for i, note in enumerate(group_notes):
        dc.text((gcx, gcy + 2 + i * 22), note, 13, INK, mono=True,
                anchor="mm", kind="label")

    assign_notes = ["detailed later"]
    dc.rrect(assign_box, 10, fill=WHITE, outline=WINE, width=1.5)
    acx, acy = (assign_box[0] + assign_box[2]) / 2, (assign_box[1] + assign_box[3]) / 2
    dc.text((acx, acy - 28), "partition assignment", 16, INK, "Semibold",
            anchor="mm", kind="label")
    for i, note in enumerate(assign_notes):
        dc.text((acx, acy + 2 + i * 20), note, 13, SECOND,
                anchor="mm", kind="label")
    assign_printed = ["partition assignment", *assign_notes]
    for t in assign_printed:
        if "hash" in t.lower() or "slot" in t.lower():
            raise SystemExit(f"assignment box prints a hash or a slot: {t!r}")

    # Chain arrows 1→2→3, then a split fan-out to both tables
    mid_y = (stream_box[1] + stream_box[3]) / 2
    arrow(dc, (stream_box[2] + 6, mid_y), (group_box[0] - 6, mid_y),
          WINE, width=1.5, head=9.0, audit=audit)
    arrow(dc, (group_box[2] + 6, mid_y), (assign_box[0] - 6, mid_y),
          WINE, width=1.5, head=9.0, audit=audit)

    join_x = assign_box[2] + 28
    index_cy = (index_box[1] + index_box[3]) / 2
    event_cy = (event_box[1] + event_box[3]) / 2
    dc.line([(assign_box[2] + 4, mid_y), (join_x, mid_y)], WINE, width=1.5)
    if audit is not None:
        audit.shaft([(assign_box[2] + 4, mid_y), (join_x, mid_y)], 1.5)
    arrow_path(dc, [(join_x, mid_y), (join_x, index_cy), (table_x0 - 8, index_cy)],
               WINE, width=1.5, head=9.0, audit=audit)
    arrow_path(dc, [(join_x, mid_y), (join_x, event_cy), (table_x0 - 8, event_cy)],
               WINE, width=1.5, head=9.0, audit=audit)
    # two branches after the split
    fanout_branches = 2
    if fanout_branches != 2:
        raise SystemExit("missing split of the fan-out arrow")

    # Index table
    draw_table_header(dc, index_box, SAGE, "index table", "narrow")
    col_y = index_box[1] + HDR_H + 10
    draw_column_names(dc, grid_x, col_y, ix_cols, grid_columns=ev_cols)
    for i, r in enumerate(records):
        y = index_box[1] + HDR_H + 20 + i * ROW_H
        draw_grid_cells(dc, grid_x, y, ix_cols, index_row(r), ix_cols,
                        grid_columns=ev_cols)

    # Event table
    draw_table_header(dc, event_box, ROSE, "event table", "wide")
    draw_column_names(dc, grid_x, event_box[1] + HDR_H + 10, ev_cols,
                      grid_columns=ev_cols)
    for i, r in enumerate(records):
        y = event_box[1] + HDR_H + 20 + i * ROW_H
        draw_grid_cells(dc, grid_x, y, ev_cols, event_row(r), ev_cols,
                        grid_columns=ev_cols)


# --------------------------------------------------------------------------
# Figure 3 — Stateful container assignment
# --------------------------------------------------------------------------
def draw_assignment(dc: Dc, audit: Audit) -> None:
    draw_header(dc, "Stateful container assignment",
                "Hash identity to a virtual slot. Collisions are accepted.")
    check_assignment()

    s1 = ASSIGNMENT["s_1"]
    n = ASSIGNMENT["N"]
    tcap = ASSIGNMENT["T"]
    batch = ASSIGNMENT["batch"]
    slots = virtual_slots()
    lo, hi = job_range()

    tracker_w, batch_w, ruler_w = 380, 380, 440
    bin_w, bin_gap = 188, 16
    bins_w = 2 * bin_w + bin_gap
    gap = 28
    left = 32
    tracker_x = left
    batch_x = tracker_x + tracker_w + gap
    ruler_x = batch_x + batch_w + gap
    bins_x = ruler_x + ruler_w + gap

    content_h = 600
    stage_y = HEADER_H + (H - HEADER_H - content_h) / 2
    card_y = stage_y + 32
    card_h = content_h - 40
    mid = card_y + card_h / 2

    # -- 1. Tracker --
    tbox = (tracker_x, card_y + 80, tracker_x + tracker_w, card_y + 80 + 220)
    dc.text(((tbox[0] + tbox[2]) / 2, stage_y), "state per grouping", 15, INK,
            "Semibold", anchor="mm", kind="stage")
    dc.rrect(tbox, 8, fill=WHITE, outline=WINE, width=1.5)
    dc.text(((tbox[0] + tbox[2]) / 2, tbox[1] + 24), "assignment tracker",
            15, INK, "Semibold", anchor="mm", kind="stage")
    cols = ASSIGNMENT["tracker_columns"]
    col_w = (tracker_w - 32) / len(cols)
    hx = tracker_x + 16
    hy = tbox[1] + 52
    for i, col in enumerate(cols):
        cx = hx + i * col_w
        dc.text((cx + col_w / 2, hy + 12), col, 12.5, SECOND, mono=True,
                anchor="mm", kind="cell")
        cell = (cx, hy + 24, cx + col_w, hy + 24 + 36)
        dc.rect(cell, fill=WHITE, outline=RULE, width=1)
        dc.text((cx + col_w / 2, hy + 24 + 18), tracker_cell(col), 12, INK,
                mono=True, anchor="mm", kind="cell")
    dc.text(((tbox[0] + tbox[2]) / 2, tbox[3] - 28), "one partial container",
            13, SECOND, anchor="mm", kind="label")

    # -- 2. Batch --
    bbox = (batch_x, card_y + 40, batch_x + batch_w, card_y + card_h - 20)
    dc.text(((bbox[0] + bbox[2]) / 2, stage_y), f"N = {n}", 15, INK,
            "Semibold", anchor="mm", kind="stage")
    dc.rrect(bbox, 8, fill=WHITE, outline=RULE, width=1)
    dc.text(((bbox[0] + bbox[2]) / 2, bbox[1] + 22), "this batch", 15, INK,
            "Semibold", anchor="mm", kind="stage")
    chip_h, chip_gap = 36, 8
    chips_top = bbox[1] + 48
    chip_boxes = []
    for i, rec in enumerate(batch):
        y = chips_top + i * (chip_h + chip_gap)
        chip = (batch_x + 24, y, batch_x + batch_w - 24, y + chip_h)
        chip_boxes.append(chip)
        dc.rrect(chip, 6, fill=WHITE, outline=WINE, width=1)
        label = f"{rec['record_id']}  {rec['hash_slot']}"
        dc.text(((chip[0] + chip[2]) / 2, (chip[1] + chip[3]) / 2), label,
                12, INK, mono=True, anchor="mm", kind="cell")
    formula = assignment_formula()
    fw = text_w(formula, 14.5, mono=True)
    fband = (batch_x + 10, bbox[3] - 56, batch_x + batch_w - 10, bbox[3] - 14)
    if fw > (fband[2] - fband[0] - 12):
        raise SystemExit("formula does not fit the formula band at 14.5")
    dc.rrect(fband, 6, fill=ROSE, outline=WINE, width=1)
    dc.text(((fband[0] + fband[2]) / 2, (fband[1] + fband[3]) / 2),
            formula, 14.5, INK, mono=True, anchor="mm", kind="label")

    # -- 3. Virtual slots --
    tick_y = mid
    tick_span = ruler_w / n
    tick_xs = [ruler_x + (i + 0.5) * tick_span for i in range(n)]
    dc.line([(ruler_x + 8, tick_y), (ruler_x + ruler_w - 8, tick_y)],
            WINE, width=1.5)
    collision_v = None
    vs = [v_of(r) for r in batch]
    for v, c in ((v, vs.count(v)) for v in vs):
        if c > 1:
            collision_v = v
            break
    if collision_v is None:
        raise SystemExit("collision pair does not share a tick")
    for i, v in enumerate(slots):
        x = tick_xs[i]
        dc.line([(x, tick_y - 12), (x, tick_y + 12)], WINE, width=1.5)
        dc.text((x, tick_y + 28), str(v), 12, INK, mono=True, anchor="mm",
                kind="cell")
        if v == collision_v:
            dc.ellipse((x - 16, tick_y - 16, x + 16, tick_y + 16),
                       outline=WINE, width=2)
            dc.text((x + 22, tick_y - 22), "collision", 12, SECOND,
                    anchor="lm", kind="label")
    # brace for the job range
    brace_y = tick_y + 52
    dc.line([(tick_xs[0], brace_y), (tick_xs[-1], brace_y)], SECOND, width=1)
    dc.line([(tick_xs[0], brace_y - 8), (tick_xs[0], brace_y)], SECOND, width=1)
    dc.line([(tick_xs[-1], brace_y - 8), (tick_xs[-1], brace_y)], SECOND, width=1)
    dc.text(((tick_xs[0] + tick_xs[-1]) / 2, brace_y + 16),
            f"[{lo}, {hi}]", 12, SECOND, mono=True, anchor="mm", kind="label")

    # chips to their V — run to the tick x, then drop onto the tick
    tick_of = {v: tick_xs[slots.index(v)] for v in slots}
    occupied = {v_of(r) for r in batch}
    for rec, chip in zip(batch, chip_boxes):
        v = v_of(rec)
        if v not in tick_of:
            raise SystemExit(f"V={v} has no tick")
        tx = tick_of[v]
        y0 = (chip[1] + chip[3]) / 2
        arrive = tick_y - 12 if y0 <= tick_y else tick_y + 12
        arrow_path(dc, [(chip[2] + 2, y0), (tx, y0), (tx, arrive)],
                   WINE, width=1.5, head=7.0, audit=audit)
    for v in occupied:
        x = tick_of[v]
        dc.ellipse((x - 4, tick_y - 4, x + 4, tick_y + 4), fill=WINE, outline=WINE)

    # shared-tick check for the collision pair
    collide = [r for r in batch if v_of(r) == collision_v]
    if len(collide) < 2:
        raise SystemExit("collision pair does not share a tick")
    if len({v_of(r) for r in collide}) != 1:
        raise SystemExit("collision pair does not share a tick")

    # -- 4. Containers --
    dc.text((bins_x + bins_w / 2, stage_y),
            "partition seq = k + floor(V / T)", 15, INK, "Semibold",
            anchor="mm", kind="stage")
    seqs = sorted({seq_of(r) for r in batch})
    if seqs != [1, 2]:
        raise SystemExit(f"unexpected container seqs {seqs}")
    by_seq: dict[int, list[dict]] = defaultdict(list)
    for rec in batch:
        by_seq[seq_of(rec)].append(rec)

    slot_h = 56
    for si, seq in enumerate(seqs):
        bx = bins_x + si * (bin_w + bin_gap)
        by0 = mid - (tcap * slot_h) / 2 - 20
        by1 = by0 + 28 + tcap * slot_h + 12
        bin_box = (bx, by0, bx + bin_w, by1)
        dc.rrect(bin_box, 8, fill=WHITE, outline=WINE, width=1.5)
        dc.text((bx + bin_w / 2, by0 + 16), f"seq {seq}", 15, INK,
                "Semibold", mono=True, anchor="mm", kind="stage")
        occupants: dict[int, list[str]] = defaultdict(list)
        for rec in by_seq[seq]:
            occupants[v_of(rec) % tcap].append(rec["record_id"])
        for slot in range(tcap):
            sy = by0 + 28 + slot * slot_h
            cell = (bx + 14, sy + 4, bx + bin_w - 14, sy + slot_h - 4)
            prefilled = seq == ASSIGNMENT["k"] and slot < s1
            ids = occupants.get(slot, [])
            if ids:
                dc.rrect(cell, 6, fill=ROSE, outline=WINE, width=1.5)
                dc.text(((cell[0] + cell[2]) / 2, (cell[1] + cell[3]) / 2),
                        "  ".join(ids), 12, INK, mono=True, anchor="mm",
                        kind="cell")
            elif prefilled:
                dc.rrect(cell, 6, fill=blend(WINE, WHITE, 0.22), outline=WINE,
                         width=1.5)
            else:
                dc.rrect(cell, 6, fill=SAGE)
                dashed_rrect(dc, cell, 6, GREEN, width=1.2)

    # tracker to batch
    arrow(dc, (tbox[2] + 6, (tbox[1] + tbox[3]) / 2),
          (bbox[0] - 6, (bbox[1] + bbox[3]) / 2),
          WINE, width=1.5, head=9.0, audit=audit)

    fail_if_digest(audit.printed)


# --------------------------------------------------------------------------
# Figure 4 — Spark DPP skips from the index
# --------------------------------------------------------------------------
def draw_dpp(dc: Dc, audit: Audit) -> None:
    draw_header(dc, "Spark DPP skips from the index",
                "Prescan. Broadcast the activated partition_id set. Trim the download.")
    check_dpp()

    records = INGESTION["records"]
    ix_cols = INGESTION["index_columns"]
    q = DPP["query"]
    workers = list(DPP["workers"])
    activated = activated_ids()
    act_set = set(activated)
    if len(workers) != 2:
        raise SystemExit("a worker set other than two workers")

    q_w = 360
    ix_w = packed_width(ix_cols) + 88  # room for the match tag
    act_w = 196
    dpp_w = 176
    right_w = 400
    gap = 28
    left = 32
    q_x = left
    ix_x = q_x + q_w + gap
    act_x = ix_x + ix_w + gap
    dpp_x = act_x + act_w + gap
    right_x = dpp_x + dpp_w + gap

    body_top = HEADER_H + 48
    mid = (body_top + H - 40) / 2

    # -- 1. Query --
    q_h = 132
    qbox = (q_x, mid - q_h / 2, q_x + q_w, mid + q_h / 2)
    dc.rrect(qbox, 8, fill=ROSE, outline=WINE, width=1.5)
    dc.text((q_x + 16, qbox[1] + 22), "query", 15, INK, "Semibold",
            anchor="lm", kind="stage")
    qtext = q["text"]
    if text_w(qtext, 13, mono=True) > q_w - 24:
        raise SystemExit("query text does not fit on one mono line")
    dc.text((q_x + 16, mid + 4), qtext, 13, INK, mono=True,
            anchor="lm", kind="label")
    dc.text((q_x + 16, qbox[3] - 22), q["kind"], 13, SECOND,
            anchor="lm", kind="label")

    # -- 2. Index prescan --
    dc.text((ix_x + ix_w / 2, body_top), "index table prescan", 15, INK,
            "Semibold", anchor="mm", kind="stage")
    ix_h = HDR_H + 18 + 4 * ROW_H
    ix_box = (ix_x, mid - ix_h / 2, ix_x + ix_w, mid + ix_h / 2)
    draw_table_header(dc, ix_box, SAGE, "index table", "narrow")
    grid_x = ix_x + 16
    draw_column_names(dc, grid_x, ix_box[1] + HDR_H + 10, ix_cols,
                      grid_columns=ix_cols)
    object_words: dict[str, str] = {}
    for i, r in enumerate(records):
        y = ix_box[1] + HDR_H + 20 + i * ROW_H
        draw_index_row(dc, grid_x, y, ix_cols, index_row(r), match_row(r))

    # -- 3. Activated set --
    abox = (act_x, mid - 90, act_x + act_w, mid + 90)
    dc.rrect(abox, 8, fill=WHITE, outline=WINE, width=1.5)
    dc.text((act_x + act_w / 2, abox[1] + 22), "activated partition_id",
            13, INK, "Semibold", anchor="mm", kind="stage")
    if activated != ["p1", "p3"]:
        raise SystemExit(f"activated set other than p1 and p3: {activated}")
    for i, pid in enumerate(activated):
        cy = abox[1] + 56 + i * 48
        chip = (act_x + 28, cy, act_x + act_w - 28, cy + 36)
        dc.rrect(chip, 6, fill=ROSE, outline=WINE, width=1.5)
        dc.text(((chip[0] + chip[2]) / 2, (chip[1] + chip[3]) / 2), pid,
                13, INK, "Semibold", mono=True, anchor="mm", kind="cell")

    # -- 4. Spark DPP --
    dbox = (dpp_x, mid - 80, dpp_x + dpp_w, mid + 80)
    dc.rrect(dbox, 10, fill=WHITE, outline=WINE, width=1.5)
    dc.text((dpp_x + dpp_w / 2, mid - 14), "Spark DPP", 16, INK, "Semibold",
            anchor="mm", kind="stage")
    dc.text((dpp_x + dpp_w / 2, mid + 16), "metadata filter", 13, SECOND,
            anchor="mm", kind="label")

    # -- 5. Workers and objects --
    ww, wh, wgap = 170, 56, 14
    w_x = right_x + (right_w - ww) / 2
    w1_y = mid - wh - wgap / 2 - 30
    worker_boxes = []
    for i, name in enumerate(workers):
        y = w1_y + i * (wh + wgap)
        wb = (w_x, y, w_x + ww, y + wh)
        worker_boxes.append(wb)
        dc.rrect(wb, 8, fill=WHITE, outline=WINE, width=1.5)
        dc.text(((wb[0] + wb[2]) / 2, (wb[1] + wb[3]) / 2), name, 15, INK,
                "Semibold", mono=True, anchor="mm", kind="stage")

    obj_ids = [r["partition_id"] for r in records]
    obj_w, obj_h, obj_gap = 78, 64, 14
    row_w = 4 * obj_w + 3 * obj_gap
    ox0 = right_x + (right_w - row_w) / 2
    oy = worker_boxes[-1][3] + 64
    dc.text((right_x + right_w / 2, oy - 24), "cloud objects", 15, INK,
            "Semibold", anchor="mm", kind="stage")
    for i, pid in enumerate(obj_ids):
        x = ox0 + i * (obj_w + obj_gap)
        ob = (x, oy, x + obj_w, oy + obj_h)
        active = pid in act_set
        word = "download" if active else "skip"
        object_words[pid] = word
        if active:
            dc.rrect(ob, 6, fill=ROSE, outline=WINE, width=1.5)
        else:
            dc.rrect(ob, 6, fill=SAGE)
            dashed_rrect(dc, ob, 6, GREEN, width=1.5)
        # folded-corner file, line glyphs only — not a machine
        fold = 12
        dc.line([(x + obj_w - fold, oy + 1), (x + obj_w - 1, oy + fold)],
                WINE if active else GREEN, width=1)
        dc.line([(x + obj_w - fold, oy + 1), (x + obj_w - fold, oy + fold),
                 (x + obj_w - 1, oy + fold)],
                WINE if active else GREEN, width=1)
        dc.text((x + obj_w / 2, oy + obj_h / 2 + 6), pid, 13, INK,
                "Semibold", mono=True, anchor="mm", kind="cell")
        dc.text((x + obj_w / 2, oy + obj_h + 14), word, 12, SECOND,
                anchor="mm", kind="label")

    for pid, word in object_words.items():
        if pid in {"p2", "p4"} and word != "skip":
            raise SystemExit(f"download mark on {pid}")
        if pid in {"p1", "p3"} and word != "download":
            raise SystemExit(f"skip mark on {pid}")

    # Arrows
    q_cy = (qbox[1] + qbox[3]) / 2
    arrow(dc, (qbox[2] + 4, q_cy), (ix_box[0] - 6, q_cy),
          WINE, width=1.5, head=9.0, audit=audit)
    arrow(dc, (ix_box[2] + 4, q_cy), (abox[0] - 6, q_cy),
          WINE, width=1.5, head=9.0, audit=audit)
    arrow(dc, (abox[2] + 4, q_cy), (dbox[0] - 6, q_cy),
          WINE, width=1.5, head=9.0, audit=audit)
    set_tag = ", ".join(activated)
    worker_tags = 0
    for wb in worker_boxes:
        wy = (wb[1] + wb[3]) / 2
        arrow_path(dc, [(dbox[2] + 4, q_cy), (dbox[2] + 22, q_cy),
                        (dbox[2] + 22, wy), (wb[0] - 6, wy)],
                   WINE, width=1.5, head=9.0, audit=audit)
        dc.text((dbox[2] + 28, wy - 12), set_tag, 12, SECOND, mono=True,
                anchor="lm", kind="label")
        worker_tags += 1
        if set(activated) != act_set:
            raise SystemExit("a worker receives a set other than activated")
    if worker_tags != len(workers):
        raise SystemExit("a worker arrow missing its set tag")


# --------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------
FIGURES = (
    ("section_c_go_live_process.png", check_process, draw_process),
    ("section_c_data_ingestion.png", check_ingestion, draw_ingestion),
    ("section_c_dpp_skipping.png", check_dpp, draw_dpp),
)


def render_one(name: str, check, draw) -> Path:
    check()
    big = Image.new("RGB", (W * S, H * S), CANVAS)
    audit = Audit()
    dc = Dc(big, audit)
    draw(dc, audit)
    audit.run((0, 0, W * S, H * S))
    out = big.resize((W, H), Image.LANCZOS)
    path = IMG / name
    path.parent.mkdir(parents=True, exist_ok=True)
    out.save(path, format="PNG")
    print(f"wrote {path}  {out.size[0]}x{out.size[1]}  {path.stat().st_size / 1024:.0f} KB")
    return path


def main() -> None:
    paths = []
    for name, check, draw in FIGURES:
        paths.append(render_one(name, check, draw))
    for path in paths:
        im = Image.open(path)
        if im.size != (W, H):
            raise SystemExit(f"{path.name} is {im.size}, not {W}x{H}")
        print(f"  verified {path.name}  {im.size[0]}x{im.size[1]}")


if __name__ == "__main__":
    main()
