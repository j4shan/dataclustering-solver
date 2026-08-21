"""Section A's illustration pane — 12.3.5, 12.3.6."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ILLUSTRATION = ROOT / "resources/graphics/section-a-illustration.html"
FIGURE_IDS = ("A.closet-problem", "A.fetch-process", "A.smart-organizer")
FIGURE_TITLES = {
    "A.closet-problem": "One outfit, one whole drawer",
    "A.fetch-process": "The same fetch in a warehouse",
    "A.smart-organizer": "What a smart organizer can change",
}
DATABASE_TERMS = (
    "data",
    "warehouse",
    "storage",
    "container",
    "record",
    "row",
    "query",
    "index",
    "materialized",
    "selected",
    "layout",
    "assignment",
    "strategy",
)


def tag_of(element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def text_of(element) -> str:
    return "".join(element.itertext())


def class_names(element) -> set[str]:
    return set((element.get("class") or "").split())


@pytest.fixture(scope="module")
def pane():
    return ET.fromstring(ILLUSTRATION.read_text())


def figures(pane) -> dict[str, ET.Element]:
    return {item.get("id"): item for item in pane if tag_of(item) == "figure"}


def test_the_six_beats_are_complete_and_ordered(pane):
    """12.3.5.1 — analogy, mapping, comparison, then the right-panel handoff."""
    children = list(pane)
    assert [tag_of(child) for child in children] == [
        "p",
        "figure",
        "p",
        "figure",
        "figure",
        "p",
    ]
    assert [child.get("id") for child in children if tag_of(child) == "figure"] == list(
        FIGURE_IDS
    )
    assert {"closet-story", "editorial-lede"} <= class_names(children[0])
    assert {"warehouse-walkthrough", "editorial-bridge"} <= class_names(children[2])
    assert {"framework-handoff", "editorial-bridge"} <= class_names(children[5])


def test_closet_stage_builds_the_model_without_database_terms(pane):
    """12.3.5.1.1, 12.3.6 — familiar actions come before technical names."""
    opening, closet = list(pane)[:2]
    body = f"{text_of(opening)} {text_of(closet)}".lower()
    for noun in (
        "closet",
        "drawer",
        "garment",
        "morning",
        "outfit",
        "catalog",
        "inventory",
        "wasted effort",
        "smart organizer",
    ):
        assert noun in body
    for term in DATABASE_TERMS:
        assert not re.search(rf"\b{re.escape(term)}\b", body), term
    assert "?" in text_of(opening)


def test_every_illustration_has_its_visible_title(pane):
    """12.3.5.2 — a sighted reader sees every specified title."""
    found = figures(pane)
    assert set(found) == set(FIGURE_IDS)
    for ident, title in FIGURE_TITLES.items():
        heading = next(child for child in found[ident] if tag_of(child) == "h3")
        assert text_of(heading).strip() == title


def test_fetch_walkthrough_maps_the_same_scenario_to_technical_terms(pane):
    """12.3.5.1.2, 12.3.6 — the scenario earns each technical mapping."""
    children = list(pane)
    body = f"{text_of(children[2])} {text_of(children[3])}".lower()
    mappings = (
        "the closet is the warehouse",
        "a drawer is a storage container",
        "a garment is a record",
        "the outfit request is a query",
        "the item catalog is the index table",
    )
    for mapping in mappings:
        assert mapping in body
    assert "records materialized but not selected" in body
    assert "opportunity" in body


def test_fetch_process_has_one_directional_order(pane):
    """12.3.5.3 — request, lookup, activation, materialization, split."""
    process = figures(pane)["A.fetch-process"]
    steps = [item.get("data-step") for item in process.iter() if item.get("data-step")]
    assert steps == ["query", "index", "activate", "materialize", "split"]
    arrows = [
        item
        for item in process.iter()
        if tag_of(item) == "path" and "open-arrow" in class_names(item)
    ]
    assert len(arrows) >= len(steps) - 1


def test_the_same_items_recur_through_all_three_figures(pane):
    """12.3.5.3 — the reader sees one scenario acquire names and one change."""
    found = figures(pane)

    def items(ident: str) -> set[str]:
        return {
            item.get("data-item")
            for item in found[ident].iter()
            if item.get("data-item")
        }

    baseline = items("A.closet-problem")
    assert baseline
    assert items("A.fetch-process") == baseline
    assert items("A.smart-organizer") == baseline


def test_smart_organizer_changes_only_assignment_and_reduces_waste(pane):
    """12.3.5.3 — fixed request and capacity, fewer unselected records."""
    organizer = figures(pane)["A.smart-organizer"]
    layouts = {
        group.get("data-layout"): group
        for group in organizer.iter()
        if group.get("data-layout")
    }
    assert set(layouts) == {"before", "after"}

    def attr(name: str, key: str) -> str:
        return layouts[name].get(key)

    for key in ("data-query", "data-selected", "data-capacity", "data-index-result"):
        assert attr("before", key)
        assert attr("before", key) == attr("after", key)

    def items(name: str) -> set[str]:
        return {
            item.get("data-item")
            for item in layouts[name].iter()
            if item.get("data-item")
        }

    def waste(name: str) -> int:
        return sum(
            item.get("data-outcome") == "waste" for item in layouts[name].iter()
        )

    assert items("before") == items("after")
    assert waste("after") < waste("before")


def test_handoff_names_what_the_right_panel_develops(pane):
    """12.3.5.1.3 — the final beat directs the reader to the problem statement."""
    handoff = text_of(list(pane)[5]).lower()
    for phrase in (
        "right panel",
        "formal problem statement",
        "objective",
        "system-wide data-skipping model",
        "effect of data clustering",
    ):
        assert phrase in handoff


def test_the_pane_carries_no_table_graphics_or_outbound_links(pane):
    """12.3.5, 13.17 — this is one closed scenario."""
    ids = [element.get("id") for element in pane.iter() if element.get("id")]
    for ident in ("event-table", "index-table", "event-support", "container-activation"):
        assert ident not in ids
        assert f"c-{ident}" not in ids
    assert not [element for element in pane.iter() if tag_of(element) in {"a", "script"}]
    body = text_of(pane).lower()
    for excluded in ("interactive canvas", "selection matrix", "architecture canvas"):
        assert excluded not in body


def test_embedded_illustrations_live_under_resources():
    """9.16 — pane fragments and standalone canvases share resources/graphics/."""
    folder = ROOT / "resources/graphics"
    names = sorted(path.name for path in folder.glob("*.html"))
    assert names
    for name in names:
        assert re.fullmatch(r"(section-[a-z]-illustration|.+-canvas)\.html", name), name
        assert not (ROOT / "simulator/gui/static" / name).exists(), name
    assert not (ROOT / "resources/illustrations").exists()
    assert not (ROOT / "resources/canvas").exists()


def test_linked_html_declares_utf8_in_the_first_kilobyte():
    """9.10 — standalone canvases name their own encoding."""
    for href in (
        "graphics/closet-canvas.html",
        "graphics/architecture-canvas.html",
    ):
        head = (ROOT / "resources" / href).read_text(encoding="utf-8")[:1024].lower()
        assert "charset" in head and "utf-8" in head
