"""The design tokens (12.7).

The criterion for this stylesheet is that **no value is invented at implementation time**,
so most of these tests read `ui-spec.md` §12.7 and check the CSS against it rather than
against a second list written here.  A hardcoded expectation would be exactly the second
source of truth: the specification is the authority, and the test's job is
to notice when the file drifts from it.
"""

from __future__ import annotations

import re

import pytest

from simulator.gui import STATIC_ROOT
from simulator.report.charts import SERIES_LIGHT

SPEC = STATIC_ROOT.parents[2] / "project_metadata" / "ui-spec.md"
TOKENS = STATIC_ROOT / "tokens.css"

HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")


@pytest.fixture(scope="module")
def css() -> str:
    """The stylesheet's **declarations**, with comments stripped.

    Every assertion below is about what the page will render, and a comment explaining
    why 17pt is *not* used would otherwise read as 17pt being used.
    """
    return re.sub(r"/\*.*?\*/", "", TOKENS.read_text(), flags=re.DOTALL)


@pytest.fixture(scope="module")
def design_tokens_section() -> str:
    """§12.7 alone — the section that fixes resolved values."""
    text = SPEC.read_text()
    start = text.index("### 12.7 Design tokens")
    return text[start : text.index("\n---", start)]


def normalized(colours) -> set[str]:
    return {colour.lower() for colour in colours}


# -- colour (12.7.1) -----------------------------------------------------------------


def test_every_colour_the_spec_fixes_is_in_the_stylesheet(css, design_tokens_section):
    specified = normalized(HEX.findall(design_tokens_section))
    assert specified, "fixture assumes §12.7 names colours by hex"
    assert specified <= normalized(HEX.findall(css))


def test_no_colour_in_the_stylesheet_was_invented(css, design_tokens_section):
    """The other direction, which is the one that catches drift.

    A colour may be here only because §12.7 fixed it, or because it is a slot of the
    validated report palette §12.7.1.6 defers to (9.4).
    """
    allowed = normalized(HEX.findall(design_tokens_section)) | normalized(SERIES_LIGHT)
    assert normalized(HEX.findall(css)) <= allowed


def test_the_chart_series_stay_in_step_with_the_generated_report(css):
    """12.7.1.6 — identity in data is one job, and one palette does it in both places."""
    for slot, colour in enumerate(SERIES_LIGHT, start=1):
        assert f"--series-{slot}: {colour};" in css


def test_the_ground_and_the_recessed_plane_are_the_only_two_planes(css):
    """12.7.1.1 — cards sit on the ground; a third fill would be an invented value."""
    assert "--card: var(--ground);" in css


@pytest.mark.parametrize("role", ["--ink", "--ink-secondary", "--ink-muted"])
def test_only_the_three_measured_inks_carry_text(css, role):
    assert re.search(rf"{role}: #[0-9a-f]{{6}};", css)


def test_the_rules_are_never_used_for_type(css):
    """12.7.1.3 — below any text threshold by construction."""
    for rule in ("--rule", "--rule-strong"):
        assert not re.search(rf"color:\s*var\({rule}\)", css)


def test_the_accent_is_decorative_only(css):
    """12.7.1.4 — 2.2:1, so text on it or as a text colour is a defect."""
    assert not re.search(r"color:\s*var\(--accent\)", css)
    assert not re.search(r"background:\s*var\(--accent\)[^;]*;\s*color:", css)


def test_the_platform_blue_never_carries_text(css):
    """12.7.1.5 — 3.9:1 fails AA for body text, so it is chrome and nothing else.

    Which is also why there is no filled primary button: white on that blue is about
    3.6:1, and a 13px label on it would fail the same threshold from the other side.
    """
    assert not re.search(r"color:\s*var\(--chrome\)", css)
    assert not re.search(r"background:\s*var\(--chrome\);\s*\n\s*color:", css)


# -- type (12.7.2) -------------------------------------------------------------------


# -- metrics (12.7.3) ----------------------------------------------------------------


# -- the spec is the authority (12.6.3.2) --------------------------------------------


def test_the_stylesheet_records_every_value_the_spec_fixes(css, design_tokens_section):
    """12.6.3.2 — one drift check, and not one assertion per value.

    Most of §12.7 is typed `I`: a hex, a radius, a font stack and an easing curve are
    replaceable, and **a restyle is not a spec violation**. A test naming any of them would
    forbid what the spec permits. What must stay true is narrower — that the two never
    disagree — so this reads whatever §12.7 currently records and looks for it in the
    stylesheet. Change a value in both and this passes; change it in one and it does not.
    """
    quoted = re.findall(r"`([^`]+)`", design_tokens_section)
    fixed = [
        value
        for value in quoted
        if re.fullmatch(r"#[0-9A-Fa-f]{6}|\d+px|cubic-bezier\([^)]*\)", value)
    ]
    assert len(fixed) > 10, "the spec section stopped recording resolved values"

    missing = [value for value in fixed if value.lower() not in css.lower()]
    assert not missing, f"§12.7 fixes values the stylesheet does not carry: {missing}"


def test_spacing_is_an_8pt_grid_with_a_4pt_sub_unit(css):
    """12.7.3.1 — every step is a multiple of 8, and only the sub-unit is not."""
    steps = re.findall(r"--space-[\w-]+: (\d+)px;", css)
    assert steps
    assert min(int(step) for step in steps) == 4
    assert all(int(step) % 8 == 0 for step in steps if int(step) != 4)


# -- motion (12.7.4) -----------------------------------------------------------------


def test_reduced_motion_leaves_the_spinner_visible(css):
    """12.7.4.3 — it degrades to a static indicator rather than disappearing.

    An evaluation takes long enough to notice (12.2.4), so it still has to read as
    running for a reader who asked for less motion.
    """
    reduced = css[css.index("prefers-reduced-motion") :]
    assert "animation: none;" in reduced
    assert "display: none" not in reduced.split("@media print")[0]


# -- focus (12.6.1.1) ----------------------------------------------------------------


def test_the_focus_ring_is_drawn_on_focus_visible_only(css):
    """The ring appears for keyboard navigation, not on a mouse click."""
    assert ":focus-visible {" in css
    assert re.search(r"^:focus \{\n  outline: none;", css, re.MULTILINE)
    assert "var(--chrome)" in css[css.index(":focus-visible") :]


# -- dependencies (10.3.5, 12.2.2) ---------------------------------------------------


def test_the_stylesheet_ships_no_third_party_anything(css):
    """No font file, no icon set, no import, and nothing fetched from the network."""
    assert "@import" not in css
    assert "@font-face" not in css
    assert "http://" not in css
    assert "https://" not in css
    assert not re.search(r"url\((?!\s*['\"]?data:)", css)


def test_it_declares_the_single_look_it_commits_to(css):
    """12.1.5.1 — light only, and every colour painted rather than inherited."""
    assert "color-scheme: light;" in css
    assert "prefers-color-scheme" not in css
    assert re.search(r"body \{[^}]*background: var\(--ground\)", css, re.DOTALL)
