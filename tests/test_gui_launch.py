"""Launching the GUI when something may already be serving (12.2.8 – 12.2.11).

The three parts are tested the way they are built.  :func:`~simulator.gui.launcher.probe`
touches a socket, so it is checked against real sockets — a live server, foreign listeners,
and a port with nothing on it.  :func:`~simulator.gui.launcher.decide` touches nothing, so
its whole rule set is checked as a table, with no server and no terminal involved.  That
split is the requirement (12.2.11), not a convenience: it is what makes the launch path
assertable at all.

`SIGTERM` is checked against a real subprocess, because a handler that looks right and
leaves the listening socket open is exactly the failure 12.2.10 exists to prevent.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

import simulator
from simulator.__main__ import main
from simulator.core import dataset as dataset_module
from simulator.gui import DEFAULT_HOST, HEALTH_PATH, SERVICE
from simulator.gui.launcher import (
    KEEP,
    RESTART,
    SHUTDOWN,
    Action,
    Probe,
    State,
    decide,
    describe,
    parse_answer,
    probe,
    stop,
)
from simulator.gui.server import build_server
from simulator.providers import synthetic
from simulator.providers.synthetic import DatasetConfig

REPO_ROOT = Path(simulator.__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def catalog_path(tmp_path_factory):
    """A catalog file on disk, which is all `simulator gui` now needs to serve.

    Small and hand-built rather than generated: what these tests exercise is the launch
    lifecycle — probing, recognising, signalling — and none of it reads a figure. The
    shape is pinned by `tests/test_catalog.py` against the real generator, so a stub here
    is not a second definition of the document, only the smallest instance of it.
    """
    path = tmp_path_factory.mktemp("launch") / "catalog.json"
    path.write_text(
        json.dumps(
            {
                "catalog_version": 1,
                "batch_id": "launchfixture",
                "corpus": {
                    "dataset_id": "launch-corpus",
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


@pytest.fixture(scope="module")
def catalog_document(catalog_path):
    return json.loads(catalog_path.read_text())


@pytest.fixture(scope="module")
def running(catalog_document):
    """A live server of ours, so a probe has something to recognise."""
    server = build_server(host=DEFAULT_HOST, port=0, catalog=catalog_document)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def free_port() -> int:
    """A port number nothing is listening on."""
    with socket.socket() as scout:
        scout.bind((DEFAULT_HOST, 0))
        return scout.getsockname()[1]


# -- what the probe finds -------------------------------------------------------------


def test_a_port_with_nothing_on_it_is_free():
    """12.2.8 — a refused connection is the one reading that clears the way to bind."""
    assert probe(DEFAULT_HOST, free_port()).state is State.FREE


def test_our_own_server_is_recognised_and_identified(running, catalog_document):
    """12.2.9 — recognised over loopback alone, with no pid file to consult."""
    found = probe(DEFAULT_HOST, running)
    assert found.state is State.OURS
    assert found.pid == os.getpid()
    # The corpus the catalogue was built against; this process loaded none (12.2.3).
    assert found.dataset_id == catalog_document["corpus"]["dataset_id"]
    assert found.started is not None


def test_a_listener_that_never_speaks_http_is_foreign():
    """12.2.8 — it holds the port, so it is not ours to stop."""
    listener = socket.socket()
    listener.bind((DEFAULT_HOST, 0))
    listener.listen(1)
    try:
        found = probe(DEFAULT_HOST, listener.getsockname()[1], timeout=0.2)
        assert found.state is State.FOREIGN
        assert found.pid is None
    finally:
        listener.close()


def test_another_service_answering_json_is_foreign():
    """12.2.8 — the signature is what identifies us, not the fact that something replied.

    The impostor answers the health path with well-formed JSON, which is the case a
    liveness check that only looked for a 200 would get wrong — and getting it wrong means
    sending `SIGTERM` to a stranger's process.
    """

    class Impostor(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - the base class names it
            body = json.dumps({"service": "something-else", "pid": 1}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer((DEFAULT_HOST, 0), Impostor)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert probe(DEFAULT_HOST, server.server_address[1]).state is State.FOREIGN
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


# -- the rule set, with nothing attached ----------------------------------------------

OURS = Probe(State.OURS, DEFAULT_HOST, 8765, pid=4321)
FREE = Probe(State.FREE, DEFAULT_HOST, 8765)
FOREIGN = Probe(State.FOREIGN, DEFAULT_HOST, 8765)


@pytest.mark.parametrize(
    "found, requested, answer, expected",
    [
        # Nothing there: launch, whatever was asked — except a shutdown, which has
        # nothing left to do.
        (FREE, None, None, Action.LAUNCH),
        (FREE, RESTART, None, Action.LAUNCH),
        (FREE, SHUTDOWN, None, Action.NOTHING_TO_STOP),
        # Someone else's process is never touched, however emphatic the request.
        (FOREIGN, None, None, Action.PORT_BUSY),
        (FOREIGN, RESTART, None, Action.PORT_BUSY),
        (FOREIGN, SHUTDOWN, None, Action.PORT_BUSY),
        # Ours, answered at the prompt.
        (OURS, None, KEEP, Action.KEEP),
        (OURS, None, RESTART, Action.STOP_THEN_LAUNCH),
        (OURS, None, SHUTDOWN, Action.STOP),
        # Ours, answered by flag.
        (OURS, RESTART, None, Action.STOP_THEN_LAUNCH),
        (OURS, SHUTDOWN, None, Action.STOP),
        # A flag beats whatever the prompt would have said.
        (OURS, SHUTDOWN, KEEP, Action.STOP),
        # Ours, and nobody could be asked.
        (OURS, None, None, Action.UNDECIDED),
    ],
)
def test_the_decision_is_a_function_of_what_was_found_and_what_was_asked(
    found, requested, answer, expected
):
    """12.2.8, 12.2.11 — every branch, with no socket and no terminal in reach."""
    assert decide(found, requested, answer) is expected


def test_a_foreign_listener_is_never_stopped():
    """12.2.8 — no combination of inputs turns a stranger's port into a target."""
    assert {
        decide(FOREIGN, requested, answer)
        for requested in (None, RESTART, SHUTDOWN)
        for answer in (None, KEEP, RESTART, SHUTDOWN)
    } == {Action.PORT_BUSY}


