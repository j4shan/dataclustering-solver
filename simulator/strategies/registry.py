"""The strategy plugin contract.

A strategy sees every feature and blob size column for every event, and the supports of
training queries only — the validation queries are removed before the view is handed
over, so leakage is impossible by construction rather than by convention.

Columns are reached by **dynamic name key**, never by an attribute the harness declares:
``view.features[name]`` and ``view.size_columns[name]``.  A corpus can therefore carry
columns this project has never seen, and a strategy written against it needs nothing
added here.

It returns one container id per event and nothing else.

Registration carries metadata beside the callable — a label, a one-line description, which
kind of strategy it claims to be, and the parameters it takes (`schema.py`).  All of it is
optional and all of it is data, so the registry can be enumerated into a selector and a
form without anything importing a strategy or learning what it does.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np

from ..core import packed_support
from .schema import COLUMN_SOURCES, ParamSpec, StrategyEntry

_REGISTERED_STRATEGIES: dict[str, StrategyEntry] = {}


@dataclass(frozen=True)
class TrainingView:
    """Everything a strategy is allowed to see when it builds a layout."""

    event_count: int
    query_count: int

    #: Every partitionable column, by name.  A strategy reaches one dynamically —
    #: ``view.features["feature_price_tier"]`` — so a corpus with columns this project has
    #: never seen needs no harness change.
    features: dict[str, np.ndarray]

    compressed_bytes: np.ndarray
    decompressed_bytes: np.ndarray

    #: The individual blob byte columns, by name.  Kept separate from ``features`` on
    #: purpose: a strategy that partitions on every feature must not silently start
    #: partitioning on byte counts.
    size_columns: dict[str, np.ndarray]

    # supp(e) restricted to training queries.  Validation flags are physically zero.
    visible_support: np.ndarray

    training_query_ids: np.ndarray
    training_query_times: np.ndarray

    #: The swept container capacity, in **records** (7.2.3.1).  A strategy that buckets
    #: reads it directly; nothing converts it against the corpus mean any more.
    target_container_rows: int
    event_id: np.ndarray

    @property
    def visible_support_size(self) -> np.ndarray:
        """How many *visible* queries selected each event.  Zero for a cold event."""
        return packed_support.support_size(self.visible_support)

    def event(self, index: int) -> dict:
        """One event's own column values, by name — what a `route` (7.1.6) is given.

        Everything that arrives with the event and nothing that describes the corpus: no
        support, no query history, no neighbouring row.  A newly arrived event has
        exactly this much about itself, which is why a route built from it is evaluable
        at write time (3.4.3).
        """
        from ..core.contract import RECORD_ID

        return {
            RECORD_ID: self.event_id[index],
            **{name: column[index] for name, column in self.features.items()},
            **{name: column[index] for name, column in self.size_columns.items()},
        }


def build_view(
    dataset, target_container_rows: int, allow_hidden_columns: bool = False
) -> TrainingView:
    training = dataset.training_query_indices()
    features = dict(dataset.features)
    if allow_hidden_columns:
        features.update(dataset.hidden_event_columns)

    return TrainingView(
        event_count=dataset.event_count,
        query_count=dataset.query_count,
        features=features,
        compressed_bytes=dataset.compressed_bytes,
        decompressed_bytes=dataset.decompressed_bytes,
        size_columns=dict(dataset.size_columns),
        visible_support=packed_support.restrict_to_queries(
            dataset.event_support, training, dataset.query_count
        ),
        training_query_ids=dataset.query_id[training],
        training_query_times=dataset.query_time[training],
        target_container_rows=target_container_rows,
        event_id=dataset.event_id,
    )


def _one_line(docstring: str | None) -> str:
    """The first line of a docstring, which is the strategy's own one-line description.

    Taking it from the source rather than asking for it again keeps one statement of what
    a strategy is, so a description cannot go stale against the code it describes.  The
    docstring's inline-literal markup is dropped, because the destination is a form label
    rather than rendered documentation and would otherwise show the backticks.
    """
    first = inspect.cleandoc(docstring or "").split("\n", 1)[0]
    return first.replace("``", "").strip()


def register(
    name: str,
    *,
    label: str | None = None,
    description: str | None = None,
    kind: str = "demonstration",
    params: Iterable[ParamSpec] = (),
    route: Callable[..., Callable[[dict], int]] | None = None,
):
    """Register a strategy, optionally with the metadata a caller needs to configure it.

    Every keyword is optional, so `@register("name")` on its own remains a complete
    registration of a strategy with no parameters (7.1.7).

    `kind` defaults to `demonstration` on purpose.  A strategy that says nothing about
    itself gets the weaker of the two claims: `baseline` asserts that the strategy reads
    no feature and can be trusted as a floor (7.1.2.3), which is not something the
    registry can check, so it is never assumed on a caller's behalf.
    """

    def wrap(strategy):
        _REGISTERED_STRATEGIES[name] = StrategyEntry(
            name=name,
            call=strategy,
            label=label or name.replace("_", " ").title(),
            description=description or _one_line(strategy.__doc__),
            kind=kind,
            params=tuple(params),
            route=route,
        )
        strategy.strategy_name = name
        return strategy

    return wrap


def entry(name: str) -> StrategyEntry:
    """The full registration — callable and metadata — of one strategy."""
    if name not in _REGISTERED_STRATEGIES:
        raise KeyError(
            f"unknown strategy {name!r}; registered: {sorted(_REGISTERED_STRATEGIES)}"
        )
    return _REGISTERED_STRATEGIES[name]


def get(name: str):
    return entry(name).call


def available() -> list[str]:
    return sorted(_REGISTERED_STRATEGIES)


#: How many events a route is checked against.  Spread evenly rather than drawn, so the
#: check is identical on every run of one corpus and a failure is reproducible.
ROUTE_SAMPLE_SIZE = 64


class RouteMismatch(ValueError):
    """A strategy's route disagrees with the layout that strategy produced."""


