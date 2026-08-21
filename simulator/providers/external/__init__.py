"""The external provider — ingest a corpus this project did not generate.

This is the seam's proof. It takes three CSV files exported from somewhere else — a
production sample, a curated fixture, another team's extract — validates them against
:mod:`simulator.core.contract`, derives what the harness needs, and writes the manifest.
It generates nothing.

    python -m simulator generate --provider external --source /path/to/export

The source directory supplies only:

    events.csv      record_id, any feature columns, at least one
                    blob_*_compressed_bytes and one blob_*_decompressed_bytes column
    queries.csv     query_id, query_time, set_name
    selections.csv  record_id, query_id — positives only

Two things are computed here rather than demanded of the exporter: the packed supports
and the per-query selected-byte totals. Both are pure functions of the three files.

``record_id`` and ``query_id`` are remapped to dense 0-based indices, because an external
corpus will use real keys — a GUID string, a sparse bigint — and everything downstream
indexes arrays positionally. The original keys are preserved in the events and queries
tables, so nothing is lost.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pyarrow
import pyarrow.csv

from ...core import contract, packed_support
from .. import register


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()[:16]


def _dense_index(keys: np.ndarray, where: str) -> dict:
    """Map arbitrary keys onto 0..n-1 in the order the table lists them.

    Duplicates are rejected rather than silently collapsed: a repeated key in an export
    means either a bad join upstream or two distinct records sharing an identifier, and
    both would corrupt every count downstream while looking like a plausible result.
    """
    position = {key: index for index, key in enumerate(keys.tolist())}
    if len(position) != keys.size:
        raise contract.ContractViolation(
            f"{where}: {keys.size - len(position)} duplicate key(s); identifiers must be unique"
        )
    return position


def _renumber(table, id_column: str, source_column: str):
    """Replace a key column with a dense 0-based one, keeping the original alongside.

    The original lands in a ``_``-prefixed column, so it is carried for traceability but
    hidden from strategies — a production key is provenance, not a feature.
    """
    columns = {
        id_column: pyarrow.array(np.arange(table.num_rows, dtype=np.uint32)),
        source_column: table.column(id_column),
    }
    for name in table.column_names:
        if name != id_column:
            columns[name] = table.column(name)
    return pyarrow.table(columns)


def _write_normalized(out: Path, events, queries, event_index, query_index) -> None:
    pyarrow.csv.write_csv(
        _renumber(events, contract.RECORD_ID, "_source_record_key"),
        out / contract.EVENTS_FILE,
    )
    pyarrow.csv.write_csv(
        _renumber(queries, contract.QUERY_ID, "_source_query_key"),
        out / contract.QUERIES_FILE,
    )
    pyarrow.csv.write_csv(
        pyarrow.table(
            {
                contract.RECORD_ID: pyarrow.array(event_index.astype(np.uint32)),
                contract.QUERY_ID: pyarrow.array(query_index.astype(np.uint32)),
            }
        ),
        out / contract.SELECTIONS_FILE,
    )


@register("external")
def ingest(config=None, out_dir: str | Path = ".", source: str | Path | None = None) -> Path:
    """Validate and adopt an externally produced corpus.

    ``config`` is accepted and ignored: an external corpus has no generator parameters.
    Its identity is the hash of the files themselves, which is the only honest id for
    data whose provenance this project does not control.
    """
    if source is None:
        raise ValueError("the external provider needs --source pointing at the CSV export")

    source, out = Path(source), Path(out_dir)
    contract.validate(source)
    out.mkdir(parents=True, exist_ok=True)

    events = pyarrow.csv.read_csv(source / contract.EVENTS_FILE)
    queries = pyarrow.csv.read_csv(source / contract.QUERIES_FILE)
    selections = pyarrow.csv.read_csv(source / contract.SELECTIONS_FILE)

    event_keys = np.array(events.column(contract.RECORD_ID).to_pylist())
    query_keys = np.array(queries.column(contract.QUERY_ID).to_pylist())
    event_position = _dense_index(event_keys, str(source / contract.EVENTS_FILE))
    query_position = _dense_index(query_keys, str(source / contract.QUERIES_FILE))

    set_name = np.array(queries.column(contract.SET_NAME).to_pylist())
    unknown = set(np.unique(set_name).tolist()) - set(contract.SET_NAMES)
    if unknown:
        raise contract.ContractViolation(
            f"{source / contract.QUERIES_FILE}: {contract.SET_NAME} has unexpected value(s) "
            f"{sorted(unknown)}; expected {list(contract.SET_NAMES)}"
        )

    try:
        event_index = np.array(
            [event_position[key] for key in selections.column(contract.RECORD_ID).to_pylist()],
            dtype=np.int64,
        )
        query_index = np.array(
            [query_position[key] for key in selections.column(contract.QUERY_ID).to_pylist()],
            dtype=np.int64,
        )
    except KeyError as unknown_key:  # a selection referring to a row that is not there
        raise contract.ContractViolation(
            f"{source / contract.SELECTIONS_FILE}: references {unknown_key}, which does "
            f"not appear in the corresponding table"
        ) from None

    event_count, query_count = events.num_rows, queries.num_rows
    roles = contract.classify_event_columns(events.column_names)

    def total(names) -> np.ndarray:
        summed = np.zeros(event_count, dtype=np.int64)
        for name in names:
            summed += events.column(name).to_numpy().astype(np.int64)
        return summed

    compressed, decompressed = total(roles["compressed"]), total(roles["decompressed"])

    # Rewrite with dense 0-based keys.  Everything downstream indexes arrays
    # positionally, and a real export uses real keys — a GUID string, a sparse bigint —
    # so the originals move to hidden columns rather than being demanded of the exporter.
    _write_normalized(out, events, queries, event_index, query_index)

    event_support = packed_support.support_from_selection_log(
        event_index, query_index, event_count, query_count
    )
    np.save(out / contract.SUPPORT_ARTIFACT, event_support)

    selected = {}
    for label, event_bytes in (("compressed", compressed), ("decompressed", decompressed)):
        totals = np.bincount(
            query_index,
            weights=event_bytes[event_index].astype(np.float64),
            minlength=query_count,
        )
        selected[label] = np.rint(totals).astype(np.int64).tolist()

    file_hashes = {name: _file_hash(out / name) for name in contract.AUTHORED_FILES}
    manifest = {
        # No generator parameters to hash, so identity is the content itself.
        "dataset_id": hashlib.sha256(
            "".join(file_hashes[name] for name in contract.AUTHORED_FILES).encode()
        ).hexdigest()[:16],
        "provider": "external",
        "source": str(source),
        "event_count": event_count,
        "query_count": query_count,
        "selection_log_rows": int(event_index.size),
        "query_time_ordering_meaningful": True,
        "selected_compressed_bytes_by_query": selected["compressed"],
        "selected_decompressed_bytes_by_query": selected["decompressed"],
        "schema": {
            "events": events.column_names,
            "queries": queries.column_names,
            "selections": selections.column_names,
        },
        "feature_columns": contract.summarize_feature_columns(out),
        "file_hashes": file_hashes,
    }
    (out / contract.MANIFEST_FILE).write_text(json.dumps(manifest, indent=2, default=str))
    return out
