"""Pre-render the formal problem statement for the GUI's Section A.

The GUI shows `problem-statement.md` as a document to be read, not parsed (PRD 12.3.1).
Doing that conversion here rather than in the browser is what lets the page ship no
third-party JavaScript, CSS, or web font (10.3.5): what arrives is finished HTML, and the
mathematics arrives as **native MathML** the browser lays out itself.

Four transformations, each of which exists for a stated reason:

*Mathematics becomes MathML.*  ``$…$`` and ``$$…$$`` are lifted out before Markdown ever
sees them — a formula is full of backslashes and underscores that Markdown would happily
mangle — converted, and put back afterwards.

*Headings gain anchors and a table of contents.*  The contents list is generated from the
headings the document already has (12.3.3), so a section added to the problem statement appears
in it with no edit here.

*``<picture>`` collapses to its light source.*  The document carries theme-switching figure
pairs for a Markdown host that follows the system.  The GUI does not: it commits to one
warm light surface (12.1.5), so a reader whose system is dark would otherwise be served the
dark figure on a light page.  Only the light variant survives (12.1.5.1).

*Outbound links open away from the page.*  The page is an application; following a citation
should not navigate out of it.

*An authored contents list is dropped.*  A document that carries one for its Markdown
readers would otherwise show it beside the generated one (12.3.3.1).

Two documents go through it, not one: the problem statement for Section A and the engine mapping
for Section C (12.5.4).  Both are committed Markdown artifacts of this repository and both
are shown as documents to be read, so they get one renderer rather than two.

Needs the ``docs`` extra (``markdown-it-py``, ``latex2mathml``) — build-time only, and
nothing under ``simulator/`` imports it (10.3.6).

    python -m tools.render_formulation                    # both
    python -m tools.render_formulation production-design  # one
"""

from __future__ import annotations

import argparse
import html
import re
import unicodedata
from pathlib import Path

#: The committed Markdown the GUI serves, and where each pre-render lands.
#:
#: **One rendering path serves both documents** (12.5.4).  Section A shows the problem statement
#: and Section C shows the engine mapping, at the same parity — anchored headings, an
#: injected table of contents, native MathML, light-variant figures — and a second renderer
#: would be a second thing to keep faithful to the source.
DOCUMENTS = {
    "formulation": (
        Path("project_metadata/problem-statement.md"),
        Path("simulator/gui/static/formulation.html"),
    ),
    "production-design": (
        Path("project_metadata/production-design.md"),
        Path("simulator/gui/static/production-design.html"),
    ),
}

SOURCE, OUTPUT = DOCUMENTS["formulation"]

#: Where the figures the document references are served from, relative to the page.
ASSET_PREFIX = "figures/"

#: How a document under ``project_metadata/`` reaches the shipped resources beside it.
#: The served tree is rooted at ``resources/`` itself, so this hop is stripped rather
#: than carried into a URL that would have to climb back out of it.
RESOURCE_HOP = "../resources/"

#: A private-use codepoint.  It must not be NUL: CommonMark *requires* U+0000 be replaced
#: with U+FFFD, which silently destroys any placeholder built from it.
SENTINEL = ""


def slugify(text: str) -> str:
    """A stable, readable anchor for a heading.

    Mirrors the shape of the anchors a Markdown host generates — lowercase, punctuation
    dropped, runs of space to a single hyphen — so a link written against the document on
    disk keeps working against the rendered page.
    """
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_]+", "-", text) or "section"


def drop_authored_contents(markdown_text: str) -> str:
    """Remove a contents list the document authors for its Markdown readers (12.3.3.1).

    The document is read in two places.  On a Markdown host it needs a contents list of
    its own, because nothing there generates one; in the pane, 12.3.3 injects one from
    the headings.  Keeping both would show the reader two lists, and would put a
    "Contents" entry inside the generated list pointing at the authored one.  The
    authored section runs from its heading to the rule that closes it.
    """
    return re.sub(r"^## Contents\n.*?(?=^---$)", "", markdown_text, flags=re.S | re.M)


