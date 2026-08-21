"""The report's three views (12.4.4 – 12.4.6).

Two kinds of check, and the split is deliberate.

**The document contract** is exercised against a real catalog build: the views draw
nothing they compute themselves (12.6.4), so what P1, P2 and P3 can show is entirely
decided by what the catalogue carries and what `reportFor` projects out of it. Those
tests assert against rows the runner actually produced and never recompute one (10.1.2).

**The drawing rules** are read out of the authored files, but only where a rule has no
behavioural expression — that P1 never *reaches* for a capacity, that the palette holds no
invented colour. A rule that shows up in the rendered tree is checked there instead: an
assertion on source text fails on a rename that changes nothing a requirement cares about,
and passes on a rewrite that breaks one.

Comments are stripped before matching, so a requirement quoted in a docstring never
satisfies a test on its own.
"""

from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess

import pytest

from simulator.gui import STATIC_ROOT

PROCESS = STATIC_ROOT / "view-process.js"
SUMMARY = STATIC_ROOT / "view-summary.js"
SCATTER = STATIC_ROOT / "view-scatter.js"
APP_CSS = STATIC_ROOT / "app.css"

#: Every KPI a metric row carries, none of which belongs in P1 (12.4.4.3).
KPIS = (
    "record_skip_ratio",
    "byte_skip_ratio",
    "waste_ratio",
    "baseline_lift",
    "management_cost",
    "materialized_records",
    "materialized_bytes",
    "container_count",
    "containers_below_target",
)


def stripped(path) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", path.read_text(), flags=re.DOTALL)


def code_only(source: str) -> str:
    """The source with its quoted strings removed as well as its comments.

    A caption is allowed to say "no capacity appears here" (12.4.3.4); what the rules
    below are about is what the code *reads*. Matching on the prose would make the
    caption fail the requirement it describes.
    """
    return re.sub(r"\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'", "", source)


@pytest.fixture(scope="module")
def process() -> str:
    return stripped(PROCESS)


@pytest.fixture(scope="module")
def summary() -> str:
    return stripped(SUMMARY)


@pytest.fixture(scope="module")
def scatter() -> str:
    return stripped(SCATTER)


@pytest.fixture(scope="module")
def css() -> str:
    return re.sub(r"/\*.*?\*/", "", APP_CSS.read_text(), flags=re.DOTALL)


@pytest.fixture(scope="module")
def catalog_document(tmp_path_factory):
    """One real catalog build: two candidates of different chain lengths (8.11).

    Deliberately ragged and deliberately off the baseline's own sweep, because those are
    the two cases the views have to survive — 12.4.4.5's uneven depths and 12.4.5.4's
    blank lift cell. The second capacity is one the baseline never sweeps, which is what
    leaves that cell blank.
    """
    from simulator.bench import catalog, metrics
    from simulator.core import dataset as dataset_module
    from simulator.providers import synthetic
    from simulator.providers.synthetic import DatasetConfig

    root = tmp_path_factory.mktemp("views")
    corpus = dataset_module.load(
        synthetic.generate(
            DatasetConfig(
                name="views-corpus",
                n_events=2_000,
                n_transaction_days=60,
                n_query_days=12,
                half_life_days=5.0,
                seed=90,
            ),
            root,
        )
    )
    definition = (
        catalog.Entry("as-1", "AS-1", ("brand_id",)),
        catalog.Entry("as-2", "AS-2", ("brand_id", "feature_price_tier > 5")),
    )
    original = metrics.DEFAULT_DIR
    metrics.DEFAULT_DIR = root / "metrics"
    try:
        return catalog.build(corpus, definition=definition, capacities=(250, 1000))
    finally:
        metrics.DEFAULT_DIR = original


#: The ids the rendered views are drawn for — every entry in the fixture document.
SELECTED = ("as-1", "as-2")


