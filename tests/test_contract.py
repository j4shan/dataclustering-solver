"""The strategy plugin contract, checked against a real generated dataset."""

from __future__ import annotations

import numpy as np
import pytest

from simulator.core import dataset as dataset_module
from simulator.core import packed_support
from simulator.core.layout import validate_and_compact
from simulator.providers import synthetic
from simulator.providers.synthetic import DatasetConfig
from simulator.strategies import (
    RouteMismatch,
    available,
    build_view,
    check_route,
    entry,
    get,
)


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    config = DatasetConfig(
        name="contract-corpus",
        n_events=5_000,
        n_transaction_days=60,
        n_query_days=20,  # both types run daily, so 40 queries
        half_life_days=5.0,
        seed=4242,
    )
    path = synthetic.generate(config, tmp_path_factory.mktemp("contract"))
    return dataset_module.load(path)


def test_validation_queries_are_removed_from_the_view(corpus):
    """Leakage is impossible by construction: those flags are physically zero."""
    view = build_view(corpus, 100)
    flags = packed_support.unpack_support_flags(view.visible_support, corpus.query_count)

    validation = np.flatnonzero(corpus.set_name == "validation")
    training = np.flatnonzero(corpus.set_name == "training")
    assert flags[:, validation].sum() == 0
    assert flags[:, training].sum() > 0


def test_the_dataset_itself_keeps_every_query(corpus):
    """Withholding happens in the view; the corpus is untouched."""
    flags = packed_support.unpack_support_flags(corpus.event_support, corpus.query_count)
    validation = np.flatnonzero(corpus.set_name == "validation")
    assert flags[:, validation].sum() > 0


def test_cold_events_exist(corpus):
    """Events wanted only by validation queries look, to a strategy, like events nobody
    ever wanted.  They must still be placed, from features alone."""
    view = build_view(corpus, 100)
    never_wanted = packed_support.support_size(corpus.event_support) == 0
    invisible = view.visible_support_size == 0
    assert (invisible & ~never_wanted).sum() > 0


def test_hidden_columns_are_gated(corpus):
    ordinary = build_view(corpus, 100)
    assert not any(name.startswith("_") for name in ordinary.features)

    opened = build_view(corpus, 100, allow_hidden_columns=True)
    assert any(name.startswith("_") for name in opened.features)


def test_every_column_is_reachable_by_dynamic_key(corpus):
    """A strategy names columns at runtime; the harness declares no attribute per column.

    This is what lets a strategy be written against a corpus whose columns this project
    has never seen, so it is asserted rather than left to convention.
    """
    view = build_view(corpus, 100)

    for name in ("brand_id", "feature_price_tier", "feature_category"):
        assert view.features[name].shape == (corpus.event_count,)
    for name in ("blob_detail_compressed_bytes", "blob_detail_decompressed_bytes"):
        assert view.size_columns[name].shape == (corpus.event_count,)


def test_size_columns_are_not_features(corpus):
    """A strategy partitioning on every feature must not silently partition on bytes."""
    view = build_view(corpus, 100)
    assert set(view.features) & set(view.size_columns) == set()
    assert not any(name.startswith("blob_") for name in view.features)

    # The totals the objective uses still agree with the columns they were summed from.
    assert view.compressed_bytes.tolist() == (
        view.size_columns["blob_detail_compressed_bytes"].tolist()
    )


def test_brand_id_reaches_strategies(corpus):
    """The corpus's strongest demand driver is discoverable, not latent.

    The shipped baselines deliberately ignore it — they read no feature at all — but a
    third-party strategy must be able to cluster on the tenant.
    """
    view = build_view(corpus, 100)
    assert "brand_id" in view.features
    assert len(set(view.features["brand_id"].tolist())) > 1


def test_view_exposes_training_query_times(corpus):
    """So a strategy can weight recent demand over year-old demand."""
    view = build_view(corpus, 100)
    training = corpus.set_name == "training"
    assert view.training_query_times.size == int(training.sum())
    assert view.training_query_times.max() <= corpus.query_time[~training].min()


@pytest.mark.parametrize("strategy_name", ["insertion_order", "random_order"])
@pytest.mark.parametrize("target_container_rows", [100, 800, 6400])
def test_example_strategies_return_valid_layouts(corpus, strategy_name, target_container_rows):
    view = build_view(corpus, target_container_rows)
    container_of_event, container_count = validate_and_compact(
        get(strategy_name)(view), corpus.event_count
    )
    assert container_of_event.shape == (corpus.event_count,)
    assert container_count >= 1
    assert set(np.unique(container_of_event).tolist()) == set(range(container_count))