def extract_math(text: str) -> tuple[str, list[tuple[str, bool]]]:
    """Replace every formula with a sentinel, returning the text and what was removed.

    Fenced code is shielded first so its ``*`` and ``$`` are never read as mathematics.
    """
    fences: list[str] = []
    formulas: list[tuple[str, bool]] = []

    def stash_fence(match: re.Match) -> str:
        fences.append(match.group(0))
        return f"{SENTINEL}F{len(fences) - 1}{SENTINEL}"

    def stash_math(display: bool):
        def go(match: re.Match) -> str:
            formulas.append((match.group(1).strip(), display))
            return f"{SENTINEL}M{len(formulas) - 1}{SENTINEL}"

        return go

    work = re.sub(r"```.*?```", stash_fence, text, flags=re.S)
    work = re.sub(r"\$\$(.+?)\$\$", stash_math(True), work, flags=re.S)
    work = re.sub(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", stash_math(False), work, flags=re.S)
    work = re.sub(
        re.escape(SENTINEL) + r"F(\d+)" + re.escape(SENTINEL),
        lambda m: fences[int(m.group(1))],
        work,
    )
    return work, formulas


def restore_math(rendered: str, formulas: list[tuple[str, bool]]) -> str:
    """Convert each stashed formula to MathML and put it back where it came from."""
    from latex2mathml.converter import convert

    def put_back(match: re.Match) -> str:
        tex, display = formulas[int(match.group(1))]
        mathml = convert(tex)
        if display:
            mathml = mathml.replace("<math", '<math display="block"', 1)
        # \boxed compiles to <menclose>, which Safari draws and Chrome's MathML Core
        # ignores.  Tag it so the stylesheet can draw the rule itself rather than leaving
        # the objective function unboxed on one engine and boxed on the other.
        if "menclose" in mathml:
            mathml = mathml.replace("<math", '<math class="is-boxed"', 1)
        return mathml

    return re.sub(
        re.escape(SENTINEL) + r"M(\d+)" + re.escape(SENTINEL), put_back, rendered
    )


def add_heading_anchors(rendered: str) -> tuple[str, list[tuple[int, str, str]]]:
    """Give every h2/h3 an id, and report the headings in document order.

    The h1 is the document's title and is deliberately excluded: it names the page rather
    than a place within it.
    """
    headings: list[tuple[int, str, str]] = []

    def anchor(match: re.Match) -> str:
        level, inner = int(match.group(1)), match.group(2)
        label = html.unescape(re.sub(r"<[^>]+>", "", inner)).strip()
        slug = slugify(label)
        headings.append((level, slug, label))
        return f'<h{level} id="{slug}">{inner}</h{level}>'

    rendered = re.sub(r"<h([23])>(.*?)</h\1>", anchor, rendered, flags=re.S)
    return rendered, headings


def build_toc(headings: list[tuple[int, str, str]], document_id: str) -> str:
    """The contents list injected at the top of the pane (12.3.3).

    A `<details>` rather than a heading and a list, because the list is long on both
    documents and a reader who has found their section wants it out of the way.  It is
    emitted **closed**: the document itself is what the pane opens on, and the summary
    remains the control for a reader who wants the list.  Native, because a mounted
    fragment runs no script of its own and no library is available to it (10.3.5, 13.3)
    — the summary is the whole control, and the arrow beside it is drawn in CSS from
    the open state.

    The summary's id carries the document, because both fragments are mounted into the
    *same* page (12.5.4) and a duplicated id would point Section C's contents label at
    Section A's.
    """
    items = [
        f'<li class="toc-h{level}"><a href="#{slug}">{html.escape(label)}</a></li>'
        for level, slug, label in headings
    ]
    label_id = f"{document_id}-toc-heading"
    return (
        '<details class="toc">'
        f'<summary id="{label_id}">Table of Content'
        '<span class="toc-arrow" aria-hidden="true"></span>'
        "</summary>"
        f'<ol>{"".join(items)}</ol>'
        "</details>"
    )


def collapse_pictures(rendered: str, asset_prefix: str) -> str:
    """Reduce each ``<picture>`` to its light ``<img>``, repointed at the served path.

    The document's figure pairs switch on ``prefers-color-scheme``.  The page is light by
    commitment, so the dark source is dropped outright rather than left to fire on a
    reader whose system happens to be dark (12.1.5.1).
    """

    def light_only(match: re.Match) -> str:
        block = match.group(0)
        img = re.search(r"<img\b[^>]*>", block, flags=re.S)
        if not img:
            return ""
        tag = re.sub(
            r'src="(?!https?:|/)([^"]+)"',
            lambda m: f'src="{asset_prefix}{m.group(1).removeprefix(RESOURCE_HOP)}"',
            img.group(0),
        )
        return f'<figure class="figure">{tag}</figure>'

    return re.sub(r"<picture>.*?</picture>", light_only, rendered, flags=re.S)


def externalize_links(rendered: str) -> str:
    """Send outbound citations to a new tab; leave in-page anchors alone."""
    return re.sub(
        r'<a href="(https?://[^"]+)"',
        r'<a href="\1" target="_blank" rel="noopener noreferrer"',
        rendered,
    )


def render(
    markdown_text: str,
    asset_prefix: str = ASSET_PREFIX,
    document_id: str = "formulation",
) -> str:
    """Markdown with mathematics in, one finished HTML fragment out."""
    from markdown_it import MarkdownIt

    work, formulas = extract_math(drop_authored_contents(markdown_text))
    rendered = MarkdownIt("commonmark").enable(["table", "strikethrough"]).render(work)
    rendered = restore_math(rendered, formulas)
    rendered, headings = add_heading_anchors(rendered)
    rendered = collapse_pictures(rendered, asset_prefix)
    rendered = externalize_links(rendered)
    return f'<article class="formulation">{build_toc(headings, document_id)}{rendered}</article>'


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="render_formulation")
    parser.add_argument(
        "document",
        nargs="?",
        choices=sorted(DOCUMENTS),
        help="which committed document to render; both by default",
    )
    parser.add_argument("--source", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--asset-prefix", default=ASSET_PREFIX)
    args = parser.parse_args(argv)

    if args.source or args.out:
        if not (args.source and args.out):
            parser.error("--source and --out are given together or not at all")
        pairs = [(args.source, args.out)]
    elif args.document:
        pairs = [DOCUMENTS[args.document]]
    else:
        pairs = list(DOCUMENTS.values())

    for source, out in pairs:
        fragment = render(
            source.read_text(encoding="utf-8"), args.asset_prefix, document_id=out.stem
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(fragment, encoding="utf-8")
        print(f"{source} -> {out}  ({len(fragment):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
