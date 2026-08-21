"""What to do about the port before binding it (12.2.8 – 12.2.11).

`python -m simulator gui` is the whole launch procedure, so it has to survive being typed
twice.  Binding blind and letting the second one die on `Address already in use` is the
failure most likely to happen in front of an audience, in the least readable form there
is, so the command asks first: **who has this port, and is it us?**

Answering that over HTTP rather than from a pid file is deliberate, and not because a pid
file would be disallowed — 12.2.7.1 permits one as operational state.  Asking the socket is
simply the better answer to the question (12.2.9.1): a running instance is recognisable
whatever directory or checkout it was started from, and a process that died hard leaves no
stale file behind to reason about.

The decision is split three ways on purpose: :func:`probe` is the only part that touches a
socket, :func:`ask` is the only part that touches a terminal, and :func:`decide` — which
holds every rule about what should happen — touches neither.  That is what makes the
launch path assertable under pytest with no server and no TTY (12.2.11).

Two refusals are behaviour, not caution:

* **A listener that is not ours is never terminated.**  The port is a guess this project
  made; the process holding it belongs to someone else.
* **A running instance is never replaced without an answer.**  With no terminal to ask at
  and no flag given, the command stops and says so, rather than choosing the destructive
  reading of silence — the instance it would kill may be the one being demonstrated.
"""

from __future__ import annotations

import http.client
import json
import os
import signal
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from . import DEFAULT_HOST, DEFAULT_PORT, HEALTH_PATH, SERVICE
from .. import logs

log = logs.get(__name__)


class State(Enum):
    """What :func:`probe` found on the port."""

    #: Nothing is listening.  The port is ours to take.
    FREE = "free"
    #: This server, identified by its own health endpoint.
    OURS = "ours"
    #: Something is listening and it is not us.  Not ours to stop.
    FOREIGN = "foreign"


class Action(Enum):
    """What the command should do about it."""

    LAUNCH = "launch"
    STOP_THEN_LAUNCH = "stop_then_launch"
    STOP = "stop"
    KEEP = "keep"
    #: The port is held by another process — report it, do not touch it.
    PORT_BUSY = "port_busy"
    #: `--stop` with nothing to stop.  The desired state already holds.
    NOTHING_TO_STOP = "nothing_to_stop"
    #: An instance is running, nobody can be asked, and no flag said what to do.
    UNDECIDED = "undecided"


#: The answers :func:`ask` and the CLI flags both resolve to, so one token set reaches
#: :func:`decide` however the decision was made.
RESTART = "restart"
SHUTDOWN = "shutdown"
KEEP = "keep"

_KEYS = {"r": RESTART, "s": SHUTDOWN, "k": KEEP, "": KEEP}

PROMPT = "[r] restart   [s] shutdown   [k] keep running\n> "


@dataclass(frozen=True)
class Probe:
    """A reading of one host and port, with whatever the holder said about itself."""

    state: State
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    pid: int | None = None
    dataset_id: str | None = None
    started: str | None = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/"


def probe(
    host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, timeout: float = 0.5
) -> Probe:
    """Ask the port who is holding it (12.2.8).

    A refused connection is the only reading of FREE.  Everything else that is not a
    well-formed answer carrying our signature — a timeout, a non-200, another service's
    JSON, a plain socket that never speaks HTTP — is FOREIGN, because in every one of
    those cases something has the port and this command may not have it.
    """
    connection = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        connection.request("GET", HEALTH_PATH)
        response = connection.getresponse()
        payload = json.loads(response.read())
        if response.status != 200 or payload.get("service") != SERVICE:
            return Probe(State.FOREIGN, host, port)
        return Probe(
            State.OURS,
            host,
            port,
            pid=payload.get("pid"),
            dataset_id=payload.get("dataset_id"),
            started=payload.get("started"),
        )
    except ConnectionRefusedError:
        return Probe(State.FREE, host, port)
    except (OSError, http.client.HTTPException, ValueError):
        # ValueError covers json.JSONDecodeError; OSError covers TimeoutError.
        return Probe(State.FOREIGN, host, port)
    finally:
        connection.close()


def decide(found: Probe, requested: str | None = None, answer: str | None = None) -> Action:
    """The whole rule set, as a pure function of what was found and what was asked.

    `requested` is the flag (`--stop`, `--restart`) and wins over `answer`, which is what
    a reader typed at the prompt.  Both being absent is meaningful rather than neutral:
    with an instance running it means nobody could be asked, and the answer is to stop and
    say so (12.2.11).
    """
    if found.state is State.FOREIGN:
        return Action.PORT_BUSY
    if found.state is State.FREE:
        return Action.NOTHING_TO_STOP if requested == SHUTDOWN else Action.LAUNCH
    return {
        SHUTDOWN: Action.STOP,
        RESTART: Action.STOP_THEN_LAUNCH,
        KEEP: Action.KEEP,
        None: Action.UNDECIDED,
    }[requested or answer]


def stop(found: Probe, timeout: float = 5.0) -> bool:
    """`SIGTERM`, then wait for the port to come free.  Returns whether it did.

    No escalation to `SIGKILL`.  A process that ignores `SIGTERM` is doing something this
    command does not understand, and killing it uninvited is how a demonstration loses
    work that had nothing to do with the demonstration.  The caller reports the pid
    instead and lets the reader decide.
    """
    if found.pid is None:
        return False
    log.info("sending SIGTERM to pid=%s", found.pid)
    try:
        os.kill(found.pid, signal.SIGTERM)
    except ProcessLookupError:
        return True  # It went away between the probe and the signal.  Same end state.
    except PermissionError:
        return False

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if probe(found.host, found.port).state is State.FREE:
            return True
        time.sleep(0.1)
    return False


def parse_answer(text: str) -> str | None:
    """One keypress, or `None` for anything that is not an offered answer.

    An empty line is `keep`: the reader pressed Enter to get out of the way, and the
    non-destructive reading is the only safe one to attach to a reflex.
    """
    return _KEYS.get(text.strip()[:1].lower())


def describe(found: Probe) -> str:
    """Which demonstration is already running, before asking whether to replace it."""
    detail = [f"pid {found.pid}"]
    if found.dataset_id:
        detail.append(f"dataset {found.dataset_id}")
    uptime = _uptime(found.started)
    if uptime:
        detail.append(f"up {uptime}")
    return f"already serving  {found.url}\n  " + " · ".join(detail)


def ask(found: Probe, attempts: int = 3) -> str:
    """Prompt, and return one of the answer tokens.  Only ever called at a terminal."""
    print(describe(found))
    print()
    for _ in range(attempts):
        try:
            answer = parse_answer(input(PROMPT))
        except (EOFError, KeyboardInterrupt):
            print()
            return KEEP
        if answer is not None:
            return answer
        print("  r, s or k — or Enter to leave it running")
    return KEEP


def _uptime(started: str | None) -> str | None:
    if not started:
        return None
    try:
        began = datetime.fromisoformat(started)
    except ValueError:
        return None
    if began.tzinfo is None:
        began = began.replace(tzinfo=timezone.utc)
    seconds = int((datetime.now(timezone.utc) - began).total_seconds())
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    return f"{seconds // 3600}h {seconds % 3600 // 60}m"
