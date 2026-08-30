"""Go Live on Databricks Lakehouse — the six-step process (12.5)."""

from __future__ import annotations

import re

import pytest

from simulator.gui import FIGURE_ROOT, STATIC_ROOT

FRAGMENT = STATIC_ROOT / "section-databricks-walkthrough.html"
PLACEHOLDER = FIGURE_ROOT / "html" / "section-databricks-illustration.html"
INDEX = STATIC_ROOT / "index.html"
ILLUSTRATION_HREF = "figures/html/section-databricks-illustration.html"
FIGURE_IDS = (
    "C.process-flow",
    "C.data-ingestion",
    "C.dpp-skipping",
)
FIGURE_TITLES = (
    "The go-live process",
    "Ingestion writes two tables",
    "Spark DPP skips from the index",
)
HEADINGS = (
    "1. Collect a target sample",
    "2. Identify split decision trees",
    "3. Estimate leaf skipping potential",
    "4. Inspect the holdout",
    "5. Implement data ingestion",
    "6. Implement query optimization",
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


def test_the_six_sections_are_complete_and_ordered(fragment):
    assert headings(fragment) == list(HEADINGS)
    assert len(stage_bodies(fragment)) == 6
    assert "<strong>Takeaway.</strong>" not in fragment
    assert "Takeaway" not in fragment


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
    assert "The go-live process" in body


def test_section_one_screens_a_sample(fragment):
    body = compact(stage_bodies(fragment)[0])
    assert "fetch query statistics" in body
    assert "data skipping" in body
    assert "cost saving" in body
    assert "benchmark harness" in body


def test_section_two_grows_trees_from_training(fragment):
    body = compact(stage_bodies(fragment)[1])
    assert "Measuring Data Layout Fitness" in body
    assert "training" in body
    assert "greedy" in body
    assert "Business insight" in body


def test_section_three_applies_mckp_to_leaves(fragment):
    body = compact(stage_bodies(fragment)[2])
    assert "Multiple-Choice Knapsack Problem" in body
    assert "Drawing Storage Boundary" in body
    assert "leaf" in body
    assert (
        'href="https://en.wikipedia.org/wiki/List_of_knapsack_problems#Multiple-choice_knapsack_problem"'
        in stage_bodies(fragment)[2]
    )


def test_section_four_inspects_the_holdout(fragment):
    body = compact(stage_bodies(fragment)[3])
    assert "holdout" in body
    assert "MCKP" in body
    assert "fixed-capacity" in body
    assert "weighted-average data skipping ratio" in body


def test_section_five_maps_ingestion(fragment):
    body = compact(stage_bodies(fragment)[4])
    assert "split decision" in body
    assert "grouping or a predicate" in body
    assert "partition_id" in body
    assert "narrow" in body
    assert "wide" in body
    assert "xxhash64" in body
    assert "pmod" in body
    assert "s_1" in body
    assert "floor(V / T)" in body
    assert "Ingestion writes two tables" in body
    assert "Stateful container assignment" not in body


def test_section_six_maps_query_optimization(fragment):
    body = compact(stage_bodies(fragment)[5])
    assert "container-skipping" in body
    assert "Dynamic Partition Pruning" in body
    assert "partition_id" in body
    assert "Spark DPP skips from the index" in body
    assert "metadata filter" in body
    assert fragment.count(
        "https://spark.apache.org/docs/latest/sql-performance-tuning.html#dynamic-partition-pruning"
    ) == 1


def test_the_left_pane_is_committed_html(fragment):
    assert fragment.lstrip().startswith('<article class="formulation">')
    assert 'class="toc"' not in fragment


def test_the_right_pane_is_four_accessible_titled_figures(placeholder):
    assert placeholder.count("<figure") == 3
    assert placeholder.count("<figcaption>") == 3
    for fig_id, title in zip(FIGURE_IDS, FIGURE_TITLES, strict=True):
        assert f'id="{fig_id}"' in placeholder
        assert title in placeholder
    assert placeholder.count("<img") == 3
    assert 'src="figures/img/section_c_go_live_process.png"' in placeholder
    assert 'src="figures/img/section_c_data_ingestion.png"' in placeholder
    assert 'src="figures/img/section_c_dpp_skipping.png"' in placeholder
    assert "section_c_partition_assignment" not in placeholder
    assert "<svg" not in placeholder


def test_the_four_rasters_are_served_and_described(placeholder):
    names = (
        "section_c_go_live_process.png",
        "section_c_data_ingestion.png",
        "section_c_dpp_skipping.png",
    )
    for name, fig_id in zip(names, FIGURE_IDS, strict=True):
        assert (FIGURE_ROOT / "img" / name).is_file()
        figure = placeholder.split(f'id="{fig_id}"')[1].split("</figure>")[0]
        alt = re.search(r'alt="([^"]+)"', figure)
        assert alt is not None and len(alt.group(1)) > 80


def test_section_c_keeps_text_on_the_left_and_figures_on_the_right():
    section = INDEX.read_text().split('id="design"')[1]
    assert 'data-mount="section-databricks-walkthrough.html"' in section
    assert f'data-mount="{ILLUSTRATION_HREF}"' in section
    assert section.index("pane-left") < section.index("pane-right")
    assert section.index("section-databricks-walkthrough.html") < section.index(
        ILLUSTRATION_HREF
    )
    assert '<a href="section-databricks-walkthrough.html">' in section
    assert f'<a href="{ILLUSTRATION_HREF}">' in section


def test_section_c_matches_section_d_type_and_fills_the_walkthrough_pane():
    from tests.test_app_shell import rule_for

    css = (STATIC_ROOT / "app.css").read_text()
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
