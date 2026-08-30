"""The application shell (12.1).

A browser is not required to check most of what 12.1 asks for.  The scroll model, the
breakpoint behaviour, the anchors and the dependency rules are all properties of the
authored files, and 12.6.3.1 makes browser-driven checks a plus rather than a gate — so
these read the files, and the optional suite (T20) drives the live page.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from simulator.gui import FIGURE_ROOT, STATIC_ROOT

#: 12.2.13 — relative, because the page is mounted under a path prefix it is not told
#: about.  A leading slash here would address the front door's root instead.
FIGURE_PREFIX = "figures/"

INDEX = STATIC_ROOT / "index.html"
APP_CSS = STATIC_ROOT / "app.css"
APP_JS = STATIC_ROOT / "app.js"


@pytest.fixture(scope="module")
def html() -> str:
    return INDEX.read_text()


@pytest.fixture(scope="module")
def css() -> str:
    return re.sub(r"/\*.*?\*/", "", APP_CSS.read_text(), flags=re.DOTALL)


def test_browser_and_wordmark_use_the_formal_project_title(html):
    assert "<title>The Data Storage Layout Problem</title>" in html
    assert '<span class="wordmark">The Data Storage Layout Problem</span>' in html


@pytest.fixture(scope="module")
def script() -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", APP_JS.read_text(), flags=re.DOTALL)


def rule_for(css: str, selector: str) -> str:
    """The declarations of one rule, so a test can assert about that rule alone."""
    match = re.search(rf"(?:^|\n|,)\s*{re.escape(selector)}\s*(?:,[^{{]*)?\{{([^}}]*)\}}", css)
    assert match, f"no rule for {selector}"
    return match.group(1)


def media_block(css: str, query: str) -> str:
    """One `@media` block, brace-matched.

    Slicing to the next marker would run on into the following at-rule — and `@media
    print` legitimately hides things that the breakpoint block must not.
    """
    start = css.index(query)
    depth, cursor = 0, css.index("{", start)
    for position in range(cursor, len(css)):
        depth += (css[position] == "{") - (css[position] == "}")
        if depth == 0:
            return css[cursor + 1 : position]
    raise AssertionError(f"unbalanced braces after {query}")


# -- four sections, in order (12.1.1) -----------------------------------------------


def test_there_are_four_sections_in_fixed_order(html):
    assert re.findall(r'<section class="section" id="([\w-]+)"', html) == [
        "problem",
        "benchmark",
        "design",
        "gini",
    ]


def test_each_section_is_a_left_right_pair(html):
    assert html.count('class="split"') == 4
    assert html.count("pane pane-left") == 4
    assert html.count("pane pane-right") == 4


def test_the_sections_are_individually_linkable(html):
    """12.1.3 — stable anchors, and a persistent control that selects between them."""
    anchors = set(re.findall(r'<section class="section" id="([\w-]+)"', html))
    navigated = set(re.findall(r'<a href="#([\w-]+)" data-nav=', html))
    assert navigated == anchors


def test_the_page_anatomy_figure_spells_the_sections_the_page_spells_them(html):
    """9.15 — the figure's labels are the page's own, and this is what holds them so.

    The figure is drawn rather than screenshotted, so nothing but this test stops a
    renamed section from leaving the README's diagram describing a page that no longer
    exists. Both halves are read here: what the top bar offers, and what each section
    calls itself once chosen.
    """
    from tools import render_figures as rf

    navigation = re.findall(r"<b>(\w)</b> ([^<]+)</a>", html)
    assert navigation == [(letter, label) for letter, label in rf.NAV]

    headings = re.findall(r'<span class="letter">(\w)</span> ([^<]+)</h1>', html)
    assert headings == [(s["letter"], s["heading"]) for s in rf.SECTIONS]


def test_section_a_keeps_its_tab_name_and_uses_the_medicine_cabinet_heading(html):
    """Section A's navigation name stays stable while its editorial heading carries the story."""
    section = html.split('id="problem"')[1].split('id="benchmark"')[0]
    assert '<a href="#problem" data-nav="problem"><b>A</b> Problem Statement</a>' in html
    assert (
        '<h1 id="problem-heading"><span class="letter">A</span> '
        "Organizing Data Like a Medicine Cabinet</h1>"
    ) in section


