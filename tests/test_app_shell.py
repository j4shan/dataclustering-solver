"""The application shell (12.1).

A browser is not required to check most of what 12.1 asks for.  The scroll model, the
breakpoint behaviour, the anchors and the dependency rules are all properties of the
authored files, and AGENTS.md makes browser-driven checks a plus rather than a gate — so
these read the files, and the optional suite (T20) drives the live page.
"""

from __future__ import annotations

import re

import pytest

from simulator.gui import SITE_ROOT

INDEX = SITE_ROOT / "index.html"
APP_CSS = SITE_ROOT / "app.css"
APP_JS = SITE_ROOT / "app.js"


@pytest.fixture(scope="module")
def html() -> str:
    return INDEX.read_text()


@pytest.fixture(scope="module")
def css() -> str:
    return re.sub(r"/\*.*?\*/", "", APP_CSS.read_text(), flags=re.DOTALL)


def test_browser_tab_uses_the_formal_project_title(html):
    """12.1.3.3 — the formal name stays on the browser tab, not on the top bar."""
    assert "<title>The Data Storage Layout Problem</title>" in html
    assert "wordmark" not in html
    assert "The Data Storage Layout Problem" not in html.split("<body>", 1)[1].split("</header>", 1)[0]


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


# -- five sections, in order (12.1.1) -----------------------------------------------


def test_there_are_five_sections_in_fixed_order(html):
    assert re.findall(r'<section class="section(?:\s[^"]*)?" id="([\w-]+)"', html) == [
        "problem",
        "gini",
        "knapsack",
        "design",
        "signal",
    ]


def test_the_five_sections_are_left_right_pairs(html):
    assert html.count('class="split"') == 5
    assert html.count("pane pane-left") == 5
    assert html.count("pane-right") == 5
    assert "section-single" not in html
    assert "pane-single" not in html


def test_the_sections_are_individually_linkable(html):
    """12.1.3 — stable anchors, and a persistent control that selects between them."""
    anchors = set(re.findall(r'<section class="section(?:\s[^"]*)?" id="([\w-]+)"', html))
    navigated = set(re.findall(r'<a href="#([\w-]+)" data-nav=', html))
    assert navigated == anchors


def test_navigation_labels_match_section_headings(html):
    """12.1.3.1 — the top bar and the section heading spell the same names."""
    navigation = re.findall(r'data-nav="[^"]+">([^<]+)</a>', html)
    headings = re.findall(r'<h1 id="[\w-]+-heading">([^<]+)</h1>', html)
    assert navigation == headings


def test_section_headings_match_their_navigation_labels(html):
    """12.1.3.1 — the section heading is the tab; a distinct editorial name is the left pane title."""
    section = html.split('id="problem"')[1].split('id="gini"')[0]
    assert '<a href="#problem" data-nav="problem">Problem Statement</a>' in html
    assert '<h1 id="problem-heading">Problem Statement</h1>' in section
    assert ">Organizing Data Like a Medicine Cabinet</h2>" in section
    knapsack = html.split('id="knapsack"')[1].split('id="design"')[0]
    assert '<h1 id="knapsack-heading">Drawing Storage Boundary</h1>' in knapsack
    assert "pane-title" not in knapsack
    design = html.split('id="design"')[1].split('id="signal"')[0]
    assert '<h1 id="design-heading">Go Live on Databricks Lakehouse</h1>' in design
    assert "pane-title" not in design
    signal = html.split('id="signal"')[1]
    assert '<h1 id="signal-heading">Business Insights as Byproduct</h1>' in signal
    assert "pane-title" not in signal


def test_section_headings_stand_alone(html):
    """12.1.3.2 — the heading is not followed by a footnote or lede."""
    assert "section-lede" not in html


def test_every_section_is_labelled_for_a_screen_reader(html):
    """12.6.1 — the panes are landmarks a screen reader can navigate."""
    labelled = re.findall(r'aria-labelledby="([\w-]+)"', html)
    for target in labelled:
        assert f'id="{target}"' in html
    panes = re.findall(r'<div class="pane(?:\s[^"]*)?"[^>]*>', html)
    assert len(panes) == 12
    assert all('role="region"' in pane for pane in panes)
    assert all('aria-label="' in pane for pane in panes)
    assert len(set(re.findall(r'aria-label="([^"]+)"', "\n".join(panes)))) == 12


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


