"""The Section A pre-render (PRD 12.3.2, 12.3.3, 12.6.3).

These assert what the transformation must produce; none of them re-derives it.  The
document on disk is used as the realistic case, but every structural claim is made against
a small fixture whose expected output can be read off by eye.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("markdown_it", reason="needs the 'docs' extra")
pytest.importorskip("latex2mathml", reason="needs the 'docs' extra")

from tools import render_formulation as rf  # noqa: E402

FORMULATION = Path("project_metadata/problem-statement.md")
PRODUCTION_DESIGN = Path("project_metadata/production-design.md")


def test_renderer_reads_the_problem_statement_source():
    source, output = rf.DOCUMENTS["formulation"]
    assert source == FORMULATION
    assert output == Path("simulator/gui/static/formulation.html")


def test_engine_mapping_does_not_link_to_unserved_markdown():
    rendered = rf.render(PRODUCTION_DESIGN.read_text(encoding="utf-8"))
    assert 'href="problem-statement.md"' not in rendered
    assert "<code>problem-statement.md</code>" in rendered


# --- anchors ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "heading, expected",
    [
        ("Data storage and fetch model", "data-storage-and-fetch-model"),
        ("3.6 A patternless query", "36-a-patternless-query"),
        ("One relation, three views", "one-relation-three-views"),
        ("Bounds are far apart", "bounds-are-far-apart"),
    ],
)
def test_slugify_drops_punctuation_and_joins_on_hyphens(heading, expected):
    assert rf.slugify(heading) == expected


def test_slugify_never_returns_an_empty_anchor():
    assert rf.slugify("!!!") == "section"


# --- mathematics ------------------------------------------------------------------


def test_extract_math_separates_display_from_inline():
    text = r"before $a+b$ middle $$c+d$$ after"
    work, formulas = rf.extract_math(text)
    assert [display for _, display in formulas] == [True, False]
    assert "$" not in work


def test_fenced_code_is_shielded_from_math_extraction():
    text = "```sql\nSELECT SUM(size * breadth) FROM t WHERE a $ b $ c;\n```\n"
    work, formulas = rf.extract_math(text)
    assert formulas == []
    assert "SELECT SUM(size * breadth)" in work


def test_math_becomes_native_mathml_with_display_on_block_formulas():
    out = rf.render("$$\\mathcal{W}(\\lambda)$$\n")
    assert "<math" in out
    assert 'display="block"' in out
    assert "\\mathcal" not in out


def test_boxed_formula_is_tagged_for_the_stylesheet():
    """\\boxed compiles to <menclose>, which Chrome's MathML Core drops."""
    out = rf.render(r"$$\boxed{x}$$")
    assert 'class="is-boxed"' in out


# --- figures ----------------------------------------------------------------------


def test_picture_collapses_to_the_light_image_only():
    block = (
        "<picture>\n"
        '  <source media="(prefers-color-scheme: dark)" srcset="img/z.dark.svg">\n'
        '  <img alt="a caption" src="img/z.light.svg">\n'
        "</picture>\n"
    )
    out = rf.collapse_pictures(block, "figures/")
    assert "z.dark.svg" not in out
    assert 'src="figures/img/z.light.svg"' in out
    assert 'alt="a caption"' in out
    assert "<source" not in out


# --- links ------------------------------------------------------------------------


def test_outbound_links_open_away_but_anchors_do_not():
    out = rf.externalize_links('<a href="https://example.org">x</a><a href="#s2">y</a>')
    assert 'href="https://example.org" target="_blank" rel="noopener noreferrer"' in out
    assert '<a href="#s2">y</a>' in out


# --- the whole document -----------------------------------------------------------


@pytest.fixture(scope="module")
def rendered() -> str:
    return rf.render(FORMULATION.read_text(encoding="utf-8"))


def test_no_sentinel_or_raw_mathematics_survives(rendered):
    assert rf.SENTINEL not in rendered
    assert "$" not in rendered


def test_every_heading_is_anchored_and_listed(rendered):
    """12.3.3 — every section of the document, and only those, reach the injected list.

    The document's own contents heading is excluded because 12.3.3.1 drops that section
    before rendering, so it is not a place in the document the generated list points at.
    """
    source = FORMULATION.read_text(encoding="utf-8")
    expected = sum(
        1
        for line in source.splitlines()
        if (line.startswith("## ") or line.startswith("### "))
        and line.strip() != "## Contents"
    )
    assert rendered.count('<li class="toc-h') == expected
    assert '<details class="toc">' in rendered
    assert '<details class="toc" open>' not in rendered


def test_an_authored_contents_section_is_dropped():
    """12.3.3.1 — the pane injects a contents list, so the authored one would duplicate it.

    Checked on a fixture whose authored entry is unmistakable, so the assertion turns on
    what the transformation does and not on whether a committed document happens to
    carry a contents section today.
    """
    source = "# T\n\nlead.\n\n## Contents\n\n- [only-in-the-authored-list](#1-one)\n\n---\n\n## 1. One\n\nBody.\n"
    out = rf.render(source)
    assert "only-in-the-authored-list" not in out
    assert ">1. One</a>" in out, "the generated list still names the section"
    assert "Body." in out, "only the contents section is removed"


def test_dropping_contents_leaves_a_document_without_one_untouched():
    """12.3.3.1 — the engine mapping authors no contents list, and nothing changes for it."""
    source = "# T\n\nlead.\n\n---\n\n## 1. One\n\nBody.\n"
    assert rf.drop_authored_contents(source) == source


def test_tables_and_code_survive_the_round_trip():
    """12.3.2 — a table and a fenced block reach the page as themselves."""
    out = rf.render("# T\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n\n```\nkept_verbatim\n```\n")
    assert "<table>" in out
    assert "kept_verbatim" in out

