"""Managed background lifecycle for the local exhibit (8.9.1, 12.2.8).

The `gui` subcommand stays a foreground process: a deployed instance and any script that
already waits on it keep that contract.  The control plane starts the same command as a
child, waits until the health endpoint recognises it, and returns.  The serving process
outlives the menu.

Identity is still the signed health response (12.2.9).  A pid the manager remembers is
never enough to stop something, and a listener that is not ours is never touched.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path

from . import DEFAULT_HOST, DEFAULT_PORT
from .launcher import Action, Probe, State, decide, describe, probe, stop
from .. import logs

log = logs.get(__name__)

READY_TIMEOUT = 60.0
POLL = 0.2


@dataclass(frozen=True)
class Outcome:
    """What one lifecycle action concluded, for the menu to print and for tests to read."""

    ok: bool
    message: str
    found: Probe | None = None
    log_path: Path | None = None

    @property
    def exit_code(self) -> int:
        return 0 if self.ok else 1


def status(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> Outcome:
    """Who is holding the port, if anyone, without binding it."""
    found = probe(host, port)
    if found.state is State.FREE:
        return Outcome(True, f"nothing is serving on {found.url}", found)
    if found.state is State.FOREIGN:
        return Outcome(
            False,
            f"port {port} on {host} is held by another process",
            found,
        )
    return Outcome(True, describe(found), found)


def launch(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    catalog: Path | None = None,
    *,
    open_browser: bool = False,
    timeout: float = READY_TIMEOUT,
    replace: bool = False,
) -> Outcome:
    """Start a background exhibit, or refuse.

    `replace` is the Build & Launch reading: an instance of ours is stopped *after* the
    caller has already finished the catalog, then a new child is started.  Without it,
    finding ours is not a launch — the menu asks, or a second invocation leaves it.
    """
    found = probe(host, port)
    if found.state is State.FOREIGN:
        return Outcome(
            False,
            f"port {port} on {host} is held by another process\n"
            "stop that process, or serve somewhere else with --port",
            found,
        )
    if found.state is State.OURS and not replace:
        return Outcome(True, f"left running  {found.url}", found)
    if found.state is State.OURS and replace:
        stopped = shutdown(host, port)
        if not stopped.ok:
            return stopped

    return _spawn(host, port, catalog, open_browser=open_browser, timeout=timeout)


def shutdown(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> Outcome:
    """Stop an instance of ours.  Already-free is success; a stranger is not."""
    found = probe(host, port)
    action = decide(found, requested="shutdown")
    if action is Action.PORT_BUSY:
        return Outcome(
            False,
            f"port {port} on {host} is held by another process",
            found,
        )
    if action is Action.NOTHING_TO_STOP:
        return Outcome(True, f"nothing is serving on {found.url}", found)
    print(f"stopping pid {found.pid}…")
    if not stop(found):
        return Outcome(
            False,
            f"pid {found.pid} did not stop — `kill -9 {found.pid}` to force it",
            found,
        )
    return Outcome(True, "stopped", found)


def restart(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    catalog: Path | None = None,
    *,
    open_browser: bool = False,
    timeout: float = READY_TIMEOUT,
) -> Outcome:
    """Stop an instance of ours, then start one.  A stranger is left alone."""
    found = probe(host, port)
    if found.state is State.FOREIGN:
        return Outcome(
            False,
            f"port {port} on {host} is held by another process",
            found,
        )
    if found.state is State.OURS:
        stopped = shutdown(host, port)
        if not stopped.ok:
            return stopped
    return _spawn(host, port, catalog, open_browser=open_browser, timeout=timeout)


def _spawn(
    host: str,
    port: int,
    catalog: Path | None,
    *,
    open_browser: bool,
    timeout: float,
) -> Outcome:
    """Start `python -m simulator gui` detached and wait until it answers as ours."""
    catalog_path = Path(catalog) if catalog is not None else Path(
        "data/catalog/strategy-catalog.json"
    )
    if not catalog_path.exists():
        return Outcome(
            False,
            f"no catalog at {catalog_path}\n"
            "build one first:\n"
            "    python -m simulator generate     # bootstrap a corpus\n"
            "    python -m simulator catalog      # score the catalogue",
        )

    log_path = logs.prepare_run_file()
    env = os.environ.copy()
    env[logs.FILE_ENV_VAR] = str(log_path)
    env[logs.TEE_ENV_VAR] = "0"

    command = [
        sys.executable,
        "-m",
        "simulator",
        "gui",
        "--host",
        host,
        "--port",
        str(port),
        "--catalog",
        str(catalog_path),
        "--no-browser",
    ]
    handle = open(log_path, "a", encoding="utf-8")
    try:
        process = subprocess.Popen(
            command,
            cwd=_repo_root(),
            stdin=subprocess.DEVNULL,
            stdout=handle,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
        )
    except OSError as failed:
        handle.close()
        return Outcome(False, f"could not start the exhibit: {failed}", log_path=log_path)

    ready = _wait_ready(host, port, process, timeout)
    if ready is None:
        handle.close()
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        return Outcome(
            False,
            f"the exhibit did not become ready in {timeout:.0f}s\n  log  {log_path}",
            log_path=log_path,
        )

    handle.close()
    print(f"serving {ready.url}")
    print(f"log  {log_path}")
    if open_browser:
        webbrowser.open(ready.url)
    return Outcome(True, f"serving {ready.url}", ready, log_path)


def _wait_ready(
    host: str, port: int, process: subprocess.Popen, timeout: float
) -> Probe | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return None
        found = probe(host, port)
        if found.state is State.OURS:
            return found
        time.sleep(POLL)
    return None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
