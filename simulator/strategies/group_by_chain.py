"""The Assignment Strategy family the demonstration GUI configures (12.4.1).

Two steps and nothing else.  A **chain** of group-by expressions splits the corpus the
way a decision tree is grown — every stage regroups every split the last one produced —
and then every resulting **leaf** is bucketed into containers of a bounded record count.

    expressions = ["brand_id", "feature_price_tier > 5"]
    capacity    = 1000 records

    corpus ──group by brand_id──▶ split ──group by price_tier > 5──▶ leaves
           ──bucket each leaf at 1000 records──▶ containers

It is a **fixture, not a result** (1.2).  It reads features, which is exactly what a
baseline may not do (7.1.2.3), and it is registered as a demonstration so no reader can
mistake a good score here for a recommendation.

Two properties are load-bearing enough to be worth stating outside the tests:

*The chain is a set, not a sequence.*  Every stage applies to every split with no early
stopping, so a leaf is an equivalence class of the whole key tuple and permuting the
expressions cannot move an event.  The expressions are sorted into a canonical order
before anything runs, so two permutations produce not merely equivalent partitions but
the identical array (12.4.1.3).

*The empty chain is the baseline.*  One leaf, bucketed in arrival order, is exactly what
``insertion_order`` does — so the thing every candidate is measured against is this
family's degenerate case rather than a separate mechanism (12.4.1.5).
"""

from __future__ import annotations

import numpy as np

from .expressions import Expression, compile_chain, validate_chain
from .registry import TrainingView, register
from .schema import ParamSpec

#: At most four stages, which is 7.1.7.3's bound and 12.4.2.6's repeater length.
MAX_CHAIN_LENGTH = 4


def canonical(expressions) -> tuple[Expression, ...]:
    """The chain in the one order this family ever evaluates it in.

    Sorting is what turns "order does not matter" from a claim about the partition into a
    claim about the array.  Without it two permutations would produce the same grouping
    with differently numbered containers, and a reader comparing two blocks that differ
    only by drag-and-drop would see two rows where there is one layout.
    """
    return tuple(sorted(expressions, key=str))


def leaf_of_event(
    expressions, features: dict[str, np.ndarray], event_count: int
) -> np.ndarray:
    """Which leaf each event falls into — its equivalence class under the key tuple.

    Each stage is factorized to a dense code first, so the combination is a lookup over
    small integers whatever the columns actually hold: text, dates and floats all reduce
    to the same shape before they are combined.
    """
    if not expressions:
        return np.zeros(event_count, dtype=np.int64)

    codes, widths = _stage_codes(canonical(expressions), features, event_count)
    return _leaf_from_codes(codes, widths, event_count)


def _stage_codes(ordered, features: dict[str, np.ndarray], event_count: int):
    """Each stage of an already-canonical chain, factorized to a dense code — once.

    Held apart from `leaf_of_event` because the codes are built stage by stage before
    same chain, and factorizing a stage again for each prefix that contains it is the
    same work done up to four times.
    """
    codes, widths = [], []
    for expression in ordered:
        distinct, code = np.unique(expression.group_keys(features), return_inverse=True)
        codes.append(code.astype(np.int64).reshape(event_count))
        widths.append(max(1, distinct.size))
    return codes, widths


def _leaf_from_codes(codes, widths, event_count: int) -> np.ndarray:
    # Mix the per-stage codes into one integer key and take a flat `unique` over that,
    # rather than a `unique(axis=0)` over the stacked codes.  The two agree exactly —
    # the key is injective on the tuple — but the row-wise version lexsorts a 2-D array
    # and costs roughly eight times as much on the shipped corpus, which is most of one
    # Evaluate click's budget (12.2.4).
    #
    # The mix only works while the product of the widths fits an int64.  Four stages over
    # high-cardinality columns can exceed that, so the slow path stays as the fallback
    # rather than the family silently wrapping around and merging unrelated leaves.
    combined = _mixed_key(codes, widths)
    if combined is None:
        _, leaf = np.unique(np.stack(codes, axis=1), axis=0, return_inverse=True)
    else:
        _, leaf = np.unique(combined, return_inverse=True)
    return leaf.astype(np.int64).reshape(event_count)


def _mixed_key(codes, widths):
    """One integer per event, injective on the code tuple — or `None` if it would not fit."""
    limit = np.iinfo(np.int64).max
    span = 1
    for width in widths:
        if span > limit // width:
            return None
        span *= width

    combined = codes[0]
    for code, width in zip(codes[1:], widths[1:]):
        combined = combined * width + code
    return combined


