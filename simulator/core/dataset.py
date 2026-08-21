"""Reading a dataset that satisfies the provider contract.

The contract is three authored CSV files plus ``manifest.json``, defined once in
:mod:`simulator.core.contract`, plus one derived ``event_support.npy`` rebuilt here when
a provider did not write it.

**Nothing here names a column a provider chose.**  Roles are decided by the convention in
the contract module, so a corpus this code has never seen — an export from a production
system, say — loads without an edit.  The moment a provider's column name appears below,
the seam has leaked.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pyarrow.csv

from . import contract, packed_support
from .contract import SUPPORT_ARTIFACT


@dataclass
class Dataset:
    """One frozen corpus, held in the shapes the evaluator wants."""

    path: Path
    manifest: dict

    event_count: int
    query_count: int

    event_id: np.ndarray
    features: dict[str, np.ndarray]
    compressed_bytes: np.ndarray
    decompressed_bytes: np.ndarray

    #: The raw blob byte columns, by name.  The objective only ever needs the two totals
    #: above, but a strategy may want to see which blob carries the weight, so the
    #: columns are kept reachable by key rather than summed away.
    size_columns: dict[str, np.ndarray]

    # supp(e) for every event, packed one flag per query.
    event_support: np.ndarray

    query_id: np.ndarray
    query_time: np.ndarray  # datetime64[D]
    set_name: np.ndarray  # "training" / "validation", authored with the dataset

    # |S_q| in bytes: what each query actually wanted.  Invariant across every layout.
    selected_compressed_bytes_by_query: np.ndarray
    selected_decompressed_bytes_by_query: np.ndarray

    hidden_event_columns: dict[str, np.ndarray]
    hidden_query_columns: dict[str, np.ndarray]

    @property
    def dataset_id(self) -> str:
        return self.manifest["dataset_id"]

    @property
    def feature_summary(self) -> list[dict]:
        """Each partitionable column's name, family and domain, from the manifest (4.12).

        Read from the manifest rather than recomputed here: the provider wrote it against
        the corpus it produced, and recomputing on every load would be a second answer to
        a question already answered.  A corpus written before the field existed reports
        nothing, which is honest — the summary is a property of the manifest, not a guess.
        """
        return list(self.manifest.get("feature_columns", []))

    @property
    def query_period(self) -> np.ndarray:
        """Calendar month each query ran in, as ``YYYY-MM`` strings.

        Months rather than quarters: the workload spans six months of daily runs, so a
        quarterly bucket would leave three points and hide the training/validation
        boundary the chart exists to show.
        """
        return self.query_time.astype("datetime64[M]").astype(str)

    def query_sets(self) -> dict[str, np.ndarray]:
        """Boolean selectors for each ``set_name``, plus the whole workload."""
        training = self.set_name == contract.TRAINING
        return {
            contract.TRAINING: training,
            contract.VALIDATION: ~training,
            "all": np.ones(self.query_count, dtype=bool),
        }

    def training_query_indices(self) -> np.ndarray:
        return np.flatnonzero(self.set_name == contract.TRAINING)


#: Defined in the contract module, because the manifest's column summary has to read a
#: column exactly the way a strategy will see it (4.12).
_column = contract.column_as_numpy


def _sum_columns(table, names) -> np.ndarray:
    total = np.zeros(table.num_rows, dtype=np.int64)
    for name in names:
        total += table.column(name).to_numpy().astype(np.int64)
    return total


def load(path: str | Path) -> Dataset:
    path = Path(path)
    manifest = json.loads((path / contract.MANIFEST_FILE).read_text())

    events = pyarrow.csv.read_csv(path / contract.EVENTS_FILE)
    queries = pyarrow.csv.read_csv(path / contract.QUERIES_FILE)

    # 4.13.  Checked here rather than trusted, because 4.2 lets a strategy read a
    # position out of the key and a corpus that broke the sequence would be scored
    # against a layout meaning something else.
    contract.validate_arrival_sequence(
        events.column(contract.RECORD_ID).to_numpy(), str(path / contract.EVENTS_FILE)
    )

    event_count = events.num_rows
    query_count = queries.num_rows

    # Roles by convention — see contract.classify_event_columns.  Any number of blob size
    # columns is allowed.  They are summed for the objective, which only ever needs a
    # total, and also kept individually so a strategy can reach one by name.
    roles = contract.classify_event_columns(events.column_names)
    compressed_bytes = _sum_columns(events, roles["compressed"])
    decompressed_bytes = _sum_columns(events, roles["decompressed"])

    event_support = _load_event_support(path, event_count, query_count)
    selected_compressed, selected_decompressed = _selected_bytes_by_query(
        path, manifest, query_count, compressed_bytes, decompressed_bytes
    )

    hidden_query_columns = tuple(
        name for name in queries.column_names if contract.is_hidden(name)
    )

    return Dataset(
        path=path,
        manifest=manifest,
        event_count=event_count,
        query_count=query_count,
        event_id=events.column(contract.RECORD_ID).to_numpy().astype(np.int64),
        features={name: _column(events, name) for name in roles["feature"]},
        compressed_bytes=compressed_bytes,
        decompressed_bytes=decompressed_bytes,
        size_columns={
            name: events.column(name).to_numpy().astype(np.int64)
            for name in roles["compressed"] + roles["decompressed"]
        },
        event_support=event_support,
        query_id=queries.column(contract.QUERY_ID).to_numpy().astype(np.int64),
        query_time=np.array(
            [str(value) for value in queries.column(contract.QUERY_TIME).to_pylist()],
            dtype="datetime64[D]",
        ),
        set_name=np.array(queries.column(contract.SET_NAME).to_pylist()),
        selected_compressed_bytes_by_query=selected_compressed,
        selected_decompressed_bytes_by_query=selected_decompressed,
        hidden_event_columns={name: _column(events, name) for name in roles["hidden"]},
        hidden_query_columns={name: _column(queries, name) for name in hidden_query_columns},
    )


def read_selection_log(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Parse the selection log into two parallel index arrays."""
    selections = pyarrow.csv.read_csv(Path(path) / contract.SELECTIONS_FILE)
    return (
        selections.column(contract.RECORD_ID).to_numpy().astype(np.int64),
        selections.column(contract.QUERY_ID).to_numpy().astype(np.int64),
    )


