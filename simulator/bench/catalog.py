"""The catalog generator (8.11).

One *catalog definition* — a list of candidates, each a label and a group-by chain — in,
one *catalog document* out: every candidate scored across the capacity sweep, the baseline
scored across its own, and the structure of each chain recorded beside its rows.

**This module runs offline and is never reachable from a serving process.**  That is the
whole point of it.  Section B used to score these layouts inside a request, which meant a
deployed instance carried the corpus in memory for its life and spent seconds of CPU per
click reproducing numbers that never varied.  The space was always small — the family is
bounded (12.4.1) and so is its sweep — so it is enumerated once, here, and the GUI is
handed the answers (12.2.4).

**It computes nothing itself.**  Every figure below comes from 7.2.4's primitive through
`run_one`, exactly as a sweep's does, which is what makes 8.10 true: a number shown in the
GUI and a number printed by the CLI mean the same thing because one function produced both.
The rows are kept **whole** rather than reduced to what the page reads (8.11.1) — a trimmed
row would be a third schema to hold level with two others.

**Every candidate is validated before any of them is scored.**  A definition is authored,
not typed by a reader, but an authoring mistake that scored five of six candidates and
skipped the sixth would ship a catalogue quietly missing an entry.  So the factory (7.1.8)
checks the whole definition first and the build refuses as a whole.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone

from .. import logs
from ..config import INTERACTIVE_CAPACITIES
from ..strategies import build as build_strategy
from ..strategies.expressions import Expression
from ..strategies.group_by_chain import chain_structure
from .runner import add_baseline_lift, new_id, run_one

log = logs.get(__name__)

#: The demonstration family every entry is drawn from (12.4.1.1).
FAMILY = "group_by_chain"

#: The reference every entry is read against (12.4.5.4).
BASELINE = "insertion_order"

#: The document's shape.  Bumped when a consumer would have to be changed to read it, so
#: a page meeting a document it does not understand says so instead of rendering blanks.
CATALOG_VERSION = 1


@dataclass(frozen=True)
class Entry:
    """One catalogued candidate: what to call it, and the chain that defines it."""

    id: str
    label: str
    expressions: tuple[str, ...]


#: The shipped catalogue (8.11.3).
#:
#: Six entries chosen to **span a structural range** rather than to score well: one stage
#: and three, the low-cardinality and high-cardinality ends, and every column family the
#: corpus offers — so a reader comparing two of them is comparing two different *shapes* of
#: answer and not two tunings of one.
#:
#: **Declaration order is not presentation order.**  `build` sorts the document by leaf
#: count, which is a property of how a chain divides *this* corpus and therefore cannot be
#: asserted from the definition alone: a chain over dates is coarse on a corpus spanning
#: two months and the finest thing here on one spanning three years.  Ordering it where the
#: corpus is known is what keeps 8.11.3 true for any corpus rather than for this one.
#:
#: **These are fixtures and not recommendations** (1.2, 12.4.1.6).  That one of them scores
#: best is a fact about this corpus and this workload, and the catalogue is ordered so that
#: nothing about the list's shape suggests otherwise.
DEFINITION: tuple[Entry, ...] = (
    Entry("as-category", "Part category", ("feature_category",)),
    Entry("as-tenant", "Tenant", ("brand_id",)),
    Entry(
        "as-tenant-tier",
        "Tenant, then price tier",
        ("brand_id", "feature_price_tier > 5"),
    ),
    Entry(
        "as-cat-warranty",
        "Category and warranty term",
        ("feature_category", "feature_warranty_years"),
    ),
    Entry("as-date", "Transaction date", ("feature_transaction_date",)),
    Entry(
        "as-tenant-cat-tier",
        "Tenant, category and price tier",
        ("brand_id", "feature_category", "feature_price_tier"),
    ),
)


def build(dataset, definition=DEFINITION, capacities=INTERACTIVE_CAPACITIES) -> dict:
    """Score the whole definition and return the document 8.11.1 describes."""
    capacities = tuple(capacities)
    started_at = time.perf_counter()
    batch_id = new_id()

    # Everything is checked before anything is scored: the factory reports every bad
    # stage across every entry at once (7.1.8.1), so one run names every mistake.
    built = [(entry, _validated(dataset, entry)) for entry in definition]

    log.info(
        "catalog start batch=%s entries=%d capacities=%d",
        batch_id,
        len(built),
        len(capacities),
    )

    rows = []
    # The baseline first, at its own sweep, whatever the entries asked for: it is the
    # reference the catalogue is read against, not one of its members (12.4.6.5).
    for capacity in capacities:
        rows.extend(_score(dataset, BASELINE, {}, capacity, batch_id, entry_id=None))

    strategies = []
    for entry, chain in built:
        for capacity in capacities:
            rows.extend(
                _score(
                    dataset,
                    FAMILY,
                    {"expressions": [str(expression) for expression in chain]},
                    capacity,
                    batch_id,
                    entry_id=entry.id,
                )
            )
        stages = chain_structure(chain, dataset.features, dataset.event_count)
        strategies.append(
            {
                "id": entry.id,
                "label": entry.label,
                "expressions": [str(expression) for expression in chain],
                "stages": stages,
                # The last prefix is the whole chain, so its split count is the leaf
                # count.  Carried explicitly because the panel states it on its own, and
                # read from the structure rather than counted again.
                "leaf_count": stages[-1]["splits"] if stages else 1,
                "capacities": list(capacities),
            }
        )

    # Ordered by how finely each chain cuts *this* corpus (8.11.3).  Granularity is a
    # structural fact and not a ranking: a finer split skips more and costs more metadata,
    # which is the trade P3 exists to draw, so neither end of this order is the good end.
    strategies.sort(key=lambda entry: entry["leaf_count"])

    add_baseline_lift(rows, baseline=BASELINE)
    elapsed = time.perf_counter() - started_at
    log.info(
        "catalog done batch=%s rows=%d elapsed=%.1fs", batch_id, len(rows), elapsed
    )

    return {
        "catalog_version": CATALOG_VERSION,
        "batch_id": batch_id,
        "built": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        # The corpus's own account of itself, carried forward so the GUI can name what
        # every figure was measured against without loading it (12.2.3, 12.4.2.3).
        "corpus": {
            "dataset_id": dataset.dataset_id,
            "provider": dataset.manifest.get("provider"),
            "event_count": dataset.event_count,
            "query_count": dataset.query_count,
            "selection_log_rows": dataset.manifest.get("selection_log_rows"),
            "feature_columns": dataset.feature_summary,
        },
        "baseline": {"strategy": BASELINE, "capacities": list(capacities)},
        "strategies": strategies,
        "rows": rows,
    }


def _validated(dataset, entry: Entry) -> tuple[Expression, ...]:
    """The entry's chain, canonical, as the factory validated it (7.1.8).

    Returned from the factory's own output rather than from the definition's text, so what
    is scored and what is reported are the same expressions in the same spelling.
    """
    strategy = build_strategy(
        FAMILY,
        {"expressions": list(entry.expressions)},
        features=dataset.features,
        block=entry.id,
    )
    return tuple(
        Expression.parse(text) for text in strategy.params.get("expressions", ())
    )


def _score(dataset, name, params, capacity, batch_id, entry_id):
    """One evaluation, tagged with the catalogue entry that asked for it.

    `Block` is the field the report's views already read to tell one series from another,
    and it carries the entry's **id** rather than its label: a label is presentation and
    may be reworded, an id is what a row is joined on.
    """
    rows = run_one(dataset, name, capacity, params=params, batch_id=batch_id)
    for row in rows:
        row["Block"] = entry_id
    return rows
