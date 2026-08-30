"""Section C — the production design (12.5).

The section renders a committed artifact and authors nothing.  So most of what 12.5 asks
for is a property of two files: the pre-rendered fragment, which must be the *whole*
document at Section A's parity, and the diagram block beside it, which must draw only what
the document already says and draw it from the 12.7 palette.

The pre-render itself is checked in `test_render_formulation.py`; what is checked here is
that Section C gets the same treatment from it, and that the two fragments can live in one
page together.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from simulator.gui import FIGURE_ROOT, STATIC_ROOT

SOURCE = Path("project_metadata/production-design.md")
FRAGMENT = STATIC_ROOT / "production-design.html"
DIAGRAMS = FIGURE_ROOT / "graphics" / "section-c-illustration.html"
ILLUSTRATION_HREF = "figures/graphics/section-c-illustration.html"  # 12.2.13
FORMULATION = STATIC_ROOT / "formulation.html"
INDEX = STATIC_ROOT / "index.html"


@pytest.fixture(scope="module")
def document() -> str:
    return SOURCE.read_text()


@pytest.fixture(scope="module")
def fragment() -> str:
    return FRAGMENT.read_text()


@pytest.fixture(scope="module")
def diagrams() -> str:
    return DIAGRAMS.read_text()


# -- the left pane, at Section A's parity (12.5.4) ------------------------------------


def test_the_artifact_is_pre_rendered_and_committed(fragment):
    """12.5.4, 12.3.2 — finished HTML arrives; no Markdown is parsed in the browser."""
    assert FRAGMENT.exists()
    assert fragment.startswith('<article class="formulation">')
    assert "```" not in fragment


def test_one_renderer_serves_both_documents():
    """12.5.4 — a second rendering path would be a second thing to keep faithful."""
    pytest.importorskip("markdown_it", reason="needs the 'docs' extra")
    from tools import render_formulation as rf

    assert {"formulation", "production-design"} <= set(rf.DOCUMENTS)
    source, out = rf.DOCUMENTS["production-design"]
    assert source.resolve() == SOURCE.resolve()
    assert out.resolve() == FRAGMENT.resolve()


def test_the_mathematics_arrives_as_native_mathml(fragment):
    """12.3.2 — the same treatment Section A gets, on a document that also has formulas."""
    assert "<math" in fragment
    assert "$" not in re.sub(r"<[^>]+>", "", fragment)


def test_the_contents_list_is_generated_from_the_documents_own_headings(
    document, fragment
):
    """12.3.3 — a section added to the artifact appears in the list with no edit here."""
    headings = re.findall(r"^## (.+)$", document, flags=re.MULTILINE)
    assert headings
    for heading in headings:
        assert f">{heading}</a>" in fragment, heading


def test_the_two_fragments_share_no_element_id():
    """12.5.4 — both mount into one page, so a duplicated id would misdirect a label."""
    pattern = r'id="([^"]+)"'
    section_a = set(re.findall(pattern, FORMULATION.read_text()))
    section_c = set(re.findall(pattern, FRAGMENT.read_text()))
    assert not (section_a & section_c)


def test_the_rendering_is_complete_rather_than_an_excerpt(document, fragment):
    """12.5.5 — a section that summarizes the mapping is a fourth restatement."""
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment))
    # Every divergence in §7, which is the part a summary would be most tempted to cut.
    for divergence in re.findall(r"^\| (7\.\d) \|", document, flags=re.MULTILINE):
        assert divergence in text, divergence
    # And the closing exclusions, which say what the document does *not* settle.
    for exclusion in re.findall(r"^- \*\*(.+?)\*\*", document, flags=re.MULTILINE):
        assert exclusion.rstrip(".") in text, exclusion


# -- the right pane's diagrams (12.5.1, 12.5.3) ---------------------------------------


def engine_markup(diagrams: str) -> str:
    """The three engine figures, before 12.5.7's appended tables."""
    cut = diagrams.find('class="illustration-rule"')
    return diagrams if cut < 0 else diagrams[:cut]


