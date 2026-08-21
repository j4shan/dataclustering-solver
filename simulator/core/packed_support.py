"""Support sets, packed one flag per query.

The problem formulation gives three names to three views of the same relation, and this
module implements the second of them:

    selection log        L        the two-column table of observations (record_id, query_id)
    support          supp(e)  per event: the set of queries that selected it
                     supp(c)  per container: the union of its members' supports
    selection set    S_q      per query: the set of events it selected

An event's support is held here as one flag per query, packed 64 flags to a machine
word: query ``q`` lives in word ``q // 64`` at bit ``q % 64``.

The packing exists for exactly two operations. ``union_by_container`` computes
``supp(c) = union of supp(e) over members``, 64 queries per machine instruction. And
``support_size`` counts the flags, which for a container is the demand breadth ``d_c``.
"""

from __future__ import annotations

import sys

import numpy as np

QUERIES_PER_WORD = 64

if sys.byteorder != "little":  # pragma: no cover - every target platform is little-endian
    raise RuntimeError("packed support assumes a little-endian byte order")


def words_required(query_count: int) -> int:
    """Machine words needed to hold one flag per query."""
    return (query_count + QUERIES_PER_WORD - 1) // QUERIES_PER_WORD


def empty_support(event_count: int, query_count: int) -> np.ndarray:
    return np.zeros((event_count, words_required(query_count)), dtype=np.uint64)


def word_and_bit_for_query(query_index: int) -> tuple[int, np.uint64]:
    """The (word offset, bit value) pair addressing one query's flag."""
    return (
        query_index // QUERIES_PER_WORD,
        np.uint64(1) << np.uint64(query_index % QUERIES_PER_WORD),
    )


def record_selection(
    support_bits: np.ndarray, query_index: int, selected_events: np.ndarray
) -> None:
    """Record that one query selected these events — one query's selection set.

    ``selected_events`` must be free of duplicates, which lets this be a plain
    fancy-index read-modify-write rather than an unbuffered scatter.
    """
    word, bit = word_and_bit_for_query(query_index)
    support_bits[selected_events, word] |= bit


def support_from_selection_log(
    event_index: np.ndarray, query_index: np.ndarray, event_count: int, query_count: int
) -> np.ndarray:
    """Build packed supports from the selection log given as two parallel index arrays."""
    support_bits = empty_support(event_count, query_count)
    order = np.argsort(query_index, kind="stable")
    events_sorted = event_index[order]
    queries_sorted = query_index[order]

    all_queries = np.arange(query_count)
    first = np.searchsorted(queries_sorted, all_queries, side="left")
    last = np.searchsorted(queries_sorted, all_queries, side="right")

    for query in range(query_count):
        if last[query] > first[query]:
            selection_set = np.unique(events_sorted[first[query] : last[query]])
            record_selection(support_bits, query, selection_set)
    return support_bits


def support_size(support_bits: np.ndarray) -> np.ndarray:
    """Number of queries in each support set.

    For an event this is ``|supp(e)|``, its demand.  For a container it is the demand
    breadth ``d_c`` — how many queries must open it.
    """
    return np.bitwise_count(support_bits).sum(axis=1, dtype=np.int64)


def restrict_to_queries(
    support_bits: np.ndarray, visible_queries: np.ndarray, query_count: int
) -> np.ndarray:
    """Copy of the supports with every query outside ``visible_queries`` removed.

    This is the holdout mechanism.  Withholding a query clears one bit position across
    every row — the transpose of withholding an event, which would clear a whole row.
    """
    visible_flags = np.zeros(support_bits.shape[1], dtype=np.uint64)
    for query in np.asarray(visible_queries, dtype=np.int64):
        word, bit = word_and_bit_for_query(int(query))
        visible_flags[word] |= bit
    return support_bits & visible_flags


def union_by_container(
    event_support: np.ndarray, container_of_event: np.ndarray, container_count: int
) -> np.ndarray:
    """``supp(c) = union of supp(e)`` over each container's members.

    Containers are made contiguous by a stable sort, then unioned one word column at a
    time so the transient gather is a single column rather than the whole array.  Empty
    containers keep an all-zero support, which ``np.bitwise_or.reduceat`` would
    otherwise get wrong.
    """
    event_count, word_count = event_support.shape
    container_support = np.zeros((container_count, word_count), dtype=np.uint64)
    if event_count == 0:
        return container_support

    members_per_container = np.bincount(container_of_event, minlength=container_count)
    occupied = np.flatnonzero(members_per_container)
    if occupied.size == 0:
        return container_support

    first_member = np.zeros(container_count, dtype=np.int64)
    np.cumsum(members_per_container[:-1], out=first_member[1:])
    order = np.argsort(container_of_event, kind="stable")

    for word in range(word_count):
        column = event_support[:, word][order]
        container_support[occupied, word] = np.bitwise_or.reduceat(
            column, first_member[occupied]
        )
    return container_support


def unpack_support_flags(support_bits: np.ndarray, query_count: int) -> np.ndarray:
    """Expand packed rows to a (rows, query_count) array of 0/1 flags.

    Only ever called on a bounded chunk of rows.  Expanding every container at once is
    the dense ``containers x queries`` matrix the design forbids.
    """
    contiguous = np.ascontiguousarray(support_bits)
    as_bytes = contiguous.view(np.uint8).reshape(contiguous.shape[0], -1)
    flags = np.unpackbits(as_bytes, axis=1, bitorder="little")
    return flags[:, :query_count]
