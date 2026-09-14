"""Assemble the published copy of the page into `build/` (12.2.14).

    python3 tools/publish.py [--out build]

**What this does and does not do.**  It copies `site/` and inlines each mounted fragment
into the document that mounts it.  It does not minify, bundle, transpile, or rewrite a
URL: every file that lands in the output is a file the repository committed, byte for
byte, except the one document whose panes were filled in (10.3.5).

**Why the inlining is the point.**  On the local server the shell fetches its eleven
fragments at load, which is invisible to a reader and keeps each fragment editable on its
own.  A public URL is read by things that do not run script — a link preview, a crawler,
a reader who turned it off — and all of them receive the file the host sends.  That file
has to be the argument, not an empty shell.

**Why the fragments do not ship.**  Once inlined they are duplicates, and a duplicate at
its own URL is a second copy of part of the page competing with it.  For the illustration
fragments it is a broken copy: opened standalone, their figures resolve against the wrong
directory and every image fails.  Dropping them from the output removes the URL rather
than fixing what it renders.

`resources/` is never read here.  The authoring material — diagram sources, figure
prompts, the scenario data — is outside the served tree by construction, so no exclude
list exists to fall out of date.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"

#: The attribute naming a fragment, and the placeholder text the fragment replaces.
MOUNT = re.compile(r'<(?P<tag>\w+)(?P<attrs>[^>]*?)\sdata-mount="(?P<src>[^"]+)"(?P<rest>[^>]*)>')


def closing_index(text: str, tag: str, start: int) -> int:
    """Where the element opened at `start` closes, counting nested tags of the same name.

    A pane body holds a paragraph today, but the rule has to survive a pane that holds a
    div, so this counts rather than finding the first close.
    """
    depth = 1
    position = start
    pattern = re.compile(rf"<(/?){tag}\b", re.IGNORECASE)
    while depth:
        found = pattern.search(text, position)
        if found is None:
            raise SystemExit(f"unclosed <{tag}> in the shell")
        depth += -1 if found.group(1) else 1
        position = found.end()
    return text.rindex(f"</{tag}", 0, position)


def inline(document: str, source: Path) -> tuple[str, list[str]]:
    """Replace every `data-mount` pane's body with the fragment it names.

    The attribute goes with it: left in place, the script would fetch the fragment again
    and overwrite what was just inlined.
    """
    mounted: list[str] = []
    while (found := MOUNT.search(document)) is not None:
        fragment = source / found.group("src")
        if not fragment.is_file():
            raise SystemExit(f"mounted fragment is missing: {found.group('src')}")
        mounted.append(found.group("src"))
        tag = found.group("tag")
        opening = f"<{tag}{found.group('attrs')}{found.group('rest')}>"
        close = closing_index(document, tag, found.end())
        document = (
            document[: found.start()]
            + opening
            + "\n"
            + fragment.read_text().strip()
            + "\n"
            + document[close:]
        )
    return document, mounted


def publish(out: Path) -> int:
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out)

    index = out / "index.html"
    document, mounted = inline(index.read_text(), out)
    if not mounted:
        raise SystemExit("no fragment was mounted — the shell changed shape")
    index.write_text(document)

    # Every inlined fragment is now a duplicate of part of the page, at a URL of its own.
    # For an illustration fragment that URL is also broken — its figures resolve against
    # the wrong directory when it is opened standalone — so removing the file removes the
    # URL rather than leaving a worse copy of the page for a crawler to find.
    for fragment in mounted:
        (out / fragment).unlink()
    for empty in sorted(out.rglob("*"), reverse=True):
        if empty.is_dir() and not any(empty.iterdir()):
            empty.rmdir()

    files = sorted(path for path in out.rglob("*") if path.is_file())
    weight = sum(path.stat().st_size for path in files)
    print(f"inlined {len(mounted)} fragments into index.html")
    for name in mounted:
        print(f"    {name}")
    # Relative while the output is inside the repository, which is the ordinary case;
    # absolute when it is not, because a test publishes into a temporary directory.
    where = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out
    print(f"\n{len(files)} files, {weight / 1_000_000:.1f} MB → {where}/")
    print("upload that directory, or point the host's output directory at it")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "build",
        help="directory to write (default: build/, replaced if it exists)",
    )
    return publish(parser.parse_args(argv).out.resolve())


if __name__ == "__main__":
    sys.exit(main())
