"""Go Live on Databricks Lakehouse — the seven-step process (12.5)."""

from __future__ import annotations

import re

import pytest

from conftest import RESOURCES
from simulator.gui import FIGURE_ROOT, SITE_ROOT

FRAGMENT = SITE_ROOT / "section-databricks-walkthrough.html"
PLACEHOLDER = FIGURE_ROOT / "html" / "section-databricks-illustration.html"
INDEX = SITE_ROOT / "index.html"
ILLUSTRATION_HREF = "figures/html/section-databricks-illustration.html"
FIGURE_IDS = (
    "databricks.layout-planning",
    "databricks.ingestion",
    "databricks.query",
)
FIGURE_TITLES = (
    "Deployment Process Flow",
    "Ingestion Time Integration",
    "Query Time Integration",
)
FIGURE_FILES = (
    "section_databricks_layout_planning",
    "section_databricks_ingestion",
    "section_databricks_query",
)
HEADINGS = (
    "1. Collect query usage statistics",
    "2. Optimize split decision trees",
    "3. Optimistic knapsack simulation",
    "4. Experiment simplified assignment on holdout",
    "5. Deploy container assignment during Ingestion",
    "6. Activate data skipping optimization",
    "7. Hybrid table architecture and continuous consolidation",
)


@pytest.fixture(scope="module")
def fragment() -> str:
    return FRAGMENT.read_text()


@pytest.fixture(scope="module")
def placeholder() -> str:
    return PLACEHOLDER.read_text()


def compact(text: str) -> str:
    return " ".join(text.split())


def headings(fragment: str) -> list[str]:
    return re.findall(r"<h2[^>]*>([^<]+)</h2>", fragment)


def stage_bodies(fragment: str) -> list[str]:
    return re.split(r"<h2[^>]*>", fragment)[1:]


def test_the_seven_sections_are_complete_and_ordered(fragment):
    assert headings(fragment) == list(HEADINGS)
    assert len(stage_bodies(fragment)) == 7
    assert "<strong>Takeaway.</strong>" not in fragment
    assert "Takeaway" not in fragment
    assert "Concluding insights" not in fragment
    assert "process concept" not in fragment


def test_the_walkthrough_is_text_only_and_opens_from_container_assignment(fragment):
    assert not re.search(r"<figure|<svg|mermaid", fragment)
    opening = fragment.split("<h2", 1)[0]
    body = compact(opening)
    assert "container assignment" in body
    assert "production data lake" in body
    assert "Databricks" in body
    assert "Problem Statement" in body
    assert "Measuring Data Layout Fitness" in body
    assert "Drawing Storage Boundary" in body
    assert "Lakehouse write path" in body
    assert "Spark read path" in body
    assert "Deployment Process Flow" in body


def test_section_one_builds_a_usage_statistics_table(fragment):
    body = compact(stage_bodies(fragment)[0])
    assert "usage_summary" in body
    assert "usage-statistics table" in body
    assert "boolean" in body
    assert "minute" in body
    assert "hour" in body
    assert "date" in body
    assert "benchmark harness" in body
    assert "usage statistics collector" in body
    assert "fetch query statistics" not in body
    assert "cost saving" not in body


def test_section_two_optimizes_trees_under_a_bound(fragment):
    body = compact(stage_bodies(fragment)[1])
    assert "Measuring Data Layout Fitness" in body
    assert "training" in body
    assert "resource monitor" in body
    assert "complexity bound" in body
    assert "beam" in body
    assert "partition limit" in body
    assert "heuristics" in body
    assert "unqualified split conditions" in body
    assert "greedy" not in body
    assert "Business insight" not in body
    assert "introduced" not in body


def test_section_three_runs_optimistic_mckp(fragment):
    body = compact(stage_bodies(fragment)[2])
    assert "Multiple-Choice Knapsack Problem" in body
    assert "Drawing Storage Boundary" in body
    assert "partition limit" in body
    assert "one container per leaf" in body
    assert "piecemeal" in body
    assert "skipping ratio" in body
    assert "marginal efficiency" in body
    assert "log container-count" in body
    assert "ingestion-time" in body
    assert "usage frequency" in body
    assert "Figure 1" in body
    assert (
        'href="https://en.wikipedia.org/wiki/List_of_knapsack_problems#Multiple-choice_knapsack_problem"'
        in stage_bodies(fragment)[2]
    )


def test_section_four_experiments_equal_size_on_holdout(fragment):
    body = compact(stage_bodies(fragment)[3])
    assert "holdout" in body
    assert "MCKP" in body
    assert "equal-size" in body
    assert "compressed record size" in body
    assert "8 MB" in body
    assert "weighted-average data skipping ratio" in body
    assert "gate" in body
    assert "freezes" in body
    assert "returns to search" in body
    assert "fixed-capacity" not in body


