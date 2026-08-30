"""The interactive control plane (8.9.1).

Dispatch and ordering are the load-bearing checks: whether a keypress reaches the
right operation, whether a missing terminal refuses rather than blocking, and whether
Build & Launch finishes the catalogue before it may replace a running exhibit.
"""

from __future__ import annotations

from simulator.__main__ import NO_TERMINAL_HELP, SUBCOMMANDS, main
from simulator.gui.launcher import State
from simulator.menu import CHOICES, Target, run


def test_no_terminal_and_no_subcommand_names_the_commands(capsys, monkeypatch):
    """8.9.1 — a script or CI job must not sit waiting for a number."""
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert main([]) == 1
    output = capsys.readouterr().out
    assert "no terminal" in output
    for name in SUBCOMMANDS:
        assert name in output
    assert NO_TERMINAL_HELP.split("\n")[0] in output


def test_the_menu_lists_every_operation():
    labels = [label for _, label in CHOICES]
    assert labels[0] == "Build & Launch"
    assert "Status" in labels
    assert "Launch" in labels
    assert "Stop" in labels
    assert "Restart" in labels
    assert "Generate corpus" in labels
    assert "Build catalogue" in labels
    assert "Run benchmark report" in labels
    assert labels[-1] == "Quit"


def test_quit_leaves_the_loop(monkeypatch, capsys):
    answers = iter(["q"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))
    assert run(Target("127.0.0.1", 9)) == 0
    assert "control plane" in capsys.readouterr().out


def test_invalid_input_is_refused_and_the_loop_continues(monkeypatch, capsys):
    answers = iter(["x", "q"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))
    assert run(Target("127.0.0.1", 9)) == 0
    assert "1–8, or q to quit" in capsys.readouterr().out


def test_eof_is_a_clean_quit(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: (_ for _ in ()).throw(EOFError()))
    assert run(Target("127.0.0.1", 9)) == 0


def test_status_is_reachable_from_the_menu(monkeypatch, capsys):
    answers = iter(["2", "q"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))
    assert run(Target("127.0.0.1", 9)) == 0
    output = capsys.readouterr().out
    assert "nothing is serving" in output


def test_a_missing_harness_stays_in_the_menu(monkeypatch, capsys):
    """10.3.9 — the menu names the extra and does not exit."""

    def missing(_where):
        raise ImportError(name="numpy")

    answers = iter(["7", "q"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))
    monkeypatch.setattr("simulator.menu._catalog", missing)
    from simulator import menu as menu_module

    monkeypatch.setitem(menu_module.ACTIONS, "7", missing)
    assert run(Target("127.0.0.1", 9)) == 0
    output = capsys.readouterr().out
    assert "harness" in output
    assert "numpy" in output


def test_build_and_launch_finishes_the_catalogue_before_replacing(monkeypatch, capsys):
    """8.9.1 — a failed or in-flight build must not stop the current exhibit."""
    order: list[str] = []

    def catalog(_args):
        order.append("catalog")
        return 0

    class Found:
        state = State.OURS

    def launch(*_args, replace, **_kwargs):
        order.append(f"launch-replace={replace}")
        return type("Outcome", (), {"message": "serving http://127.0.0.1:9/"})()

    answers = iter(["1", "q"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))
    monkeypatch.setattr("simulator.menu.cmd_catalog", catalog, raising=False)
    monkeypatch.setattr("simulator.__main__.cmd_catalog", catalog)
    monkeypatch.setattr("simulator.menu.probe", lambda *_: Found())
    monkeypatch.setattr("simulator.menu.manager.launch", launch)
    assert run(Target("127.0.0.1", 9)) == 0
    assert order == ["catalog", "launch-replace=True"]
    assert "serving" in capsys.readouterr().out


def test_a_failed_catalogue_does_not_replace_a_running_exhibit(monkeypatch, capsys):
    launched = []

    def catalog(_args):
        return 1

    def launch(**_kwargs):
        launched.append(True)
        raise AssertionError("launch must not run after a failed catalog")

    answers = iter(["1", "q"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))
    monkeypatch.setattr("simulator.__main__.cmd_catalog", catalog)
    monkeypatch.setattr("simulator.menu.manager.launch", launch)
    assert run(Target("127.0.0.1", 9)) == 0
    assert launched == []
    assert "was not replaced" in capsys.readouterr().out