def test_every_section_is_labelled_for_a_screen_reader(html):
    """12.6.1 — the panes are landmarks a screen reader can navigate."""
    labelled = re.findall(r'aria-labelledby="([\w-]+)"', html)
    for target in labelled:
        assert f'id="{target}"' in html
    panes = re.findall(r'<div class="pane [^"]+"[^>]*>', html)
    assert len(panes) == 8
    assert all('role="region"' in pane for pane in panes)
    assert all('aria-label="' in pane for pane in panes)
    assert len(set(re.findall(r'aria-label="([^"]+)"', "\n".join(panes)))) == 8


# -- the scroll model (12.1.2, 12.1.7) -----------------------------------------------


def test_the_shell_bounds_the_selected_section(css):
    """12.1.7 — the selected section fills the height below the top bar, and no more.

    The shell does not scroll: the sections the nav did not select are not laid out, so
    there is nothing here to scroll through, and a scrollbar would mean the cap below had
    failed rather than that the page had grown.
    """
    shell = rule_for(css, ".shell")
    assert "height: calc(100dvh - var(--top-bar-height))" in shell
    assert "overflow-y: hidden" in shell


def test_the_page_never_scrolls_horizontally(css):
    """12.1.2 — wide content scrolls inside its own container instead."""
    assert "overflow-x: hidden" in rule_for(css, ".shell")
    assert "overflow-x: auto" in rule_for(css, ".scroll-x")


def test_the_header_contains_navigation_at_narrow_widths(css):
    """12.1.2 — the persistent control scrolls locally instead of widening the page."""
    navigation = rule_for(css, ".section-nav")
    assert "flex: 1" in navigation
    assert "min-width: 0" in navigation
    assert "overflow-x: auto" in navigation


def test_panes_are_bounded_and_scroll_independently(css):
    pane = rule_for(css, ".pane")
    assert "overflow-y: auto" in pane
    assert "min-height: 0" in pane


def test_the_bound_can_actually_take_effect(css):
    """`min-height: 0` on every flex and grid child in the chain.

    Without it a child's automatic minimum size is its content: the pane grows the
    section instead of scrolling, and 12.1.2 silently does not happen.
    """
    for selector in (".split", ".pane"):
        assert "min-height: 0" in rule_for(css, selector)


def test_a_section_is_capped_at_the_height_it_is_given(css):
    """12.1.7 — the selected section is capped, not floored.

    A `min-height: 100%` section grows to its content, which overflows the shell and
    leaves the panes nothing to be bounded by. The browser suite caught that; this keeps
    it caught without a browser.
    """
    section = rule_for(css, ".section")
    assert "height: 100%" in section
    assert "min-height: 100%" not in section


def test_only_the_selected_section_is_laid_out(css):
    """12.1.1 — one section is displayed at a time, and `hidden` is what says so.

    Authored rather than left to the user agent: `.section`'s own `display: flex` and the
    default `[hidden] { display: none }` carry equal specificity, so the rule that has to
    win is the one this page writes down.
    """
    assert "display: none" in rule_for(css, ".section[hidden]")


def test_below_the_breakpoint_the_page_scrolls_once(css):
    """12.1.6, 12.1.7 — the bound is released so no scroll nests inside another.

    Load-bearing rather than a refinement: the wide case caps the shell at the viewport
    and hides its overflow, so without the release a tall stacked section would be clipped
    rather than merely double-scrolled.
    """
    stacked = media_block(css, "@media (max-width: 1000px)")
    assert "height: auto" in stacked
    assert "overflow: visible" in stacked
    assert "grid-template-columns: minmax(0, 1fr);" in stacked


def test_nothing_is_hidden_at_a_narrow_width(css):
    """12.1.6 — within the section on screen, the panes stack; they do not disappear.

    Scoped to the breakpoint block alone: `@media print` hides the navigation bar, which
    is correct and has nothing to do with a narrow viewport, and 12.1.1's section-level
    hiding is a base-level rule this test deliberately does not reach into — what a narrow
    viewport must never do is drop a *pane* of the section it is showing.
    """
    assert "display: none" not in media_block(css, "@media (max-width: 1000px)")


# -- reading (12.1.9) -----------------------------------------------------------------


