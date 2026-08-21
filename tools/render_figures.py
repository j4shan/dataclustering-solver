#!/usr/bin/env python3
"""Render the documentation figures, and write light/dark SVG pairs into
resources/img/:

    python3 tools/render_figures.py

Two of the three read resources/data/closet-scenario.json and state quantities
computed from it — rerun after editing the scenario. The third, the page anatomy, draws
the served page's structure and states no scenario quantity at all (9.15).

No third-party dependencies.
"""

from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
SCENARIO = ROOT / "resources" / "data" / "closet-scenario.json"
OUTDIR = ROOT / "resources" / "img"

# Single-quoted inner name: this string is interpolated into a double-quoted
# XML attribute, so nested double quotes would break the document.
FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"

# Palette slots. Blue = needed, red = wasted; both validated against each
# surface (adjacent CVD dE 23.8 light / 25.7 dark, contrast >= 3:1 in both).
# Colour is never the only channel: needed is solid, wasted is striped,
# skipped is an empty ring.
THEMES = {
    "light": {
        "surface": "#fcfcfb",
        "ink": "#0b0b0b",
        "ink2": "#52514e",
        "muted": "#898781",
        "grid": "#e1e0d9",
        "border": "#dedcd4",
        "needed": "#2a78d6",
        "wasted": "#d03b3b",
        "chip": "#f0efec",
    },
    "dark": {
        "surface": "#1a1a19",
        "ink": "#ffffff",
        "ink2": "#c3c2b7",
        "muted": "#898781",
        "grid": "#2c2c2a",
        "border": "#333331",
        "needed": "#3987e5",
        "wasted": "#d03b3b",
        "chip": "#26261f",
    },
}

CELL_W, CELL_H = 26, 22
TAG_W, LABEL_W = 26, 98


# --------------------------------------------------------------------------
# model
# --------------------------------------------------------------------------

def load():
    return json.loads(SCENARIO.read_text())


def selections(scenario):
    """query_id -> set of event ids selected by it (the selection log, pivoted)."""
    sel = {q["id"]: set() for q in scenario["queries"]}
    for event_id, query_id in scenario["selection_log"]:
        sel[query_id].add(event_id)
    return sel


def evaluate(scenario, layout):
    """Activation, waste and cost for one layout, per §§3.4-3.5 of the problem statement."""
    sel = selections(scenario)
    qids = [q["id"] for q in scenario["queries"]]

    containers = []
    for con in layout["containers"]:
        support = {q for q in qids if sel[q] & set(con["events"])}
        size = len(con["events"])
        needed = sum(1 for q in qids for e in con["events"] if e in sel[q])
        opened = size * len(support)
        containers.append({
            **con,
            "support": support,
            "size": size,
            "breadth": len(support),
            "opened": opened,
            "needed": needed,
            "wasted": opened - needed,
        })

    opened = sum(c["opened"] for c in containers)
    needed = sum(c["needed"] for c in containers)
    return {
        "containers": containers,
        "opened": opened,
        "needed": needed,
        "wasted": opened - needed,
        "amplification": opened / needed if needed else 0.0,
    }


def cell_state(container, event_id, query_id, sel):
    if query_id not in container["support"]:
        return "skipped"
    return "needed" if event_id in sel[query_id] else "wasted"


# --------------------------------------------------------------------------
# svg helpers
# --------------------------------------------------------------------------

def text(x, y, s, *, fill, size=11, weight=400, anchor="start", mono=False, opacity=None):
    extra = ' font-variant-numeric="tabular-nums"' if mono else ""
    op = f' opacity="{opacity}"' if opacity is not None else ""
    return (
        f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{extra}{op}>'
        f'{escape(s)}</text>'
    )


def rect(x, y, w, h, *, fill="none", stroke="none", rx=0, sw=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>'
    )


