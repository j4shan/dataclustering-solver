"""The published copy — 12.2.14.

The page a reader opens on a public URL is not the file the local server hands over: the
server sends a shell that fetches eleven fragments, and the published copy has them
already in it.  Every other test in this suite reads the authored tree, so none of them
would see the published one break.

These run the shipped publish step into a temporary directory and read what it wrote.
The two failures they exist for are silent ones.  A fragment that stops being inlined
leaves a pane that is empty for everyone who does not run script — which is a link
preview, a crawler, and a reader who turned it off — and the page still looks right in a
browser.  A file that drifts into the served tree gets published with it, and nothing
about the page changes to say so.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"

sys.path.insert(0, str(ROOT / "tools"))
import publish  # noqa: E402


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> Path:
    """One publish, read by every test below."""
    out = tmp_path_factory.mktemp("build") / "site"
    publish.publish(out)
    return out


@pytest.fixture(scope="module")
def document(built: Path) -> str:
    return (built / "index.html").read_text()


def text_of(document: str) -> str:
    """The prose a reader without script would see, with the markup taken out."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", document)).lower()


def test_every_mounted_pane_is_filled_in(document):
    """12.2.14 — the published document carries the argument, not a shell.

    `data-mount` surviving is the specific regression: the attribute left in place means
    the script fetches the fragment again at load, so a browser still renders correctly
    and only the readers who run no script get an empty page.
    """
    assert "data-mount" not in document
    assert "Loading the" not in document
    assert "<noscript" not in document


def test_each_section_carries_its_own_argument(document):
    """One phrase per section, taken from the fragment that had to be inlined to have it."""
    prose = text_of(document)
    for phrase in (
        "medicine cabinet is the corpus",
        "weighted gini",
        "multiple-choice knapsack",
        "dynamic partition pruning",
    ):
        assert phrase in prose, phrase


def test_the_published_document_is_the_whole_page(document):
    """A shell is a few kilobytes; the page is not.  This catches a partial inline."""
    assert len(text_of(document)) > 50_000
    assert document.count("<math") > 50


def test_no_asset_the_page_names_is_missing(built: Path, document: str):
    """12.2.13 — every reference is relative, so every reference is a path in the output."""
    named = re.findall(r'(?:src|href)="([^"#:]+)"', document)
    assert named
    for reference in named:
        assert not reference.startswith("/"), reference
        assert (built / reference).is_file(), reference


def test_no_fragment_ships_beside_the_document_that_inlined_it(built: Path):
    """An inlined fragment at its own URL is a second copy of part of the page.

    The illustration fragments are the sharp case: standalone, their figures resolve
    against the wrong directory and every image fails, so what a crawler would index is a
    broken page competing with a correct one.
    """
    assert not (built / "figures" / "html").exists()
    for orphan in ("formulation.html", "section-gini-walkthrough.html"):
        assert not (built / orphan).exists(), orphan


def test_no_authoring_material_reaches_the_published_copy(built: Path):
    """12.2.14 — the working notes behind the exhibit are not part of the exhibit."""
    assert not list(built.rglob("*.drawio"))
    assert not list(built.rglob("*_prompt.*"))
    assert not (built / "resources").exists()
    assert not (built / "figures" / "data").exists()


def test_the_published_copy_carries_the_servers_headers(built: Path):
    """12.6.5 on a host with no middleware to add them.

    The policy is copied rather than re-derived, so this asserts the two files agree
    rather than asserting a string: a policy tightened in one place and not the other is
    the failure, and it is invisible until someone inspects a response.
    """
    headers = (built / "_headers").read_text()
    server = (ROOT / "simulator" / "gui" / "server.py").read_text()
    policy = re.search(r'"default-src \'self\'",(.*?)\)\n', server, re.DOTALL)
    assert policy
    for directive in re.findall(r'"([a-z-]+ [^"]+)"', policy.group(1)):
        assert directive in headers, directive
    assert "X-Content-Type-Options: nosniff" in headers
    assert "Cache-Control" in headers
    assert "no-store" not in headers


def test_the_publish_step_reads_only_the_served_tree():
    """`resources/` is not excluded by a list; it is not reachable from the input at all.

    An exclude list is the thing that falls out of date when a figure is added.  This
    asserts the shape that makes one unnecessary.
    """
    source = (ROOT / "tools" / "publish.py").read_text()
    body = re.sub(r'""".*?"""', "", source, flags=re.DOTALL)
    assert "resources" not in body
    assert 'SITE = ROOT / "site"' in source
