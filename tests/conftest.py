"""Shared helpers.

Whether a file a test depends on would survive a clone is a question for git, not for
the disk, so the helpers that ask it live here.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Authoring material — diagram sources, figure prompts, scenario data. Never served,
#: never published, so no test may reach it through the site tree.
RESOURCES = REPO_ROOT / "resources"


def _git(*args) -> subprocess.CompletedProcess:
    if not (REPO_ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)


def is_excluded_from_the_repository(path) -> bool:
    """Would a clone be missing this file?

    A test that reads a path off the working tree proves the file is on *this* machine,
    not that it ships. The two came apart once already: an unanchored ignore rule
    swallowed the committed scenario file, every filesystem assertion kept passing, and a
    clone could not regenerate a single figure. So wherever a test depends on a file
    being present for someone else, it asks git rather than the disk.

    Tracked settles it — ignore rules do not apply to a file already in the index, which
    is why `git check-ignore` stays silent about one and why asking it alone is not
    enough. Untracked is not the question either: a newly generated artifact is untracked
    until it is staged, and that is work in progress. Untracked *and* ignored is the
    question, because no one can stage that without changing a rule.
    """
    if _git("ls-files", "--error-unmatch", str(path)).returncode == 0:
        return False
    return an_ignore_rule_matches(path)


def an_ignore_rule_matches(path) -> bool:
    """Does some ignore rule name this path, whether or not it is tracked today?

    A tracked file still ships, so this is not the same failure as the one above — it is
    the trap set for later. Drop such a file from the index for any reason and it cannot
    be added back, and the rule that swallowed it was written for something else.
    """
    return _git("check-ignore", "--no-index", "-q", str(path)).returncode == 0