def test_section_five_deploys_ingestion(fragment):
    body = compact(stage_bodies(fragment)[4])
    assert "split decision" in body
    assert "grouping or a predicate" in body
    assert "partition_id" in body
    assert "narrow" in body
    assert "wide" in body
    assert "group-by" in body
    assert "xxhash64" in body
    assert "pmod" in body
    assert "s_1" in body
    assert "floor(V / T)" in body
    assert "Ingestion Time Integration" in body
    assert "streaming_sink" in body
    assert "Auto Loader" in body
    assert "CRON" in body
    assert "write-ahead log" in body
    assert "partitioned_sink" in body
    assert "small files" in body
    assert "Stateful container assignment" not in body
    assert "process concept" not in body


def test_section_six_activates_dpp(fragment):
    body = compact(stage_bodies(fragment)[5])
    assert "Container-skipping" in body
    assert "Dynamic Partition Pruning" in body
    assert "partition_id" in body
    assert "Query Time Integration" in body
    assert "metadata filter" in body
    assert "usage_summary" in body
    assert "partitioned_sink" in body
    assert "256 GB" in body
    assert "256 MB" in body
    assert "Spark config: autoBroadcastJoinThreshold" in body
    assert (
        'href="https://spark.apache.org/docs/latest/sql-performance-tuning.html"'
        in stage_bodies(fragment)[5]
    )
    assert "#dynamic-partition-pruning" not in fragment
    assert "process concept" not in body


def test_section_seven_consolidates_and_tiers_ingest(fragment):
    body = compact(stage_bodies(fragment)[6])
    assert "OPTIMIZE" in body
    assert "Z-order" in body
    assert "one file" in body
    assert "disjoint" in body
    assert "streaming_sink" in body
    assert "partitioned_sink" in body
    assert "optimizer" in body
    assert "tree-split" in body
    assert "unoptimized" in body
    assert "schema" in body
    assert "Complementary layouts" in body


def test_the_left_pane_is_committed_html(fragment):
    assert fragment.lstrip().startswith('<article class="formulation">')
    assert 'class="toc"' not in fragment


def test_the_right_pane_is_three_accessible_titled_figures(placeholder):
    assert placeholder.count("<figure") == 3
    assert placeholder.count("<figcaption>") == 3
    for fig_id, title, name in zip(FIGURE_IDS, FIGURE_TITLES, FIGURE_FILES, strict=True):
        assert f'id="{fig_id}"' in placeholder
        assert title in placeholder
        figure = placeholder.split(f'id="{fig_id}"')[1].split("</figure>")[0]
        assert "raster-illustration" in placeholder.split(f'id="{fig_id}"')[0][-200:]
        assert 'class="illustration-stage"' in figure
        assert "is-empty" not in figure
        assert f'src="figures/img/{name}.png"' in figure
        alt = figure.split('alt="')[1].split('"')[0]
        assert len(alt) > 200, f"{name}: the alt text has to describe the drawing"
        assert (FIGURE_ROOT / "img" / f"{name}.png").exists()
        assert (RESOURCES / "img_src" / f"{name}.drawio").exists()
        assert (RESOURCES / "img_prompt" / f"{name}_prompt.md").exists()
    assert placeholder.count("<img") == 3
    assert "section_c_go_live_process" not in placeholder
    assert "section_c_data_ingestion" not in placeholder
    assert "section_c_dpp_skipping" not in placeholder
    assert "section_c_partition_assignment" not in placeholder
    assert "<svg" not in placeholder


def test_no_figure_repeats_the_title_the_pane_already_prints():
    """The h3 above the stage carries the title; the drawing never draws it."""
    for name, title in zip(FIGURE_FILES, FIGURE_TITLES, strict=True):
        source = (RESOURCES / "img_src" / f"{name}.drawio").read_text()
        assert title not in source
        assert 'spec_id="title"' not in source


def test_the_obsolete_section_c_rasters_are_gone():
    for name in (
        "section_c_go_live_process.png",
        "section_c_data_ingestion.png",
        "section_c_dpp_skipping.png",
    ):
        assert not (FIGURE_ROOT / "img" / name).exists()


def test_section_databricks_keeps_text_on_the_left_and_figures_on_the_right():
    section = INDEX.read_text().split('id="design"')[1].split('id="signal"')[0]
    assert 'data-mount="section-databricks-walkthrough.html"' in section
    assert f'data-mount="{ILLUSTRATION_HREF}"' in section
    assert section.index("pane-left") < section.index("pane-right")
    assert section.index("section-databricks-walkthrough.html") < section.index(
        ILLUSTRATION_HREF
    )


def test_section_databricks_matches_section_gini_type_and_fills_the_walkthrough_pane():
    from tests.test_app_shell import rule_for

    css = (SITE_ROOT / "app.css").read_text()
    declarations = rule_for(css, "#design .pane-left")
    for declaration in (
        "--text-body: 15px",
        "--text-small: 13px",
        "--text-heading: 19px",
        "--text-title: 24px",
    ):
        assert declaration in declarations
    assert "max-width: none" in rule_for(
        css, "#design .pane-left > .formulation"
    )
