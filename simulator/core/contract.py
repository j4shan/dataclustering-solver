"""The dataset contract — the one seam between a provider and the simulator.

A provider writes three CSV files and a manifest.  The simulator reads them and never
learns which provider produced them: not through a column list, not through a config
object, not through an import.  Everything the harness needs is either in the contract
below or derivable from it.

Column roles are decided by **convention, not by enumeration**, which is what lets a
corpus the simulator has never seen load without code changes:

    record_id                       identity — the unique key, one row per event
    blob_*_compressed_bytes         size, summed into the compressed total
    blob_*_decompressed_bytes       size, summed into the decompressed total
    _-prefixed                      hidden — generator truth, withheld from strategies
    anything else                   a feature a strategy may partition on

The asymmetry between the two prefixes is deliberate.  ``blob_`` is **enforced**: the
objective is byte-weighted, so a corpus whose sizes the loader cannot find is not
scoreable and is rejected at validation rather than scored wrongly.  ``feature_`` is
**not** enforced anywhere — it is a provider-side readability convention, and an
unrecognised column is still classified as a feature.  That is what keeps an unfamiliar
corpus loadable without a code change.

Every column reaches a strategy by dynamic name key: features through
``view.features[name]``, blob sizes through ``view.size_columns[name]``.  Nothing above
this module enumerates a column name.

``event_support.npy`` is derived, not authored.  A provider may write it as an
optimization; when it is absent the loader rebuilds it from ``selections.csv``, so an
external corpus needs only the three CSVs.
"""

from __future__ import annotations

from pathlib import Path

EVENTS_FILE = "events.csv"
QUERIES_FILE = "queries.csv"
SELECTIONS_FILE = "selections.csv"
MANIFEST_FILE = "manifest.json"

#: Written by a provider.  Everything else in a dataset directory is derived.
AUTHORED_FILES = (EVENTS_FILE, QUERIES_FILE, SELECTIONS_FILE)

#: Derived from selections.csv; rebuilt on load when missing.
SUPPORT_ARTIFACT = "event_support.npy"

RECORD_ID = "record_id"
QUERY_ID = "query_id"
QUERY_TIME = "query_time"
SET_NAME = "set_name"

REQUIRED_EVENT_COLUMNS = (RECORD_ID,)
REQUIRED_QUERY_COLUMNS = (QUERY_ID, QUERY_TIME, SET_NAME)
REQUIRED_SELECTION_COLUMNS = (RECORD_ID, QUERY_ID)

#: The two set_name values the metric table is keyed on.
TRAINING, VALIDATION = "training", "validation"
SET_NAMES = (TRAINING, VALIDATION)

HIDDEN_PREFIX = "_"
BLOB_PREFIX = "blob_"
COMPRESSED_SUFFIX = "_compressed_bytes"
DECOMPRESSED_SUFFIX = "_decompressed_bytes"

#: The three kinds of thing a column can hold, as far as anything above this seam cares.
#: A *family*, not a dtype: what matters downstream is which operations mean something on
#: a column, and `int32` and `float64` answer that question identically.
NUMERIC, TEXT, TEMPORAL = "numeric", "text", "temporal"

#: Above this many distinct values, a column's domain is summarized by its range rather
#: than listed.  Forty brands are worth showing a reader; six hundred thousand ids are not.
MAX_ENUMERATED_VALUES = 50


class ContractViolation(Exception):
    """A dataset directory does not satisfy the contract."""


def is_hidden(column: str) -> bool:
    """Generator truth: present in the table, withheld from strategies by default."""
    return column.startswith(HIDDEN_PREFIX)


def is_size(column: str) -> bool:
    """A blob's byte count.  Both halves of the name carry meaning: the prefix says the
    column measures a blob, the suffix says which of the two totals it feeds."""
    return column.startswith(BLOB_PREFIX) and column.endswith(
        (COMPRESSED_SUFFIX, DECOMPRESSED_SUFFIX)
    )


def classify_event_columns(names) -> dict[str, tuple[str, ...]]:
    """Sort an events table's columns into their four roles."""
    roles: dict[str, list[str]] = {
        "identity": [],
        "compressed": [],
        "decompressed": [],
        "hidden": [],
        "feature": [],
    }
    for name in names:
        if name == RECORD_ID:
            roles["identity"].append(name)
        elif is_hidden(name):
            roles["hidden"].append(name)
        elif is_size(name) and name.endswith(COMPRESSED_SUFFIX):
            roles["compressed"].append(name)
        elif is_size(name) and name.endswith(DECOMPRESSED_SUFFIX):
            roles["decompressed"].append(name)
        else:
            roles["feature"].append(name)
    return {role: tuple(columns) for role, columns in roles.items()}


def dtype_family(dtype) -> str:
    """Which family a column's dtype belongs to.

    Defined once, here, because two very different callers need the same answer: the
    manifest summary below, which tells a reader what a column holds, and the expression
    grammar, which decides from it which operators may be applied to that column.  Two
    definitions would eventually disagree, and the disagreement would show up as a form
    offering an operator the evaluator then refuses.
    """
    import numpy as np

    if np.issubdtype(dtype, np.datetime64):
        return TEMPORAL
    if np.issubdtype(dtype, np.number) or np.issubdtype(dtype, np.bool_):
        return NUMERIC
    return TEXT


