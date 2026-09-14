"""Mounted fragments and the stylesheet — 12.6.5.

A fragment is authored apart from the stylesheet and mounted by assignment (12.6.5), so a
class whose rule was never written fails silently: the markup is correct, the selector
matches nothing, and the element renders as a browser default inside an otherwise
tokenized page. Nothing in the page's construction would catch it, so this does.

The check is deliberately structural rather than visual. It asserts that a rule exists for
every class a fragment names — not what the rule says, which §12.7 records.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

STATIC = Path("site")
HTML = STATIC / "figures" / "html"

#: The fragments mounted into a pane by `data-mount`, and the wrapper the document
#: pre-render emits around every collapsed figure pair (12.3).
FRAGMENTS = [
    HTML / "section-problem-illustration.html",
    HTML / "section-gini-illustration.html",
    HTML / "section-budget-illustration.html",
    HTML / "section-databricks-illustration.html",
    STATIC / "section-gini-walkthrough.html",
    STATIC / "section-budget-walkthrough.html",
    STATIC / "section-databricks-walkthrough.html",
    STATIC / "section-problem-glossary.html",
    STATIC / "section-gini-glossary.html",
]
PRE_RENDERED = [
    STATIC / "formulation.html",
]

#: Classes the Markdown renderer emits that this page deliberately does not style. Syntax
#: highlighting is excluded outright (10.3.5, 10.3.5), so the fenced-code language class has
#: nothing to hang a rule on and is not a forgotten one.
UNSTYLED_BY_DESIGN = {"language-sql", "language-text"}


def rules() -> str:
    return (STATIC / "app.css").read_text() + (STATIC / "tokens.css").read_text()


def classes_in(markup: str) -> set[str]:
    return {name for value in re.findall(r'class="([^"]+)"', markup) for name in value.split()}


@pytest.mark.parametrize("fragment", FRAGMENTS + PRE_RENDERED, ids=lambda p: Path(p).name)
def test_every_class_a_mounted_fragment_uses_is_defined(fragment):
    stylesheet = rules()
    used = classes_in(Path(fragment).read_text())
    assert used, f"{fragment} names no class at all — did it move?"
    undefined = sorted(
        name
        for name in used - UNSTYLED_BY_DESIGN
        if f".{name}" not in stylesheet
    )
    assert not undefined, f"{fragment} uses classes no rule defines: {undefined}"


def test_the_check_would_notice_a_missing_rule():
    """The guard on the guard: an unknown class is caught, not quietly passed over."""
    assert ".no-such-class-as-this" not in rules()
