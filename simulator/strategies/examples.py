"""The shipped strategies.

Neither is research, and neither is a recommendation. They exist so the harness has
something to run and the charts have points on them, and between them they span **floor
to industry default** (7.1.5): `random_order` destroys all structure, while
`insertion_order` preserves arrival order — which on a corpus accumulating in time is the
age-ordered layout most storage systems apply without being asked. A candidate strategy
is read against `insertion_order`, because beating the default is the claim that matters;
`random_order` only says what structure is worth at all.

Both are deterministic — `random_order` shuffles from a fixed seed — so two runs on one
corpus produce byte-identical layouts and any change in a reported number came from the
corpus or the evaluator.
"""

from __future__ import annotations

import numpy as np

from ..core.contract import RECORD_ID
from .registry import TrainingView, register
from .schema import ParamSpec

#: Fixed so a "random" layout is still reproducible. Reported in the metric row's Params.
RANDOM_ORDER_SEED = 20260809


def _cut_into_containers(order: np.ndarray, view: TrainingView) -> np.ndarray:
    """Assign container ids by position in ``order``, cutting every N rows.

    Containers hold a fixed *row* count, so their byte sizes vary with event size — the
    honest behaviour of a system that appends until a row count trips, and what keeps the
    size-health and fragmentation terms non-trivial.  The capacity is swept directly in
    records (7.2.3.1), so nothing is converted here.
    """
    position_in_order = np.empty(view.event_count, dtype=np.int64)
    position_in_order[order] = np.arange(view.event_count)
    return (position_in_order // max(1, view.target_container_rows)).astype(np.int32)


def _insertion_order_route(*, target_container_rows: int, **_):
    """Build `insertion_order`'s per-event route (7.1.5.1).

    The whole strategy, for one event: `record_id` is the arrival sequence (4.2), so an
    event's container is a function of its own key and the capacity, with no other event
    in scope. This is the shape 7.1.6 asks for, and the reason the baseline can be run at
    write time rather than only over a corpus that already exists.
    """
    capacity = max(1, target_container_rows)

    def route(features) -> int:
        return int(features[RECORD_ID]) // capacity

    return route


@register(
    "insertion_order",
    label="Insertion order",
    kind="baseline",
    route=_insertion_order_route,
)
def insertion_order(view: TrainingView, **_) -> np.ndarray:
    """Cut the arrival sequence every ``target_container_rows`` rows.

    What a storage system produces with no layout policy at all, appending records in the
    order they arrive. It consults no feature column and no selection history — but on a
    corpus that accumulates in time (5.3) arrival order carries the recency gradient, so
    the layout it produces is the age-ordered one most storage systems apply by default.
    That is what makes it the comparator a candidate has to beat (7.1.5), rather than a
    blank floor: `random_order` is the floor.

    No sort is needed. `record_id` **is** the arrival sequence, resolved by the provider
    at write time and checked when the corpus loads (4.2, 4.6, 4.13), so position is read
    from the key rather than reconstructed from the corpus.
    """
    return (view.event_id // max(1, view.target_container_rows)).astype(np.int32)


@register(
    "random_order",
    label="Random order",
    kind="baseline",
    params=[
        ParamSpec(
            name="seed",
            label="Shuffle seed",
            kind="int",
            required=False,
            default=RANDOM_ORDER_SEED,
            description="Fixed so that a random layout is still reproducible.",
        )
    ],
)
def random_order(view: TrainingView, seed: int = RANDOM_ORDER_SEED, **_) -> np.ndarray:
    """Shuffle every event, then cut every ``target_container_rows`` rows.

    The floor: a layout with no structure whatsoever, not even the incidental structure
    of arrival order. Its purpose is to make the reader's default assumption testable —
    that `insertion_order` is "doing nothing" — by showing what doing *actually* nothing
    costs. Where the two diverge is exactly the value already banked by storing records
    in the order they arrived.
    """
    return _cut_into_containers(
        np.random.default_rng(seed).permutation(view.event_count), view
    )