@pytest.fixture(scope="module")
def evaluated(rendered):
    """The document projected for a selection — what the three views actually take.

    Taken from the same node run that drew them, and produced by `reportFor` rather than
    by a Python restatement of it (10.1.2), so these tests assert against the shape the
    page really hands its views.
    """
    return rendered["report"]


# -- the order the reader meets them in (12.4.3.1) ------------------------------------


def test_the_three_views_mount_in_the_fixed_order():
    """12.4.3.1 — what was built, what it scored, how the scores trade off."""
    source = stripped(STATIC_ROOT / "section-b.js")
    assert "const VIEWS = [processView, summaryView, scatterView]" in source
    assert "for (const view of VIEWS) container.append(view(report))" in source


def test_the_pane_states_the_corpus_it_ran_against():
    """12.4.3.3 — from the response, so a stale report still names its own corpus."""
    source = stripped(STATIC_ROOT / "section-b.js")
    for field in ("report.dataset_id", "report.event_count", "report.query_count"):
        assert field in source, field


# -- P1, the process view (12.4.4) ----------------------------------------------------


def test_p1_shows_nothing_that_depends_on_capacity(process):
    """12.4.4.4 — one shape across the whole sweep, and bucketing is not a stage."""
    code = code_only(process).lower()
    assert "target_container_rows" not in code
    assert "capacit" not in code
    assert "bucket" not in code


def test_p1_carries_no_kpi(process):
    """12.4.4.3 — structure here, score in P2 and P3."""
    for kpi in KPIS:
        assert kpi not in process, kpi
    # It never even reaches for the metric rows, which is the structural form of the rule.
    assert "report.rows" not in process


def test_p1_draws_every_column_from_one_shared_root(process, css):
    """12.4.4.1 — side by side from one root is what makes two chains comparable."""
    assert "process-root" in process
    assert "repeat(var(--column-count, 1), minmax(0, 1fr))" in css
    # Each column drops its own connector out of the root bar, so the join is geometry.
    assert ".process-column::before" in css


def test_p1_labels_arrows_with_expressions_and_blocks_with_nothing(process):
    """12.4.4.2 and 13.16 — an arrow is a stage; a block carries no number.

    The absence is asserted, not merely unasserted: the count cost a second pass over the
    corpus to describe a layout the first pass had already built, and this is what stops
    it coming back.
    """
    assert "stage.expression" in process
    assert "arrow-label" in process
    assert "stage.subsets" not in process
    assert "block-count" not in process


def test_p1_columns_are_ragged(css):
    """12.4.4.5 — a shorter chain ends higher; the depth is information."""
    columns = css.split(".process-columns {")[1].split("}")[0]
    assert "align-items: start" in columns
    assert "grid-auto-rows" not in columns


def test_p1_never_reaches_for_the_baseline(process):
    """12.4.4.6 — its diagram is a root with no arrows, so it gets no column."""
    assert "baseline" not in code_only(process).lower()


# -- P2, the summary table (12.4.5) ---------------------------------------------------


def test_p2_is_one_row_per_candidate_and_capacity_capped_at_twenty(summary):
    """12.4.5.1 — sixteen candidate rows plus the baseline's four."""
    assert "const MAX_ROWS = 20" in summary
    assert ".slice(0, MAX_ROWS)" in summary
    assert "row.target_container_rows" in summary


def test_p2_groups_its_columns_and_labels_the_groups(summary):
    """12.4.5.2 — twenty rows of ungrouped numbers is a table nobody reads."""
    for group in ("Split", "Data skipping", "Metadata cost"):
        assert f'"{group}"' in summary, group
    assert 'cell.scope = "colgroup"' in summary


def test_p2_carries_the_container_count_and_no_stand_in_for_size_health(summary):
    """12.4.5.3, 13.14 — the count is required; the count below the floor is excluded.

    Under 12.4.1.4's packing the floor count is one per leaf, which P1 already prints,
    and the cost model's fragmentation term is the container count restated. A column
    that cannot separate the layouts it is read across is worse than no column.
    """
    split = summary.split("LAYOUT_COLUMNS")[1].split("PAIRED_COLUMNS")[0]
    assert "row.container_count" in split
    assert "containers_below_target" not in summary
    assert "management_cost_fragmentation_term" not in summary


