"""What a documented command needs must be a declared dependency (10.3.9).

This suite exists because the gap it guards was real and invisible: `pytest` reached the
project only as a transitive dependency of an *optional* extra, so the README's own
`pip install -e .` then `python -m pytest` did not work on a clean machine, and every
developer's environment had pytest from somewhere else to hide it.

Read from `pyproject.toml` rather than from the running interpreter — asking the
environment whether pytest is importable would always say yes, since a test is running.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


@pytest.fixture(scope="module")
def project() -> dict:
    return tomllib.loads(PYPROJECT.read_text())["project"]


def test_the_test_runner_is_declared(project):
    """10.3.9 — `python -m pytest` is documented, so its tool is a declared dependency."""
    dev = project["optional-dependencies"]["dev"]
    assert any(requirement.startswith("pytest") for requirement in dev)


def test_the_dev_group_runs_the_whole_suite(project):
    """10.3.9 — a documented command that quietly runs less than it appears to."""
    extras = project["optional-dependencies"]
    assert "docs" not in extras
    assert "data" in " ".join(extras["dev"])


def test_the_package_to_ship_is_declared_not_discovered():
    """10.3.9 — flat-layout auto-discovery meets three top-level directories and refuses.

    Which made the documented `pip install -e .` fail outright on a clean checkout.
    """
    config = tomllib.loads(PYPROJECT.read_text())
    assert config["build-system"]["build-backend"]
    assert config["tool"]["setuptools"]["packages"]["find"]["include"] == ["simulator*"]


def named(requirements):
    return {r.split(">")[0].split("=")[0].split("[")[0].strip() for r in requirements}


def test_the_serving_set_is_the_named_asgi_stack_and_nothing_else(project):
    """10.3.1 — what an install needs to serve the page, and no more.

    The list is closed rather than bounded: what 10.3.1 protects is that an install
    either works or fails loudly once, and a set that grows by one convenience at a time
    is how that stops being true.  Adding a name here means amending the clause first.
    """
    assert named(project["dependencies"]) == {"fastapi", "uvicorn"}


def test_the_numeric_stack_is_not_installed_to_serve_the_page(project):
    """10.3.1 — the serving process computes nothing, so it carries no numeric stack.

    This is what makes 12.2.5 structural rather than a matter of discipline: a
    computation added to the server would need a library the serving install does not
    have, and would fail on a clean checkout rather than merely breaking a rule.
    """
    assert named(project["optional-dependencies"]["data"]) == {"numpy", "pyarrow"}
    assert not named(project["dependencies"]) & named(
        project["optional-dependencies"]["data"]
    )


def test_the_dev_group_brings_what_the_suite_builds_a_corpus_with(project):
    """10.3.9 — part of the suite builds a corpus, so `dev` must supply what builds it."""
    assert "data" in " ".join(project["optional-dependencies"]["dev"])


def test_retired_document_tooling_is_not_declared(project):
    """The one-time document renderer is gone, so its libraries are not a dependency."""
    everything = " ".join(
        project["dependencies"]
        + [r for group in project["optional-dependencies"].values() for r in group]
    )
    assert "markdown-it-py" not in everything
    assert "latex2mathml" not in everything
    assert "matplotlib" not in everything


def test_no_browser_tooling_survives(project):
    """Browser-driven checks are not performed, so nothing declares one."""
    everything = " ".join(
        project["dependencies"]
        + [r for group in project["optional-dependencies"].values() for r in group]
    )
    assert "playwright" not in everything
    assert "selenium" not in everything
