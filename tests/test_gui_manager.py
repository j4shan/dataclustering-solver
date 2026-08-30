"""Managed background lifecycle for the local exhibit (8.9.1, 12.2.8)."""

from __future__ import annotations

import json
import socket
import time
from pathlib import Path

import pytest

import simulator
from simulator.gui import DEFAULT_HOST
from simulator.gui.launcher import State, probe
from simulator.gui.manager import launch, restart, shutdown, status
from simulator import logs

REPO_ROOT = Path(simulator.__file__).resolve().parents[1]


@pytest.fixture
def catalog_path(tmp_path):
    path = tmp_path / "catalog.json"
    path.write_text(
        json.dumps(
            {
                "catalog_version": 1,
                "batch_id": "managerfixture",
                "corpus": {
                    "dataset_id": "manager-corpus",
                    "event_count": 500,
                    "query_count": 6,
                    "feature_columns": [],
                },
                "baseline": {"strategy": "insertion_order", "capacities": [1000]},
                "strategies": [],
                "rows": [],
            }
        )
    )
    return path


def free_port() -> int:
    with socket.socket() as scout:
        scout.bind((DEFAULT_HOST, 0))
        return scout.getsockname()[1]


@pytest.fixture
def log_dir(tmp_path, monkeypatch):
    monkeypatch.setenv(logs.DIR_ENV_VAR, str(tmp_path / "logs"))
    return tmp_path / "logs"


def test_status_on_a_free_port_is_success(log_dir):
    port = free_port()
    reading = status(DEFAULT_HOST, port)
    assert reading.ok
    assert "nothing is serving" in reading.message
    assert reading.found.state is State.FREE


def test_status_reports_a_foreign_listener():
    listener = socket.socket()
    listener.bind((DEFAULT_HOST, 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    try:
        reading = status(DEFAULT_HOST, port)
        assert not reading.ok
        assert "held by another process" in reading.message
        assert reading.found.state is State.FOREIGN
    finally:
        listener.close()


def test_stop_on_a_free_port_is_success():
    port = free_port()
    outcome = shutdown(DEFAULT_HOST, port)
    assert outcome.ok
    assert "nothing is serving" in outcome.message


def test_a_foreign_listener_is_never_stopped_or_replaced():
    listener = socket.socket()
    listener.bind((DEFAULT_HOST, 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    try:
        assert shutdown(DEFAULT_HOST, port).ok is False
        assert launch(DEFAULT_HOST, port).ok is False
        assert restart(DEFAULT_HOST, port).ok is False
        assert probe(DEFAULT_HOST, port).state is State.FOREIGN
    finally:
        listener.close()


def test_launch_without_a_catalog_refuses_and_names_the_build(tmp_path):
    missing = tmp_path / "no-such-catalog.json"
    outcome = launch(DEFAULT_HOST, free_port(), catalog=missing)
    assert not outcome.ok
    assert "no catalog" in outcome.message
    assert "generate" in outcome.message


def test_background_launch_stop_and_log_capture(catalog_path, log_dir, monkeypatch):
    """12.2.8, 10.3.7 — the child answers as ours, the log holds its output, stop frees the port."""
    monkeypatch.setattr("webbrowser.open", lambda *_: None)
    port = free_port()
    started = launch(
        DEFAULT_HOST,
        port,
        catalog_path,
        open_browser=True,
        timeout=60,
    )
    try:
        assert started.ok, started.message
        assert started.found is not None
        assert started.found.state is State.OURS
        assert started.log_path is not None
        assert started.log_path.exists()
        deadline = time.monotonic() + 5
        written = ""
        while time.monotonic() < deadline:
            written = started.log_path.read_text(encoding="utf-8")
            if "serving" in written or "bound" in written:
                break
            time.sleep(0.1)
        assert started.log_path.exists()

        reading = status(DEFAULT_HOST, port)
        assert reading.ok
        assert reading.found.pid == started.found.pid

        stopped = shutdown(DEFAULT_HOST, port)
        assert stopped.ok
        assert probe(DEFAULT_HOST, port).state is State.FREE
    finally:
        if probe(DEFAULT_HOST, port).state is State.OURS:
            shutdown(DEFAULT_HOST, port)


def test_launch_when_ours_without_replace_leaves_it(catalog_path, log_dir, monkeypatch):
    monkeypatch.setattr("webbrowser.open", lambda *_: None)
    port = free_port()
    first = launch(DEFAULT_HOST, port, catalog_path, timeout=60)
    try:
        assert first.ok
        second = launch(DEFAULT_HOST, port, catalog_path, replace=False)
        assert second.ok
        assert "left running" in second.message
        assert probe(DEFAULT_HOST, port).pid == first.found.pid
    finally:
        shutdown(DEFAULT_HOST, port)


def test_replace_restarts_after_the_caller_has_already_built(
    catalog_path, log_dir, monkeypatch
):
    monkeypatch.setattr("webbrowser.open", lambda *_: None)
    port = free_port()
    first = launch(DEFAULT_HOST, port, catalog_path, timeout=60)
    try:
        assert first.ok
        first_pid = first.found.pid
        replaced = launch(
            DEFAULT_HOST, port, catalog_path, replace=True, timeout=60
        )
        assert replaced.ok, replaced.message
        assert replaced.found.pid != first_pid
        assert probe(DEFAULT_HOST, port).state is State.OURS
    finally:
        shutdown(DEFAULT_HOST, port)


def test_readiness_timeout_stops_the_child_and_names_the_log(
    catalog_path, log_dir, monkeypatch
):
    monkeypatch.setattr(
        "simulator.gui.manager._wait_ready", lambda *_a, **_k: None
    )
    port = free_port()
    outcome = launch(DEFAULT_HOST, port, catalog_path, timeout=0.1)
    assert not outcome.ok
    assert "did not become ready" in outcome.message
    assert outcome.log_path is not None
    assert probe(DEFAULT_HOST, port).state is State.FREE