def test_p2_pairs_the_two_query_sets_and_shows_no_third(summary):
    """12.4.3.2 — a number without its set name is a defect, and `all` is neither half."""
    assert '{ key: "training"' in summary
    assert '{ key: "validation"' in summary
    assert 'row.Set_Name !== "training" && row.Set_Name !== "validation"' in summary


def test_p2_gives_the_held_out_column_the_weight(css):
    """5.12.6 — and by weight, not by colour alone (12.6.2)."""
    block = css.split(".summary td.set-validation {")[1].split("}")[0]
    assert "font-weight" in block


# -- P3, the paired scatter plots (12.4.6) --------------------------------------------


def test_p3_plots_share_one_box_and_one_x_domain(scatter):
    """12.4.6.1 — a point's horizontal position means the same thing in both."""
    assert scatter.count("const GEOMETRY =") == 1
    # One domain, computed once over every point, then handed to both plots.
    assert "const xMax = niceMax(" in scatter
    assert "plotFor(plot, series, baseline, xMax)" in scatter


def test_p3_plots_container_count_against_the_two_activation_measures(scatter):
    """12.4.6.1 — X is container count; Y is record count, then byte weight."""
    assert 'key: "materialized_records"' in scatter
    assert 'key: "materialized_bytes"' in scatter
    assert "x: row.container_count" in scatter
    assert scatter.index('key: "materialized_records"') < scatter.index(
        'key: "materialized_bytes"'
    )


def test_p3_names_the_query_set_it_drew(scatter):
    """12.4.3.2 — 12.4.6 does not choose the set, so the choice is stated."""
    assert 'const SET = "validation"' in scatter
    assert 'row.Set_Name === SET' in scatter
    assert "held out" in scatter.lower()


def test_p3_connects_a_series_in_capacity_order(scatter):
    """12.4.6.3 — the line is the trade the sweep traces, not a fit."""
    assert ".sort((a, b) => a.capacity - b.capacity)" in scatter
    assert 'svg("polyline"' in scatter


def test_p3_direct_labels_every_point(scatter):
    """12.4.6.4 — nothing is reachable only by pointing at it."""
    assert "point-label" in scatter
    assert "count(point.capacity)" in scatter


def test_p3_draws_the_baseline_as_a_grey_dashed_line_with_no_legend_entry(scatter, css):
    """12.4.6.5 — the reference the candidates are read against, not a fifth candidate."""
    assert "if (series.length) figure.append(legend(figure, series))" in scatter
    assert "function legend(figure, series)" in scatter
    line = css.split(".plot .baseline-line {")[1].split("}")[0]
    assert "var(--series-baseline)" in line
    assert "stroke-dasharray" in line


def test_p3_distinguishes_a_series_by_shape_as_well_as_colour(scatter, css):
    """12.4.6.8, 12.6.2 — colour is never the only difference."""
    shapes = re.search(r"const SHAPES = \[(.*?)\]", scatter, re.DOTALL).group(1)
    assert len(set(re.findall(r'"(\w+)"', shapes))) == 4
    for index in (1, 2, 3, 4):
        assert f".plot .series-{index} {{ --mark: var(--series-{index}); }}" in css


def test_p3_takes_the_report_palette_and_not_the_ui_accent(css):
    """12.4.6.8 — series colours are 9.4's validated set, not 12.7.1.6's chrome."""
    plots = css.split(".plot-pair {")[1]
    assert "var(--chrome)" not in plots
    assert "var(--accent)" not in plots
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", plots), "no colour is invented here"


def test_p3_highlight_is_series_level_and_mirrored_across_both_plots(scatter):
    """12.4.6.6 — one gesture, both plots, because the figure holds both."""
    assert "figure.querySelectorAll(\"[data-series]\")" in scatter
    assert 'classList.toggle("dimmed"' in scatter