def test_the_top_bar_is_a_raised_3d_bar(css):
    """12.1.3.4 — a ground-to-recessed face, a top-edge highlight, and a drop shadow."""
    bar = rule_for(css, ".top-bar")
    assert "linear-gradient(" in bar
    assert "var(--ground)" in bar
    assert "var(--recessed)" in bar
    assert "inset 0 1px 0 var(--ground)" in bar
    assert "box-shadow" in bar


def test_selectable_tabs_highlight_on_hover(css):
    """12.1.3.5 — a tab that can be chosen is visibly live before it is selected."""
    hover = rule_for(css, ".section-nav a:hover:not([aria-current=\"true\"])")
    assert "background" in hover
    assert "var(--accent)" in hover


def test_tab_labels_are_one_pixel_larger_than_chrome(css):
    """12.7.2.5 — section-tab labels sit one pixel above 13px chrome."""
    assert "font-size: calc(var(--text-body) + 1px)" in rule_for(css, ".section-nav a")


def test_panes_are_bounded_and_scroll_independently(css):
    pane = rule_for(css, ".pane")
    assert "overflow-y: auto" in pane
    assert "min-height: 0" in pane


def test_the_bound_can_actually_take_effect(css):
    """`min-height: 0` on every flex and grid child in the chain.

    Without it a child's automatic minimum size is its content: the pane grows the
    section instead of scrolling, and 12.1.2 silently does not happen.
    """
    for selector in (".split", ".pane", ".pane-body", ".pane-stack.pane-right"):
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
    assert "line-height: var(--leading-prose)" in rule_for(css, ".pane:has(.formulation)")


def test_section_problem_formulation_fills_the_right_pane(css):
    """12.3 — the document uses the pane, not a character clamp inside it."""
    assert "max-width: none" in rule_for(css, "#problem .pane-right .formulation")


def test_section_problem_illustration_is_one_pixel_larger_than_chrome(css):
    """12.3 — the left pane remaps the type tokens so every beat steps together."""
    declarations = rule_for(css, "#problem .pane-left")
    assert "--text-body: 14px" in declarations
    assert "--text-small: 12px" in declarations
    assert "--text-heading: 18px" in declarations
    assert "--text-title: 23px" in declarations


def test_section_problem_formulation_is_one_pixel_larger_than_chrome(css):
    """12.3 — body, headings, and small type each step one pixel above 12.7.2."""
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


def test_section_problem_puts_the_illustration_on_the_left(html):
    """12.3 / 12.3 — drawings first, then the dictionary, then the formulation."""
    section = html.split('id="problem"')[1].split('id="gini"')[0]
    assert section.index("section-problem-illustration.html") < section.index(
        "section-problem-glossary.html"
    )
    assert section.index("section-problem-glossary.html") < section.index("formulation.html")
    assert re.search(
        r'data-mount="figures/html/section-problem-illustration.html"',
        section,
    )
    assert re.search(r'data-mount="section-problem-glossary.html"', section)
    assert re.search(r'data-mount="formulation.html"', section)
    assert "twelve events in three containers" not in section


def test_section_problem_right_column_stacks_the_dictionary_above_the_formulation(css):
    """12.3 / 12.8 — dictionary 30% on top, independently bounded, lower band 70%."""
    stack = rule_for(css, ".pane-stack.pane-right")
    assert "grid-template-rows: minmax(8rem, 30%) minmax(0, 70%)" in stack
    assert "display: table" in rule_for(css, ".glossary table")
    assert "border-bottom: 1px solid var(--rule)" in rule_for(css, ".glossary th")


# -- dependencies (10.3.5, 10.3.5) -------------------------------------------------------


def test_the_page_ships_no_third_party_anything(html):
    """No framework, no bundler, no CDN, no font, no icon set."""
    assert "http://" not in html
    assert "https://" not in html
    for stylesheet in re.findall(r'<link rel="stylesheet" href="([^"]+)"', html):
        assert (SITE_ROOT / stylesheet).exists()
    for source in re.findall(r'<script[^>]+src="([^"]+)"', html):
        assert (SITE_ROOT / source).exists()


def _mounted_path(fragment: str):
    """Where a `data-mount` path lands on disk — which is simply where it lands.

    12.2.13 — every mount is relative to the page, and the served tree is the repository
    tree, so resolving one is a join rather than a prefix rule.  A leading slash would
    address the host's root instead, which is what the inventory check below forbids.
    """
    return SITE_ROOT / fragment


