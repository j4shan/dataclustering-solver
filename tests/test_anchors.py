"""Correctness anchors.

Three properties have values derivable without running the evaluator, so they pin it
down on whatever input is handed to it.  There is no fixture dataset: the anchors hold
for any input, so these tests build their own.
"""

from __future__ import annotations

import numpy as np
import pytest

from simulator.core.evaluate import evaluate, summarize_containers
from simulator.core.layout import validate_and_compact

from conftest import make_toy_corpus


def waste_of(corpus, container_of_event) -> int:
    container_count = int(container_of_event.max()) + 1
    containers = summarize_containers(
        container_of_event,
        corpus.event_support,
        corpus.compressed_bytes,
        corpus.decompressed_bytes,
        container_count,
    )
    materialized_volume = int(
        (containers.compressed_bytes * containers.demand_breadth).sum()
    )
    selected_volume = int(corpus.selected_compressed_bytes_by_query.sum())
    return materialized_volume - selected_volume


def single_container_waste(corpus) -> int:
    """The closed form: nothing in the evaluator participates in predicting it."""
    return corpus.queries_appearing_in_log * int(corpus.compressed_bytes.sum()) - int(
        corpus.selected_compressed_bytes_by_query.sum()
    )


def test_one_container_per_event_wastes_nothing(toy_corpus):
    """Every activated container holds only the event that was selected."""
    container_of_event = np.arange(toy_corpus.event_count, dtype=np.int32)
    assert waste_of(toy_corpus, container_of_event) == 0


def test_single_container_matches_the_closed_form(toy_corpus):
    container_of_event = np.zeros(toy_corpus.event_count, dtype=np.int32)
    assert waste_of(toy_corpus, container_of_event) == single_container_waste(toy_corpus)


def test_refinement_never_increases_waste(rng):
    """Splitting a container weakly reduces waste; an increase is always a bug."""
    corpus = make_toy_corpus(rng, event_count=300, query_count=29)
    container_of_event = rng.integers(0, 12, size=corpus.event_count).astype(np.int32)
    before = waste_of(corpus, container_of_event)

    for _ in range(25):
        victim = int(rng.integers(0, container_of_event.max() + 1))
        members = np.flatnonzero(container_of_event == victim)
        if members.size < 2:
            continue
        goes_left = rng.random(members.size) < 0.5
        if not goes_left.any() or goes_left.all():
            continue
        split = container_of_event.copy()
        split[members[goes_left]] = container_of_event.max() + 1
        compacted, _ = validate_and_compact(split, corpus.event_count)
        assert waste_of(corpus, compacted) <= before


def test_extremes_bracket_every_other_layout(rng):
    """The two anchors are also the range every real result has to sit inside."""
    corpus = make_toy_corpus(rng, event_count=250, query_count=31)
    worst = waste_of(corpus, np.zeros(corpus.event_count, dtype=np.int32))
    best = waste_of(corpus, np.arange(corpus.event_count, dtype=np.int32))
    for _ in range(10):
        somewhere_between, _ = validate_and_compact(
            rng.integers(0, 20, size=corpus.event_count), corpus.event_count
        )
        assert best <= waste_of(corpus, somewhere_between) <= worst


@pytest.mark.parametrize("query_count", [1, 63, 64, 65, 128, 129])
def test_word_boundaries(rng, query_count):
    """Packing is only interesting where it wraps a 64-query word."""
    corpus = make_toy_corpus(
        rng, event_count=120, query_count=query_count, selection_share=0.05
    )
    assert waste_of(corpus, np.arange(corpus.event_count, dtype=np.int32)) == 0
    assert waste_of(
        corpus, np.zeros(corpus.event_count, dtype=np.int32)
    ) == single_container_waste(corpus)


def test_skipping_ratios_are_anchored_at_both_extremes(toy_corpus):
    """The two layouts whose skipping is derivable without running the evaluator.

    One container per event: a query opens exactly the events it selected, so the share
    of the corpus it skipped is 1 minus its own selection share. All events in one
    container: every query opens everything, so nothing is skipped at all.
    """
    everything = evaluate(
        toy_corpus, np.zeros(toy_corpus.event_count, dtype=np.int32), 1000
    )["all"]
    assert everything["record_skip_ratio"] == pytest.approx(0.0)
    assert everything["byte_skip_ratio"] == pytest.approx(0.0)
    assert everything["container_skip_ratio"] == pytest.approx(0.0)

    singletons = evaluate(
        toy_corpus, np.arange(toy_corpus.event_count, dtype=np.int32), 1000
    )["all"]
    selection_share = np.array(
        [
            len({e for e, q in toy_corpus.selection_log_pairs if q == query})
            for query in range(toy_corpus.query_count)
        ]
    ) / toy_corpus.event_count
    assert singletons["record_skip_ratio"] == pytest.approx(1.0 - selection_share.mean())


def test_skipping_and_waste_disagree_on_ranking_is_impossible_at_fixed_granularity(rng):
    """At one container count, more skipping must mean less waste — they are two views
    of the same materialized volume, and a divergence would mean one is miscomputed."""
    corpus = make_toy_corpus(rng, event_count=400, query_count=41)
    previous = None
    for seed in range(6):
        layout, _ = validate_and_compact(
            np.random.default_rng(seed).integers(0, 20, size=corpus.event_count),
            corpus.event_count,
        )
        row = evaluate(corpus, layout, 1000)["all"]
        current = (row["byte_skip_ratio"], row["waste_ratio"])
        if previous is not None:
            assert (current[0] > previous[0]) == (current[1] < previous[1]) or current == previous
        previous = current


def test_training_and_validation_waste_account_for_the_total(toy_corpus):
    container_of_event, _ = validate_and_compact(
        np.random.default_rng(9).integers(0, 15, size=toy_corpus.event_count),
        toy_corpus.event_count,
    )
    rows = evaluate(toy_corpus, container_of_event, target_container_rows=1000)
    assert (
        rows["training"]["waste_bytes"] + rows["validation"]["waste_bytes"]
        == rows["all"]["waste_bytes"]
    )
