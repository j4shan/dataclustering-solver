"""The reusable figure-zoom widget (12.1.10)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from simulator.gui import SITE_ROOT

RUNNER = Path(__file__).parent / "js" / "test_figure_zoom.mjs"

needs_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="node is not installed; the widget runs in a browser"
)


@needs_node
def test_attach_zoom_steps_and_is_idempotent():
    finished = subprocess.run(
        ["node", str(RUNNER), str(SITE_ROOT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert finished.returncode == 0, finished.stderr
    payload = json.loads(finished.stdout)
    assert payload["ok"] is True
    assert payload["steps"][0] < 1 < payload["steps"][-1]


def test_the_widget_is_not_a_second_html_assignment():
    source = (SITE_ROOT / "figure-zoom.js").read_text()
    assert ".innerHTML" not in source
    assert "localStorage" not in source
    assert "sessionStorage" not in source


def test_the_buttons_live_on_the_stage_not_the_scroller():
    """12.1.10 — chrome is pinned to the placeholder; only the drawing pans."""
    source = (SITE_ROOT / "figure-zoom.js").read_text()
    css = (SITE_ROOT / "app.css").read_text()
    assert "zoom-viewport" in source
    assert "overflow: hidden" in css.split(".is-zoomable {", 1)[1].split("}", 1)[0]
    assert "overflow: auto" in css.split(".zoom-viewport {", 1)[1].split("}", 1)[0]


def test_the_buttons_sit_at_the_top_middle():
    """12.1.10 — the pair is centred on the stage, clear of the scrollbar."""
    widget = (SITE_ROOT / "app.css").read_text().split(".zoom-widget {", 1)[1].split("}", 1)[0]
    assert "margin-inline: auto" in widget
    assert "left: 0" in widget
    assert "right: 0" in widget
    assert "right: var(--space-1)" not in widget


def test_the_shell_attaches_after_mount():
    app = (SITE_ROOT / "app.js").read_text()
    assert 'from "./figure-zoom.js"' in app
    assert "attachZoom(pane)" in app
