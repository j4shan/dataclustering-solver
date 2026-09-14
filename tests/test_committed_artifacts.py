"""Artifacts the project generates once and then commits (10.3.10, 10.3.11).

This project's generated-and-committed deliverables are the explainer figures
and the pre-rendered document fragments the GUI mounts. Committing
them is a deliberate decision with a stated reason — it is what lets an install of the
three runtime dependencies serve the page without rebuilding anything — and it creates
a failure mode that no other test in this suite can see.

**The artifact stops shipping.** An ignore rule written for one directory quietly matches
another, the file leaves the repository, and every test that reads it off the working tree
keeps passing because the author's disk still has it. That is not hypothetical: an
unanchored `data/` swallowed the committed scenario file, and the only symptom was that a
clone could not find a figure.

The one-time generators that produced these files are gone (10.3.3). Currency against a
generator is therefore out of scope; presence and clone-reachability remain.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import an_ignore_rule_matches, is_excluded_from_the_repository

ROOT = Path(__file__).resolve().parents[1]

#: Every artifact this project generates and then commits, with why it is committed.
#: A path here is a promise to a clone, so each is checked for both failure modes.
COMMITTED = {
    "resources/data/closet-scenario.json":
        "the source of truth the two Problem Statement rasters are rendered from (9.7)",
    "site/formulation.html":
        "Problem Statement's left pane; committing it is what lets a default install serve "
        "the page without rebuilding (10.3.10)",
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
