"""The Assignment Strategy family (12.4.1).

Most of these run against a hand-built view rather than a generated corpus, because the
properties being pinned — a full container, a respected capacity, a permutation that
changes nothing — are arithmetic a reader should be able to check by eye.
"""

from __future__ import annotations

import numpy as np
import pytest

from simulator.core import packed_support
from simulator.core import dataset as dataset_module
from simulator.providers import synthetic
from simulator.providers.synthetic import DatasetConfig
from simulator.strategies import Expression, ExpressionChainError, build_view, entry, get
from simulator.strategies import group_by_chain as family
from simulator.strategies.group_by_chain import (
    MAX_CHAIN_LENGTH,
    bucket_leaves,
    canonical,
    chain_structure,
    leaf_of_event,
)
from simulator.strategies.registry import TrainingView


def view_over(features: dict, capacity: int, event_id=None) -> TrainingView:
    """A TrainingView carrying nothing but what this family reads."""
    event_count = len(next(iter(features.values())))
    return TrainingView(
        event_count=event_count,
        query_count=1,
        features=features,
        compressed_bytes=np.ones(event_count, dtype=np.int64),
        decompressed_bytes=np.ones(event_count, dtype=np.int64),
        size_columns={},
        visible_support=packed_support.empty_support(event_count, 1),
        training_query_ids=np.array([0]),
        training_query_times=np.array(["2024-01-01"], dtype="datetime64[D]"),
        target_container_rows=capacity,
        event_id=np.arange(event_count) if event_id is None else np.asarray(event_id),
    )


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    config = DatasetConfig(
        name="chain-corpus",
        n_events=5_000,
        n_transaction_days=60,
        n_query_days=20,
        half_life_days=5.0,
        seed=77,
    )
    return dataset_module.load(
        synthetic.generate(config, tmp_path_factory.mktemp("chain"))
    )


# -- the two steps ------------------------------------------------------------------


def test_the_chain_groups_events_that_share_a_key_tuple():
    """A leaf is the equivalence class of the whole tuple, not of the last stage."""
    features = {
        "brand": np.array(["a", "a", "b", "b", "a", "b"], dtype=object),
        "tier": np.array([1, 9, 1, 9, 9, 1], dtype=np.int64),
    }
    chain = (Expression.parse("brand"), Expression.parse("tier > 5"))
    leaf = leaf_of_event(chain, features, 6)

    # (a,low) (a,high) (b,low) (b,high) (a,high) (b,low)
    assert leaf.tolist() == [0, 1, 2, 3, 1, 2]
    assert len(set(leaf.tolist())) == 4


def test_a_leaf_no_larger_than_the_capacity_becomes_one_container():
    leaf = np.array([0, 0, 0, 1, 1])
    containers = bucket_leaves(leaf, np.arange(5), capacity=3)
    assert containers.tolist() == [0, 0, 0, 1, 1]


def test_a_large_leaf_is_filled_to_the_brim_and_the_last_takes_the_remainder():
    """12.4.1.4 — the baseline's packing rule, applied inside every leaf.

    Ten records at a capacity of four give 4/4/2: two full containers and what is left.
    """
    containers = bucket_leaves(np.zeros(10, dtype=np.int64), np.arange(10), capacity=4)
    assert np.bincount(containers).tolist() == [4, 4, 2]


def test_only_the_last_container_of_a_leaf_is_ever_short():
    """The property behind the rule, over several leaves of unequal size at once."""
    leaf = np.repeat([0, 1, 2], [10, 4, 7])
    containers = bucket_leaves(leaf, np.arange(21), capacity=4)
    for one in np.unique(leaf):
        sizes = np.bincount(containers[leaf == one])
        sizes = sizes[sizes > 0].tolist()
        assert all(size == 4 for size in sizes[:-1]), sizes
        assert 0 < sizes[-1] <= 4, sizes
    assert np.bincount(containers).tolist() == [4, 4, 2, 4, 4, 3]


def test_a_leaf_that_divides_exactly_has_no_remainder():
    """Nothing manufactures an empty container when the count comes out even."""
    containers = bucket_leaves(np.zeros(8, dtype=np.int64), np.arange(8), capacity=4)
    assert np.bincount(containers).tolist() == [4, 4]


@pytest.mark.parametrize(
    "event_count, capacity",
    [
        (1, 1),  # one event, capacity one — the smallest thing there is
        (1, 10),  # capacity larger than the whole input
        (7, 3),  # a remainder in every leaf
        (10, 10),  # capacity exactly the input size
        (33, 4),  # uneven leaves, uneven remainders
        (100, 1),  # every event its own container
        (101, 4),  # one past a round number
    ],
)
def test_the_capacity_is_never_exceeded(event_count, capacity):
    """It is a maximum, so no arrangement of any leaf may overshoot it.

    The pairs are chosen boundaries rather than a cross product: this asserts one
    invariant, and a full grid runs the same code path twenty-eight times.
    """
    leaf = np.arange(event_count) % 3
    containers = bucket_leaves(leaf, np.arange(event_count), capacity=capacity)
    assert np.bincount(containers).max() <= capacity


