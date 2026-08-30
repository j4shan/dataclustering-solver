"""Problem Statement's terminology pane — 12.3."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

GLOSSARY = Path("simulator/gui/static/section-problem-glossary.html")

TERMS = (
    "Event / record",
    "Corpus",
    "Container",
    "Container capacity",
    "Layout",
    "Query",
    "Selected events",
    "Index table",
    "Activation",
    "Materialized volume",
    "Skipped container",
    "Waste",
    "Aggregate waste",
    "Selection log",
    "Assignment strategy",
)


def test_the_glossary_is_a_two_column_term_definition_table():
    root = ET.fromstring(GLOSSARY.read_text())
    assert "glossary" in (root.get("class") or "").split()
    tables = [element for element in root.iter() if element.tag == "table"]
    assert len(tables) == 1
    headers = ["".join(cell.itertext()).strip() for cell in tables[0].iter("th")]
    assert headers == ["Term", "Definition"]
    rows = tables[0].findall("tbody/tr")
    assert len(rows) == 15
    terms = ["".join(row[0].itertext()) for row in rows]
    for expected, actual in zip(TERMS, terms, strict=True):
        assert expected in actual
    for row in rows:
        assert len(row) == 2
        assert "".join(row[1].itertext()).strip()


def test_the_glossary_is_not_a_paraphrase_of_the_closet_appendix():
    body = GLOSSARY.read_text().lower()
    for stale in ("closet", "wardrobe", "garment"):
        assert stale not in body
