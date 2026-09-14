"""How the figures load — 12.1.10.

Eleven of the twelve figures are 5 MB between them, and all twelve land in the document
once the pane fragments mount at load.  Loaded eagerly, that is 5 MB a reader waits
through before the first sentence appears.

The arrangement this asserts has two halves and only works as a pair.  `loading="lazy"`
keeps every figure but the first off the critical path, so the page opens on one image.
A `prefetch` link then pulls each of them anyway, quietly, once the page is interactive —
because this page is *presented* as well as linked, and a figure that starts loading when
a section is opened is a figure that is blank at the moment someone points at it.  Same
bytes as before; earlier text, and nothing missing when a section is opened.

Drop the lazy attributes and the page is slow to open.  Drop the prefetches and it is
fast to open and blank on the first click into each section.  Neither failure shows up in
any other test here, and neither is visible on a fast local connection — which is the
only connection this page is ever developed on.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest

from simulator.gui import SITE_ROOT

#: The first figure of the landing section: what a reader sees before scrolling or
#: clicking anything, and so the one image that may not wait behind another request.
EAGER = "figures/img/section_problem_medical_cabinet.png"

IMG = re.compile(r"<img\b[^>]*?/?>", re.DOTALL)


def images() -> list[tuple[Path, str, str]]:
    """Every `<img>` the site authors, as (file, tag, src)."""
    found = []
    for path in sorted(SITE_ROOT.rglob("*.html")):
        for tag in IMG.findall(path.read_text()):
            source = re.search(r'src="([^"]+)"', tag)
            assert source, f"{path.name}: an image with no src"
            found.append((path, tag, source.group(1)))
    return found


@pytest.fixture(scope="module")
def shell() -> str:
    return (SITE_ROOT / "index.html").read_text()


@pytest.fixture(scope="module")
def prefetched(shell: str) -> set[str]:
    return set(re.findall(r'<link rel="prefetch" href="([^"]+)"', shell))


def png_size(src: str) -> tuple[int, int]:
    """The figure's real dimensions, read from its IHDR rather than from the markup."""
    data = (SITE_ROOT / src).read_bytes()
    assert data[12:16] == b"IHDR", src
    return struct.unpack(">II", data[16:24])


def test_the_site_has_figures_to_check():
    assert len(images()) >= 10


def test_every_figure_reserves_its_own_space():
    """A lazy image with no dimensions moves the text under it when it lands.

    The attributes are checked against the file, not merely for being present: a
    figure replaced at a different aspect ratio leaves the old numbers behind, and the
    symptom is a page that reflows once per image instead of never.
    """
    for path, tag, src in images():
        width = re.search(r'width="(\d+)"', tag)
        height = re.search(r'height="(\d+)"', tag)
        assert width and height, f"{path.name}: {src} declares no size"
        assert (int(width.group(1)), int(height.group(1))) == png_size(src), src


def test_only_the_first_figure_loads_eagerly():
    """Everything else waits, so opening the page costs one image rather than all of them."""
    eager = [src for _, tag, src in images() if 'loading="lazy"' not in tag]
    assert eager == [EAGER]


def test_every_deferred_figure_is_prefetched(prefetched: set[str]):
    """12.1.10 — a figure must be in cache before a reader opens its section.

    This is the half that keeps the page presentable: without it the first click into
    each section shows an empty stage for as long as the figure takes to arrive.
    """
    for _, tag, src in images():
        if 'loading="lazy"' in tag:
            assert src in prefetched, f"{src} is deferred but never prefetched"


def test_the_eager_figure_is_not_prefetched(prefetched: set[str]):
    """It is already being fetched; a prefetch for it is a second request for one image."""
    assert EAGER not in prefetched


def test_no_prefetch_names_a_figure_the_page_does_not_show(prefetched: set[str]):
    """A prefetch left behind after a figure is dropped downloads a file nobody displays."""
    shown = {src for _, _, src in images()}
    for src in prefetched:
        assert src in shown, f"{src} is prefetched but displayed nowhere"
        assert (SITE_ROOT / src).is_file(), src