@pytest.mark.parametrize(
    "event_count, capacity",
    [(1, 1), (7, 4), (33, 4), (100, 1), (100, 10)],
)
def test_every_event_lands_in_exactly_one_container(event_count, capacity):
    leaf = np.arange(event_count) % 4
    containers = bucket_leaves(leaf, np.arange(event_count), capacity=capacity)
    assert containers.shape == (event_count,)
    assert set(np.unique(containers).tolist()) == set(range(containers.max() + 1))


def test_a_container_never_spans_two_leaves():
    """Bucketing happens *within* a leaf; the split would mean nothing otherwise."""
    leaf = np.array([0, 0, 0, 1, 1, 1, 2])
    containers = bucket_leaves(leaf, np.arange(7), capacity=10)
    for container in np.unique(containers):
        assert len(set(leaf[containers == container].tolist())) == 1


def test_records_fill_a_container_in_arrival_order_not_row_order():
    """`record_id` carries arrival; an external corpus need not be written in it."""
    features = {"tier": np.zeros(6, dtype=np.int64)}
    shuffled = view_over(features, capacity=3, event_id=[5, 4, 3, 2, 1, 0])
    containers = get("group_by_chain")(shuffled, expressions=[])
    # Rows 5,4,3 arrived first, so they share the first container.
    assert containers.tolist() == [1, 1, 1, 0, 0, 0]


# -- the two properties the spec leans on -------------------------------------------


@pytest.mark.parametrize("capacity", [1, 7, 250, 333, 1000])
def test_the_empty_chain_reproduces_the_baseline_byte_for_byte(corpus, capacity):
    """12.4.1.5 — the baseline is this family's degenerate case, not a rival mechanism.

    At every capacity, including ones the corpus does not divide by. 12.4.1.4's packing
    is the baseline's own, so the degenerate case is the same array and not merely an
    equivalent grouping — which is only exact because both fill to the brim.
    """
    view = build_view(corpus, capacity)
    assert np.array_equal(
        get("insertion_order")(view), get("group_by_chain")(view, expressions=[])
    )


@pytest.mark.parametrize(
    "chain",
    [
        ["brand_id", "feature_price_tier > 5"],
        ["feature_price_tier > 5", "brand_id"],
        ["feature_warranty_years", "brand_id", "feature_price_tier / 4"],
    ],
)
def test_permuting_the_chain_produces_the_identical_layout(corpus, chain):
    """12.4.1.3 — order is not a parameter, so it may not reach the array either."""
    view = build_view(corpus, 250)
    reference = get("group_by_chain")(view, expressions=sorted(chain))
    assert np.array_equal(get("group_by_chain")(view, expressions=chain), reference)
    assert np.array_equal(
        get("group_by_chain")(view, expressions=list(reversed(chain))), reference
    )


def test_canonical_order_is_what_makes_that_true():
    """Stated separately, because it is the mechanism and not the promise."""
    chain = [Expression.parse("tier > 5"), Expression.parse("brand")]
    assert [str(e) for e in canonical(chain)] == ["brand", "tier > 5"]
    assert canonical(chain) == canonical(list(reversed(chain)))


def test_the_family_is_deterministic(corpus):
    view = build_view(corpus, 250)
    chain = ["brand_id", "feature_price_tier > 5"]
    assert np.array_equal(
        get("group_by_chain")(view, expressions=chain),
        get("group_by_chain")(view, expressions=chain),
    )


# -- refusing to run --------------------------------------------------------------


def test_an_unknown_column_is_rejected_before_any_event_moves(corpus):
    view = build_view(corpus, 250)
    with pytest.raises(ExpressionChainError, match="unknown column"):
        get("group_by_chain")(view, expressions=["brnad_id"])


def test_every_bad_stage_is_reported_at_once(corpus):
    view = build_view(corpus, 250)
    with pytest.raises(ExpressionChainError) as raised:
        get("group_by_chain")(view, expressions=["nope", "brand_id", "also_nope"])
    assert [failure.stage for failure in raised.value.failures] == [0, 2]


def test_a_size_column_is_not_a_feature_and_cannot_be_split_on(corpus):
    """7.1.2.2 — a family that partitions on every feature must not reach byte counts."""
    view = build_view(corpus, 250)
    size_column = next(iter(corpus.size_columns))
    with pytest.raises(ExpressionChainError, match="unknown column"):
        get("group_by_chain")(view, expressions=[size_column])


