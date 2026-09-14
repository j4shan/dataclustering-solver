"""The presentation page — one document carrying the problem, the measures, and the design.

**The repository tree is the site tree.**  `site/` is what this server hands over and what
a publish step copies, unchanged, so the directory layout on disk is the URL layout in the
browser and a path that resolves for a reader of the repository resolves for a reader of
the page.  There is one root and no mapping: what is not in `site/` cannot be requested,
which is what keeps diagram sources and figure prompts — `resources/`, never served —
out of a public deployment by construction rather than by an exclude list someone has to
maintain.

The root is found from ``__file__`` and never from the working directory, so the page
serves identically wherever ``python -m simulator gui`` is invoked from.  It sits outside
this package deliberately: the exhibit is authored material, not code that ships with the
module.
"""

from __future__ import annotations

from pathlib import Path

#: The served tree, and the published tree: the page, its assets, and its figures.
SITE_ROOT = Path(__file__).resolve().parents[2] / "site"

#: Explainer assets, under the page's own ``figures/`` path rather than a mounted alias.
FIGURE_ROOT = SITE_ROOT / "figures"

#: Loopback, and not as a default that something else may widen (12.2.1): the page is a
#: local reading surface, and the process that serves it is reachable only from the
#: machine running it.
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