def _load_event_support(path: Path, event_count: int, query_count: int) -> np.ndarray:
    """The packed supports, memory-mapped when built alongside the dataset."""
    artifact = path / SUPPORT_ARTIFACT
    if artifact.exists():
        return np.ascontiguousarray(np.load(artifact, mmap_mode="r"))
    event_index, query_index = read_selection_log(path)
    return packed_support.support_from_selection_log(
        event_index, query_index, event_count, query_count
    )


def _selected_bytes_by_query(
    path: Path, manifest: dict, query_count: int, compressed_bytes, decompressed_bytes
):
    """Bytes each query actually wanted — ``|S_q|``, invariant across every layout.

    Cached in the manifest by the provider, which is what keeps a run from re-parsing a
    selection log that may be hundreds of megabytes of CSV.
    """
    if "selected_compressed_bytes_by_query" in manifest:
        return (
            np.asarray(manifest["selected_compressed_bytes_by_query"], dtype=np.int64),
            np.asarray(manifest["selected_decompressed_bytes_by_query"], dtype=np.int64),
        )

    event_index, query_index = read_selection_log(path)
    totals = [
        np.bincount(
            query_index,
            weights=event_bytes[event_index].astype(np.float64),
            minlength=query_count,
        )
        for event_bytes in (compressed_bytes, decompressed_bytes)
    ]
    return tuple(np.rint(total).astype(np.int64) for total in totals)