def test_a_hidden_column_cannot_be_split_on(corpus):
    """4.9 — generator truth is analysable, not partitionable."""
    view = build_view(corpus, 250)
    hidden = next(iter(corpus.hidden_event_columns))
    with pytest.raises(ExpressionChainError, match="unknown column"):
        get("group_by_chain")(view, expressions=[hidden])


# -- how it registers ---------------------------------------------------------------


def test_it_registers_as_a_demonstration_fixture():
    """12.4.1.6 — it reads features, so it may never be labelled a baseline (7.1.2.3)."""
    registered = entry("group_by_chain")
    assert registered.kind == "demonstration"


def test_its_one_parameter_is_a_bounded_expression_set():
    """7.1.7.3 — the bound is on the parameter, not on whatever renders it."""
    spec = entry("group_by_chain").params[0]
    assert (spec.name, spec.kind) == ("expressions", "expression_set")
    assert spec.maximum_length == MAX_CHAIN_LENGTH == 4
    assert spec.describe()["maximum_length"] == 4
    assert not spec.required  # the empty chain is the baseline, and it is valid


# -- the process view's data (12.4.4.2) ----------------------------------------------


def profile_features(rng=None):
    """Three columns of unequal cardinality, so every prefix has a distinct count."""
    return {
        "a": np.array(list("xy") * 6),
        "b": np.arange(12) % 3,
        "c": np.arange(12) % 4,
    }


def test_the_stages_are_the_canonical_chain_in_canonical_order():
    """12.4.4.2 — an arrow per stage, carrying the expression as the grammar spells it."""
    features = profile_features()
    chain = [Expression.parse(text) for text in ("c", "a", "b")]

    stages = chain_structure(chain, features, 12)
    assert [entry["expression"] for entry in stages] == [str(e) for e in canonical(chain)]


def test_each_stage_carries_the_splits_the_corpus_stands_in_after_it():
    """8.11.2 — the count is cumulative over the prefix, not the stage in isolation.

    `a` takes two values and `b` three, so after `a` the corpus is in 2 groups and after
    `a·b` it is in 6.  Both are derivable without running the code, which is what makes
    this an anchor rather than a recomputation (10.1.4).
    """
    features = profile_features()
    stages = chain_structure([Expression.parse(t) for t in ("a", "b")], features, 12)
    assert [entry["splits"] for entry in stages] == [2, 6]


def test_the_last_stage_is_the_leaf_count(): 
    """8.11.2 — the whole chain is its own last prefix, so the two cannot disagree."""
    features = profile_features()
    chain = [Expression.parse(t) for t in ("a", "b", "c")]
    stages = chain_structure(chain, features, 12)
    assert stages[-1]["splits"] == len(np.unique(leaf_of_event(chain, features, 12)))


def test_a_stage_carries_its_expression_and_its_splits_and_nothing_else():
    """12.4.2.1 — what the catalogue lists, and 13.16 — what P1 must not draw."""
    features = profile_features()
    stages = chain_structure([Expression.parse(t) for t in ("a", "b", "c")], features, 12)
    assert all(set(entry) == {"expression", "splits"} for entry in stages)


def test_the_stages_are_the_same_whatever_order_the_chain_arrives_in():
    """12.4.1.3 — order is a no-op, and the diagram must not imply otherwise."""
    features = profile_features()
    forward = [Expression.parse(t) for t in ("a", "b", "c")]
    assert chain_structure(forward, features, 12) == chain_structure(
        list(reversed(forward)), features, 12
    )


def test_an_empty_chain_has_no_stages():
    """12.4.1.5 — the degenerate case is legal, and its diagram is a root with no arrows."""
    assert chain_structure([], profile_features(), 12) == []


# -- the overflow fallback ------------------------------------------------------------


def test_the_slow_path_agrees_with_the_mixed_key_exactly(monkeypatch):
    """The fallback runs only when the key would not fit an int64 (a wide four-stage
    chain), so nothing on the shipped corpus reaches it. Forced here, because a branch
    no test enters is a branch that rots.
    """
    features = profile_features()
    chain = [Expression.parse(t) for t in ("a", "b", "c")]

    fast_leaf = leaf_of_event(chain, features, 12)

    monkeypatch.setattr(family, "_mixed_key", lambda codes, widths: None)
    assert np.array_equal(leaf_of_event(chain, features, 12), fast_leaf)


def test_the_mixed_key_refuses_a_product_that_would_not_fit():
    """The guard bounds the product of the widths, before anything overflows."""
    codes = [np.zeros(4, dtype=np.int64) for _ in range(3)]
    assert family._mixed_key(codes, [2, 3, 4]) is not None
    assert family._mixed_key(codes, [2**32, 2**32, 2**32]) is None
