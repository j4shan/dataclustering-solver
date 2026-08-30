"""Section D — the Gini split-search illustration (12.8).

The left pane is a committed walkthrough. The right pane is four figures of
the same twelve-event instance. Nothing here is a recommendation (1.2) and
nothing here computes a Gini in the GUI (13.19).
"""

from __future__ import annotations

import re
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

import pytest

from simulator.gui import FIGURE_ROOT, STATIC_ROOT

SOURCE = Path("project_metadata/section-d-walkthrough.md")
FRAGMENT = STATIC_ROOT / "section-d-walkthrough.html"
DIAGRAMS = FIGURE_ROOT / "graphics" / "section-d-illustration.html"
ILLUSTRATION_HREF = "figures/graphics/section-d-illustration.html"
INDEX = STATIC_ROOT / "index.html"

FIGURE_IDS = (
    "D.lorenz-wealth",
    "D.split-comparison",
    "D.selective-tree",
    "D.search-trajectory",
)
FIGURE_TITLES = {
    "D.lorenz-wealth": "When wealth sits in few hands",
    "D.split-comparison": "The same twelve records, two cuts",
    "D.selective-tree": "A chain multiplies every branch; a tree need not",
    "D.search-trajectory": "Stop when the next cut returns too little",
}

#: 12.5.7.1 events with used_count derived from that selection log (12.8.4).
INSTANCE = (
    ("r01", "us-east", "click", 1),
    ("r02", "us-east", "click", 0),
    ("r03", "us-east", "view", 2),
    ("r04", "us-west", "click", 0),
    ("r05", "us-west", "view", 0),
    ("r06", "eu-west", "click", 1),
    ("r07", "eu-west", "view", 0),
    ("r08", "ap-south", "click", 0),
    ("r09", "ap-south", "view", 0),
    ("r10", "us-east", "purchase", 1),
    ("r11", "us-west", "purchase", 1),
    ("r12", "eu-west", "purchase", 0),
)

