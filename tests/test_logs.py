"""The execution log (10.3.7).

Every assertion here is about the *facility* — where a record goes, what its file is
called, and what a record is not allowed to contain. What any particular line says is the
business of the module that emits it.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone

import pytest

from simulator import logs

RUN_FILE = re.compile(r"^(\d{8}T\d{6}Z)-(\d+)\.log$")


@pytest.fixture(scope="module")
def tiny_dataset(tmp_path_factory):
    """Small enough to build inside a unit test, real enough to refuse a bad column."""
    from simulator.core import dataset as dataset_module
    from simulator.providers import synthetic
    from simulator.providers.synthetic import DatasetConfig

    config = DatasetConfig(
        name="log-corpus",
        n_events=300,
        n_transaction_days=20,
        n_query_days=5,
        half_life_days=5.0,
        seed=92,
    )
    return dataset_module.load(synthetic.generate(config, tmp_path_factory.mktemp("logs")))


@pytest.fixture
def log_dir(tmp_path, monkeypatch):
    """A log root of our own, and the package logger left as we found it."""
    monkeypatch.setenv(logs.DIR_ENV_VAR, str(tmp_path))
    logger = logging.getLogger(logs.ROOT)
    before = list(logger.handlers)
    try:
        yield tmp_path
    finally:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()
        for handler in before:
            logger.addHandler(handler)


# -- the run file -------------------------------------------------------------------


def test_a_run_writes_one_file_into_a_directory_it_creates(log_dir):
    """10.3.7 — the directory is not a precondition the reader has to satisfy."""
    nested = log_dir / "deeper" / "still"
    os.environ[logs.DIR_ENV_VAR] = str(nested)
    run_file = logs.configure("gui")
    assert run_file.exists()
    assert run_file.parent == nested


def test_the_name_is_a_utc_timestamp_then_the_pid(log_dir):
    """10.3.7 — timestamp first, so the directory sorts into the order things happened."""
    matched = RUN_FILE.match(logs.configure("gui").name)
    assert matched, "file name does not match <UTC timestamp>Z-<pid>.log"
    stamp, pid = matched.groups()
    assert int(pid) == os.getpid()
    assert datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(
        tzinfo=timezone.utc
    ) <= datetime.now(timezone.utc)


def test_sorting_the_names_sorts_the_runs(log_dir):
    """The whole reason the timestamp leads: `ls` is the chronology."""
    moments = [
        datetime(2026, 8, 20, 5, 55, 54, tzinfo=timezone.utc),
        datetime(2026, 8, 20, 5, 55, 55, tzinfo=timezone.utc),
        datetime(2026, 8, 21, 1, 0, 0, tzinfo=timezone.utc),
    ]
    names = [logs.run_file_name(when=m, pid=999) for m in moments]
    assert sorted(names) == names


def test_two_runs_in_one_second_do_not_collide(log_dir):
    """Same second, different process: the pid is what separates them."""
    moment = datetime(2026, 8, 20, 5, 55, 54, tzinfo=timezone.utc)
    assert logs.run_file_name(when=moment, pid=1) != logs.run_file_name(
        when=moment, pid=2
    )


def test_nothing_is_pruned(log_dir):
    """10.3.7 — files accumulate; there is no retention policy but `rm`."""
    first = logs.configure("generate")
    second = logs.configure("gui")
    assert first != second
    assert first.exists() and second.exists()
    assert len(list(log_dir.glob("*.log"))) == 2


# -- where a record goes ------------------------------------------------------------


def test_a_record_reaches_both_the_file_and_the_stream(log_dir, capsys):
    """10.3.7 — the file is a tee, so an error is never only in the file."""
    run_file = logs.configure("gui")
    logs.get("simulator.test").info("bound host=%s port=%s", "127.0.0.1", 8765)

    assert "bound host=127.0.0.1 port=8765" in run_file.read_text()
    assert "bound host=127.0.0.1 port=8765" in capsys.readouterr().out


def test_the_file_keeps_what_the_terminal_is_spared(log_dir, capsys):
    """The file is DEBUG and the stream is INFO, which is what makes a tee useful."""
    run_file = logs.configure("gui")
    logs.get("simulator.test").debug("probe state=free")

    assert "probe state=free" in run_file.read_text()
    assert "probe state=free" not in capsys.readouterr().out


def test_the_root_logger_is_never_touched(log_dir):
    """Configuring this package must not reconfigure someone else's application."""
    root = logging.getLogger()
    before = list(root.handlers), root.level

    logs.configure("gui")

    assert (list(root.handlers), root.level) == before
    # And records stop at the package logger rather than climbing to the root.
    assert logging.getLogger(logs.ROOT).propagate is False


def test_configuring_twice_does_not_double_every_record(log_dir, capsys):
    """A second `configure` replaces its handlers rather than stacking them."""
    logs.configure("generate")
    run_file = logs.configure("gui")
    logs.get("simulator.test").info("once")

    assert run_file.read_text().count("once") == 1
    assert capsys.readouterr().out.count("once") == 1


# -- what a record may not carry ----------------------------------------------------


def test_the_timestamp_is_the_one_the_health_endpoint_publishes(log_dir):
    """10.3.7 — one clock and one format across the process's operational surface."""
    run_file = logs.configure("gui")
    logs.get("simulator.test").info("anything")
    stamp = run_file.read_text().splitlines()[-1].split()[0]
    assert datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")