def check_route(entry_or_name, view: TrainingView, layout, params: dict | None = None):
    """Verify a strategy's `route` against its own layout on a sample (7.1.6).

    A route is a claim: *this layout can be reproduced one event at a time, from that
    event alone*.  The harness holds the strategy to it rather than taking it, which is
    what turns write-time assignability (3.4.3) from an assertion into a checked
    property.  A strategy declaring no route makes no claim and is checked for nothing.

    Returns the number of events checked, so a caller can report that the claim was
    actually exercised rather than silently skipped.
    """
    entry_ = entry_or_name if hasattr(entry_or_name, "route") else entry(entry_or_name)
    if entry_.route is None:
        return 0

    route = entry_.route(target_container_rows=view.target_container_rows, **(params or {}))
    layout = np.asarray(layout)
    sample = np.unique(
        np.linspace(0, view.event_count - 1, num=min(view.event_count, ROUTE_SAMPLE_SIZE))
        .astype(np.int64)
    )
    for index in sample:
        routed = route(view.event(int(index)))
        if int(routed) != int(layout[index]):
            raise RouteMismatch(
                f"{entry_.name}: route sent event {int(index)} to container {int(routed)} "
                f"but the layout puts it in {int(layout[index])}; a route that disagrees "
                f"with the layout it belongs to would misplace a newly arrived event"
            )
    return int(sample.size)


def column_choices(dataset) -> dict[str, list[str]]:
    """What each column family of `dataset` is called, for resolving a schema (7.1.7.2).

    The only place a corpus's column names are read for presentation.  They are read, not
    listed: no provider-chosen name appears in this file, which is what 4.3 requires.
    """
    return {source: sorted(getattr(dataset, source)) for source in COLUMN_SOURCES}


def describe(dataset=None) -> list[dict]:
    """Every registered strategy as JSON-native metadata (7.1.9).

    With a `dataset`, column-valued parameters come back offering exactly the columns that
    corpus carries; without one they come back unresolved, which is the honest answer
    before a corpus is loaded rather than a guess at one.
    """
    columns = column_choices(dataset) if dataset is not None else None
    entries = (_REGISTERED_STRATEGIES[name] for name in available())
    return [
        (registered.resolve(columns) if columns else registered).describe()
        for registered in entries
    ]
