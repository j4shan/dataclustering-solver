"""Invariants, re-checked against a real generated dataset.

The anchors in ``test_anchors`` prove the evaluator on arbitrary arrays.  These re-run
the same properties once a provider has produced an actual corpus, which is where a
mismatch between the generator and the contract would surface.
"""

from __future__ import annotations

import numpy as np
import pytest

from simulator.core import dataset as dataset_module
from simulator.core import packed_support
from simulator.core.evaluate import evaluate, summarize_containers
from simulator.core.layout import InvalidLayout, validate_and_compact
from simulator.providers import synthetic
from simulator.providers.synthetic import DatasetConfig


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    config = DatasetConfig(
        name="test-corpus",
        n_events=6_000,
        n_transaction_days=72,
        n_query_days=24,  # both types run daily, so 48 queries
        half_life_days=6.0,  # 12 half-lives across 72 days, as shipped
        seed=99,
    )
    path = synthetic.generate(config, tmp_path_factory.mktemp("corpus"))
    return dataset_module.load(path)


def waste_of(corpus, container_of_event) -> int:
    containers = summarize_containers(
        container_of_event,
        corpus.event_support,
        corpus.compressed_bytes,
        corpus.decompressed_bytes,
        int(container_of_event.max()) + 1,
    )
    materialized_volume = int(
        (containers.compressed_bytes * containers.demand_breadth).sum()
    )
    return materialized_volume - int(corpus.selected_compressed_bytes_by_query.sum())


def test_query_time_boundary_is_consistent_with_set_name(corpus):
    """A corpus that mislabels its split must fail loudly, not report interpolation."""
    training = corpus.set_name == "training"
    assert training.any() and (~training).any()
    assert corpus.query_time[training].max() <= corpus.query_time[~training].min()


def test_query_ids_are_unique(corpus):
    assert len(np.unique(corpus.query_id)) == corpus.query_count


def test_every_query_has_a_non_empty_selection_set(corpus):
    assert (corpus.selected_compressed_bytes_by_query > 0).all()


def test_demand_decays_with_age_and_never_stops(corpus):
    """Recency is a decaying weight, not a cutoff — the property the whole corpus turns on.

    Two things have to hold together, and it is easy to build a generator that gets one
    without the other. Demand must fall steeply with age (or the layout has no cold
    region to skip), *and* no age may be categorically unreachable (or the model is a
    hard window wearing a decay's clothing).
    """
    support_size = packed_support.support_size(corpus.event_support)
    age_rank = np.argsort(np.argsort(corpus.features["feature_transaction_date"]))
    quartile = age_rank * 4 // corpus.event_count  # 0 = oldest, 3 = newest
    mean_demand = [support_size[quartile == q].mean() for q in range(4)]

    # Checked over the aged region only. Demand is *not* monotone at the newest end and
    # should not be: a transaction from the final day existed for only one query day, so
    # it had fewer chances to be selected than one from six months earlier. That is
    # causality, not weak decay, and asserting monotonicity across all four would be
    # asserting something false.
    assert mean_demand[0] < mean_demand[1] < mean_demand[2], (
        f"demand does not decay with age: {mean_demand}"
    )
    assert max(mean_demand) > 4 * mean_demand[0], "decay too weak to create a cold region"

    # ... and the oldest quartile is still reachable: some of it is selected.
    assert (support_size[quartile == 0] > 0).any(), "oldest data categorically excluded"


def test_the_corpus_contains_never_selected_events(corpus):
    """Events no query ever wanted — formulation §3.2 and §8.6 both turn on these existing.

    Under a decay model they arise probabilistically rather than by a boundary, so the
    assertion is distributional: they exist, and they skew old.
    """
    never_selected = packed_support.support_size(corpus.event_support) == 0
    assert never_selected.any()

    transaction_date = corpus.features["feature_transaction_date"].astype("datetime64[D]").astype(int)
    assert transaction_date[never_selected].mean() < transaction_date[~never_selected].mean()


def test_demand_rises_with_the_brand_multiplier(corpus):
    """`brand_id` is the corpus's strongest signal, and it has to actually be one.

    Asserted as a monotone trend between the lowest and highest multiplier present rather
    than pairwise across all ten: the draw is Bernoulli, so adjacent multipliers can and
    do swap places by sampling noise without the signal being absent.
    """
    support_size = packed_support.support_size(corpus.event_support)
    multiplier = corpus.hidden_event_columns["_brand_demand_multiplier"]

    present = sorted(set(multiplier.tolist()))
    assert len(present) > 1, "corpus has no spread of brand multipliers to test"

    lowest = support_size[multiplier == present[0]].mean()
    highest = support_size[multiplier == present[-1]].mean()
    assert highest > 2 * lowest, (
        f"brand multiplier {present[0]} -> {present[-1]} moved demand only "
        f"{lowest:.2f} -> {highest:.2f}"
    )