def column_as_numpy(table, name: str):
    """One column as a numpy array, whatever type the provider wrote it as.

    Strings arrive as object arrays rather than raising, which is what lets a provider
    author readable labels instead of integer codes.
    """
    import numpy as np
    import pyarrow

    column = table.column(name)
    try:
        return column.to_numpy()
    except (pyarrow.ArrowInvalid, TypeError):
        return np.array(column.to_pylist())


def summarize_feature_columns(path: str | Path) -> list[dict]:
    """What each partitionable column is called, holds, and ranges over (4.12).

    Read back from the **written** ``events.csv`` with the same reader the loader uses,
    rather than from whatever the provider held in memory.  A provider may write a date
    as a string and have it read back as a date; summarizing what it wrote would describe
    a corpus nobody ever sees.  The extra parse is paid once, at generation.

    Hidden, identity and blob-size columns are absent: this is the list a catalogue
    author composes a group-by against (4.12), and those three are not partitionable.
    """
    import numpy as np
    import pyarrow.csv

    events = pyarrow.csv.read_csv(Path(path) / EVENTS_FILE)
    summaries = []
    for name in classify_event_columns(events.column_names)["feature"]:
        values = column_as_numpy(events, name)
        family = dtype_family(values.dtype)
        distinct = np.unique(values[~_missing(values)])

        summary: dict = {
            "name": name,
            "family": family,
            "cardinality": int(distinct.size),
        }
        if distinct.size <= MAX_ENUMERATED_VALUES:
            summary["values"] = [_plain(value) for value in distinct]
        if family in (NUMERIC, TEMPORAL) and distinct.size:
            summary["minimum"] = _plain(distinct[0])
            summary["maximum"] = _plain(distinct[-1])
        summaries.append(summary)
    return summaries


def _missing(values):
    import numpy as np

    if values.dtype == object:
        return np.array([value is None for value in values])
    if np.issubdtype(values.dtype, np.floating):
        return np.isnan(values)
    return np.zeros(values.shape, dtype=bool)


def _plain(value):
    """A numpy scalar as something ``json.dumps`` will take without a custom encoder.

    Dates render as their ISO string, which is also the form the expression grammar wants
    them quoted in, so a reader can copy a value out of the summary into an expression.
    """
    import numpy as np

    if isinstance(value, np.datetime64):
        return str(value)
    return value.item() if hasattr(value, "item") else value


def validate_arrival_sequence(record_id, source: str) -> None:
    """Check that ``record_id`` is the dense 0-based arrival sequence 4.2 declares.

    A strategy may read an event's position straight out of its key — that is what makes
    a layout routable one event at a time (7.1.6) instead of derivable only from the
    whole corpus.  The property is a provider's obligation (4.6), so it is checked once
    on load rather than assumed everywhere it is read.

    Deliberately not part of :func:`validate`, which also runs against a corpus produced
    elsewhere: an external source arrives with whatever keys it has, and renumbering them
    by row position is what ingest is for.
    """
    import numpy as np

    values = np.asarray(record_id)
    expected = np.arange(values.shape[0])
    if values.shape[0] and not np.array_equal(values, expected):
        first = int(np.flatnonzero(values != expected)[0])
        raise ContractViolation(
            f"{source}: {RECORD_ID} must be the arrival sequence — dense, 0-based and "
            f"ascending — but row {first} carries {values[first]!r}; a provider resolves "
            f"the order at write time and mints {RECORD_ID} from the row position"
        )


def validate(path: str | Path) -> dict[str, tuple[str, ...]]:
    """Check a dataset directory against the contract before anything reads it.

    Returns the event column roles, so a caller that validates does not then have to
    classify a second time.  Raises :class:`ContractViolation` with a message naming the
    file and the column, because a provider author is the person who sees it.
    """
    import pyarrow.csv

    path = Path(path)
    for name in AUTHORED_FILES:
        if not (path / name).exists():
            raise ContractViolation(f"{path}: missing required file {name!r}")

    checks = (
        (EVENTS_FILE, REQUIRED_EVENT_COLUMNS),
        (QUERIES_FILE, REQUIRED_QUERY_COLUMNS),
        (SELECTIONS_FILE, REQUIRED_SELECTION_COLUMNS),
    )
    columns_by_file = {}
    for filename, required in checks:
        names = pyarrow.csv.read_csv(path / filename).column_names
        missing = [column for column in required if column not in names]
        if missing:
            raise ContractViolation(
                f"{path / filename}: missing required column(s) {missing}"
            )
        columns_by_file[filename] = names

    roles = classify_event_columns(columns_by_file[EVENTS_FILE])
    if not roles["compressed"] or not roles["decompressed"]:
        raise ContractViolation(
            f"{path / EVENTS_FILE}: needs at least one {BLOB_PREFIX}*{COMPRESSED_SUFFIX} "
            f"and one {BLOB_PREFIX}*{DECOMPRESSED_SUFFIX} column; the objective is "
            f"byte-weighted, so a dataset whose sizes cannot be found is not scoreable"
        )
    return roles