def state_cell(x, y, state, c, w=CELL_W - 5, h=CELL_H - 5):
    """One matrix cell. Solid / striped / empty — readable without colour."""
    if state == "needed":
        return rect(x, y, w, h, fill=c["needed"], rx=3)
    if state == "wasted":
        return (
            rect(x, y, w, h, fill=c["wasted"], rx=3)
            + rect(x, y, w, h, fill="url(#hatch)", rx=3)
        )
    return rect(x, y, w, h, fill="none", stroke=c["grid"], rx=3, sw=1)


def defs(c):
    return (
        '<defs><pattern id="hatch" patternUnits="userSpaceOnUse" '
        'width="6" height="6" patternTransform="rotate(45)">'
        f'<line x1="0" y1="0" x2="0" y2="6" stroke="{c["surface"]}" '
        'stroke-width="2.4"/></pattern></defs>'
    )


def svg(width, height, body, c, title):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">'
        f'<title>{escape(title)}</title>'
        + defs(c)
        + rect(0, 0, width, height, fill=c["surface"])
        + body
        + "</svg>"
    )


def legend(x, y, c):
    """Shared three-state key."""
    out = []
    items = [
        ("needed", "selected by the query"),
        ("wasted", "opened, not selected — waste"),
        ("skipped", "never opened — skipped"),
    ]
    cx = x
    for state, label in items:
        out.append(state_cell(cx, y - 10, state, c, w=13, h=13))
        out.append(text(cx + 20, y, label, fill=c["ink2"], size=11))
        cx += 26 + len(label) * 6.0
    return "".join(out), cx


# --------------------------------------------------------------------------
# figure 1 — the selection matrix
# --------------------------------------------------------------------------

def figure_matrix(scenario, theme):
    c = THEMES[theme]
    sel = selections(scenario)
    queries = scenario["queries"]
    layouts = scenario["layouts"]

    grid_w = len(queries) * CELL_W
    panel_w = TAG_W + LABEL_W + grid_w
    gap = 40
    margin = 22
    width = margin * 2 + panel_w * 2 + gap

    body = []
    body.append(text(margin, 28, "The same events, the same queries, two layouts",
                     fill=c["ink"], size=15, weight=600))
    body.append(text(margin, 48,
                     "Rows are events grouped into containers · columns are queries · "
                     "a container is opened when any of its rows is selected",
                     fill=c["ink2"], size=11))

    panel_top = 74
    bottoms = []

    for pi, layout in enumerate(layouts):
        px = margin + pi * (panel_w + gap)
        ev = evaluate(scenario, layout)
        y = panel_top

        body.append(text(px, y, layout["name"], fill=c["ink"], size=13, weight=600))
        body.append(text(px, y + 16, layout["caption"], fill=c["muted"], size=10.5))

        grid_x = px + TAG_W + LABEL_W
        hy = y + 38
        for qi, q in enumerate(queries):
            body.append(text(grid_x + qi * CELL_W + (CELL_W - 5) / 2, hy,
                             str(q["id"]), fill=c["muted"], size=9.5,
                             anchor="middle", mono=True))
        body.append(text(grid_x - 10, hy, "query_id →",
                         fill=c["muted"], size=9.5, anchor="end"))

        top = hy + 10
        for con in ev["containers"]:
            n = len(con["events"])
            bh = n * CELL_H + 8
            body.append(rect(px, top, panel_w, bh, fill="none",
                             stroke=c["border"], rx=6))
            body.append(rect(px + 5, top + bh / 2 - 9, 18, 18,
                             fill=c["chip"], rx=5))
            body.append(text(px + 14, top + bh / 2 + 4, str(con["tag"]),
                             fill=c["ink2"], size=10.5, weight=600,
                             anchor="middle", mono=True))

            for ri, event_id in enumerate(con["events"]):
                ry = top + 4 + ri * CELL_H
                body.append(text(px + TAG_W + LABEL_W - 10, ry + 15, event_id,
                                 fill=c["ink2"], size=10.5, anchor="end"))
                for qi, q in enumerate(queries):
                    st = cell_state(con, event_id, q["id"], sel)
                    body.append(state_cell(grid_x + qi * CELL_W + 1, ry + 2, st, c))
            top += bh + 12

        fy = top + 10
        body.append(text(px, fy, f'{ev["opened"]} events opened',
                         fill=c["ink2"], size=11))
        body.append(text(px, fy + 17, f'{ev["wasted"]} wasted',
                         fill=c["wasted"], size=13, weight=700))
        label = f'{ev["wasted"]} wasted'
        body.append(text(px + 13 * 0.62 * len(label) + 8, fy + 17,
                         f'· {ev["amplification"]:.2f}× read amplification',
                         fill=c["muted"], size=11))
        bottoms.append(fy + 17)

    ly = max(bottoms) + 34
    leg, _ = legend(margin, ly, c)
    body.append(leg)
    body.append(text(margin, ly + 20,
                     "Within a container a column is all-filled or all-empty — "
                     "that is what activation means. Waste is every red cell.",
                     fill=c["muted"], size=10.5))

    height = ly + 36
    return svg(width, height, "".join(body), c,
               "Selection matrix under two layouts, showing container activation and waste")


