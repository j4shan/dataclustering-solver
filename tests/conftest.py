"""Random inputs for the correctness anchors.

The anchors hold for *any* input, so the tests build their own arrays rather than
depending on a curated fixture dataset.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pytest

from simulator.core import packed_support

REPO_ROOT = Path(__file__).resolve().parents[1]


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


class ToyCorpus:
    """A minimal stand-in for a loaded dataset.

    ``core.evaluate`` duck-types its dataset — it touches only the supports, the byte
    columns and the query sets — which is what lets the anchors run against arrays built
    here instead of a generated corpus.
    """

    def __init__(
        self,
        event_count,
        query_count,
        compressed_bytes,
        decompressed_bytes,
        selection_log_pairs,
        set_name,
    ):
        self.event_count = event_count
        self.query_count = query_count
        self.compressed_bytes = compressed_bytes
        self.decompressed_bytes = decompressed_bytes
        self.selection_log_pairs = selection_log_pairs
        self.set_name = set_name

        event_index = np.array([e for e, _ in selection_log_pairs], dtype=np.int64)
        query_index = np.array([q for _, q in selection_log_pairs], dtype=np.int64)

        self.event_support = packed_support.support_from_selection_log(
            event_index, query_index, event_count, query_count
        )
        self.selected_compressed_bytes_by_query = np.bincount(
            query_index,
            weights=compressed_bytes[event_index].astype(float),
            minlength=query_count,
        ).astype(np.int64)
        self.selected_decompressed_bytes_by_query = np.bincount(
            query_index,
            weights=decompressed_bytes[event_index].astype(float),
            minlength=query_count,
        ).astype(np.int64)
        self.query_period = np.array([f"P{q % 4}" for q in range(query_count)])

    def query_sets(self):
        training = self.set_name == "training"
        return {
            "training": training,
            "validation": ~training,
            "all": np.ones(self.query_count, dtype=bool),
        }

    @property
    def queries_appearing_in_log(self) -> int:
        """The demand breadth a single container holding everything would have."""
        return len({query for _, query in self.selection_log_pairs})


def make_toy_corpus(rng, event_count=400, query_count=37, selection_share=0.02) -> ToyCorpus:
    compressed_bytes = rng.integers(500, 5_000_000, size=event_count).astype(np.int64)
    decompressed_bytes = compressed_bytes * rng.integers(3, 7, size=event_count)

    selection_log_pairs = set()
    for query in range(query_count):
        # Every query selects at least one event, so every query appears in the log.
        selection_size = max(1, int(rng.poisson(selection_share * event_count)))
        selection_set = rng.choice(
            event_count, size=min(selection_size, event_count), replace=False
        )
        selection_log_pairs.update((int(event), query) for event in selection_set)

    training_count = query_count // 2
    set_name = np.array(
        ["training"] * training_count + ["validation"] * (query_count - training_count)
    )
    return ToyCorpus(
        event_count,
        query_count,
        compressed_bytes,
        decompressed_bytes,
        sorted(selection_log_pairs),
        set_name,
    )


@pytest.fixture
def rng():
    return np.random.default_rng(12345)


@pytest.fixture
def toy_corpus(rng):
    return make_toy_corpus(rng)