STAGE1_FORBIDDEN = (
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


def groups_on(column: int) -> list[tuple[int, int]]:
    buckets: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for row in INSTANCE:
        key = row[column]
        buckets[key][0] += 1
        buckets[key][1] += row[3]
    return [tuple(pair) for pair in buckets.values()]


@pytest.fixture(scope="module")
def document() -> str:
    return SOURCE.read_text()


@pytest.fixture(scope="module")
def fragment() -> str:
    return FRAGMENT.read_text()


@pytest.fixture(scope="module")
def diagrams() -> str:
    return DIAGRAMS.read_text()


def test_the_instance_gini_values_are_the_walkthroughs_arithmetic():
    """12.8.4 — 7/18 and 1/9 are properties of the authored instance."""
    assert weighted_gini(groups_on(1)) == Fraction(7, 18)
    assert weighted_gini(groups_on(2)) == Fraction(1, 9)


def test_the_artifact_is_pre_rendered_and_committed(fragment):
    """12.8.2, 12.3.2 — finished HTML arrives; no Markdown is parsed in the browser."""
    assert FRAGMENT.exists()
    assert fragment.startswith('<article class="formulation">')
    assert "```" not in fragment


def test_the_walkthrough_has_no_contents_list(fragment):
    """12.8.2 — a sequential presentation, not a reference document."""
    assert 'class="toc"' not in fragment


def test_the_mathematics_arrives_as_native_mathml(fragment):
    assert "<math" in fragment
    assert "$" not in re.sub(r"<[^>]+>", "", fragment)


def test_the_three_stages_are_complete_and_ordered(document):
    headings = re.findall(r"^## (.+)$", document, flags=re.MULTILINE)
    assert headings == [
        "1. A familiar kind of unevenness",
        "2. The same unevenness in a warehouse",
        "3. A search that evolves the split",
    ]


def test_each_stage_has_a_definition_table_and_a_takeaway(document):
    stages = re.split(r"^## ", document, flags=re.MULTILINE)[1:]
    assert len(stages) == 3
    for stage in stages:
        assert "| term |" in stage
        assert "**Takeaway.**" in stage


def test_the_walkthrough_contains_no_figure_or_argument_graph(document):
    assert not re.search(r"<figure|<svg|mermaid|!\[[^\]]*\]\(", document)


def test_first_public_terms_are_wiki_links_and_later_mentions_are_citations(document):
    """12.8.6.1 — wiki at first introduction; citation form afterwards."""
    assert "[Lorenz curve](https://en.wikipedia.org/wiki/Lorenz_curve)" in document
    assert "[Gini coefficient](https://en.wikipedia.org/wiki/Gini_coefficient)" in document
    assert document.index("Lorenz curve") < document.index("Gini coefficient")
    assert document.count("https://en.wikipedia.org/wiki/Lorenz_curve") == 1
    assert document.count("https://en.wikipedia.org/wiki/Gini_coefficient") == 1
    assert "($G(S)$, defined in §1)" in document
    assert "($W(\\lambda)$, defined in §2.5)" in document


def test_stage_one_uses_only_inequality_language(document):
    """12.8.1.1 — warehouse vocabulary waits for stage 2."""
    stage1 = re.split(r"^## ", document, flags=re.MULTILINE)[1]
    body = stage1.lower()
    for noun in STAGE1_FORBIDDEN:
        assert not re.search(rf"\b{noun}\b", body), noun


def test_stage_two_maps_usage_and_states_gini_is_not_waste(document):
    stage2 = re.split(r"^## ", document, flags=re.MULTILINE)[2]
    assert "used_count" in stage2
    assert "7/18" in stage2
    assert "1/9" in stage2
    assert "W(\\lambda)" in stage2


def test_stage_three_names_the_search_and_does_not_recommend(document):
    stage3 = re.split(r"^## ", document, flags=re.MULTILINE)[3]
    assert "group-by-chain" in stage3
    assert "selective tree" in stage3
    assert "Section B" in stage3
    assert "does not select, rank, or recommend" in stage3


def test_exactly_four_titled_figures(diagrams):
    ids = re.findall(r'<figure class="illustration" id="([^"]+)">', diagrams)
    assert ids == list(FIGURE_IDS)
    for ident, title in FIGURE_TITLES.items():
        heading = re.search(
            rf'<figure class="illustration" id="{ident}">\s*<h3[^>]*>([^<]+)</h3>',
            diagrams,
        )
        assert heading, ident
        assert heading.group(1) == title


def test_the_right_pane_is_figures_only(diagrams):
    """12.8.3 — no editorial lede; captions may name what is drawn."""
    assert "editorial-lede" not in diagrams
    assert diagrams.count("<svg") == 4
    assert diagrams.count("<figcaption>") == 4


def test_lorenz_figure_uses_no_warehouse_vocabulary(diagrams):
    start = diagrams.find('id="D.lorenz-wealth"')
    end = diagrams.find('id="D.split-comparison"')
    body = diagrams[start:end].lower()
    for noun in STAGE1_FORBIDDEN:
        assert not re.search(rf"\b{noun}\b", body), noun


def test_every_figure_is_announced_to_a_screen_reader(diagrams):
    assert diagrams.count('role="img"') == 4
    assert diagrams.count("<title") == 4
    assert diagrams.count("<desc") == 4


def test_no_state_is_carried_by_colour_alone(diagrams):
    """12.6.2 — hatch, dash, or a printed label sits beside every fill."""
    assert "stroke-dasharray" in diagrams
    assert "d-hatch" in diagrams or "d-gini-bow" in diagrams
    assert "skip candidate" in diagrams


def test_the_diagrams_state_the_instance_gini_values(diagrams):
    assert "1/9" in diagrams
    assert "7/18" in diagrams


def test_the_walkthrough_shares_no_element_id_with_the_other_documents(fragment):
    """All three documents mount into one page."""
    pattern = r'id="([^"]+)"'
    others = set()
    for name in ("formulation.html", "production-design.html"):
        others |= set(re.findall(pattern, (STATIC_ROOT / name).read_text()))
    mine = set(re.findall(pattern, fragment))
    assert not (mine & others)


def test_section_d_keeps_text_on_the_left_and_figures_on_the_right():
    html = INDEX.read_text()
    section = html.split('id="gini"')[1]
    assert 'data-mount="section-d-walkthrough.html"' in section
    assert f'data-mount="{ILLUSTRATION_HREF}"' in section
    assert section.index("pane-left") < section.index("pane-right")
    assert section.index("section-d-walkthrough.html") < section.index(ILLUSTRATION_HREF)


def test_section_d_is_reachable_without_scripting():
    section = INDEX.read_text().split('id="gini"')[1]
    assert '<a href="section-d-walkthrough.html">' in section
    assert f'<a href="{ILLUSTRATION_HREF}">' in section


def test_section_d_type_is_one_pixel_larger_than_section_a():
    """12.8.7 — both D panes remap tokens one step above A's 14/12/18/23."""
    from tests.test_app_shell import rule_for

    css = (STATIC_ROOT / "app.css").read_text()
    declarations = rule_for(css, "#gini .pane-left")
    assert "--text-body: 15px" in declarations
    assert "--text-small: 13px" in declarations
    assert "--text-heading: 19px" in declarations
    assert "--text-title: 24px" in declarations


def test_section_d_walkthrough_fills_the_left_pane():
    """12.8.1.6 — the document uses the pane, not a character clamp inside it."""
    from tests.test_app_shell import rule_for

    css = (STATIC_ROOT / "app.css").read_text()
    assert "max-width: none" in rule_for(css, "#gini .pane-left > .formulation")


def test_the_diagrams_use_the_explainer_family():
    """12.8.3 — wine / sage family; not the 12.7 gray series; no orange."""
    body = DIAGRAMS.read_text()
    assert "#7A1F2B" in body
    assert "#F8EEF0" in body
    assert "#1B4D3E" in body
    assert "#EEF4F0" in body
    # The orange slot of 12.7.1.4 must not appear as a figure colour.
    assert "#d4a27f" not in body.lower()