def test_prose_is_set_for_sustained_reading(css):
    """Generous leading; other reading prose keeps a character-width measure (12.1.9)."""
    assert "max-width: var(--measure)" in css
    assert "line-height: var(--leading-prose)" in rule_for(css, ".pane:has(> .formulation)")


def test_section_a_formulation_fills_the_right_pane(css):
    """12.3.1.1 — the document uses the pane, not a character clamp inside it."""
    assert "max-width: none" in rule_for(css, "#problem .pane-right > .formulation")


def test_section_a_illustration_is_one_pixel_larger_than_chrome(css):
    """12.3.5.5 — the left pane remaps the type tokens so every beat steps together."""
    declarations = rule_for(css, "#problem .pane-left")
    assert "--text-body: 14px" in declarations
    assert "--text-small: 12px" in declarations
    assert "--text-heading: 18px" in declarations
    assert "--text-title: 23px" in declarations


def test_section_a_formulation_is_one_pixel_larger_than_chrome(css):
    """12.3.1.2 — body, headings, and small type each step one pixel above 12.7.2."""
    assert "font-size: calc(var(--text-body) + 1px)" in rule_for(css, "#problem .pane-right")
    assert "font-size: calc(var(--text-title) + 1px)" in rule_for(
        css, "#problem .pane-right h1"
    )
    assert "font-size: calc(var(--text-heading) + 1px)" in rule_for(
        css, "#problem .pane-right h2"
    )
    assert "font-size: calc(var(--text-body) + 1px)" in rule_for(
        css, "#problem .pane-right h3"
    )
    assert "font-size: calc(var(--text-small) + 1px)" in rule_for(
        css, "#problem .pane-right :is(code, kbd, samp, pre)"
    )


def test_section_a_puts_the_illustration_on_the_left(html):
    """12.3.5 / 12.3.1 — drawings first, then the formulation."""
    section = html.split('id="problem"')[1].split('id="benchmark"')[0]
    assert section.index("section-a-illustration.html") < section.index("formulation.html")
    assert re.search(
        r'class="pane pane-left"[^>]*data-mount="figures/graphics/section-a-illustration.html"',
        section,
    )
    assert re.search(
        r'class="pane pane-right"[^>]*data-mount="formulation.html"',
        section,
    )
    assert "Open the medicine-cabinet walkthrough" in section
    assert "twelve events in three containers" not in section


# -- dependencies (10.3.5, 13.3) -------------------------------------------------------


def test_the_page_ships_no_third_party_anything(html):
    """No framework, no bundler, no CDN, no font, no icon set."""
    assert "http://" not in html
    assert "https://" not in html
    for stylesheet in re.findall(r'<link rel="stylesheet" href="([^"]+)"', html):
        assert (STATIC_ROOT / stylesheet).exists()
    for source in re.findall(r'<script src="([^"]+)"', html):
        assert (STATIC_ROOT / source).exists()


def _mounted_path(fragment: str):
    if fragment.startswith(FIGURE_PREFIX):
        return FIGURE_ROOT / fragment[len(FIGURE_PREFIX) :]
    return STATIC_ROOT / fragment


def test_every_mounted_fragment_exists(html):
    mounted = re.findall(r'data-mount="([^"]+)"', html)
    assert mounted
    for fragment in mounted:
        assert _mounted_path(fragment).exists()


def test_the_page_works_without_scripting_for_the_documents(html):
    """Sections A and C are documents; a reader with no scripting still reaches them."""
    assert html.count("<noscript>") >= 2
    for fragment in re.findall(r'data-mount="([^"]+)"', html):
        assert f'href="{fragment}"' in html


# -- markup safety (12.6.5) ------------------------------------------------------------


def test_html_is_assigned_only_where_the_content_is_a_build_artifact(script):
    """12.6.5 — the one place, and the reason it is safe.

    Everything derived from a request is written as text or built as nodes.  A sanitizer
    is not available to fall back on: 13.3 rules out the library, so the boundary has to
    hold by construction.
    """
    assignments = re.findall(r"\.innerHTML\s*=\s*([^;]+);", script)
    assert assignments == ["await response.text()"]


def test_the_page_has_a_safe_constructor_for_everything_else(script):
    """The helper later sections build their nodes with, so text goes in as text."""
    assert "function element(" in script
    assert "node.textContent = text" in script