def chain_structure(expressions, features, event_count: int) -> list:
    """How this chain divides this corpus: each stage, and the splits it leaves behind.

    One entry per stage in canonical order, carrying the expression in the grammar's own
    spelling and the number of distinct groups the corpus stands in **after that prefix of
    the chain** (8.11.2).  The counts are cumulative rather than per-stage-in-isolation,
    because that is what the chain actually does: every stage regroups every split the
    last one produced, so the figure a reader needs is where the corpus has got to.  The
    last entry's count is therefore the chain's leaf count.

    It lives here because only the family knows how a chain divides a corpus, and 12.2.5
    and 12.4.2.6 keep every surface that displays the number free of computing it.

    **Where the number may and may not appear.**  13.16 keeps it out of P1, whose blocks
    carry no figure a reader could mistake for a score; 12.4.2.1 puts it in the catalogue
    list, where it is a number beside the chain that produced it.  Nothing about capacity
    enters: a chain has one shape across its whole sweep (12.4.4.4), so one structure
    describes a candidate at every capacity it is swept across.

    Built from the same two helpers `leaf_of_event` uses, on each prefix in turn.  There
    is no second way of counting a split here: `_stage_codes` factorizes each stage once
    and every prefix is folded by `_leaf_from_codes`, so the last entry agrees with
    `leaf_of_event` by construction rather than by a check (10.1.2).
    """
    ordered = canonical(expressions)
    if not ordered:
        return []

    codes, widths = _stage_codes(ordered, features, event_count)
    structure = []
    for depth, expression in enumerate(ordered, start=1):
        leaf = _leaf_from_codes(codes[:depth], widths[:depth], event_count)
        # `_leaf_from_codes` returns a dense code, so the highest one is the count.
        structure.append(
            {"expression": str(expression), "splits": int(leaf.max()) + 1}
        )
    return structure


def bucket_leaves(
    leaf: np.ndarray, arrival_order: np.ndarray, capacity: int
) -> np.ndarray:
    """Cut every leaf into containers of at most ``capacity`` records (12.4.1.4).

    Containers are **filled to the capacity** and the last one of each leaf takes what is
    left: a leaf of ``n`` records at capacity ``c`` becomes ``n // c`` full containers and
    a remainder, which is what the baseline does and therefore the only rule under which a
    candidate and the baseline are packed the same way.  A leaf no larger than the capacity
    is its own remainder and becomes one container.

    Within a leaf the order is arrival order and nothing more.  Ordering by support, or
    by size, would be an assignment strategy, and this project ships none (13.12).
    """
    capacity = max(1, int(capacity))
    event_count = leaf.size

    counts = np.bincount(leaf)
    # Group the events by leaf while preserving arrival order inside each one.
    order = arrival_order[np.argsort(leaf[arrival_order], kind="stable")]
    starts = np.concatenate(([0], np.cumsum(counts)[:-1]))

    position_in_leaf = np.empty(event_count, dtype=np.int64)
    position_in_leaf[order] = np.arange(event_count) - np.repeat(starts, counts)

    containers_in_leaf = np.maximum(1, -(-counts // capacity))  # ceil, in integers
    #  Fill to the brim: the first `capacity` records of a leaf go in its first container,
    #  the next `capacity` in its second, and so on.  The highest index a leaf of `n`
    #  reaches is `(n - 1) // capacity`, which is `containers_in_leaf - 1`, so the offsets
    #  below stay exact and no container can hold more than the capacity.
    bucket = position_in_leaf // capacity

    offset = np.concatenate(([0], np.cumsum(containers_in_leaf)[:-1]))
    return (offset[leaf] + bucket).astype(np.int32)


@register(
    "group_by_chain",
    label="Group-by chain",
    kind="demonstration",
    description=(
        "Split the corpus by a set of feature expressions, then bucket every leaf to a"
        " fixed record capacity."
    ),
    params=[
        ParamSpec(
            name="expressions",
            label="Group-by expressions",
            kind="expression_set",
            required=False,
            maximum_length=MAX_CHAIN_LENGTH,
            description=(
                "One expression per split, over the corpus's feature columns —"
                " `brand_id`, `feature_price_tier > 5`, `feature_price_tier / 10`."
                " Order does not affect the layout."
            ),
        )
    ],
)
def group_by_chain(view: TrainingView, expressions=(), **_) -> np.ndarray:
    """Group by a set of feature expressions, then bucket each leaf to the capacity.

    ``expressions`` arrives as text from a form, or already parsed from a caller that has
    one.  Either way it is validated against this corpus before a single event moves: an
    unknown column or a mistyped literal is a rejection, never a silently empty split.
    """
    if all(isinstance(item, Expression) for item in expressions):
        parsed = tuple(expressions)
        validate_chain(parsed, view.features)
    else:
        # Text from a form: compile the whole chain at once so a reader learns about
        # every bad stage in one round trip rather than one per attempt (7.1.8).
        parsed = compile_chain([str(item) for item in expressions], view.features)

    leaf = leaf_of_event(parsed, view.features, view.event_count)
    # Arrival order, which record_id carries.  The synthetic corpus happens to arrive
    # dense and ascending; an external one generally will not, and a bucketer that
    # assumed otherwise would be silently wrong on real data.
    arrival_order = np.argsort(view.event_id, kind="stable")
    return bucket_leaves(leaf, arrival_order, view.target_container_rows)
