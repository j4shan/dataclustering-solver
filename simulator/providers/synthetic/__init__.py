"""The synthetic provider — six hundred thousand auto part sales across forty brands, and
six months of daily reports.

Provisional, and reproducible from the seed and parameters recorded in the manifest, so
its output is never committed.  It exists so the harness can be exercised on a corpus
whose demand structure is known by construction: you can read ``workload.py`` and
predict what a query will select, which is the property that makes a diagnostic result
interpretable.

It reaches the simulator only through :mod:`simulator.core.contract`.
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
from . import config as config_module
from . import features as feature_generator
from . import sizes as size_generator
from . import workload as workload_generator

DatasetConfig = config_module.DatasetConfig


def _dataset_id(config: DatasetConfig) -> str:
    payload = json.dumps(config.as_dict(), sort_keys=True, default=str).encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()[:16]


@register("synthetic")
def generate(config: DatasetConfig | None = None, out_dir: str | Path = ".") -> Path:
    """Write a complete dataset satisfying the provider contract."""
    config = config or DatasetConfig()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(config.seed)

    features = feature_generator.generate(config, rng)
    sizes = size_generator.generate(config, rng, features)
    workload = workload_generator.generate(config, rng, features)
    query_count = len(workload.selection_sets)

    # The selection log and the packed supports are built together, one query at a time.
    # Within a single query the event indices are unique, so recording a selection is a
    # plain fancy-index write rather than an unbuffered scatter.
    event_support = packed_support.empty_support(config.n_events, query_count)
    logged_events, logged_queries = [], []
    support_size_full = np.zeros(config.n_events, dtype=np.int32)

    for query, selection_set in enumerate(workload.selection_sets):
        packed_support.record_selection(event_support, query, selection_set)
        logged_events.append(selection_set.astype(np.uint32))
        logged_queries.append(np.full(selection_set.size, query, dtype=np.uint32))
        support_size_full[selection_set] += 1

    selection_log_event = np.concatenate(logged_events)
    selection_log_query = np.concatenate(logged_queries)

    events_table = pyarrow.table(
        {
            contract.RECORD_ID: pyarrow.array(np.arange(config.n_events, dtype=np.int64)),
            "brand_id": pyarrow.array(features["brand_id"]),
            "feature_transaction_date": pyarrow.array(
                [str(day) for day in features["feature_transaction_date"]]
            ),
            **{
                name: pyarrow.array(column)
                for name, column in features.items()
                if name.startswith("feature_") and name != "feature_transaction_date"
            },
            **{name: pyarrow.array(column) for name, column in sizes.items()},
            # Generator truth: demand over *every* query, validation included, and the
            # brand multiplier that shaped it.  Withheld from strategies by the leading
            # underscore, so the driver is analysable without being handed over.
            "_support_size_full": pyarrow.array(support_size_full.astype(np.int16)),
            "_brand_demand_multiplier": pyarrow.array(
                features["_brand_demand_multiplier"].astype(np.int16)
            ),
        }
    )
    queries_table = pyarrow.table(
        {
            contract.QUERY_ID: pyarrow.array(np.arange(query_count, dtype=np.int64)),
            contract.QUERY_TIME: pyarrow.array([str(day) for day in workload.query_time]),
            contract.SET_NAME: pyarrow.array(workload.set_name),
            "_query_type": pyarrow.array(
                [workload_generator.QUERY_TYPE_NAMES[int(k)] for k in workload.query_type]
            ),
            "_half_saturation": pyarrow.array(workload.half_saturation),
        }
    )
    selection_table = pyarrow.table(
        {
            contract.RECORD_ID: pyarrow.array(selection_log_event),
            contract.QUERY_ID: pyarrow.array(selection_log_query),
        }
    )

    pyarrow.csv.write_csv(events_table, out / contract.EVENTS_FILE)
    pyarrow.csv.write_csv(queries_table, out / contract.QUERIES_FILE)
    pyarrow.csv.write_csv(selection_table, out / contract.SELECTIONS_FILE)
    np.save(out / contract.SUPPORT_ARTIFACT, event_support)

    # |S_q| in bytes is a property of the dataset alone — invariant across every layout,
    # strategy and sweep point — so it is recorded here and never recomputed.  Caching
    # it is what lets a run skip parsing selections.csv entirely.
    compressed = sizes["blob_detail_compressed_bytes"]
    decompressed = sizes["blob_detail_decompressed_bytes"]
    selected = {}
    for label, event_bytes in (("compressed", compressed), ("decompressed", decompressed)):
        totals = np.bincount(
            selection_log_query,
            weights=event_bytes[selection_log_event].astype(np.float64),
            minlength=query_count,
        )
        selected[label] = np.rint(totals).astype(np.int64).tolist()

    manifest = {
        "dataset_id": _dataset_id(config),
        "provider": "synthetic",
        "config": config.as_dict(),
        "event_count": config.n_events,
        "query_count": query_count,
        "selection_log_rows": int(selection_log_event.size),
        "query_time_ordering_meaningful": True,
        "selected_compressed_bytes_by_query": selected["compressed"],
        "selected_decompressed_bytes_by_query": selected["decompressed"],
        "schema": {
            "events": events_table.schema.names,
            "queries": queries_table.schema.names,
            "selections": selection_table.schema.names,
        },
        "feature_columns": contract.summarize_feature_columns(out),
        "file_hashes": {
            name: _file_hash(out / name) for name in contract.AUTHORED_FILES
        },
    }
    (out / contract.MANIFEST_FILE).write_text(json.dumps(manifest, indent=2, default=str))
    return out
