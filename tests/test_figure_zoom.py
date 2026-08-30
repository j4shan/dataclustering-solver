"""The reusable figure-zoom widget (12.1.10)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from simulator.gui import STATIC_ROOT

RUNNER = Path(__file__).parent / "js" / "test_figure_zoom.mjs"

needs_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="node is not installed; the widget runs in a browser"
)


@needs_node
def test_attach_zoom_steps_and_is_idempotent():
    finished = subprocess.run(
        ["node", str(RUNNER), str(STATIC_ROOT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert finished.returncode == 0, finished.stderr
    payload = json.loads(finished.stdout)
    assert payload["ok"] is True
    assert payload["steps"][0] < 1 < payload["steps"][-1]


def test_the_widget_is_not_a_second_html_assignment():
    source = (STATIC_ROOT / "figure-zoom.js").read_text()
    assert ".innerHTML" not in source
    assert "localStorage" not in source
    assert "sessionStorage" not in source


def test_the_shell_attaches_after_mount():
    app = (STATIC_ROOT / "app.js").read_text()
    assert 'from "./figure-zoom.js"' in app
    assert "attachZoom(pane)" in app
