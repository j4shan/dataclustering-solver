"""A layout: the assignment of every event to a container.

The formulation's decision variable, and the only thing under our control.
"""

from __future__ import annotations

import numpy as np


class InvalidLayout(ValueError):
    pass


def validate_and_compact(
    container_of_event: np.ndarray, event_count: int
) -> tuple[np.ndarray, int]:
    """Check a strategy's return value and renumber containers to ``0..K-1``.

    Strategies may emit any non-negative labels they like; the evaluator wants a dense
    range so container totals can be a ``bincount``.
    """
    assignment = np.asarray(container_of_event)
    if assignment.ndim != 1:
        raise InvalidLayout(f"expected a 1-D array, got shape {assignment.shape}")
    if assignment.shape[0] != event_count:
        raise InvalidLayout(f"expected {event_count} entries, got {assignment.shape[0]}")
    if not np.issubdtype(assignment.dtype, np.integer):
        if not np.all(np.isfinite(assignment)):
            raise InvalidLayout("container ids contain non-finite values")
        assignment = assignment.astype(np.int64)
    if assignment.min() < 0:
        raise InvalidLayout("container ids must be non-negative")

    _, compacted = np.unique(assignment, return_inverse=True)
    return compacted.astype(np.int32, copy=False), int(compacted.max()) + 1


def container_size_health(
    container_bytes: np.ndarray,
    container_records: np.ndarray,
    target_container_rows: int,
) -> dict[str, float]:
    """Distribution of container sizes against the target.

    Detects a layout that bought waste reduction by shrinking containers below the
    floor, which the formulation names as the sole force opposing fine granularity.

    Two denominations, deliberately (6.3.5).  The percentiles stay in **bytes**, because
    that is what a storage system pays for and what the objective is measured in.  The
    floor is counted in **records**, because that is the unit the capacity is swept in
    (7.2.3.1) and a shortfall against a target has to be measured in the target's own
    unit to mean anything.
    """
    if container_bytes.size == 0:
        return {}
    return {
        "container_bytes_p50": float(np.percentile(container_bytes, 50)),
        "container_bytes_p95": float(np.percentile(container_bytes, 95)),
        "container_bytes_min": int(container_bytes.min()),
        "container_bytes_max": int(container_bytes.max()),
        "container_records_p50": float(np.percentile(container_records, 50)),
        "containers_below_target": int((container_records < target_container_rows).sum()),
    }
