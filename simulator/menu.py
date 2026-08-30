"""The interactive control plane (8.9.1).

`python -m simulator` with no subcommand opens this when stdin is a terminal.  Every
operation the CLI already offers is a numbered choice; the serving process, when this
menu starts it, is a managed background exhibit and outlives the loop.

The rule set for the port lives in `gui.launcher` and `gui.manager`.  This module only
asks, prints, and calls.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from .gui import Deployment
from .gui.launcher import KEEP, RESTART, SHUTDOWN, State, ask, probe
from .gui import manager

CHOICES = (
    ("1", "Build & Launch"),
    ("2", "Status"),
    ("3", "Launch"),
    ("4", "Stop"),
    ("5", "Restart"),
    ("6", "Generate corpus"),
    ("7", "Build catalogue"),
    ("8", "Run benchmark report"),
    ("q", "Quit"),
)


@dataclass(frozen=True)
class Target:
    host: str
    port: int


def run(target: Target | None = None) -> int:
    """Loop until the reader quits.  The exhibit, if running, is left as it is."""
    deployment = Deployment.from_environment()
    where = target or Target(deployment.host, deployment.port)
    print()
    print("dataclustering-solver  ·  control plane")
    print("A numbered choice does the work; q leaves the exhibit running.")
    while True:
        _banner(where)
        try:
            typed = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if typed in {"q", "quit"}:
            return 0
        action = ACTIONS.get(typed)
        if action is None:
            print("  1–8, or q to quit")
            continue
        try:
            action(where)
        except ImportError as missing:
            print(_harness_needed(missing))
        except SystemExit as stopped:
            # Harness commands raise SystemExit for a named install gap (10.3.9).
            if stopped.code not in (0, None):
                print(stopped)
            elif stopped.code is None:
                pass


def _banner(where: Target) -> None:
    print()
    reading = manager.status(where.host, where.port)
    print(f"exhibit  {reading.message}")
    print()
    for key, label in CHOICES:
        print(f"  {key}  {label}")
    print()


def _build_and_launch(where: Target) -> None:
    """Score the catalogue, then start (or replace) the exhibit (8.9.1).

    The catalog finishes before any running instance of ours is stopped.  A failed
    build leaves the current exhibit alone.
    """
    from .__main__ import cmd_catalog

    print("building the catalogue…")
    code = cmd_catalog(argparse.Namespace(dataset=None, out=None, command="catalog"))
    if code not in (0, None):
        print("catalogue build failed — the exhibit was not replaced")
        return
    found = probe(where.host, where.port)
    outcome = manager.launch(
        where.host,
        where.port,
        open_browser=True,
        replace=found.state is State.OURS,
    )
    print(outcome.message)


def _status(where: Target) -> None:
    print(manager.status(where.host, where.port).message)


def _launch(where: Target) -> None:
    from .gui.launcher import probe

    found = probe(where.host, where.port)
    if found.state is State.OURS:
        answer = ask(found)
        if answer is KEEP:
            print(f"left running  {found.url}")
            return
        if answer is SHUTDOWN:
            print(manager.shutdown(where.host, where.port).message)
            return
        if answer is RESTART:
            print(
                manager.restart(
                    where.host, where.port, open_browser=True
                ).message
            )
            return
    print(manager.launch(where.host, where.port, open_browser=True).message)


def _stop(where: Target) -> None:
    print(manager.shutdown(where.host, where.port).message)


def _restart(where: Target) -> None:
    print(manager.restart(where.host, where.port, open_browser=True).message)


def _generate(_where: Target) -> None:
    from .__main__ import cmd_generate

    cmd_generate(
        argparse.Namespace(
            provider="synthetic", source=None, name=None, command="generate"
        )
    )


def _catalog(_where: Target) -> None:
    from .__main__ import cmd_catalog

    cmd_catalog(argparse.Namespace(dataset=None, out=None, command="catalog"))


def _report(_where: Target) -> None:
    from .__main__ import cmd_run

    cmd_run(argparse.Namespace(dataset=None, rebuild=False, command="run"))


def _harness_needed(missing: ImportError) -> str:
    from .__main__ import HARNESS_GROUP

    package = missing.name or str(missing)
    return (
        f"this action needs the harness, and {package} is not installed.\n"
        f"    pip install -e '.[{HARNESS_GROUP}]'"
    )


ACTIONS = {
    "1": _build_and_launch,
    "2": _status,
    "3": _launch,
    "4": _stop,
    "5": _restart,
    "6": _generate,
    "7": _catalog,
    "8": _report,
}