ENGINE_TITLES = {
    "engine-pruning": "How a predicate decides which files are opened",
    "engine-layout": "The layout is written, and then rewritten underneath",
    "engine-selection-log": "The selection log has to be constructed",
}


def test_the_diagrams_are_inline_and_depend_on_nothing(diagrams):
    """12.5.3, 10.3.5 — inline SVG, no diagramming library, no outbound request."""
    engine = engine_markup(diagrams)
    assert engine.count("<svg") == 3
    assert "<script" not in diagrams
    assert not re.search(r'(src|href)="https?://', diagrams)


def test_the_diagrams_take_their_colour_from_the_tokens(diagrams):
    """12.5.3 — drawn from the 12.7 palette; a literal is only ever a fallback."""
    tokens = re.findall(r"var\((--[\w-]+)(?:,\s*([^)]+))?\)", diagrams)
    assert tokens
    known = (STATIC_ROOT / "tokens.css").read_text()
    for name, _fallback in tokens:
        assert f"{name}:" in known, name
    # Every literal colour in the file is a fallback inside a var(), never a bare value.
    for literal in re.findall(r"#[0-9A-Fa-f]{3,8}\b", diagrams):
        assert re.search(rf"var\(--[\w-]+,\s*{literal}\s*\)", diagrams), literal


def test_no_state_in_a_diagram_is_carried_by_colour_alone(diagrams):
    """12.6.2 — a pruned file is dashed, waste is hatched, approximation is written."""
    assert diagrams.count("stroke-dasharray") >= 3
    assert "engine-hatch" in diagrams
    assert "approximate" in diagrams


def test_every_diagram_is_announced_to_a_screen_reader(diagrams):
    """12.6.1 — a figure that only a sighted reader can read is half a figure."""
    engine = engine_markup(diagrams)
    assert engine.count('role="img"') == 3
    assert engine.count("<title") == 3
    assert engine.count("<desc") == 3
    for svg in re.findall(r"<svg[^>]*>", engine):
        assert "aria-labelledby" in svg


def test_engine_sequence_has_lead_visible_titles_and_transition(diagrams):
    """12.5.3.2–3 — prose frames the engine sequence and every figure is visible by name."""
    lead_at = diagrams.find('class="editorial-lede"')
    first_engine = diagrams.find('id="engine-pruning"')
    assert 0 <= lead_at < first_engine

    for ident, title in ENGINE_TITLES.items():
        heading = re.search(
            rf'<figure class="illustration" id="{ident}">\s*<h3[^>]*>([^<]+)</h3>',
            diagrams,
        )
        assert heading, ident
        assert heading.group(1) == title

    last_engine = diagrams.find('id="engine-selection-log"')
    transition_at = diagrams.find('class="editorial-bridge"')
    first_rule = diagrams.find('class="illustration-rule"')
    assert last_engine < transition_at < first_rule


def test_the_diagrams_name_the_sections_they_draw(diagrams):
    """12.5.2 — they render the artifact's content and author none of their own."""
    for section in ("§4, §7.1", "§7.6, §7.7", "§6"):
        assert section in diagrams, section


def test_the_diagrams_use_the_projects_own_vocabulary(diagrams):
    """12.3.6 — a synonym for a defined term is a defect.

    The terms are enumerated here rather than read out of the engine mapping: this
    asserts what the diagrams must say, and a test that harvested its expectation from
    the prose beside them would pass whatever the two happened to drift to together.
    """
    text = re.sub(r"<[^>]+>", " ", diagrams).lower()
    for term in ("container", "activated", "waste", "selection log", "layout", "predicate"):
        assert term in text, term
    # Terms the documents never use, and which would be a second vocabulary if they did.
    for synonym in ("bucket", "shard", "chunk", "segment"):
        assert synonym not in text, synonym


def test_no_diagram_asserts_a_measured_number(diagrams):
    """12.6.4, and §8 of the artifact — no figure in this document is measured."""
    text = re.sub(r"<[^>]+>", " ", diagrams)
    text = re.sub(r"§\d+(\.\d+)?", "", text)  # section references are not measurements
    assert not re.search(r"\b\d+(\.\d+)?\s*(%|MB|GB|s\b|rows|bytes)", text)


