"""The presentation page — one document carrying the problem, the measures, and the design.

The served tree lives beside the server rather than at the repository root, so the
document root is found from ``__file__`` and never from the working directory: the page
serves identically wherever ``python -m simulator gui`` is invoked from.

Two roots, because they are populated differently.  ``STATIC_ROOT`` holds what this
package owns — the authored page, styles, scripts, the committed document fragments,
and authored walkthrough fragments.  Embedded illustration HTML lives under
``resources/html/`` (see AGENTS.md), not here.  ``FIGURE_ROOT`` is the explainer assets,
which are not copied here: the document that references them is the same file the
repository ships, so the server maps its ``figures/`` prefix onto ``resources/`` and
both readers see one set of figures.
"""

from __future__ import annotations

from pathlib import Path

#: The authored page and the pre-rendered formulation.
STATIC_ROOT = Path(__file__).resolve().parent / "static"

#: Explainer assets, served under the page's ``figures/`` prefix.
FIGURE_ROOT = Path(__file__).resolve().parents[2] / "resources"

#: Loopback, and not as a default that something else may widen (12.2.1): the page is a
#: local reading surface, and the process that serves it is reachable only from the
#: machine running it.
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
