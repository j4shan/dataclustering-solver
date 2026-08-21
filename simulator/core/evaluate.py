"""Scoring a layout — the objective function.

A container is *activated* by a query when it holds at least one event that query
selected.  This is the black-box pre-scan of the problem formulation, assumed exact and
free, so activation is containment and no property of any index enters here.

    container_bytes[c]   sum of member sizes
    supp(c)              union of member supports
    demand_breadth[c]    |supp(c)| — how many queries must open it
    materialized_volume  sum over containers of container_bytes[c] * demand_breadth[c]
    waste                materialized volume - selected volume

**The headline KPIs are skipping ratios**, one per query and then averaged:

    record_skip_ratio    1 - materialized records / corpus records
    byte_skip_ratio      1 - materialized bytes   / corpus bytes

They answer "how much of the corpus did a query avoid touching?", which is the quantity a
storage system's cost actually tracks, and they sit on a bounded 0–1 scale that two
corpora can be compared on. Waste ratio is retained beside them — it is the formulation's
objective and what optimization drives — but it is denominated in *selected* volume, so a
query selecting very little reports a huge ratio for reasons that say nothing about the
layout. That makes it a poor headline and a good objective.

Per-query figures are accumulated into a length-Q vector, never materialized as a dense
containers-by-queries activation matrix.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import packed_support
from .layout import container_size_health

CONTAINERS_PER_CHUNK = 2048


@dataclass(frozen=True)
class ContainerStatistics:
    """Everything the objective needs about one layout's containers."""

    compressed_bytes: np.ndarray  # int64[containers]
    decompressed_bytes: np.ndarray  # int64[containers]
    record_counts: np.ndarray  # int64[containers] — |E_c|
    support: np.ndarray  # uint64[containers, words] — supp(c)
    demand_breadth: np.ndarray  # int64[containers] — d_c

    @property
    def container_count(self) -> int:
        return self.compressed_bytes.shape[0]


def _total_bytes_by_container(
    event_bytes: np.ndarray, container_of_event: np.ndarray, container_count: int
) -> np.ndarray:
    # bincount accumulates in float64.  Byte totals here stay far below 2**53, so the
    # sum is exact and the round trip back to int64 is lossless.
    totals = np.bincount(
        container_of_event, weights=event_bytes.astype(np.float64), minlength=container_count
    )
    return np.rint(totals).astype(np.int64)


def summarize_containers(
    container_of_event: np.ndarray,
    event_support: np.ndarray,
    compressed_bytes: np.ndarray,
    decompressed_bytes: np.ndarray,
    container_count: int,
) -> ContainerStatistics:
    container_support = packed_support.union_by_container(
        event_support, container_of_event, container_count
    )
    return ContainerStatistics(
        compressed_bytes=_total_bytes_by_container(
            compressed_bytes, container_of_event, container_count
        ),
        decompressed_bytes=_total_bytes_by_container(
            decompressed_bytes, container_of_event, container_count
        ),
        record_counts=np.bincount(container_of_event, minlength=container_count).astype(
            np.int64
        ),
        support=container_support,
        demand_breadth=packed_support.support_size(container_support),
    )


def materialized_volume_by_query(
    container_support: np.ndarray, container_weights: np.ndarray, query_count: int
) -> np.ndarray:
    """For each query, the total weight of every container it activates — ``M_q``.

    ``container_weights`` is per-container bytes or per-container record counts; the
    accumulation is identical, which is why record and byte skipping share one code path.
    """
    materialized = np.zeros(query_count, dtype=np.int64)
    for first in range(0, container_support.shape[0], CONTAINERS_PER_CHUNK):
        last = first + CONTAINERS_PER_CHUNK
        activation_flags = packed_support.unpack_support_flags(
            container_support[first:last], query_count
        )
        materialized += activation_flags.T.astype(np.int64) @ container_weights[first:last]
    return materialized


def activated_containers_by_query(
    container_support: np.ndarray, query_count: int
) -> np.ndarray:
    """For each query, how many containers it must open."""
    activated = np.zeros(query_count, dtype=np.int64)
    for first in range(0, container_support.shape[0], CONTAINERS_PER_CHUNK):
        last = first + CONTAINERS_PER_CHUNK
        activation_flags = packed_support.unpack_support_flags(
            container_support[first:last], query_count
        )
        activated += activation_flags.sum(axis=0, dtype=np.int64)
    return activated


def _mean_skip_ratio(
    materialized: np.ndarray, corpus_total: int, queries_in_set: np.ndarray
) -> float:
    """Average over queries of ``1 - materialized / corpus_total``.

    The per-query ratio is averaged rather than the totals being divided, so every query
    counts once regardless of how much it selected. With a constant denominator the two
    agree exactly; they would not if the corpus varied per query, and averaging is the
    form that stays correct.
    """
    if not queries_in_set.any() or corpus_total <= 0:
        return float("nan")
    return float(1.0 - (materialized[queries_in_set] / corpus_total).mean())


