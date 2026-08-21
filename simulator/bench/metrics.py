"""The metric table.

One CSV file per run, concatenated on read.  Append-only comes free from never
rewriting a file — no database, no locking.  The table is a few hundred rows, so CSV
costs nothing and keeps results diffable without tooling.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

DEFAULT_DIR = Path("data/metrics")


def write_run(rows: list[dict], run_id: str, out_dir: str | Path | None = None) -> Path:
    # Resolved on the call rather than bound at import: a default argument would freeze
    # `DEFAULT_DIR` at definition time, so redirecting the table would silently not work.
    out = Path(out_dir if out_dir is not None else DEFAULT_DIR)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"run_{run_id}.csv"

    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(key)

    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _render(row.get(k)) for k in columns})
    return path


def _render(value):
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return value


def read_all(out_dir: str | Path | None = None) -> list[dict]:
    out = Path(out_dir if out_dir is not None else DEFAULT_DIR)
    if not out.exists():
        return []
    rows: list[dict] = []
    for path in sorted(out.glob("run_*.csv")):
        with path.open(newline="") as handle:
            for row in csv.DictReader(handle):
                rows.append({k: _coerce(v) for k, v in row.items()})
    return rows


def _coerce(value: str):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value
