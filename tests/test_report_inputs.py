"""Where a chart's numbers come from (8.4).

One rule, two surfaces.  A chart is drawn from the metric rows of the evaluation that
produced them — the sweep hands its rows to the report, and the catalog build hands its rows
to the page.  Neither re-reads the metric table to draw, and the table is the durable
record rather than the render's input (11.12 records why re-rendering from it is not a
capability this project has).

These are structural rather than pixel-level on purpose: what 8.4 constrains is the
*direction data flows*, and that is a property of which module imports which.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from simulator.bench import metrics
from simulator.report import charts, page

REPORT_DIR = Path(charts.__file__).parent


def imported_modules(path: Path) -> set[str]:
    """Every module name the file imports, however it spells the import."""
    tree = ast.parse(path.read_text())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            names.add(base)
            names.update(f"{base}.{alias.name}" for alias in node.names)
    return names


@pytest.mark.parametrize("source", sorted(REPORT_DIR.glob("*.py")), ids=lambda p: p.name)
def test_the_report_never_reads_the_metric_table(source):
    """8.4 — the table is written beside a render, never consulted by one."""
    for name in imported_modules(source):
        assert "metrics" not in name, f"{source.name} imports {name}"


@pytest.mark.parametrize("renderer", [charts.render_all, page.render])
def test_a_renderer_is_handed_its_rows(renderer):
    """8.4 — rows arrive as an argument, so a chart cannot outrun what produced it."""
    assert "rows" in inspect.signature(renderer).parameters


def test_the_table_reader_is_not_on_any_render_path():
    """8.4, 11.12 — regenerating from disk is not a capability, so nothing calls it.

    `read_all` stays as the format's own reader — 8.2 defines the table as CSV files
    concatenated on read, and that promise needs an implementation to be checkable — but
    a caller appearing on a render path would mean 8.4 had quietly stopped being true.
    """
    assert callable(metrics.read_all)
    package = Path(metrics.__file__).parents[1]  # simulator/, the shipped code only
    callers = [
        str(source.relative_to(package))
        for source in package.rglob("*.py")
        if source.name != "metrics.py" and "read_all" in source.read_text()
    ]
    assert callers == []