def test_state_is_carried_by_an_attribute_the_stylesheet_reads(script, css):
    """12.6.2 — and one source of truth for it, rather than a class beside an attribute."""
    assert 'setAttribute("aria-current"' in script
    assert '.section-nav a[aria-current="true"]' in css


def test_the_current_section_is_marked_by_more_than_colour(css):
    """12.6.2 — weight and a filled ground as well, so it survives greyscale."""
    current = rule_for(css, '.section-nav a[aria-current="true"]')
    assert "font-weight" in current
    assert "background" in current


def test_the_location_hash_decides_which_section_is_displayed(script):
    """12.1.1, 12.1.3 — the nav selects, and the anchor a reader followed is the selection.

    Driven by `hashchange` rather than by a click handler: the nav is already a list of
    anchors, so one path covers a click, a typed URL, a restored tab and the back button,
    and the address bar keeps naming what is on screen (12.1.3).
    """
    assert 'addEventListener("hashchange"' in script
    assert "section.hidden = name !== id" in script


# -- Section B: the strategy catalogue (12.4.2) ---------------------------------------
#
# What stood here: eleven tests over a builder — a block bar, a chain repeater, a
# capacity box, an Evaluate button, a spinner and a stale marker. All eleven described
# controls that no longer exist. The tests below describe what replaced them, and the
# first one is the load-bearing claim of the whole redesign.


@pytest.fixture(scope="module")
def section_b() -> str:
    return re.sub(
        r"/\*.*?\*/|//[^\n]*", "", (STATIC_ROOT / "section-b.js").read_text(), flags=re.DOTALL
    )


@pytest.fixture(scope="module")
def catalog_view() -> str:
    return re.sub(
        r"/\*.*?\*/|//[^\n]*",
        "",
        (STATIC_ROOT / "catalog-view.js").read_text(),
        flags=re.DOTALL,
    )


def test_the_shell_describes_a_catalogue_not_a_builder(html):
    """12.4.2.5 — authored copy must not describe the retired compose-and-Evaluate flow."""
    for gone in (
        "Compose up to four",
        "press Evaluate",
        "runs the harness",
        "configure a block",
    ):
        assert gone not in html, gone
    assert "pre-scored catalogue" in html
    assert "choose a catalogue entry" in html


def test_the_page_anatomy_source_describes_a_catalogue():
    """9.15 — the figure generator must spell Section B as the page now is."""
    from tools import render_figures as rf

    section_b = next(s for s in rf.SECTIONS if s["letter"] == "B")
    blob = repr(section_b)
    for gone in ("Candidate builder", "Evaluate button", "runs the harness"):
        assert gone not in blob, gone
    assert section_b["left"][0] == "Strategy catalogue"
    source = Path(rf.__file__).read_text()
    assert "runs the harness" not in source


def test_the_panel_holds_no_control_that_starts_work(section_b):
    """12.4.2.5 — choosing redraws from data already held; nothing is set running.

    The page issues exactly one request, at load, for the catalogue itself. A second
    `fetch` anywhere in this file would mean a reader's action had reacquired a cost —
    which is the thing the redesign exists to remove.
    """
    assert section_b.count("fetch(") == 1
    assert 'fetch("api/catalog")' in section_b
    for gone in ("api/evaluate", "api/family", "api/dataset", "runBenchmark", "spinner"):
        assert gone not in section_b, gone


def test_nothing_a_reader_touches_can_fail(section_b):
    """12.4.2.5 — a selection cannot be rejected, so there is no violation surface.

    The builder needed one because the factory could refuse what a reader typed. Nothing
    is typed now, so the machinery for reporting a refusal is gone rather than idle.
    """
    for gone in ("violation", "state.violations", "window.confirm"):
        assert gone not in section_b, gone


def test_the_selection_ceiling_comes_from_the_shared_module(section_b, catalog_view):
    """12.4.2.2 — one statement of the bound, and the page does not restate it.

    A literal four in the page would be a second copy of a limit P2's row budget and P3's
    series count both depend on.
    """
    assert "MAX_SELECTED" in section_b
    assert "export const MAX_SELECTED = 4" in catalog_view
    assert not re.search(r"length\s*>=\s*4\b", section_b)


def test_the_select_control_is_disabled_rather_than_hidden(section_b):
    """12.4.2.2 — the ceiling is visible before it is reached."""
    assert "control.disabled = !chosen && full" in section_b
    assert "state.selected.length >= MAX_SELECTED" in section_b


