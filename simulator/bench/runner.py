"""The sweep runner.

One operation is primitive: (dataset, strategy, parameters) -> metric rows.  Everything
else — sweeps, comparison, charts — is built on it.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ..config import SweepConfig
from ..core import management_cost
from ..core.evaluate import byte_skip_ratio_by_period, evaluate
from ..core.layout import validate_and_compact
from ..strategies import build_view, check_route, get
from . import metrics


def new_id() -> str:
    """A short identifier for one run or one batch of them."""
    return uuid.uuid4().hex[:12]


def run_one(
    dataset,
    strategy_name: str,
    target_container_rows: int,
    weights: management_cost.CostWeights | None = None,
    allow_hidden_columns: bool = False,
    params: dict | None = None,
    batch_id: str | None = None,
) -> list[dict]:
    """Score one strategy at one parameter setting: one row per ``set_name``.

    ``batch_id`` names the *request* these rows belong to (8.3.1), where ``Run_ID`` names
    this one evaluation within it.  A caller running several evaluations for one purpose
    — a sweep, or one click of the GUI's Evaluate — passes the same batch id to all of
    them, so the comparison they were produced for is recoverable from the CSV afterwards.
    A lone call is its own batch.
    """
    weights = weights or management_cost.CostWeights()
    params = dict(params or {})
    strategy = get(strategy_name)

    view = build_view(dataset, target_container_rows, allow_hidden_columns)

    started = time.perf_counter()
    proposed_layout = strategy(view, **params)
    assign_seconds = time.perf_counter() - started

    # 7.1.6.  A strategy that claims its layout is reproducible one event at a time is
    # held to the claim here, against the ids it just returned rather than the compacted
    # ones below.  A strategy claiming nothing is checked for nothing.
    check_route(strategy_name, view, proposed_layout, params)

    container_of_event, container_count = validate_and_compact(
        proposed_layout, dataset.event_count
    )

    started = time.perf_counter()
    metrics_by_set = evaluate(dataset, container_of_event, target_container_rows)
    evaluate_seconds = time.perf_counter() - started

    container_bytes = np.bincount(
        container_of_event,
        weights=dataset.compressed_bytes.astype(float),
        minlength=container_count,
    )
    container_records = np.bincount(container_of_event, minlength=container_count)
    cost = management_cost.get()(
        container_bytes, container_records, target_container_rows, weights
    )

    run_id = new_id()
    run_timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    return [
        {
            "Strategy_Name": strategy_name,
            "Set_Name": set_name,
            "Params": json.dumps(
                {"target_container_rows": target_container_rows, **params}, sort_keys=True
            ),
            "target_container_rows": target_container_rows,
            "Dataset_ID": dataset.dataset_id,
            "Batch_ID": batch_id or run_id,
            "Run_ID": run_id,
            "Run_Timestamp": run_timestamp,
            "Used_Hidden_Columns": allow_hidden_columns,
            **kpis,
            **cost,
            "assign_seconds": round(assign_seconds, 4),
            "evaluate_seconds": round(evaluate_seconds, 4),
        }
        for set_name, kpis in metrics_by_set.items()
    ]


def sweep(
    dataset,
    config: SweepConfig | None = None,
    out_dir: str | Path | None = None,
    verbose: bool = True,
) -> list[dict]:
    config = config or SweepConfig()
    rows: list[dict] = []
    # One sweep is one request, so every row it produces shares a batch (8.3.1).
    batch_id = new_id()

    for strategy_name in config.strategies:
        for target_container_rows in config.values:
            produced = run_one(
                dataset, strategy_name, target_container_rows, batch_id=batch_id
            )
            rows.extend(produced)
            if verbose:
                held_out = next(r for r in produced if r["Set_Name"] == "validation")
                print(
                    f"  {strategy_name:<16} capacity={target_container_rows:>6} rec  "
                    f"containers={held_out['container_count']:>6}  "
                    f"skip rec={held_out['record_skip_ratio']:6.3f}"
                    f"  byte={held_out['byte_skip_ratio']:6.3f}  "
                    f"waste={held_out['waste_ratio']:7.3f}  "
                    f"({held_out['evaluate_seconds']:.2f}s)"
                )

    metrics.write_run(rows, batch_id, out_dir)
    return rows


def skip_ratio_by_period_per_strategy(
    dataset, config: SweepConfig, target_container_rows: int
) -> dict[str, dict[str, float]]:
    """Held-out byte skipping ratio by calendar period, one entry per strategy."""
    by_strategy = {}
    for strategy_name in config.strategies:
        view = build_view(dataset, target_container_rows)
        container_of_event, _ = validate_and_compact(
            get(strategy_name)(view), dataset.event_count
        )
        by_strategy[strategy_name] = byte_skip_ratio_by_period(
            dataset, container_of_event, "validation"
        )
    return by_strategy


def add_baseline_lift(rows: list[dict], baseline: str = "insertion_order") -> list[dict]:
    """Attach each row's waste ratio relative to the do-nothing layout.

    Keyed on the capacity as well as the set, so a row is only ever compared against a
    baseline built at the same capacity.  A row at a capacity the baseline never swept
    gets ``None`` rather than a nearest or interpolated reference (12.4.5.4): a
    comparison against a layout that was never built is not a comparison.
    """
    baseline_ratio = {
        (row["Set_Name"], row["target_container_rows"]): row["waste_ratio"]
        for row in rows
        if row["Strategy_Name"] == baseline
    }
    for row in rows:
        reference = baseline_ratio.get((row["Set_Name"], row["target_container_rows"]))
        # Two reasons there is no lift, and both render as 12.4.5.4's blank cell: the
        # baseline never swept this capacity, or it wasted nothing there and the ratio is
        # undefined rather than infinite. Written out because `if reference` alone reads
        # as the first reason while silently also meaning the second.
        no_reference = reference is None or reference == 0
        row["baseline_lift"] = None if no_reference else row["waste_ratio"] / reference
    return rows