def test_registry_lists_the_shipped_strategies():
    assert available() == ["group_by_chain", "insertion_order", "random_order"]


def test_the_shipped_strategies_divide_into_baselines_and_one_fixture():
    """7.1.2.3 — the distinction is load-bearing, so it is asserted and not assumed.

    Two baselines bracket what ordering alone is worth; the one demonstration family
    exists to give the GUI something to configure, and is never a result (1.2).
    """
    by_kind: dict[str, list[str]] = {}
    for name in available():
        by_kind.setdefault(entry(name).kind, []).append(name)
    assert by_kind == {
        "baseline": ["insertion_order", "random_order"],
        "demonstration": ["group_by_chain"],
    }


def test_insertion_order_builds_fixed_row_containers(corpus):
    """The swept capacity *is* the row count, and every full container hits it (7.2.3.1)."""
    view = build_view(corpus, 250)
    container_of_event, container_count = validate_and_compact(
        get("insertion_order")(view), corpus.event_count
    )
    rows_per_container = np.bincount(container_of_event, minlength=container_count)

    # Every container but the last holds exactly the derived row count.
    assert set(rows_per_container[:-1].tolist()) == {250}
    assert 0 < rows_per_container[-1] <= 250


@pytest.mark.parametrize("strategy_name", ["insertion_order", "random_order"])
def test_shipped_strategies_are_deterministic(corpus, strategy_name):
    """Including the random one — it shuffles from a fixed seed."""
    first = get(strategy_name)(build_view(corpus, 100))
    second = get(strategy_name)(build_view(corpus, 100))
    assert np.array_equal(first, second)


def test_random_order_actually_reorders(corpus):
    """Otherwise the two shipped strategies would silently be the same layout."""
    view = build_view(corpus, 100)
    assert not np.array_equal(get("random_order")(view), get("insertion_order")(view))


def test_random_order_also_builds_fixed_row_containers(corpus):
    """The two differ in ordering only — granularity must be identical, or the sweep
    would be comparing container sizes rather than orderings."""
    view = build_view(corpus, 100)
    sizes = [
        np.bincount(validate_and_compact(get(name)(view), corpus.event_count)[0])
        for name in ("insertion_order", "random_order")
    ]
    assert sorted(sizes[0].tolist()) == sorted(sizes[1].tolist())


def test_insertion_order_is_the_arrival_sequence_cut_by_capacity(corpus):
    """Closed form: with `record_id` the arrival sequence (4.2), event i is in i // c.

    Derivable without running the strategy, which is the point — the layout is a function
    of the key and the capacity, not of the corpus around each event.
    """
    view = build_view(corpus, 250)
    expected = np.arange(corpus.event_count) // 250

    assert np.array_equal(get("insertion_order")(view), expected)


def test_the_baseline_route_agrees_with_the_layout_it_belongs_to(corpus):
    """7.1.5.1 — the seam's first instance, held to its claim rather than trusted."""
    view = build_view(corpus, 250)
    layout = get("insertion_order")(view)

    assert check_route("insertion_order", view, layout) > 0


def test_a_route_sees_one_event_and_no_corpus(corpus):
    """7.1.6 — what `route` is handed is what a newly arrived event carries (3.4.3)."""
    view = build_view(corpus, 250)
    event = view.event(17)

    assert event["record_id"] == corpus.event_id[17]
    assert set(event) == {"record_id", *view.features, *view.size_columns}


def test_a_route_that_disagrees_with_its_layout_is_rejected(corpus):
    """A route is a claim about a layout; the harness holds the strategy to it."""
    view = build_view(corpus, 250)
    layout = get("insertion_order")(view)
    liar = entry("insertion_order").__class__(
        name="liar",
        call=get("insertion_order"),
        label="Liar",
        description="Routes every event to container 0.",
        kind="baseline",
        route=lambda **_: (lambda features: 0),
    )

    with pytest.raises(RouteMismatch, match="liar"):
        check_route(liar, view, layout)


def test_a_strategy_claiming_no_route_is_checked_for_nothing(corpus):
    """`route` is optional (7.1.6): declaring none is not a failure, it is silence."""
    view = build_view(corpus, 250)

    assert entry("random_order").route is None
    assert check_route("random_order", view, get("random_order")(view)) == 0
