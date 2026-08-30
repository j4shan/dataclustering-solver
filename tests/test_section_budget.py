"""Drawing Storage Boundary — the storage-boundary feasibility illustration (12.9)."""

from __future__ import annotations

import re

import pytest

from simulator.gui import FIGURE_ROOT, STATIC_ROOT

FRAGMENT = STATIC_ROOT / "section-budget-walkthrough.html"
PLACEHOLDER = FIGURE_ROOT / "html" / "section-budget-illustration.html"
INDEX = STATIC_ROOT / "index.html"
ILLUSTRATION_HREF = "figures/html/section-budget-illustration.html"
FIGURE_IDS = (
    "E.storage-limits",
    "E.knapsack-ladder",
    "E.greedy-guardrails",
)
FIGURE_TITLES = (
    "The Container Assignment Problem",
    "Convert to Multiple-Choice Knapsack Problem (MCKP)",
    "Greedy Optimality relies on Decaying Marginal Efficiency",
)

HEADINGS = (
    "1. Working with Storage Container Limits",
    "2. Problem Generalization: Multiple-choice Knapsack",
    "3. Greedy Optimization",
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


def test_the_three_sections_are_complete_and_ordered(fragment):
    assert headings(fragment) == list(HEADINGS)
    stages = stage_bodies(fragment)
    assert len(stages) == 3
    for stage in stages:
        assert "<th>term</th>" in stage
    assert "<strong>Takeaway.</strong>" not in fragment
    assert "Takeaway" not in fragment


def test_the_walkthrough_is_text_only_and_opens_from_the_split_tree(fragment):
    assert not re.search(r"<figure|<svg|mermaid", fragment)
    body = compact(fragment)
    assert "data split trees" in body
    assert "high value potential" in body
    assert "Measuring Data Layout Fitness" in body
    assert "medicine-cabinet walkthrough" in body
    assert "observed query-level selection history" in body
    assert "production" not in fragment.lower()


def test_section_one_states_the_storage_limits_and_the_static_study(fragment):
    body = compact(stage_bodies(fragment)[0])
    assert "container-count ceiling" in body
    assert "container-size floor" in body
    assert "SSD" in body
    assert "S3" in body
    assert "multiple-choice knapsack" in body
    assert "may not transfer" in body
    assert "cost-versus-benefit" in body
    assert "Problem Statement" in body and "§2.5" in body
    assert "leaf benefit" in body
    assert "Poisson" in body
    assert "empty-unit" in body
    assert "Measuring Data Layout Fitness §3.1" in body


def test_section_two_maps_the_allocation_onto_a_geometric_knapsack(fragment):
    body = compact(stage_bodies(fragment)[1])
    assert "multiple-choice knapsack problem" in body
    assert "geometric series" in body
    assert "upgrade edge" in body
    assert "marginal efficiency" in body
    assert "predecessor-constrained" in body


def test_section_three_states_greedy_complexity_and_the_three_guardrails(fragment):
    stages = stage_bodies(fragment)
    body = compact(stages[2])
    assert "resource can be added one unit at a time" in body
    assert "every group's next marginal gain is no larger" in body
    assert "leaf benefits" in body
    assert "defined in §1" in body
    assert "does not guarantee the theorem" in body
    assert "O" in stages[2]
    assert "log" in stages[2]
    assert "starting count" in body
    assert "13.5" in body
    assert "size floor" in body
    assert "50%" in body
    assert "full table scan" in body
    assert "<!-- reserved:" not in stages[2]


def test_external_references_are_introduced_once(fragment):
    mckp = "https://en.wikipedia.org/wiki/List_of_knapsack_problems#Multiple-choice_knapsack_problem"
    poisson = "https://en.wikipedia.org/wiki/Poisson_distribution"
    theorem = "https://doi.org/10.1287/opre.34.6.909"
    assert fragment.count(mckp) == 1
    assert fragment.count(poisson) == 1
    assert fragment.count(theorem) == 1
    for url in (mckp, poisson, theorem):
        assert (
            f'href="{url}" target="_blank" rel="noopener noreferrer"' in fragment
        )


def test_the_left_pane_is_committed_html(fragment):
    """The GUI mounts this fragment; it is not generated from Markdown."""
    assert fragment.startswith('<article class="formulation">')
    assert 'class="toc"' not in fragment
    assert "<math" in fragment
    assert "$" not in re.sub(r"<[^>]+>", "", fragment)


def test_the_right_pane_is_three_accessible_titled_figures(placeholder):
    """All three rasters are accepted; no stage holds a placeholder."""
    assert placeholder.count("<figure") == 3
    assert placeholder.count("<figcaption>") == 3
    for fig_id, title in zip(FIGURE_IDS, FIGURE_TITLES, strict=True):
        assert f'id="{fig_id}"' in placeholder
        assert title in placeholder
    assert placeholder.count("<img") == 3
    assert 'src="figures/img/section_e_storage_limits.png"' in placeholder
    assert 'src="figures/img/section_e_knapsack_ladder.png"' in placeholder
    assert 'src="figures/img/section_e_greedy_guardrails.png"' in placeholder
    assert "Visualization placeholder" not in placeholder
    assert "<svg" not in placeholder
    assert "E.container-budget" not in placeholder


def test_the_storage_limits_figure_is_served_and_described(placeholder):
    """An accepted raster needs the file behind it and text beside it."""
    assert (FIGURE_ROOT / "img" / "section_e_storage_limits.png").is_file()
    figure = placeholder.split('id="E.storage-limits"')[1].split("</figure>")[0]
    alt = re.search(r'alt="([^"]+)"', figure)
    assert alt is not None and len(alt.group(1)) > 80
    assert "forthcoming" not in figure
    assert "K1 + K2 = 1,000" in figure


def test_the_greedy_guardrails_figure_is_served_and_described(placeholder):
    """An accepted raster needs the file behind it and text beside it."""
    assert (FIGURE_ROOT / "img" / "section_e_greedy_guardrails.png").is_file()
    figure = placeholder.split('id="E.greedy-guardrails"')[1].split("</figure>")[0]
    alt = re.search(r'alt="([^"]+)"', figure)
    assert alt is not None and len(alt.group(1)) > 80
    assert "forthcoming" not in figure
    assert "K = 11" in figure


def test_section_e_keeps_text_on_the_left_and_visualization_on_the_right():
    section = INDEX.read_text().split('id="knapsack"')[1]
    assert 'data-mount="section-budget-walkthrough.html"' in section
    assert f'data-mount="{ILLUSTRATION_HREF}"' in section
    assert section.index("pane-left") < section.index("pane-right")
    assert section.index("section-budget-walkthrough.html") < section.index(ILLUSTRATION_HREF)
    assert '<a href="section-budget-walkthrough.html">' in section
    assert f'<a href="{ILLUSTRATION_HREF}">' in section


def test_section_e_matches_section_d_type_and_fills_the_walkthrough_pane():
    from tests.test_app_shell import rule_for

    css = (STATIC_ROOT / "app.css").read_text()
    declarations = rule_for(css, "#knapsack .pane-left")
    for declaration in (
        "--text-body: 15px",
        "--text-small: 13px",
        "--text-heading: 19px",
        "--text-title: 24px",
    ):
        assert declaration in declarations
    assert "max-width: none" in rule_for(
        css, "#knapsack .pane-left > .formulation"
    )