def _summarize_query_set(
    materialized_volume: np.ndarray,
    selected_volume: np.ndarray,
    queries_in_set: np.ndarray,
    prefix: str,
) -> dict[str, float]:
    """Aggregate materialized and selected volume over one subset of queries."""
    materialized_total = int(materialized_volume[queries_in_set].sum())
    selected_total = int(selected_volume[queries_in_set].sum())
    waste_total = materialized_total - selected_total
    waste_per_query = (materialized_volume - selected_volume)[queries_in_set]

    summary = {
        f"{prefix}materialized_bytes": materialized_total,
        f"{prefix}selected_bytes": selected_total,
        f"{prefix}waste_bytes": waste_total,
        f"{prefix}waste_ratio": waste_total / selected_total if selected_total else float("nan"),
        f"{prefix}read_amplification": (
            materialized_total / selected_total if selected_total else float("nan")
        ),
    }
    if waste_per_query.size:
        summary[f"{prefix}waste_per_query_median"] = float(np.percentile(waste_per_query, 50))
        summary[f"{prefix}waste_per_query_p95"] = float(np.percentile(waste_per_query, 95))
        summary[f"{prefix}waste_per_query_max"] = int(waste_per_query.max())
    return summary


def evaluate(dataset, container_of_event: np.ndarray, target_container_rows: int):
    """Score a layout, returning one row of metrics per ``set_name``.

    ``container_of_event`` must already be validated and compacted — ``bench.runner``
    does that before calling here.  ``dataset`` is duck-typed: anything exposing the
    supports, byte columns and query sets will do, which is what lets the correctness
    anchors run against arrays they build themselves.
    """
    container_count = (
        int(container_of_event.max()) + 1 if container_of_event.size else 0
    )
    containers = summarize_containers(
        container_of_event,
        dataset.event_support,
        dataset.compressed_bytes,
        dataset.decompressed_bytes,
        container_count,
    )

    materialized_compressed = materialized_volume_by_query(
        containers.support, containers.compressed_bytes, dataset.query_count
    )
    materialized_decompressed = materialized_volume_by_query(
        containers.support, containers.decompressed_bytes, dataset.query_count
    )
    materialized_records = materialized_volume_by_query(
        containers.support, containers.record_counts, dataset.query_count
    )
    activated = activated_containers_by_query(containers.support, dataset.query_count)

    corpus_compressed_bytes = int(dataset.compressed_bytes.sum())
    corpus_records = int(dataset.event_count)
    shared = {
        "container_count": container_count,
        **container_size_health(
            containers.compressed_bytes, containers.record_counts, target_container_rows
        ),
    }

    rows: dict[str, dict] = {}
    for set_name, queries_in_set in dataset.query_sets().items():
        # The headline pair, first in the row because they are what the report leads on.
        row = {
            "record_skip_ratio": _mean_skip_ratio(
                materialized_records, corpus_records, queries_in_set
            ),
            "byte_skip_ratio": _mean_skip_ratio(
                materialized_compressed, corpus_compressed_bytes, queries_in_set
            ),
            "container_skip_ratio": _mean_skip_ratio(
                activated, container_count, queries_in_set
            ),
            "materialized_records": int(materialized_records[queries_in_set].sum()),
        }
        row.update(shared)
        row.update(
            _summarize_query_set(
                materialized_compressed,
                dataset.selected_compressed_bytes_by_query,
                queries_in_set,
                "",
            )
        )
        row.update(
            _summarize_query_set(
                materialized_decompressed,
                dataset.selected_decompressed_bytes_by_query,
                queries_in_set,
                "decompressed_",
            )
        )
        row["query_count"] = int(queries_in_set.sum())
        rows[set_name] = row
    return rows


def byte_skip_ratio_by_period(
    dataset, container_of_event: np.ndarray, set_name: str = "validation"
) -> dict[str, float]:
    """Byte skipping ratio for one query set, grouped by the calendar month it ran in.

    The shape of this series is not assumed: it can rise, flatten, or fall again as
    demand returns to regions the layout already suits.  No slope is fitted.
    """
    container_count = (
        int(container_of_event.max()) + 1 if container_of_event.size else 0
    )
    containers = summarize_containers(
        container_of_event,
        dataset.event_support,
        dataset.compressed_bytes,
        dataset.decompressed_bytes,
        container_count,
    )
    materialized = materialized_volume_by_query(
        containers.support, containers.compressed_bytes, dataset.query_count
    )
    corpus_compressed_bytes = int(dataset.compressed_bytes.sum())
    queries_in_set = dataset.query_sets()[set_name]

    return {
        str(period): _mean_skip_ratio(
            materialized,
            corpus_compressed_bytes,
            queries_in_set & (dataset.query_period == period),
        )
        for period in np.unique(dataset.query_period[queries_in_set])
    }