# -- the prompt -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "typed, expected",
    [
        ("r", RESTART),
        ("R", RESTART),
        ("restart", RESTART),
        ("s", SHUTDOWN),
        ("k", KEEP),
        ("", KEEP),
        ("  \n", KEEP),
        ("x", None),
        ("42", None),
    ],
)
def test_one_keypress_is_the_whole_answer(typed, expected):
    """12.2.11 — and an unrecognised one is not silently read as something else."""
    assert parse_answer(typed) is expected


def test_pressing_enter_leaves_the_demonstration_alone():
    """12.2.11 — the reflex answer is the one that destroys nothing."""
    assert decide(OURS, None, parse_answer("")) is Action.KEEP


def test_the_reader_is_told_which_instance_before_being_asked_about_it():
    began = (datetime.now(timezone.utc) - timedelta(minutes=12)).isoformat(timespec="seconds")
    rendered = describe(Probe(State.OURS, "127.0.0.1", 8765, 4321, "synthetic-600k", began))
    assert "http://127.0.0.1:8765/" in rendered
    assert "pid 4321" in rendered
    assert "synthetic-600k" in rendered
    assert "up 12m" in rendered


def test_an_instance_that_says_nothing_about_itself_is_still_describable():
    """A health payload missing its optional fields must not break the prompt."""
    assert "pid 4321" in describe(Probe(State.OURS, "127.0.0.1", 8765, 4321))


# -- stopping -------------------------------------------------------------------------


def test_an_instance_with_no_pid_is_not_stoppable():
    """12.2.8 — nothing is signalled on the strength of a probe that found no pid."""
    assert stop(Probe(State.FOREIGN, DEFAULT_HOST, 8765)) is False


def test_sigterm_closes_the_listening_socket_and_exits_clean(catalog_path):
    """12.2.10 — restart depends on the port actually coming free, not just the exit."""
    port = free_port()
    process = subprocess.Popen(
        [
            sys.executable, "-m", "simulator", "gui",
            "--catalog", str(catalog_path),
            "--port", str(port),
            "--no-browser",
        ],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if probe(DEFAULT_HOST, port).state is State.OURS:
                break
            assert process.poll() is None, process.stdout.read()
            time.sleep(0.2)
        else:
            pytest.fail("the server never came up")

        found = probe(DEFAULT_HOST, port)
        assert found.pid == process.pid

        assert stop(found, timeout=10) is True
        assert process.wait(timeout=10) == 0
        assert probe(DEFAULT_HOST, port).state is State.FREE
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


# -- the command ----------------------------------------------------------------------


def test_stopping_nothing_is_success_not_an_error(capsys):
    """12.2.11 — `--stop` asks for a state, and that state already holds."""
    assert main(["gui", "--stop", "--port", str(free_port())]) == 0
    assert "nothing is serving" in capsys.readouterr().out


def test_a_foreign_port_is_reported_and_left_alone(capsys):
    """12.2.8 — and the reader is pointed at --port rather than at a kill."""
    listener = socket.socket()
    listener.bind((DEFAULT_HOST, 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    try:
        assert main(["gui", "--port", str(port), "--stop"]) == 1
        output = capsys.readouterr().out
        assert "held by another process" in output
        assert "--port" in output
    finally:
        listener.close()


def test_a_running_instance_meeting_no_terminal_refuses_rather_than_guesses(
    running, capsys, monkeypatch
):
    """12.2.11 — non-interactive and unasked, it exits non-zero and names the flags."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    assert main(["gui", "--port", str(running)]) == 1
    output = capsys.readouterr().out
    assert "already serving" in output
    assert "--restart" in output and "--stop" in output


def test_stop_and_restart_are_not_both_answerable():
    """12.2.11 — they answer the same question, and both says neither."""
    with pytest.raises(SystemExit):
        main(["gui", "--stop", "--restart"])