# -- the section, mounted (12.5.1) ----------------------------------------------------


def test_section_c_is_the_same_left_right_split_as_section_a():
    """12.5.1 — two panes, document on the left, diagrams on the right."""
    html = INDEX.read_text()
    section = html.split('id="design"')[1]
    assert 'data-mount="production-design.html"' in section
    assert f'data-mount="{ILLUSTRATION_HREF}"' in section
    assert section.index("pane-left") < section.index("pane-right")


def test_section_c_is_reachable_without_scripting():
    """12.1.4 — a document pane that needs a script to be a document is a defect."""
    section = INDEX.read_text().split('id="design"')[1]
    assert '<a href="production-design.html">' in section
    assert f'<a href="{ILLUSTRATION_HREF}">' in section


# -- the appended table illustrations (12.5.7) ----------------------------------------


TABLE_IDS = (
    "c-event-table",
    "c-index-table",
    "c-event-support",
    "c-container-activation",
)
RECORD_IDS = [f"r{i:02d}" for i in range(1, 13)]
CONTAINERS = {
    "c1": RECORD_IDS[0:4],
    "c2": RECORD_IDS[4:8],
    "c3": RECORD_IDS[8:12],
}
SELECTIONS = {
    "q1": {"r01", "r03"},
    "q2": {"r03", "r06"},
    "q3": {"r10", "r11"},
}
TITLES = {
    "c-event-table": "Twelve events in three containers",
    "c-index-table": "The index table",
    "c-event-support": "Event support",
    "c-container-activation": "Activation and container support",
}


def _figure(diagrams: str, ident: str) -> str:
    match = re.search(
        rf'<figure class="illustration" id="{ident}">.*?</figure>',
        diagrams,
        flags=re.S,
    )
    assert match, ident
    return match.group(0)


def test_the_right_pane_appends_the_table_illustrations_after_the_engine(diagrams):
    """12.5.7 — four tables after the last engine figure, rules between every pair."""
    engine_end = diagrams.rfind('id="engine-selection-log"')
    assert engine_end > 0
    first_table = min(diagrams.find(f'id="{ident}"') for ident in TABLE_IDS)
    assert first_table > engine_end

    order = [m.group(1) for m in re.finditer(r'<figure class="illustration" id="([^"]+)"', diagrams)]
    assert order[-4:] == list(TABLE_IDS)

    # The stack is three engine figures, then (hr, table) four times.
    assert diagrams.count('class="illustration-rule"') == 4
    for ident in TABLE_IDS:
        rule_at = diagrams.rfind('class="illustration-rule"', 0, diagrams.find(f'id="{ident}"'))
        assert rule_at > 0, ident


def test_every_appended_table_carries_its_visible_title(diagrams):
    """12.5.7.2 — the titles named in 12.5.7.1, announced to a sighted reader."""
    for ident, title in TITLES.items():
        heading = re.search(
            rf'<figure class="illustration" id="{ident}">\s*<h3[^>]*>([^<]+)</h3>',
            diagrams,
        )
        assert heading, ident
        assert heading.group(1) == title


def test_appendix_tables_expose_titles_columns_and_row_headers(diagrams):
    """12.6.1 — table relationships remain navigable without their visual geometry."""
    appendix = diagrams[diagrams.find('id="c-event-table"') :]
    table_tags = re.findall(r"<table([^>]*)>", appendix)
    assert len(table_tags) == 10
    assert all("aria-labelledby=" in attributes for attributes in table_tags)

    for head in re.findall(r"<thead>(.*?)</thead>", appendix, flags=re.S):
        header_attributes = re.findall(r"<th([^>]*)>", head)
        assert header_attributes
        assert all('scope="col' in attributes for attributes in header_attributes)

    rows = re.findall(
        r'<tr data-record="(r\d+)">(.*?)</tr>',
        appendix,
        flags=re.S,
    )
    assert rows
    for record, cells in rows:
        assert re.search(
            rf'<th scope="row" class="mono">{record}</th>',
            cells,
        ), record