# --------------------------------------------------------------------------
# figure 2 — zoom into one activated and one bypassed container
# --------------------------------------------------------------------------

def figure_zoom(scenario, theme):
    c = THEMES[theme]
    sel = selections(scenario)
    spec = scenario["zoom"]
    layout = next(l for l in scenario["layouts"] if l["key"] == spec["layout"])
    ev = evaluate(scenario, layout)
    by_tag = {x["tag"]: x for x in ev["containers"]}
    qid = spec["query"]
    qlabel = next(q["label"] for q in scenario["queries"] if q["id"] == qid)
    picked = sorted(sel[qid])

    card_w, gap, margin = 330, 30, 22
    width = margin * 2 + card_w * 2 + gap

    body = []
    body.append(text(margin, 28, f"Inside two containers, during one query",
                     fill=c["ink"], size=15, weight=600))
    body.append(text(margin, 48,
                     f"Query {qid} · “{qlabel}” · selects {', '.join(picked)}",
                     fill=c["ink2"], size=11))

    card_top = 70
    heights = []

    for ci, (tag, opened) in enumerate([(spec["activated_tag"], True),
                                        (spec["bypassed_tag"], False)]):
        con = by_tag[tag]
        cx = margin + ci * (card_w + gap)
        rows = con["events"]
        card_h = 74 + len(rows) * 30 + 44

        body.append(rect(cx, card_top, card_w, card_h, fill="none",
                         stroke=c["border"], rx=10,
                         dash=None if opened else "5 4"))

        body.append(rect(cx + 16, card_top + 18, 20, 20, fill=c["chip"], rx=5))
        body.append(text(cx + 26, card_top + 32, str(tag), fill=c["ink2"],
                         size=11, weight=600, anchor="middle", mono=True))
        head = "OPENED" if opened else "SKIPPED"
        body.append(text(cx + 46, card_top + 32, f"Container {tag} — {head}",
                         fill=c["ink"] if opened else c["muted"],
                         size=12.5, weight=600))

        hits = sum(1 for e in rows if e in sel[qid])
        body.append(text(cx + 16, card_top + 56,
                         f"index scan:  {hits} of {len(rows)} lines point here",
                         fill=c["muted"], size=10.5))

        ry = card_top + 74
        for event_id in rows:
            if opened:
                st = "needed" if event_id in sel[qid] else "wasted"
                note = "selected" if st == "needed" else "opened, not selected"
                note_fill = c["ink2"] if st == "needed" else c["wasted"]
            else:
                st, note, note_fill = "skipped", "not read", c["muted"]
            body.append(state_cell(cx + 16, ry + 6, st, c, w=15, h=15))
            body.append(text(cx + 40, ry + 18, event_id,
                             fill=c["ink2"] if opened else c["muted"], size=11))
            body.append(text(cx + card_w - 16, ry + 18, note,
                             fill=note_fill, size=10, anchor="end"))
            ry += 30

        body.append(rect(cx + 16, ry + 6, card_w - 32, 1, fill=c["grid"]))
        if opened:
            hit = sum(1 for e in rows if e in sel[qid])
            summary = (f'{con["size"]} read · {hit} selected · '
                       f'{con["size"] - hit} wasted')
            fill = c["wasted"]
        else:
            summary = "0 read · nothing in this container was selected"
            fill = c["muted"]
        body.append(text(cx + 16, ry + 28, summary, fill=fill, size=11, weight=600))
        heights.append(card_top + card_h)

    fy = max(heights) + 28
    body.append(text(margin, fy,
                     "Left: the container holds one selected event, so all of it is read — "
                     "the other two are pure waste.",
                     fill=c["ink2"], size=10.5))
    body.append(text(margin, fy + 17,
                     "Right: no index line points at this container, so it is never read "
                     "and costs nothing at all.",
                     fill=c["ink2"], size=10.5))

    return svg(width, fy + 32, "".join(body), c,
               "An activated container with wasted events, beside a bypassed container")