def test_selection_is_marked_by_more_than_colour(section_b):
    """12.6.2 — a state carried by colour alone is not carried."""
    assert 'control.setAttribute("aria-pressed"' in section_b
    assert "entry-mark" in section_b


def test_each_entry_lists_its_chain_its_splits_and_its_containers(section_b):
    """12.4.2.1 — what distinguishes two entries before any score is read."""
    assert "stage.expression" in section_b
    assert "stage.splits" in section_b
    assert "entry.leaf_count" in section_b
    assert "containersByCapacity" in section_b


def test_the_panel_states_the_fixture_framing_where_a_reader_sees_it(section_b):
    """12.4.2.4 — a list of scored candidates reads as a leaderboard unless it says not."""
    assert "FIXTURE_NOTE" in section_b
    note = re.search(r'const FIXTURE_NOTE =\s*(.+?);', section_b, re.DOTALL).group(1)
    assert "not recommendations" in note
    assert "not a ranking" in note


def test_the_columns_come_from_the_document_rather_than_the_page(section_b):
    """12.4.2.3, 12.2.3 — listed without a corpus in the serving process."""
    assert "state.catalog.corpus.feature_columns" in section_b


def test_the_page_computes_no_figure_of_its_own(section_b):
    """12.4.2.6, 12.6.4 — every number displayed is a field of the document.

    Arithmetic on a metric value is what this rules out. Formatting is not arithmetic,
    and `dom.js` owns all of it.
    """
    assert not re.search(r"row\.\w+\s*[-+*/]\s*row\.", section_b)
    assert not re.search(r"\.reduce\(", section_b)


def test_an_opening_selection_is_the_coarsest_and_not_the_best(section_b):
    """12.4.2.4, 8.11.3 — preselecting the best entries would be a recommendation."""
    assert "OPENING_SELECTION" in section_b
    assert ".slice(0, OPENING_SELECTION)" in section_b
    # From the front of the document's own order, which is structural — never sorted here.
    assert not re.search(r"\.sort\(", section_b)


def test_the_report_says_so_when_nothing_is_selected(section_b):
    """12.4.3.8 — empty, and it names the control that fills it."""
    assert "if (!state.selected.length)" in section_b
    assert "Nothing selected" in section_b


def test_the_projection_holds_no_dom_so_it_can_be_tested_directly(catalog_view):
    """12.6.3 — the rule with logic in it is a pure function, and is unit-tested."""
    for forbidden in ("document.", "window.", "createElement"):
        assert forbidden not in catalog_view, forbidden


def test_nothing_from_a_request_is_parsed_as_markup():
    """12.6.5 — checked across **every** script the page loads, not just today's.

    Scoped to the directory rather than to a list of files on purpose: the report views
    render expressions, block names and violation messages, all of which came from a
    request. This fails the moment a new script assigns one of them as markup, including
    scripts that do not exist yet.
    """
    mounting = "app.js"  # the one file allowed to, and only for a build artifact
    for script in sorted(STATIC_ROOT.glob("*.js")):
        source = re.sub(r"/\*.*?\*/|//[^\n]*", "", script.read_text(), flags=re.DOTALL)
        assert "insertAdjacentHTML" not in source, script.name
        assert ".outerHTML" not in source, script.name
        assignments = re.findall(r"\.innerHTML\s*=\s*([^;]+);", source)
        if script.name == mounting:
            assert assignments == ["await response.text()"], script.name
        else:
            assert assignments == [], script.name


def test_the_page_builds_its_nodes_rather_than_writing_them():
    """12.6.5 — one shared constructor, and text goes in as text.

    The builder and all three report views construct through `dom.js`, so the rule is
    kept in one place rather than repeated in five files that could each drift.
    """
    source = (STATIC_ROOT / "dom.js").read_text()
    assert "created.textContent = text" in source
    for script in ("section-b.js", "view-process.js", "view-summary.js", "view-scatter.js"):
        assert 'from "./dom.js"' in (STATIC_ROOT / script).read_text(), script


def test_no_state_survives_a_reload(section_b):
    """13.4 — persistence is excluded outright, not relocated to a different store."""
    for store in ("localStorage", "sessionStorage", "document.cookie", "history.pushState"):
        assert store not in section_b