def test_the_brand_multiplier_redistributes_demand_without_adding_it(corpus):
    """The multiplier is a relative scale: the draw is normalized back to the target rate.

    If it inflated the overall rate instead, brand would be a volume knob rather than a
    clusterable structure, and the corpus's selection rates would drift with `n_brands`.
    """
    selected_per_query = corpus.manifest["selection_log_rows"] / corpus.query_count
    share = selected_per_query / corpus.event_count
    config = corpus.manifest["config"]
    expected = (config["profitability_rate"] + config["complaint_rate"]) / 2
    assert share == pytest.approx(expected, rel=0.35), (
        f"selected share per query {share:.4f} is far from the configured {expected:.4f}"
    )


def test_events_with_empty_support_are_handled(corpus):
    """An event no query wants still occupies storage and contributes no demand breadth.

    Asserted against a corpus constructed to contain such events rather than against
    whichever ones the generator happens to leave out, so the arithmetic below is tested
    at a known size regardless of how the workload is parameterized.
    """
    cold_events = slice(0, corpus.event_count // 10)
    support_with_cold = corpus.event_support.copy()
    support_with_cold[cold_events] = 0
    assert (packed_support.support_size(support_with_cold) == 0).sum() >= (
        corpus.event_count // 10
    )

    # Put every cold event in container 1 and everything else in container 0.
    container_of_event = np.zeros(corpus.event_count, dtype=np.int32)
    container_of_event[cold_events] = 1

    containers = summarize_containers(
        container_of_event,
        support_with_cold,
        corpus.compressed_bytes,
        corpus.decompressed_bytes,
        2,
    )

    # No query activates it, so it is read by nobody however large it is ...
    assert containers.demand_breadth[1] == 0
    assert int((containers.compressed_bytes * containers.demand_breadth).sum()) == int(
        containers.compressed_bytes[0] * containers.demand_breadth[0]
    )
    # ... and it still carries real bytes, so size health continues to count it.
    assert containers.compressed_bytes[1] > 0


def test_training_and_validation_waste_account_for_the_total(corpus):
    container_of_event, _ = validate_and_compact(
        np.random.default_rng(3).integers(0, 40, size=corpus.event_count),
        corpus.event_count,
    )
    rows = evaluate(corpus, container_of_event, 200)
    assert (
        rows["training"]["waste_bytes"] + rows["validation"]["waste_bytes"]
        == rows["all"]["waste_bytes"]
    )
    for set_name in ("training", "validation", "all"):
        assert rows[set_name]["materialized_bytes"] >= rows[set_name]["selected_bytes"]


def test_single_container_upper_bound(corpus):
    container_of_event = np.zeros(corpus.event_count, dtype=np.int32)
    queries_in_log = int((corpus.selected_compressed_bytes_by_query > 0).sum())
    expected = queries_in_log * int(corpus.compressed_bytes.sum()) - int(
        corpus.selected_compressed_bytes_by_query.sum()
    )
    assert waste_of(corpus, container_of_event) == expected


def test_one_container_per_event_wastes_nothing(corpus):
    assert waste_of(corpus, np.arange(corpus.event_count, dtype=np.int32)) == 0


def test_refinement_never_increases_waste(corpus):
    rng = np.random.default_rng(11)
    container_of_event, _ = validate_and_compact(
        rng.integers(0, 25, size=corpus.event_count), corpus.event_count
    )
    before = waste_of(corpus, container_of_event)
    for _ in range(8):
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


@pytest.mark.parametrize("defect", ["wrong_length", "negative_ids"])
def test_layout_validation_rejects_malformed_returns(corpus, defect):
    malformed = (
        np.array([0, 1, 2])
        if defect == "wrong_length"
        else -np.ones(corpus.event_count, dtype=np.int32)
    )
    with pytest.raises(InvalidLayout):
        validate_and_compact(malformed, corpus.event_count)


def test_container_ids_are_compacted(corpus):
    sparse_labels = np.full(corpus.event_count, 7, dtype=np.int64)
    sparse_labels[: corpus.event_count // 2] = 4000
    compacted, container_count = validate_and_compact(sparse_labels, corpus.event_count)
    assert container_count == 2
    assert set(np.unique(compacted).tolist()) == {0, 1}
