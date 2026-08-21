"""Artifacts the project generates once and then commits (10.3.10, 10.3.11).

Three of this project's deliverables are produced by a script and then checked in: the
explainer figures, and the two pre-rendered document fragments the GUI mounts. Committing
them is a deliberate decision with a stated reason — it is what lets an install of the
three runtime dependencies serve the page without the `docs` extra — and it creates two
failure modes that no other test in this suite can see.

**The artifact stops shipping.** An ignore rule written for one directory quietly matches
another, the file leaves the repository, and every test that reads it off the working tree
keeps passing because the author's disk still has it. That is not hypothetical: an
unanchored `data/` swallowed the committed scenario file, and the only symptom was that a
clone could not regenerate a figure.

**The artifact goes stale.** Someone edits the source document or the generator and does
not rerun it. The committed copy is now a different thing from what the generator would
produce, tests read the committed copy, and the repository ships the old one.

Both are checked by comparing against the real generator, never by a second implementation
of it (10.1.2): the test runs the shipped code and asserts the committed bytes are what it
returns.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import an_ignore_rule_matches, is_excluded_from_the_repository

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "simulator" / "gui" / "static"
FIGURES = ROOT / "resources" / "img"

#: Every artifact this project generates and then commits, with why it is committed.
#: A path here is a promise to a clone, so each is checked for both failure modes.
COMMITTED = {
    "resources/data/closet-scenario.json":
        "the source of truth every scenario figure and the canvas derive from (9.1)",
    "simulator/gui/static/formulation.html":
        "Section A's left pane; committing it is what lets a default install serve "
        "the page without the docs extra (10.3.6)",
    "simulator/gui/static/production-design.html":
        "Section C's left pane, on the same terms (12.5.4)",
    "resources/img/selection-matrix.light.svg": "the centrepiece figure (9.2)",
    "resources/img/selection-matrix.dark.svg": "its dark variant (9.7)",
    "resources/img/container-zoom.light.svg": "the two container outcomes (9.5)",
    "resources/img/container-zoom.dark.svg": "its dark variant (9.7)",
    "resources/img/page-anatomy.light.svg": "the page anatomy (9.15)",
    "resources/img/page-anatomy.dark.svg": "its dark variant (9.7)",
}


@pytest.mark.parametrize("path", sorted(COMMITTED), ids=lambda p: Path(p).name)
def test_a_committed_artifact_is_present(path):
    """It is committed precisely so that it is there without being rebuilt."""
    assert (ROOT / path).exists(), COMMITTED[path]


@pytest.mark.parametrize("path", sorted(COMMITTED), ids=lambda p: Path(p).name)
def test_a_committed_artifact_reaches_a_clone(path):
    """10.3.10 — present on this disk is not the same as present in a clone.

    This is the assertion the filesystem checks elsewhere cannot make.
    """
    assert not is_excluded_from_the_repository(path), (
        f"{path} is ignored and unstaged, so a clone will not have it — {COMMITTED[path]}"
    )


@pytest.mark.parametrize("path", sorted(COMMITTED), ids=lambda p: Path(p).name)
def test_no_ignore_rule_names_a_committed_artifact(path):
    """10.3.10 — `.gitignore` records "deliberately NOT ignored" as a comment; this enforces it.

    A tracked file matched by an ignore rule still ships, so the test above is satisfied
    — but it can never be re-added once it leaves the index, and the rule that matched it
    was written for something else. That is the shape the scenario file's loss took.
    """
    assert not an_ignore_rule_matches(path), (
        f"an ignore rule names {path}, which is committed on purpose — {COMMITTED[path]}"
    )


# -- currency: the committed copy is what the generator produces now -------------------


@pytest.fixture(scope="module")
def figures():
    from tools import render_figures as rf

    scenario = rf.load()
    return rf, {
        f"selection-matrix.{theme}.svg": rf.figure_matrix(scenario, theme)
        for theme in rf.THEMES
    } | {
        f"container-zoom.{theme}.svg": rf.figure_zoom(scenario, theme)
        for theme in rf.THEMES
    } | {
        f"page-anatomy.{theme}.svg": rf.figure_anatomy(theme) for theme in rf.THEMES
    }


def test_every_committed_figure_is_current(figures):
    """10.3.11 — a figure edited in the generator but not rerun ships as the old drawing.

    Regenerate with `python3 tools/render_figures.py`.
    """
    _, fresh = figures
    stale = [name for name, svg in fresh.items()
             if (FIGURES / name).read_text() != svg]
    assert stale == [], f"regenerate: {stale}"


def test_the_figure_set_is_exactly_what_the_generator_writes(figures):
    """9.7 — a figure dropped from the generator leaves a committed orphan behind."""
    _, fresh = figures
    assert {p.name for p in FIGURES.glob("*.svg")} == set(fresh)


def test_every_pre_rendered_fragment_is_current():
    """10.3.11 — a fragment older than its source serves a document nobody wrote.

    Regenerate with `python -m tools.render_formulation`.
    """
    pytest.importorskip("markdown_it", reason="needs the 'docs' extra")
    pytest.importorskip("latex2mathml", reason="needs the 'docs' extra")
    from tools import render_formulation as rf

    stale = []
    for source, out in rf.DOCUMENTS.values():
        fresh = rf.render(
            source.read_text(encoding="utf-8"), rf.ASSET_PREFIX, document_id=out.stem
        )
        if out.read_text(encoding="utf-8") != fresh:
            stale.append(out.name)
    assert stale == [], f"regenerate: {stale}"
