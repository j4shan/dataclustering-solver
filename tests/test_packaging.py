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
    """10.3.9 — a documented command that quietly runs less than it appears to.

    The pre-render tests import the `docs` tooling. Without it they are not collected at
    all — no failure, no skip line, just fifteen fewer tests — so `dev` pulls `docs` in.
    """
    dev = " ".join(project["optional-dependencies"]["dev"])
    assert "docs" in dev, "installing [dev] must also bring what the docs tests import"


def test_the_package_to_ship_is_declared_not_discovered():
    """10.3.9 — flat-layout auto-discovery meets three top-level directories and refuses.

    Which made the documented `pip install -e .` fail outright on a clean checkout.
    """
    config = tomllib.loads(PYPROJECT.read_text())
    assert config["build-system"]["build-backend"]
    assert config["tool"]["setuptools"]["packages"]["find"]["include"] == ["simulator*"]


def named(requirements):
    return {r.split(">")[0].split("=")[0].split("[")[0].strip() for r in requirements}


def test_the_exhibit_set_is_the_named_asgi_stack_and_nothing_else(project):
    """10.3.1 — what a deployed instance installs to serve the page, and no more.

    The list is closed rather than bounded: what 10.3.1 protects is that an install
    either works or fails loudly once, and a set that grows by one convenience at a time
    is how that stops being true.  Adding a name here means amending the clause first.
    """
    assert named(project["dependencies"]) == {"fastapi", "uvicorn"}


def test_the_harness_is_not_installed_to_serve_the_page(project):
    """10.3.1 — the serving process has no scoring to do, so it carries no scorer.

    This is what makes 12.2.5 structural rather than a matter of discipline: a
    computation added to the server would need a library the exhibit install does not
    have, and would fail on the deployed image rather than merely breaking a rule.
    """
    assert named(project["optional-dependencies"]["harness"]) == {
        "numpy",
        "pyarrow",
        "matplotlib",
    }
    assert not named(project["dependencies"]) & named(
        project["optional-dependencies"]["harness"]
    )


def test_the_dev_group_brings_the_harness_the_suite_needs(project):
    """10.3.9 — most of the suite scores something, so `dev` must supply the scorer."""
    assert "harness" in " ".join(project["optional-dependencies"]["dev"])


def test_build_time_tooling_stays_out_of_the_runtime_set(project):
    """10.3.6 — what only *produces* a committed artifact is never installed by default."""
    runtime = " ".join(project["dependencies"])
    for build_only in ("markdown-it-py", "latex2mathml"):
        assert build_only not in runtime
    assert "markdown-it-py" in " ".join(project["optional-dependencies"]["docs"])


def test_no_browser_tooling_survives(project):
    """12.6.3.1 — browser-driven checks are not performed, so nothing declares one."""
    everything = " ".join(
        project["dependencies"]
        + [r for group in project["optional-dependencies"].values() for r in group]
    )
    assert "playwright" not in everything
    assert "selenium" not in everything
