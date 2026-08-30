"""Measuring Data Layout Fitness — split-search illustration (12.8).

The left pane is a committed HTML walkthrough. The right column opens with a
terminology dictionary and continues with the split-cycle APNG plus one
continued Gini example. Nothing here is a recommendation (1.2) and
nothing here computes a Gini in the GUI (12.8).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

import pytest

from simulator.gui import FIGURE_ROOT, STATIC_ROOT

FRAGMENT = STATIC_ROOT / "section-gini-walkthrough.html"
GLOSSARY = STATIC_ROOT / "section-gini-glossary.html"
DIAGRAMS = FIGURE_ROOT / "html" / "section-gini-illustration.html"
ILLUSTRATION_HREF = "figures/html/section-gini-illustration.html"
INDEX = STATIC_ROOT / "index.html"

FIGURE_IDS = (
    "D.tree-split-cycle",
    "D.lorenz-wealth",
    "D.split-comparison",
    "D.selective-tree",
)
FIGURE_TITLES = {
    "D.tree-split-cycle": "Recursive Partitioning with a Decision Tree",
    "D.lorenz-wealth": "Comparing Inequality with Lorenz Curves",
    "D.split-comparison": "Evaluating Weighted Gini Across Data Splits",
    "D.selective-tree": "Growing a Selective Tree from a Brand Split",
}

LORENZ_FORBIDDEN = (
    "warehouse",
    "container",
    "record",
    "query",
    "index",
    "materialized",
    "selected",
    "layout",
    "assignment",
    "strategy",
    "skip",
)

GLOSSARY_TERMS = (
    "Grouping",
    "Leaf",
    "Cut",
    "fitness(leaf)",
    "OPT(leaf)",
    "Container size",
    "Evaluation budget",
    "Unit",
    "Population weight",
    "Group-wide rate",
    "Query-conditional rate",
    "Poisson parameter",
    "Group-wide skip ratio",
    "Query-conditional skip ratio",
    "Weighted Gini",
    "Extra groups",
    "Incremental gain",
)

HEADINGS_H2 = (
    "1. Explore Data Split Trees",
    "2. Practical Consideration",
    "3. Choosing a Value function to Optimize",
)
HEADINGS_H3 = (
    "3.1 Group-wide skipping ratio",
    "3.2 Query-conditional skipping ratio",
    "3.3 Weighted Gini",
)


def weighted_gini(groups: list[tuple[int, int]]) -> Fraction:
    """Population-weighted Gini from (n_g, U_g) pairs — test arithmetic, not GUI code."""
    n_total = sum(n for n, _ in groups)
    u_total = sum(u for _, u in groups)
    rows = sorted(
        ((Fraction(u, n) if n else Fraction(0), n, u) for n, u in groups if n),
        key=lambda row: row[0],
    )
    cum_q = Fraction(0)
    acc = Fraction(0)
    for _density, n, u in rows:
        p = Fraction(n, n_total)
        q = Fraction(u, u_total)
        cum_q += q
        acc += p * (2 * cum_q - q)
    return 1 - acc


def headings(fragment: str) -> list[str]:
    return re.findall(r"<h2[^>]*>([^<]+)</h2>", fragment)


def h3_headings(fragment: str) -> list[str]:
    return re.findall(r"<h3[^>]*>([^<]+)</h3>", fragment)


def stage_bodies(fragment: str) -> list[str]:
    return re.split(r"<h2[^>]*>", fragment)[1:]


def h3_bodies(fragment: str) -> list[str]:
    return re.split(r"<h3[^>]*>", fragment)[1:]


def figure_ids(markup: str) -> list[str]:
    return re.findall(r'<figure[^>]*\bid="([^"]+)"', markup)


@pytest.fixture(scope="module")
def fragment() -> str:
    return FRAGMENT.read_text()


@pytest.fixture(scope="module")
def diagrams() -> str:
    return DIAGRAMS.read_text()


def test_the_auto_parts_gini_per_group_matches_the_drawn_counts():
    """G/k on the warehouse beats is G divided by the drawn group count."""
    category = [(14, 15), (13, 14), (11, 12), (10, 10), (7, 7), (45, 42)]
    brand = [(8, 22), (7, 18), (7, 8), (6, 14), (6, 5), (66, 33)]
    tree = [(2, 12), (6, 10), (2, 12), (5, 6), (7, 8), (6, 14), (6, 5), (66, 33)]
    assert round(float(weighted_gini(category)), 2) == 0.04
    assert round(float(weighted_gini(brand)), 2) == 0.38
    assert round(float(weighted_gini(tree)), 2) == 0.41
    assert len(category) == 6 and round(0.04 / 6, 3) == 0.007
    assert len(brand) == 6 and round(0.38 / 6, 3) == 0.063
    assert len(tree) == 8 and round(0.41 / 8, 3) == 0.051


def test_the_left_pane_is_committed_html(fragment):
    """The GUI mounts this fragment; it is not generated from Markdown."""
    assert FRAGMENT.exists()
    assert fragment.startswith('<article class="formulation">')
    assert "```" not in fragment


def test_the_walkthrough_has_no_contents_list(fragment):
    assert 'class="toc"' not in fragment


def test_the_mathematics_arrives_as_native_mathml(fragment):
    assert "<math" in fragment
    assert "$" not in re.sub(r"<[^>]+>", "", fragment)


def test_the_sections_are_complete_and_ordered(fragment):
    assert headings(fragment) == list(HEADINGS_H2)
    assert h3_headings(fragment) == list(HEADINGS_H3)
    assert "<h1" not in fragment
    assert "Recursive Partitioning with a Decision Tree" in fragment
    assert "Exploring a Data Tree with Gini" in fragment
    assert "Figure D." not in fragment


def test_definition_tables_sit_with_new_terms_and_there_is_no_takeaway(fragment):
    stages = stage_bodies(fragment)
    assert len(stages) == 3
    assert "<th>term</th>" in stages[0]
    assert "<th>term</th>" in stages[1]
    metrics = h3_bodies(fragment)
    assert len(metrics) == 3
    for stage in metrics:
        assert "<th>term</th>" in stage
    assert "<strong>Takeaway.</strong>" not in fragment
    assert "Takeaway" not in fragment


def test_the_walkthrough_contains_no_figure_or_argument_graph(fragment):
    assert not re.search(r"<figure|<svg|mermaid", fragment)


def test_public_terms_are_wiki_or_arxiv_links(fragment):
    assert fragment.count("https://en.wikipedia.org/wiki/Gini_coefficient") == 1
    assert fragment.count("https://en.wikipedia.org/wiki/Poisson_distribution") == 1
    assert fragment.count("https://en.wikipedia.org/wiki/Simulated_annealing") == 1
    assert fragment.count("https://en.wikipedia.org/wiki/Evolutionary_algorithm") == 1
    assert fragment.count("https://en.wikipedia.org/wiki/Beam_search") == 1
    assert fragment.count("https://arxiv.org/abs/2004.10898") == 1
    assert "Lorenz" not in fragment
    assert "defined in §1" in fragment
    assert "Problem Statement" in fragment and "§2.5" in fragment


def test_section_one_states_the_objective_and_fitness_versus_opt(fragment):
    body = stage_bodies(fragment)[0]
    assert "quantified data skipping goal" in body
    assert "split search" in body
    assert "value function" in body
    assert "data-skipping potential" in body
    assert "heuristic" in body.lower()
    assert "sub-optimal" in body
    assert "fitness of the leaf" in body
    assert "OPT of the leaf" in body
    assert "subproblem" in body
    assert "evaluation budget" in body
    assert "does not claim a tractable solver" in body


def test_section_two_names_the_routine_and_does_not_recommend(fragment):
    body = stage_bodies(fragment)[1]
    assert "production" not in fragment.lower()
    assert "storage system" in body
    assert "greedy top-down" in body
    assert "simulated annealing" in body
    assert "evolutionary search" in body
    assert "beam search" in body
    assert "priority queue" in body
    assert "qd-tree" in body
    assert "data-retention policy" in body
    assert "does not select, rank, or recommend" in body


def test_skip_formulas_print_the_poisson_form_on_the_same_line(fragment):
    for stage in h3_bodies(fragment)[:2]:
        assert "&#x02248;" in stage
        assert stage.count("&#x02248;") == 1


def test_gini_section_is_condensed_and_not_waste(fragment):
    body = h3_bodies(fragment)[2]
    assert "in economics" not in body.lower()
    assert "Lorenz" not in body
    assert "not a skip ratio" in body
    section3 = stage_bodies(fragment)[2]
    assert "Problem Statement" in section3 and "§2.5" in section3


def test_the_glossary_is_a_two_column_term_definition_table():
    root = ET.fromstring(GLOSSARY.read_text())
    assert "glossary" in (root.get("class") or "").split()
    tables = [element for element in root.iter() if element.tag == "table"]
    assert len(tables) == 1
    headers = ["".join(cell.itertext()).strip() for cell in tables[0].iter("th")]
    assert headers == ["Term", "Definition"]
    rows = tables[0].findall("tbody/tr")
    assert len(rows) == 17
    terms = ["".join(row[0].itertext()) for row in rows]
    for expected, actual in zip(GLOSSARY_TERMS, terms, strict=True):
        assert expected in actual
    for row in rows:
        assert len(row) == 2
        assert "".join(row[1].itertext()).strip()


def test_the_figures_are_the_apng_then_one_continued_example(diagrams):
    assert figure_ids(diagrams) == list(FIGURE_IDS)
    assert "Exploring a Data Tree with Gini" in diagrams
    assert diagrams.index("D.tree-split-cycle") < diagrams.index("gini-example-title")
    assert diagrams.index("gini-example-title") < diagrams.index("D.lorenz-wealth")
    for ident, title in FIGURE_TITLES.items():
        heading = re.search(
            rf'<figure[^>]*id="{ident}"[^>]*>\s*<h3[^>]*>([^<]+)</h3>',
            diagrams,
            flags=re.DOTALL,
        )
        assert heading, ident
        assert heading.group(1) == title


def test_the_apng_is_the_committed_raster(diagrams):
    start = diagrams.find('id="D.tree-split-cycle"')
    end = diagrams.find('id="D.lorenz-wealth"')
    body = diagrams[start:end]
    assert "Recursive Partitioning with a Decision Tree" in body
    assert "Visualization placeholder" not in body
    assert 'src="figures/img/section_gini_tree_split_cycle.png"' in body
    alt = re.search(r'<img[^>]*\balt="([^"]+)"', body)
    assert alt and len(alt.group(1).split()) >= 12
    raster = Path("resources/img/section_gini_tree_split_cycle.png")
    assert raster.is_file()
    prompt = Path("resources/img_prompt/d_tree_split_cycle_prompt.txt")
    assert prompt.is_file()


def test_the_right_pane_has_no_editorial_lede(diagrams):
    assert "editorial-lede" not in diagrams
    assert diagrams.count("<svg") == 4
    assert diagrams.count("<figcaption>") == 4


def test_lorenz_figure_uses_no_warehouse_vocabulary(diagrams):
    start = diagrams.find('id="D.lorenz-wealth"')
    end = diagrams.find('id="D.split-comparison"')
    body = diagrams[start:end].lower()
    for noun in LORENZ_FORBIDDEN:
        assert not re.search(rf"\b{noun}\b", body), noun


def test_every_drawn_figure_is_announced_to_a_screen_reader(diagrams):
    assert diagrams.count('role="img"') == 3
    assert diagrams.count("<title") == 3
    assert diagrams.count("<desc") == 3
    assert 'aria-labelledby="d-tree-split-cycle-title"' in diagrams


def test_no_state_is_carried_by_colour_alone(diagrams):
    """12.6.2 — dash or a printed label sits beside every fill."""
    assert "stroke-dasharray" in diagrams
    assert "0.50" in diagrams
    assert "Rest combined (35)" in diagrams
    assert "Selection rate" in diagrams


def test_the_diagrams_state_the_instance_gini_values(diagrams):
    assert "G = 0.04" in diagrams
    assert "G = 0.38" in diagrams
    assert "G = 0.41" in diagrams
    assert "G/k = 0.007" in diagrams
    assert "G/k = 0.063" in diagrams
    assert "G/k = 0.051" in diagrams
    assert "ΔG/Δk = 0.015" in diagrams
    assert "D.search-trajectory" not in diagrams
    assert "11/24" not in diagrams
    assert "region · 7/18" not in diagrams


def test_lorenz_figure_is_a_six_neighborhood_connected_scatter(diagrams):
    start = diagrams.find('id="D.lorenz-wealth"')
    end = diagrams.find('id="D.split-comparison"')
    body = diagrams[start:end]
    assert "A perfectly equal distribution." in body
    assert "The top 10% controls 90% of the wealth." in body
    assert "% of wealth" in body
    assert "Six neighborhoods" in body
    assert "diagonal" not in body.lower()
    assert "the bow is G" not in body
    assert "high G" not in body
    assert "G = 0.8112" in body
    assert "d-lorenz-hatch" in body
    assert "Neighbour population %" in body
    assert "Cumulative wealth %" in body
    assert "N1" in body and "N6" in body
    assert body.count("<circle") == 12
    assert body.count('stroke-dasharray="3 3"') == 2
    assert body.count("<table") == 1


def test_split_figure_is_two_auto_parts_trees(diagrams):
    start = diagrams.find('id="D.split-comparison"')
    end = diagrams.find('id="D.selective-tree"')
    body = diagrams[start:end]
    assert "Wealth is query selection rate" in body
    assert "Split by product category" in body
    assert "Split by tenant brand" in body
    assert "density nearly even" in body
    assert "feature_category" not in body
    assert "brand_id" not in body
    assert "brand-000" not in body
    assert "brakes" in body
    assert "Brand name" in body
    assert "Weight %" in body
    assert "Original Data" in body
    assert "Sales event" not in body
    assert "all sales" not in body
    assert "Rest combined (9)" in body
    assert "Rest combined (35)" in body
    assert "illustration-kicker" in body
    assert "G/k = 0.007" in body
    assert "G/k = 0.063" in body
    assert body.count("<table") == 2


def test_selective_tree_grows_from_the_brand_split(diagrams):
    start = diagrams.find('id="D.selective-tree"')
    body = diagrams[start:]
    assert "Original Data" in body
    assert "Sales event" not in body
    assert "category = brakes" in body
    assert "price tier &gt; 5" in body
    assert "Rest combined (35)" in body
    assert "group-by-chain" not in body
    assert "us-east" not in body
    assert 'id="d-layer-root-l1"' in body
    assert 'id="d-layer-l1-l2"' in body
    assert "CASE WHEN feature_category" in body
    assert "CASE WHEN feature_price_tier" in body
    assert "GROUP BY l1, l2" in body
    assert "GROUP BY 1, 2" not in body
    assert "multi-way grouping" in body
    assert "local conditional grouping" in body
    assert "G/k = 0.051" in body
    assert "ΔG/Δk = 0.015" in body
    assert body.count("<svg") == 1


def test_section_d_title_matches_the_navigation_label():
    html = INDEX.read_text()
    assert 'data-nav="gini">Measuring Data Layout Fitness</a>' in html
    assert '<h1 id="gini-heading">Measuring Data Layout Fitness</h1>' in html


def test_the_walkthrough_shares_no_element_id_with_the_other_documents(fragment):
    pattern = r'id="([^"]+)"'
    others = set()
    for name in ("formulation.html", "section-gini-glossary.html"):
        others |= set(re.findall(pattern, (STATIC_ROOT / name).read_text()))
    mine = set(re.findall(pattern, fragment))
    assert not (mine & others)


def test_section_d_stacks_terminology_above_the_figures():
    html = INDEX.read_text()
    section = html.split('id="gini"')[1].split('id="knapsack"')[0]
    assert 'data-mount="section-gini-walkthrough.html"' in section
    assert 'data-mount="section-gini-glossary.html"' in section
    assert f'data-mount="{ILLUSTRATION_HREF}"' in section
    assert "pane-stack pane-right" in section
    assert section.index("section-gini-walkthrough.html") < section.index(
        "section-gini-glossary.html"
    )
    assert section.index("section-gini-glossary.html") < section.index(ILLUSTRATION_HREF)


def test_section_d_is_reachable_without_scripting():
    section = INDEX.read_text().split('id="gini"')[1]
    assert '<a href="section-gini-walkthrough.html">' in section
    assert '<a href="section-gini-glossary.html">' in section
    assert f'<a href="{ILLUSTRATION_HREF}">' in section


def test_section_d_type_is_one_pixel_larger_than_section_a():
    from tests.test_app_shell import rule_for

    css = (STATIC_ROOT / "app.css").read_text()
    declarations = rule_for(css, "#gini .pane-left")
    assert "--text-body: 15px" in declarations
    assert "--text-small: 13px" in declarations
    assert "--text-heading: 19px" in declarations
    assert "--text-title: 24px" in declarations


def test_section_d_walkthrough_fills_the_left_pane():
    from tests.test_app_shell import rule_for

    css = (STATIC_ROOT / "app.css").read_text()
    assert "max-width: none" in rule_for(css, "#gini .pane-left > .formulation")
