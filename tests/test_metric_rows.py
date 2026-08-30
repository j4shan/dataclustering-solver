"""The shape of a metric row: capacity denomination, run identity, and baseline lift.

These pin what a *row* promises whoever reads it — the sweep's CSV and the GUI's response
carry the same schema (8.10), so one set of expectations covers both.  Every assertion is a row the
runner actually produced — nothing recomputes an evaluation to check one.
"""

from __future__ import annotations

import json

import pytest

from simulator.bench.runner import add_baseline_lift, run_one
from simulator.config import INTERACTIVE_CAPACITIES, SweepConfig
from simulator.core import dataset as dataset_module
from simulator.providers import synthetic
from simulator.providers.synthetic import DatasetConfig


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    config = DatasetConfig(
        name="metric-row-corpus",
        n_events=4_000,
        n_transaction_days=60,
        n_query_days=20,
        half_life_days=5.0,
        seed=515,
    )
    path = synthetic.generate(config, tmp_path_factory.mktemp("metric-rows"))
    return dataset_module.load(path)


def test_the_swept_capacity_is_a_record_count(corpus):
    """7.2.3.1 — the sweep names the unit the bucketer uses, with nothing converted.

    A capacity that divides the corpus evenly produces exactly that many containers, which
    is only true if the number is read as records.  Under the old byte target the same
    figure would have been divided by the corpus mean first.
    """
    rows = run_one(corpus, "insertion_order", 250)
    assert rows[0]["target_container_rows"] == 250
    assert rows[0]["container_count"] == corpus.event_count // 250
    assert json.loads(rows[0]["Params"])["target_container_rows"] == 250


def test_size_health_counts_the_floor_in_records_and_percentiles_in_bytes(corpus):
    """6.3.5 — a shortfall is only meaningful in the unit of the target it falls short of.

    Every container but the last is full at a capacity that does not divide the corpus,
    so exactly one falls below the floor while the byte percentiles stay byte-scaled.
    """
    row = run_one(corpus, "insertion_order", 300)[0]
    assert corpus.event_count % 300 != 0, "fixture must not divide evenly"
    assert row["containers_below_target"] == 1
    assert row["container_records_p50"] == 300
    assert row["container_bytes_p50"] > 1000  # bytes, not records


def test_a_full_layout_is_charged_no_fragmentation(corpus):
    """The cost model's shortfall term re-denominates with the sweep (7.2.3.1).

    At a capacity that divides the corpus, no container is short of anything, so the
    fragmentation term is exactly zero and management cost is the container count alone.
    """
    row = run_one(corpus, "insertion_order", 250)[0]
    assert row["management_cost_fragmentation_term"] == 0.0
    assert row["management_cost"] == row["container_count"]


def test_activated_volume_is_reported_in_both_denominations(corpus):
    """6.3.8 — the record count and the byte weight of what activation materialized.

    Both are columns because they can rank two layouts differently whenever activation
    concentrates in unusually sized events; a ratio hides which of the two moved.
    """
    row = run_one(corpus, "insertion_order", 250)[0]
    assert row["materialized_records"] > 0
    assert row["materialized_bytes"] > 0
    assert row["materialized_bytes"] >= row["selected_bytes"]


def test_rows_of_one_evaluation_share_a_run_id_and_a_batch(corpus):
    """8.3.1 — the run id names the evaluation, the batch id names the request."""
    rows = run_one(corpus, "insertion_order", 250, batch_id="one-click")
    assert {row["Batch_ID"] for row in rows} == {"one-click"}
    assert len({row["Run_ID"] for row in rows}) == 1
    assert {row["Set_Name"] for row in rows} == {"training", "validation", "all"}


def test_evaluations_of_one_batch_keep_distinct_run_ids(corpus):
    """Twenty rows landing at one timestamp are not twenty unrelated runs (8.3.1)."""
    produced = [
        run_one(corpus, "insertion_order", capacity, batch_id="one-click")
        for capacity in (250, 500)
    ]
    run_ids = {row["Run_ID"] for rows in produced for row in rows}
    batch_ids = {row["Batch_ID"] for rows in produced for row in rows}
    assert len(run_ids) == 2
    assert batch_ids == {"one-click"}


def test_a_lone_evaluation_is_its_own_batch(corpus):
    """A caller that asks for nothing still gets a usable provenance pair."""
    row = run_one(corpus, "insertion_order", 250)[0]
    assert row["Batch_ID"] == row["Run_ID"]


def test_baseline_lift_is_blank_at_a_capacity_the_baseline_never_swept(corpus):
    """12.4.5.4 — a comparison against a layout that was never built is not a comparison."""
    rows = add_baseline_lift(
        run_one(corpus, "insertion_order", 250)
        + run_one(corpus, "random_order", 250)
        + run_one(corpus, "random_order", 333)
    )
    matched = [r for r in rows if r["Strategy_Name"] == "random_order" and r["target_container_rows"] == 250]
    unmatched = [r for r in rows if r["target_container_rows"] == 333]
    assert all(r["baseline_lift"] is not None for r in matched)
    assert all(r["baseline_lift"] is None for r in unmatched)


def test_the_sweep_and_the_interactive_capacities_are_both_record_counts():
    """The CLI sweeps eight capacities; the catalogue sweeps four of them (8.11, 12.4.5.1)."""
    config = SweepConfig()
    assert config.variable == "target_container_rows"
    assert config.default_rows in config.values
    assert len(INTERACTIVE_CAPACITIES) == 4
    assert all(isinstance(capacity, int) for capacity in INTERACTIVE_CAPACITIES)