def test_the_appended_tables_share_one_twelve_event_instance(diagrams):
    """12.5.7.1 — one storage-model instance, reused; not a measured engine result."""
    events = _figure(diagrams, "c-event-table")
    records_by_container = {}
    for bank in re.finditer(
        r'<div class="container-bank"[^>]*data-container="(c[123])"[^>]*>(.*?)</table>',
        events,
        flags=re.S,
    ):
        records_by_container[bank.group(1)] = re.findall(r'data-record="(r\d+)"', bank.group(2))
    assert records_by_container == CONTAINERS
    assert "data-query=" not in events
    assert "is-focal" not in events

    index = _figure(diagrams, "c-index-table")
    assert "blob" not in index.lower()
    assert re.findall(r'data-record="(r\d+)"', index) == RECORD_IDS
    for query, selected in SELECTIONS.items():
        cells = re.findall(
            rf'<tr data-record="(r\d+)">.*?<td[^>]*data-query="{query}"[^>]*>(.*?)</td>',
            index,
            flags=re.S,
        )
        marked = {record for record, cell in cells if "is-selected" in cell or cell.strip() == "1"}
        assert marked == selected, query

    support = _figure(diagrams, "c-event-support")
    assert 'data-record="r03"' in support
    assert 'class="is-focal"' in support
    assert "event support" in re.sub(r"<[^>]+>", " ", support).lower()
    assert "q1 and q2" in support

    activation = _figure(diagrams, "c-container-activation")
    assert 'data-container="c1"' in activation
    assert "container support" in re.sub(r"<[^>]+>", " ", activation).lower()
    assert "q1 and q2" in activation


def test_index_paragraph_connects_storage_schema_to_dpp(diagrams):
    """12.5.7.1 — the prose bridge names both the abstract index and Spark mechanism."""
    event_end = diagrams.find("</figure>", diagrams.find('id="c-event-table"'))
    paragraph_at = diagrams.find('class="index-explanation"')
    index_at = diagrams.find('id="c-index-table"')
    assert event_end < paragraph_at < index_at
    paragraph = re.search(
        r'<p class="index-explanation">(.*?)</p>',
        diagrams,
        flags=re.S,
    )
    assert paragraph
    text = re.sub(r"<[^>]+>", " ", paragraph.group(1)).lower()
    for term in (
        "features",
        "container_id",
        "record_id",
        "partition",
        "dynamic partition pruning",
    ):
        assert term in text


def test_appendix_formal_terms_are_keyword_chips(diagrams):
    """12.5.7.1 — formal terms are visually scannable without becoming a glossary."""
    chips = {
        re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", value)).strip().lower()
        for value in re.findall(
            r'<span class="keyword-chip">(.*?)</span>',
            diagrams,
            flags=re.S,
        )
    }
    assert {
        "index table",
        "selection log",
        "event support",
        "activation",
        "container support",
    } <= chips


def test_focal_arrows_target_r03_and_c1(diagrams):
    """12.5.7.1 — the arrows identify their exact row and bank, not a generic caption."""
    support = _figure(diagrams, "c-event-support")
    activation = _figure(diagrams, "c-container-activation")
    assert re.search(
        r'<svg class="[^"]*\bopen-arrow\b[^"]*"[^>]*data-target="r03"',
        support,
    )
    assert re.search(
        r'<svg class="[^"]*\bopen-arrow\b[^"]*"[^>]*data-target="c1"',
        activation,
    )


def test_the_appended_tables_are_not_a_measurement_of_the_engine(diagrams):
    """12.5.7, 12.6.4 — the instance is pedagogical; it states no engine metric."""
    appendix = diagrams[diagrams.find('id="c-event-table"') :]
    text = re.sub(r"<[^>]+>", " ", appendix)
    assert not re.search(r"\b\d+(\.\d+)?\s*(%|MB|GB|s\b|rows|bytes)", text)