def test_p3_highlight_adds_emphasis_and_never_information(css):
    """12.4.6.7 — everything a reader needs is already drawn."""
    dimmed = css.split(".legend-entry.dimmed {")[1].split("}")[0]
    assert dimmed.strip() == "opacity: 0.25;"


def test_p3_legend_is_the_control_and_hover_is_its_mirror(scatter):
    """12.4.6.6, 13.7 — focusable and keyboard-operable, with hover as the mirror."""
    assert 'node("button", `legend-entry' in scatter
    assert 'button.setAttribute("aria-pressed", "false")' in scatter
    for gesture in ("click", "focus", "blur", "mouseenter", "mouseleave"):
        assert f'addEventListener("{gesture}"' in scatter, gesture


# -- the contract the views are drawn from --------------------------------------------


def test_the_response_carries_everything_the_three_views_draw(evaluated):
    """12.6.4 — the views assert no number, so the response must hold every one."""
    assert evaluated["process"], "P1 needs one entry per configured block"
    for entry in evaluated["process"]:
        assert entry["block"]
        for stage in entry["stages"]:
            assert isinstance(stage["expression"], str)
            # The split count rides along for the catalogue panel (12.4.2.1); that P1
            # does not *draw* it is 13.16, and is checked where P1 is drawn.
            assert set(stage) == {"expression", "splits"}

    for row in evaluated["rows"]:
        for field in KPIS:
            if field == "baseline_lift":
                continue
            assert field in row, field
        assert "baseline_lift" in row


def test_the_process_payload_never_carries_the_baseline(evaluated):
    """12.4.4.6 — P1 cannot draw a baseline column because it is never sent one."""
    blocks = {entry["block"] for entry in evaluated["process"]}
    assert evaluated["baseline"] not in blocks


def test_both_halves_come_back_for_every_configuration(evaluated):
    """12.4.3.2 — P2's paired columns need both, for every row it will draw."""
    by_configuration = {}
    for row in evaluated["rows"]:
        key = (row["Block"], row["Strategy_Name"], row["target_container_rows"])
        by_configuration.setdefault(key, set()).add(row["Set_Name"])
    assert by_configuration
    for key, sets in by_configuration.items():
        assert {"training", "validation"} <= sets, key


# -- the views, executed (12.4.4 – 12.4.6) --------------------------------------------
#
# Everything above reads the source.  Everything below *runs* it, against a real batch,
# in node with a minimal DOM.  Node is not a runtime dependency, so these skip cleanly
# when it is absent — the rule 12.6.3.1 sets for browser checks, one level down.

RENDERER = pathlib.Path(__file__).parent / "js" / "render-views.mjs"

needs_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="node is not installed; the views run in a browser"
)


