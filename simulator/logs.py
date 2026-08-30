"""The execution log (10.3.7).

Every run writes one file. Events and errors go to stdout *and* to that file; the file is a
tee, not a replacement, because the command a reader runs is a foreground one they are
watching, and moving errors somewhere they have to go looking would make a failed
demonstration harder to read rather than easier.

**Interface is not logging** (10.3.7).  The prompt, the dataset summary, `serving
http://…` — those are what the command *says to the reader*, and they stay on stdout as
themselves, printed.  Only events and errors become records.  Folding the two together
would put a timestamp and a logger name in front of a prompt.

**Records carry no reader-supplied content** (10.3.7.2).  Not a request body, not an
expression, not a block name.  Identifiers and counts stand in, which keeps 12.2.7.1's rule
that operational state is never a channel between readers, and removes log injection
outright rather than escaping for it.

**Run files are never pruned** (10.3.7).  The directory grows one file per run.  It is
gitignored and disposable; `rm -rf data/logs` is the whole retention policy.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

#: One file per run, under the same ephemeral root as every other runtime artifact, so
#: `.gitignore`'s `data/` already covers it.
DEFAULT_DIR = Path("data/logs")

#: Overridable so a test can point the whole facility at a tmp_path without monkeypatching
#: a module global — the same reason `metrics.DEFAULT_DIR` is read at call time.
DIR_ENV_VAR = "SIMULATOR_LOG_DIR"

#: A managed background exhibit is handed one file and writes everything there (10.3.7):
#: printed lines through a redirected stdout, logger records through this path, and no
#: stream handler — there is no terminal to tee to.
FILE_ENV_VAR = "SIMULATOR_LOG_FILE"
TEE_ENV_VAR = "SIMULATOR_LOG_TEE"

#: Everything under `simulator.*` is a child of this, so one call configures the package
#: and nothing touches the root logger: importing `simulator` as a library configures
#: nothing at all.
ROOT = "simulator"

LINE = "%(asctime)s %(levelname)-7s %(name)-22s %(message)s"


class _Formatter(logging.Formatter):
    """Timestamps in the same UTC ISO-8601 the health endpoint publishes (12.2.9)."""

    def formatTime(self, record, datefmt=None) -> str:  # noqa: N802 - base class name
        moment = datetime.fromtimestamp(record.created, tz=timezone.utc)
        return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def log_directory() -> Path:
    return Path(os.environ.get(DIR_ENV_VAR) or DEFAULT_DIR)


def run_file_name(when: datetime | None = None, pid: int | None = None) -> str:
    """`20260819T163505Z-11660.log`.

    Timestamp first, then pid.  Uniqueness would hold either way — a pid cannot repeat
    within one second — but ordering only holds this way round, and a log directory is
    read in the order things happened far more often than it is searched by pid.
    """
    when = when or datetime.now(timezone.utc)
    return f"{when.strftime('%Y%m%dT%H%M%SZ')}-{pid or os.getpid()}.log"


def _unclaimed(directory: Path, name: str) -> Path:
    """`name`, or the first suffixed variant of it that does not exist yet.

    A pid cannot repeat within one second, so two *runs* never collide.  Two calls inside
    one process can, and clobbering a file would lose records — which is a worse outcome
    than the retention 10.3.7 deliberately leaves out, so the name gives way instead.
    """
    candidate = directory / name
    stem, suffix = name[: -len(".log")], ".log"
    attempt = 1
    while candidate.exists():
        candidate = directory / f"{stem}-{attempt}{suffix}"
        attempt += 1
    return candidate


def prepare_run_file() -> Path:
    """Claim a run-file path without attaching handlers.

    The control plane uses this so a background exhibit and its manager agree on one
    file before the child process starts (10.3.7).
    """
    directory = log_directory()
    directory.mkdir(parents=True, exist_ok=True)
    return _unclaimed(directory, run_file_name())


def configure(command: str = "", stream=None) -> Path:
    """Attach the handlers and return the run file.  Called once, from the CLI.

    Returns the path so the caller can print it as interface — telling a reader where the
    record went is a thing the command says to them, not a thing it logs.

    A background exhibit is handed `FILE_ENV_VAR` and `TEE_ENV_VAR=0`: the file already
    exists, and there is no stream to tee to.
    """
    explicit = (os.environ.get(FILE_ENV_VAR) or "").strip()
    if explicit:
        run_file = Path(explicit)
        run_file.parent.mkdir(parents=True, exist_ok=True)
        run_file.touch()
    else:
        run_file = prepare_run_file()

    logger = logging.getLogger(ROOT)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    for stale in list(logger.handlers):
        logger.removeHandler(stale)
        stale.close()

    to_file = logging.FileHandler(run_file, encoding="utf-8")
    to_file.setLevel(logging.DEBUG)
    to_file.setFormatter(_Formatter(LINE))
    logger.addHandler(to_file)

    tee = (os.environ.get(TEE_ENV_VAR, "1") or "1").strip() != "0"
    if tee:
        to_stream = logging.StreamHandler(stream if stream is not None else sys.stdout)
        to_stream.setLevel(logging.INFO)
        to_stream.setFormatter(_Formatter(LINE))
        logger.addHandler(to_stream)

    if command:
        # DEBUG, so it reaches the file but not the terminal: stdout already shows the
        # command the reader typed, and the banner belongs in the record, not in front of it.
        logger.debug("run start command=%s pid=%s", command, os.getpid())
    return run_file


def get(name: str) -> logging.Logger:
    """A child logger for a module.  `get(__name__)` at module scope."""
    return logging.getLogger(name if name.startswith(ROOT) else f"{ROOT}.{name}")