# --------------------------------------------------------------------------
# figure 3 — the anatomy of the served page
# --------------------------------------------------------------------------

#: Nav labels, section headings and pane contents, spelled as
#: simulator/gui/static/index.html spells them. A test holds the two in step.
NAV = [
    ("A", "Problem Statement"),
    ("B", "Data Skipping Experiment"),
    ("C", "Spark + Delta Lake Implementation"),
]

SECTIONS = [
    {
        "letter": "A",
        "heading": "Organizing a data warehouse like a closet",
        "note": "a document — nothing to configure",
        "left": ("The closet walkthrough",
                 ["one outfit and its wasted handling,",
                  "the same fetch with technical names,",
                  "one learned assignment change"]),
        "right": ("The formal statement",
                  ["problem-statement.md, pre-rendered",
                   "native MathML, with its own contents list"]),
    },
    {
        "letter": "B",
        "heading": "Assignment Strategy Benchmark",
        "note": "the interactive section — runs the harness",
        "left": ("Candidate builder",
                 ["up to four candidates, each a chain of",
                  "group-by expressions over the feature columns",
                  "plus the container capacities to sweep",
                  "one Evaluate button — all candidates at once"]),
        "right": ("Benchmark report", [
            ("P1", "process diagram — what was built"),
            ("P2", "summary table — what it scored"),
            ("P3", "paired scatter plots — how the scores trade off"),
        ]),
    },
    {
        "letter": "C",
        "heading": "Spark + Delta Lake Implementation",
        "note": "a document — nothing to configure",
        "left": ("The engine mapping",
                 ["production-design.md, pre-rendered",
                  "at Section A's parity"]),
        "right": ("The mechanisms drawn",
                  ["three diagrams: the file as container,",
                   "clustering as layout, statistics as index"]),
    },
]


def _pane(x, y, w, h, title, lines, c):
    """One pane of a section: a bordered box, a title, and what it holds."""
    out = [rect(x, y, w, h, fill="none", stroke=c["border"], rx=6)]
    out.append(text(x + 12, y + 21, title, fill=c["ink"], size=11, weight=600))
    ly = y + 40
    for line in lines:
        if isinstance(line, tuple):
            # A named view of the benchmark report — the label is a word, not a colour.
            key, label = line
            out.append(rect(x + 12, ly - 14, w - 24, 26, fill=c["chip"],
                            stroke=c["border"], rx=5))
            out.append(text(x + 22, ly + 3, key, fill=c["needed"], size=10.5,
                            weight=700, mono=True))
            out.append(text(x + 46, ly + 3, label, fill=c["ink2"], size=10))
            ly += 34
        else:
            out.append(text(x + 12, ly, line, fill=c["ink2"], size=10))
            ly += 16
    return "".join(out)


