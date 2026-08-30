"""Section A's illustration pane — 12.3.5, 12.3.6."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ILLUSTRATION = ROOT / "resources/graphics/section-a-illustration.html"
FIGURES = {
    "A.medical-cabinet": "figures/img/section_a_medical_cabinet.png",
    "A.smart-organizer": "figures/img/section_a_smart_organizer.png",
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
    return " ".join("".join(element.itertext()).split())


def class_names(element) -> set[str]:
    return set((element.get("class") or "").split())


@pytest.fixture(scope="module")
def pane():
    return ET.fromstring(ILLUSTRATION.read_text())


def figures(pane) -> dict[str, ET.Element]:
    return {item.get("id"): item for item in pane if tag_of(item) == "figure"}


def test_the_five_beats_are_complete_and_ordered(pane):
    """12.3.5.1 — mental model, mapping, restocking, then handoff."""
    children = list(pane)
    assert [tag_of(child) for child in children] == [
        "p",
        "figure",
        "p",
        "figure",
        "p",
    ]
    assert [child.get("id") for child in children if tag_of(child) == "figure"] == list(
        FIGURES
    )
    assert {"cabinet-story", "editorial-lede"} <= class_names(children[0])
    assert {"warehouse-walkthrough", "editorial-bridge"} <= class_names(children[2])
    assert {"framework-handoff", "editorial-bridge"} <= class_names(children[4])


def test_opening_builds_the_medicine_cabinet_model_before_technical_terms(pane):
    """12.3.5.1.1, 12.3.6 — familiar actions establish the mental model."""
    opening = list(pane)[0]
    body = text_of(opening).lower()
    for noun in (
        "dispensary",
        "medicine cabinet",
        "small drawer",
        "medicine box",
        "prescriptions",
        "counter",
        "drawer chart",
        "put back unused",
        "wasted effort",
    ):
        assert noun in body
    for term in DATABASE_TERMS:
        assert not re.search(rf"\b{re.escape(term)}\b", body), term


def test_both_local_raster_illustrations_have_useful_alternative_text(pane):
    """12.3.5.2–12.3.5.4 — exactly two local PNG figures are embedded."""
    found = figures(pane)
    assert set(found) == set(FIGURES)
    assert not [element for element in pane.iter() if tag_of(element) == "svg"]

    for ident, source in FIGURES.items():
        images = [element for element in found[ident].iter() if tag_of(element) == "img"]
        assert len(images) == 1
        image = images[0]
        assert image.get("src") == source
        assert len(image.get("alt", "").split()) >= 12
        assert (ROOT / "resources/img" / Path(source).name).is_file()


def test_technical_walkthrough_defines_terms_beside_the_cabinet_model(pane):
    """12.3.5.1.2, 12.3.6 — the familiar account earns each technical name."""
    walkthrough = text_of(list(pane)[2]).lower()
    mappings = (
        "medicine cabinet is the corpus",
        "small drawer is a storage container",
        "medicine box is a record",
        "counter batch is a query",
        "drawer chart acts as the index table",
        "pulling a named drawer is container activation",
    )
    for mapping in mappings:
        assert mapping in walkthrough
    for phrase in (
        "materialized but not selected",
        "whole containing unit",
        "demand history",
        "past retrievals",
        "demand band",
    ):
        assert phrase in walkthrough


def test_smart_organizer_is_framed_as_a_demonstration_not_a_recommendation(pane):
    """1.2, 12.3.5.1.2 — the fixture exposes the seam without ranking it."""
    organizer = figures(pane)["A.smart-organizer"]
    caption = text_of(organizer).lower()
    for phrase in (
        "deliberately simple",
        "capacity",
        "whole-drawer retrieval",
        "not a recommended assignment strategy",
    ):
        assert phrase in caption


def test_handoff_names_what_the_right_panel_develops(pane):
    """12.3.5.1.3 — the final beat directs the reader to the problem statement."""
    handoff = text_of(list(pane)[4]).lower()
    for phrase in (
        "right panel",
        "formal problem",
        "objective formula",
        "system-wide data-skipping model",
        "effect of data clustering",
    ):
        assert phrase in handoff


def test_the_pane_carries_no_extra_graphics_or_outbound_links(pane):
    """12.3.5 — this is one closed editorial sequence."""
    assert not [
        element for element in pane.iter() if tag_of(element) in {"a", "script", "table"}
    ]
    assert len([element for element in pane.iter() if tag_of(element) == "img"]) == 2
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


def test_the_architecture_canvas_draws_what_exists():
    """9.13 — a built component is never marked as specified-not-built."""
    page = (ROOT / "resources/graphics/architecture-canvas.html").read_text(
        encoding="utf-8"
    )
    assert "bench/catalog.py" in page
    assert "strategy-catalog.json" in page
    assert "simulator/menu.py" in page
    assert "specified, not built" not in page
    assert "interactive strategy demo" not in page
