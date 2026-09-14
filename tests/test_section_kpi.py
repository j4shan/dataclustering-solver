"""Business Signal in Cold Data — the single-pane KPI illustration (12.10)."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from conftest import RESOURCES
from simulator.gui import FIGURE_ROOT, SITE_ROOT

ROOT = Path(__file__).resolve().parents[1]
FRAGMENT = FIGURE_ROOT / "html" / "section-kpi-illustration.html"
INDEX = SITE_ROOT / "index.html"
SPEC = ROOT / "project_metadata" / "product_spec" / "section-kpi-illustration.md"
PROMPTS = (
    RESOURCES / "img_prompt" / "section_kpi_advertising_prompt.txt",
    RESOURCES / "img_prompt" / "section_kpi_ecommerce_prompt.txt",
    RESOURCES / "img_prompt" / "section_kpi_social_prompt.txt",
)
FIGURE_IDS = (
    "signal.advertising",
    "signal.ecommerce",
    "signal.social",
)
FIGURE_TITLES = (
    "Ad Spend and Conversion",
    "On-hand Inventory and Sell-through",
    "Impressions and Engagement",
)
OPENING = (
    "A data layout shaped by query usage often follows the same concentrations "
    "a business already records as KPIs. Split search isolates the cold and hot "
    "segments of a corpus; a multiple-choice knapsack then spends a limited "
    "container budget where the skipping benefit is largest. The search that "
    "builds a skip layout also quarantines subclusters that queries almost "
    "never touch. Those idle clusters name the campaigns, products, or posts "
    "that fail the KPI the queries were written to serve."
)
ADVERTISING = (
    "A conversion query selects the events that ended in a sale. Campaigns that "
    "never convert stay in the corpus as real bytes with zero demand. Split "
    "search puts those events in cold leaves, and the knapsack spends almost "
    "no extra containers on them. On the map, tile area is ad spend and "
    "brightness is conversion rate. The large dim tiles are spend on campaigns "
    "that do not convert."
)
ECOMMERCE = (
    "A pick-and-pack query selects the SKUs that sell. Products that do not "
    "move are never selected, so they land in a cold leaf. Tile area is "
    "on-hand inventory and brightness is sell-through. The pale tiles are "
    "stock those queries have already treated as unused."
)
SOCIAL = (
    "Queries that measure engagement select the posts that received it. Posts "
    "that received none are missing from the selection log. Tile area is "
    "impressions and brightness is engagement rate. The dim cluster is content "
    "those queries already skip."
)
CAPTIONS = (
    "Tile area is ad spend and brightness is conversion rate. The large dim group is spend that did not convert.",
    "Tile area is on-hand inventory and brightness is sell-through. The pale group is stock that does not sell.",
    "Tile area is impressions and brightness is engagement rate. The dim group is content that drew none.",
)


def tag_of(element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def text_of(element) -> str:
    return " ".join("".join(element.itertext()).split())


@pytest.fixture(scope="module")
def pane():
    return ET.fromstring(FRAGMENT.read_text())


@pytest.fixture(scope="module")
def fragment() -> str:
    return FRAGMENT.read_text()


def test_the_beats_are_complete_and_ordered(pane):
    children = [child for child in pane if tag_of(child) in {"p", "figure"}]
    assert [tag_of(child) for child in children] == [
        "p",
        "p",
        "figure",
        "p",
        "figure",
        "p",
        "figure",
    ]
    assert [child.get("id") for child in children if tag_of(child) == "figure"] == list(
        FIGURE_IDS
    )


def test_the_locked_paragraphs_are_copied_verbatim(pane):
    paragraphs = [text_of(child) for child in pane if tag_of(child) == "p"]
    assert paragraphs == [OPENING, ADVERTISING, ECOMMERCE, SOCIAL]


def test_the_locked_captions_and_titles_are_copied_verbatim(pane):
    figures = [child for child in pane if tag_of(child) == "figure"]
    titles = []
    captions = []
    for figure in figures:
        titles.append(text_of(next(c for c in figure if tag_of(c) == "h3")))
        captions.append(text_of(next(c for c in figure if tag_of(c) == "figcaption")))
    assert titles == list(FIGURE_TITLES)
    assert captions == list(CAPTIONS)


def test_rasters_are_deferred_and_the_pane_does_not_reference_a_missing_file(fragment):
    assert "<img" not in fragment
    assert "<svg" not in fragment
    assert fragment.count("Figure deferred. See the rendering prompt.") == 3
    assert "forthcoming" not in fragment
    assert "teach" not in fragment.lower()
    assert "production" not in fragment.lower()
    assert "discovery surface" not in fragment
    assert "business improvement" not in fragment
    assert "—" not in fragment
    assert "–" not in fragment


def test_the_spec_keeps_no_recommendation_and_the_column_contract():
    spec = SPEC.read_text()
    assert "**No recommendation.**" in spec
    assert "group`, `tile_id`, `label`, `size`, `kpi`, `band`" in spec
    assert "signal.advertising" in spec
    assert "signal.ecommerce" in spec
    assert "signal.social" in spec
    assert OPENING in spec
    assert ADVERTISING in spec
    assert ECOMMERCE in spec
    assert SOCIAL in spec
    for caption in CAPTIONS:
        assert caption in spec


def test_each_figure_has_a_rendering_prompt():
    for path in PROMPTS:
        assert path.is_file()
        text = path.read_text()
        assert "group" in text
        assert "tile_id" in text
        assert "band" in text
        assert "Finviz" in text
        assert "#1B4D3E" in text
        assert "#7A1F2B" in text
        assert "hatch" in text
        assert "Accepted path:" in text


def test_section_signal_is_a_single_pane_after_databricks():
    html = INDEX.read_text()
    ids = re.findall(r'<section class="section(?:\s[^"]*)?" id="([\w-]+)"', html)
    assert ids[-1] == "signal"
    section = html.split('id="signal"')[1]
    assert 'data-nav="signal">Business Signal in Cold Data</a>' in html
    assert '<h1 id="signal-heading">Business Signal in Cold Data</h1>' in section
    assert 'class="section section-single"' in html
    assert 'data-mount="figures/html/section-kpi-illustration.html"' in section
    assert "split" not in section.split("</section>")[0]


def test_section_signal_matches_the_walkthrough_type_and_fills_the_pane():
    from tests.test_app_shell import rule_for

    css = (SITE_ROOT / "app.css").read_text()
    declarations = rule_for(css, "#signal .pane-single")
    for declaration in (
        "--text-body: 15px",
        "--text-small: 13px",
        "--text-heading: 19px",
        "--text-title: 24px",
    ):
        assert declaration in declarations
    assert "max-width: none" in rule_for(css, "#signal .illustration-stack")
    assert "flex: 1" in rule_for(css, ".section-single > .pane-single")
    assert "min-height: 0" in rule_for(css, ".section-single > .pane-single")