def test_every_mounted_fragment_exists(html):
    mounted = re.findall(r'data-mount="([^"]+)"', html)
    assert mounted
    for fragment in mounted:
        assert _mounted_path(fragment).exists()


def test_every_pane_declares_the_fragment_that_fills_it(html):
    """Every pane names the fragment the shell fetches into it at load.

    Fetching is what keeps each fragment editable on its own.  A pane with no
    `data-mount` stays on its loading placeholder forever.
    """
    sections = re.findall(r'<section class="section[^"]*" id="([\w-]+)"', html)
    assert len(sections) == 5
    for identifier in sections:
        opened = html.split(f'id="{identifier}"')[1]
        body = opened.split("</section>")[0]
        assert "data-mount=" in body, identifier
    mounted = re.findall(r'data-mount="([^"]+)"', html)
    assert len(mounted) == len(set(mounted)) >= len(sections)
    for fragment in mounted:
        assert _mounted_path(fragment).is_file(), fragment


# -- markup safety (12.6.5) ------------------------------------------------------------


def test_html_is_assigned_only_where_the_content_is_a_build_artifact(script):
    """12.6.5 — the one place, and the reason it is safe.

    Everything derived from a request is written as text or built as nodes.  A sanitizer
    is not available to fall back on: 10.3.5 rules out the library, so the boundary has to
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


def test_nothing_from_a_request_is_parsed_as_markup():
    """12.6.5 — checked across **every** script the page loads, not just today's.

    Scoped to the directory rather than to a list of files on purpose: the report views
    render expressions, block names and violation messages, all of which came from a
    request. This fails the moment a new script assigns one of them as markup, including
    scripts that do not exist yet.
    """
    mounting = "app.js"  # the one file allowed to, and only for a build artifact
    for script in sorted(SITE_ROOT.glob("*.js")):
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
    source = (SITE_ROOT / "dom.js").read_text()
    assert "created.textContent = text" in source


def test_no_state_survives_a_reload():
    """12.2.7 — persistence is excluded outright, not relocated to a different store."""
    for script in SITE_ROOT.glob("*.js"):
        text = script.read_text()
        for store in ("localStorage", "sessionStorage", "document.cookie", "history.pushState"):
            assert store not in text, script.name


# -- addressing -----------------------------------------------------------------------

#: What actually makes a browser resolve against the site root: a leading slash on a URL
#: the page emits.  A protocol-relative or absolute URL is 12.2.2's concern, not this
#: one, and a bare `#anchor` addresses nothing at all.
ROOT_ABSOLUTE = re.compile(
    r"""(?:
          (?:                                 # quoted, which is every case but one
              \b(?:src|href|action)\s*=       # an attribute, or a property assigned in JS
            | @import\s+                      # a stylesheet pulling another one in
            | \bfetch\( | \bnew\s+URL\(     # a script asking for something itself
            | \bfrom\s+                       # a module import
          )\s*['"](/(?!/)[^'"]*)
        | \burl\(\s*['"]?(/(?!/)[^'")\s>]*)   # CSS, where the quotes are optional
     )""",
    re.IGNORECASE | re.VERBOSE,
)


def root_absolute(text: str) -> list[str]:
    """Every URL in `text` that starts at the site root.

    The quote is required everywhere except inside `url(`, because prose is full of paths
    — a comment naming a directory describes one rather than fetching it, and a check that
    flagged it would be checking English.
    """
    return [
        found.group(1) or found.group(2) for found in ROOT_ABSOLUTE.finditer(text)
    ]


#: Every document this process serves that a person authored or a generator wrote.
SERVED = sorted(
    document
    for extension in ("*.html", "*.js", "*.css", "*.svg")
    for document in SITE_ROOT.rglob(extension)
)


def test_the_inventory_of_served_documents_is_not_empty():
    """A scan that found nothing would pass the next test for the wrong reason."""
    assert len(SERVED) > 5


@pytest.mark.parametrize("document", SERVED, ids=lambda p: p.name)
def test_no_served_document_addresses_the_site_root(document):
    """12.2.13 — every URL the page emits is relative to its own document.

    A leading slash resolves against whatever host the page is opened from rather than
    against the page, so it breaks the moment the site is served from anywhere but the
    root of an origin.  The rule is checked here rather than remembered, because the next
    person to write a URL into a page will not have read this docstring.
    """
    offending = root_absolute(document.read_text(encoding="utf-8"))
    assert offending == [], f"{document.name} addresses the site root: {offending}"