def figure_anatomy(theme):
    c = THEMES[theme]
    margin, frame_w, gap = 22, 836, 14
    pane_w = (frame_w - gap * 3) / 2
    width = margin * 2 + frame_w

    body = [
        text(margin, 28, "The demonstration page, section by section",
             fill=c["ink"], size=15, weight=600),
        text(margin, 48,
             "One local page on loopback — three sections in fixed order, one shown at a "
             "time, each a left and a right pane on a wide viewport",
             fill=c["ink2"], size=11),
    ]

    # the top bar
    top = 70
    bar_h = 34
    body.append(rect(margin, top, frame_w, bar_h, fill=c["chip"],
                     stroke=c["border"], rx=6))
    body.append(text(margin + 14, top + 22, "The Data Storage Layout Problem",
                     fill=c["ink"], size=11.5, weight=600))
    # The nav is set from the right edge inward, so a renamed section lengthens the group
    # leftward into the bar's empty middle instead of overrunning the frame.
    items = [(f"{letter} {label}", 16 + len(f"{letter} {label}") * 6.2)
             for letter, label in NAV]
    nx = margin + frame_w - 14 - (sum(w for _, w in items) + 8 * (len(items) - 1))
    for item, w in items:
        body.append(rect(nx, top + 7, w, 20, fill=c["surface"],
                         stroke=c["border"], rx=5))
        body.append(text(nx + w / 2, top + 21, item, fill=c["ink2"], size=10.5,
                         anchor="middle"))
        nx += w + 8

    # the three sections
    y = top + bar_h + 12
    for section in SECTIONS:
        right_title, right_lines = section["right"]
        left_lines = section["left"][1]
        if isinstance(right_lines[0], tuple):
            pane_h = 34 * len(right_lines) + 34
        else:
            pane_h = 40 + 16 * max(len(left_lines), len(right_lines)) + 16
        band_h = 36 + pane_h + 14

        body.append(rect(margin, y, frame_w, band_h, fill="none",
                         stroke=c["border"], rx=8))
        body.append(rect(margin + 14, y + 9, 20, 20, fill=c["chip"], rx=5))
        body.append(text(margin + 24, y + 23, section["letter"], fill=c["ink2"],
                         size=11, weight=700, anchor="middle", mono=True))
        body.append(text(margin + 42, y + 24, section["heading"], fill=c["ink"],
                         size=12.5, weight=600))
        body.append(text(margin + frame_w - 14, y + 24, section["note"],
                         fill=c["muted"], size=10, anchor="end"))

        py = y + 36
        left_title, left_lines = section["left"]
        body.append(_pane(margin + gap, py, pane_w, pane_h, left_title, left_lines, c))
        body.append(_pane(margin + gap * 2 + pane_w, py, pane_w, pane_h,
                          right_title, right_lines, c))
        y += band_h + 12

    body.append(text(margin, y + 12,
                     "Sections A and C are documents to read; B is the one that runs the "
                     "harness.",
                     fill=c["ink2"], size=10.5))
    body.append(text(margin, y + 29,
                     "Nothing is fetched from a network — every asset comes from the "
                     "local process, and an evaluation is kept nowhere.",
                     fill=c["muted"], size=10.5))

    return svg(width, y + 44, "".join(body), c,
               "The anatomy of the demonstration page: navigation, the three sections it "
               "selects between, and the panes each holds")


# --------------------------------------------------------------------------

def main():
    scenario = load()
    OUTDIR.mkdir(parents=True, exist_ok=True)

    for theme in THEMES:
        (OUTDIR / f"selection-matrix.{theme}.svg").write_text(
            figure_matrix(scenario, theme))
        (OUTDIR / f"container-zoom.{theme}.svg").write_text(
            figure_zoom(scenario, theme))
        (OUTDIR / f"page-anatomy.{theme}.svg").write_text(
            figure_anatomy(theme))

    print(f"wrote 6 figures to {OUTDIR.relative_to(ROOT)}/\n")
    for layout in scenario["layouts"]:
        ev = evaluate(scenario, layout)
        print(f'{layout["name"]:>10}: opened {ev["opened"]:>3} · '
              f'needed {ev["needed"]:>3} · wasted {ev["wasted"]:>3} · '
              f'{ev["amplification"]:.2f}x')
        for con in ev["containers"]:
            print(f'{"":>12}[{con["tag"]}] size {con["size"]} × breadth '
                  f'{con["breadth"]} = {con["opened"]:>2} opened, '
                  f'{con["wasted"]:>2} wasted')


if __name__ == "__main__":
    main()
