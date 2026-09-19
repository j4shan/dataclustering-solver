"""Business Insights as Byproduct — the two-pane illustration (12.10).

The prose is the author's own text, held in §2.2 of the spec and copied into the
walkthrough.  These tests assert that copy relation and the figure contract.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from conftest import RESOURCES
from simulator.gui import FIGURE_ROOT, SITE_ROOT

ROOT = Path(__file__).resolve().parents[1]
WALKTHROUGH = SITE_ROOT / "section-kpi-walkthrough.html"
FRAGMENT = FIGURE_ROOT / "html" / "section-kpi-illustration.html"
INDEX = SITE_ROOT / "index.html"
SPEC = ROOT / "project_metadata" / "product_spec" / "section-kpi-illustration.md"
PROMPT = RESOURCES / "img_prompt" / "section_kpi_ecommerce_prompt.txt"
RASTER = "figures/img/section_kpi_ecommerce.png"
FIGURE_ID = "signal.ecommerce"
FIGURE_TITLE = "Ecommerce warehouse usage map"
FOOTNOTE = "The pale group is stock that does not sell."


def tag_of(element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def text_of(element) -> str:
    return " ".join("".join(element.itertext()).split())


@pytest.fixture(scope="module")
def walkthrough():
    return ET.fromstring(WALKTHROUGH.read_text())


@pytest.fixture(scope="module")
def pane():
    return ET.fromstring(FRAGMENT.read_text())


@pytest.fixture(scope="module")
def fragment() -> str:
    return FRAGMENT.read_text()


def test_the_beats_are_complete_and_ordered(walkthrough, pane):
    """I2: the two paragraphs of §2.2 on the left; the figure on the right."""
    prose = [child for child in walkthrough if tag_of(child) == "p"]
    assert [tag_of(child) for child in prose] == ["p", "p"]
    assert not any(tag_of(child) == "figure" for child in walkthrough)
    figures = [child for child in pane.iter() if tag_of(child) == "figure"]
    assert [child.get("id") for child in figures] == [FIGURE_ID]
    assert not any(tag_of(child) == "p" for child in pane.iter())


def test_the_fragment_copies_the_authors_prose_verbatim(walkthrough):
    """I3: §2.2 is the author's text and the walkthrough reproduces it."""
    spec = SPEC.read_text()
    body = spec.split("### 2.2 Prose")[1].split("### 2.3")[0]
    authored = [line.strip() for line in body.splitlines() if line.strip()]
    assert len(authored) == 2, "§2.2 holds the two paragraphs"
    rendered = [text_of(c) for c in walkthrough if tag_of(c) == "p"]
    assert rendered == authored


def test_the_prose_asserts_no_number(walkthrough):
    """I3.2."""
    prose = " ".join(text_of(c) for c in walkthrough if tag_of(c) == "p")
    assert not re.search(r"\d", prose)


def test_the_locked_title_is_copied_verbatim_and_there_is_no_caption(pane):
    figures = [child for child in pane if tag_of(child) == "figure"]
    assert len(figures) == 1
    figure = figures[0]
    title = next(c for c in figure if tag_of(c) == "h3")
    assert text_of(title) == FIGURE_TITLE
    assert not any(tag_of(c) == "figcaption" for c in figure)


def test_the_raster_is_mounted_and_the_pane_does_not_reference_a_missing_file(
    fragment, pane
):
    walkthrough = WALKTHROUGH.read_text()
    assert fragment.count("<img") == 1
    assert "<svg" not in fragment
    assert "Figure deferred" not in fragment
    assert "forthcoming" not in fragment
    for text in (fragment, walkthrough):
        assert "teach" not in text.lower()
        assert "production" not in text.lower()
        assert "discovery surface" not in text
        assert "business improvement" not in text
        assert "—" not in text
        assert "–" not in text
        assert FOOTNOTE not in text
    img = pane.find(".//img")
    assert img is not None
    assert img.get("src") == RASTER
    assert (SITE_ROOT / RASTER).is_file()
    # The alt text describes the committed raster, which is sixteen departments
    # encoded by fill alone.  An earlier alt text described eighteen and a green
    # cold-leaf stroke, neither of which the map has (I5.1, I6).
    alt = img.get("alt") or ""
    assert "Eighteen departments" not in alt
    assert "green stroke" not in alt
    assert "Sixteen departments" in alt


def test_the_spec_keeps_no_recommendation_and_the_column_contract():
    spec = SPEC.read_text()
    assert "**No recommendation.**" in spec
    assert "group`, `tile_id`, `label`, `size`, `kpi`, `band`" in spec
    assert FIGURE_ID in spec
    assert "signal.advertising" not in spec
    assert "signal.social" not in spec
    # The pane argues that the usage reading is a by-product of layout work
    # already paid for.  It still reports no measured outcome.
    assert "does not claim a business result" not in spec
    assert "It reports no measured outcome" in spec
    assert FIGURE_TITLE in spec
    assert "### 2.2 Prose" in spec
    assert FOOTNOTE not in spec


def test_the_figure_has_a_rendering_prompt():
    assert PROMPT.is_file()
    text = PROMPT.read_text()
    assert "tile_id" in text
    assert "band" in text
    assert "Finviz" in text
    assert "#7A1F2B" in text


def test_obsolete_domain_maps_are_not_kept_as_authoring():
    for stem in ("section_kpi_advertising", "section_kpi_social"):
        assert not (RESOURCES / "img_prompt" / f"{stem}_prompt.txt").exists()
        assert not (RESOURCES / "img_src" / f"{stem}.drawio").exists()
        assert not (SITE_ROOT / "figures" / "img" / f"{stem}.png").exists()


def test_section_signal_is_a_two_pane_split_after_databricks():
    html = INDEX.read_text()
    ids = re.findall(r'<section class="section(?:\s[^"]*)?" id="([\w-]+)"', html)
    assert ids[-1] == "signal"
    section = html.split('id="signal"')[1].split("</section>")[0]
    assert 'data-nav="signal">Business Insights as Byproduct</a>' in html
    assert '<h1 id="signal-heading">Business Insights as Byproduct</h1>' in section
    assert 'class="split"' in section
    assert 'data-mount="section-kpi-walkthrough.html"' in section
    assert 'data-mount="figures/html/section-kpi-illustration.html"' in section
    assert section.index("section-kpi-walkthrough.html") < section.index(
        "section-kpi-illustration.html"
    )


def test_section_signal_matches_the_walkthrough_type_and_the_30_70_split():
    from tests.test_app_shell import rule_for

    css = (SITE_ROOT / "app.css").read_text()
    declarations = rule_for(css, "#signal .pane-left")
    for declaration in (
        "--text-body: 15px",
        "--text-small: 13px",
        "--text-heading: 19px",
        "--text-title: 24px",
    ):
        assert declaration in declarations
    assert declarations == rule_for(css, "#signal .pane-right")
    assert "max-width: none" in rule_for(css, "#signal .illustration-stack")
    assert "max-width: none" in rule_for(css, "#signal .pane-left > .formulation")
    assert "grid-template-columns: minmax(0, 30%) minmax(0, 70%)" in rule_for(
        css, "#signal .split"
    )