def render(document, selected, scratch):
    """Project a catalog document and draw the three views, in one node run.

    The projection is `reportFor` and the drawing is the three view modules — the page's
    own, imported rather than restated (10.1.2) — so what comes back is what a reader
    selecting those entries would be looking at.
    """
    payload = scratch / "catalog.json"
    payload.write_text(json.dumps(document))
    finished = subprocess.run(
        ["node", str(RENDERER), str(STATIC_ROOT), str(payload), ",".join(selected)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(finished.stdout)


@pytest.fixture(scope="module")
def rendered(catalog_document, tmp_path_factory):
    """The three views as element trees, drawn from one real catalog document."""
    if shutil.which("node") is None:
        pytest.skip("node is not installed")
    return render(catalog_document, SELECTED, tmp_path_factory.mktemp("render"))


def walk(tree):
    yield tree
    for child in tree["children"]:
        yield from walk(child)


def classes(node_) -> str:
    """An HTML element carries its class as a property; an SVG one as an attribute."""
    return node_.get("class") or node_["attrs"].get("class", "")


def having(tree, name):
    return [n for n in walk(tree) if name in classes(n).split()]


@needs_node
def test_p1_draws_one_column_per_candidate(rendered, evaluated):
    """12.4.4.1 — every configured A.S. gets a column, and only those."""
    columns = having(rendered["p1"], "process-column")
    assert len(columns) == len(evaluated["process"])
    labels = [n["text"] for n in having(rendered["p1"], "process-column-label")]
    assert labels == [entry["block"] for entry in evaluated["process"]]


@needs_node
def test_p1_columns_end_at_their_own_depth(rendered, evaluated):
    """12.4.4.5 — a one-stage chain is not padded down to a two-stage one."""
    depths = [len(having(column, "process-stage")) for column in having(rendered["p1"], "process-column")]
    assert depths == [len(entry["stages"]) for entry in evaluated["process"]]
    assert len(set(depths)) > 1, "the fixture is meant to be ragged"


@needs_node
def test_p1_labels_each_stage_with_its_expression(rendered, evaluated):
    """12.4.4.2 — an arrow carries the expression, in the engine's own spelling."""
    expected = [stage for entry in evaluated["process"] for stage in entry["stages"]]
    assert [n["text"] for n in having(rendered["p1"], "arrow-label")] == [
        stage["expression"] for stage in expected
    ]
    assert having(rendered["p1"], "block-count") == []


@needs_node
def test_p1_names_no_capacity_anywhere_it_is_drawn(rendered, evaluated):
    """12.4.4.4 — the sweep is not in this picture, not even as a number."""
    drawn = rendered["p1"]["text"]
    for row in evaluated["rows"]:
        if row["Block"]:
            assert f"{row['target_container_rows']:,}" not in drawn


@needs_node
def test_p2_draws_one_row_per_configuration_with_the_baseline_first(rendered, evaluated):
    """12.4.5.1 — the baseline's sweep on top, then every candidate row."""
    body = [n for n in walk(rendered["p2"]) if n["tag"] == "tr" and "row-" in classes(n)]
    configurations = {
        (row["Block"], row["target_container_rows"]) for row in evaluated["rows"]
    }
    assert len(body) == len(configurations)
    assert len(body) <= 20

    kinds = [classes(row) for row in body]
    assert kinds.count("row-baseline") == len(evaluated["baseline_capacities"])
    assert kinds[: kinds.count("row-baseline")] == ["row-baseline"] * kinds.count("row-baseline")


@needs_node
def test_p2_leaves_an_undefined_lift_blank_and_fills_the_rest(catalog_document, tmp_path_factory):
    """12.4.5.4 — blank where there is no comparable baseline, never a substitute.

    The shipped generator sweeps every candidate at the baseline's own capacities, so a
    catalogue it builds cannot produce this cell. It stays reachable for the other reason
    `add_baseline_lift` returns nothing — a baseline that wasted nothing, where the ratio
    is undefined rather than infinite — and P2 must render both the same way. The document
    is edited here rather than generated, because what is under test is the view's rule
    and not the generator's arithmetic.
    """
    if shutil.which("node") is None:
        pytest.skip("node is not installed")
    document = json.loads(json.dumps(catalog_document))
    blanked = 0
    for row in document["rows"]:
        if row["Block"] == "as-2" and row["target_container_rows"] == 250:
            row["baseline_lift"] = None
            blanked += 1
    assert blanked, "the fixture must contain the rows this test blanks"

    trees = render(document, SELECTED, tmp_path_factory.mktemp("blank"))
    blanks = having(trees["p2"], "blank")
    off_sweep = [
        row
        for row in trees["report"]["rows"]
        if row["Set_Name"] in ("training", "validation") and row["baseline_lift"] is None
    ]
    # P2 pairs the training and validation columns and draws no `all` column, so the
    # blank cells are one per set-dependent row rather than one per row the fixture
    # touched — which is why the count is taken from the projection, not from the edit.
    assert off_sweep, "the edit above must reach rows P2 actually draws"
    assert len(blanks) == len(off_sweep)
    for cell in blanks:
        assert cell["text"].strip() == "no comparable baseline at this capacity"
        assert having(cell, "sr-only"), "the explanation is for a screen reader, not the table"


@needs_node
def test_p2_pairs_every_set_dependent_column(rendered):
    """12.4.3.2 — four paired metrics, so eight set-labelled sub-columns."""
    sets = [n["text"] for n in having(rendered["p2"], "set")]
    assert sets == ["Train", "Held out"] * 4


@needs_node
def test_p3_is_two_plots_sharing_a_box_and_an_x_domain(rendered):
    """12.4.6.1 — the same container count sits at the same horizontal position."""
    plots = having(rendered["p3"], "plot")
    assert len(plots) == 2
    assert len({plot["attrs"]["viewBox"] for plot in plots}) == 1

    # The first `TICKS + 1` ticks of each plot are its X axis, drawn before the Y axis.
    x_ticks = [[n["text"] for n in having(plot, "tick")][:5] for plot in plots]
    assert x_ticks[0] == x_ticks[1]


@needs_node
def test_p3_plots_the_two_activation_measures_against_container_count(rendered):
    """12.4.6.1 — record count on the left, byte weight on the right."""
    titles = [n["text"] for n in having(rendered["p3"], "axis-title")]
    assert titles == [
        "Total containers",
        "Activated record count (held out)",
        "Total containers",
        "Activated record byte weight (held out)",
    ]


@needs_node
def test_p3_direct_labels_every_point_in_both_plots(rendered, evaluated):
    """12.4.6.4 — a reader never has to hover to learn which point is which."""
    held_out = [row for row in evaluated["rows"] if row["Set_Name"] == "validation"]
    labels = having(rendered["p3"], "point-label")
    assert len(labels) == 2 * len(held_out)
    assert {label["text"] for label in labels} == {
        f"{row['target_container_rows']:,}" for row in held_out
    }


@needs_node
def test_p3_gives_the_baseline_a_dashed_line_and_no_legend_entry(rendered, evaluated):
    """12.4.6.5 — the reference the candidates are read against, not a fifth candidate."""
    assert len(having(rendered["p3"], "baseline-line")) == 2
    entries = [n["text"] for n in having(rendered["p3"], "legend-entry")]
    assert evaluated["baseline"] not in entries
    assert entries == [entry["block"] for entry in evaluated["process"]]


@needs_node
def test_p3_marks_differ_in_shape_between_series(rendered):
    """12.4.6.8, 12.6.2 — colour is never the only difference."""
    shapes = {}
    for group in [n for n in walk(rendered["p3"]) if n["attrs"].get("data-series")]:
        for mark in having(group, "mark"):
            shapes.setdefault(group["attrs"]["data-series"], set()).add(mark["tag"])
    assert len(shapes) > 1
    assert len({frozenset(tags) for tags in shapes.values()}) == len(shapes)


@needs_node
def test_p3_highlighting_one_series_mirrors_across_both_plots(rendered, evaluated):
    """12.4.6.6 — one gesture, both plots, and the legend is the control."""
    highlighted = evaluated["process"][0]["block"]
    groups = [
        n for n in walk(rendered["p3_highlighted"]) if n["attrs"].get("data-series")
    ]
    # Two plot series plus one legend entry per candidate.
    assert len(groups) == 3 * len(evaluated["process"])
    for group in groups:
        dimmed = "dimmed" in classes(group).split()
        assert dimmed == (group["attrs"]["data-series"] != highlighted), group["attrs"]


@needs_node
def test_p3_highlighting_adds_no_node_and_removes_none(rendered):
    """12.4.6.7 — emphasis, never information: the tree is the same tree."""

    def shape(tree):
        return (tree["tag"], tree["text"], [shape(child) for child in tree["children"]])

    assert shape(rendered["p3"]) == shape(rendered["p3_highlighted"])
