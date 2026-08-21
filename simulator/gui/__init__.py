"""The demonstration GUI — one page carrying the problem, a run, and the design.

The served tree lives beside the server rather than at the repository root, so the
document root is found from ``__file__`` and never from the working directory: the page
serves identically wherever ``python -m simulator gui`` is invoked from.

Two roots, because they are populated differently.  ``STATIC_ROOT`` holds what this
package owns — the authored page, styles, scripts, and the documents pre-rendered by
``tools/render_formulation.py``.  Embedded illustration HTML lives under
``resources/graphics/`` (9.16), not here.  ``FIGURE_ROOT`` is the explainer assets,
which are not copied here: the document that references them is the same file the
repository ships, so the server maps its ``figures/`` prefix onto ``resources/`` and
both readers see one set of figures.

**One image, two deployments** (10.3.12).  The same process serves a reader's laptop and
a public instance behind a front door; what differs between them arrives in the
environment, never in a second code path.  :class:`Deployment` is that environment, read
once, and everything downstream takes it as an argument.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

#: The authored page and the pre-rendered formulation.
STATIC_ROOT = Path(__file__).resolve().parent / "static"

#: Explainer assets, referenced by ``tools/render_formulation.ASSET_PREFIX``.
FIGURE_ROOT = Path(__file__).resolve().parents[2] / "resources"

#: Loopback is the *default*, not the requirement (12.2.1): a demonstration is reachable
#: only from the machine running it, and a deployed instance binds what its platform
#: hands it.  What keeps the deployed one private is the front door (12.2.15), because a
#: managed platform gives every service a public hostname whatever it binds.
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765

#: How a launcher tells this server apart from anything else holding the port (12.2.9).
#: Both halves import it from here so the signature cannot drift between the process that
#: publishes it and the probe that checks it.
SERVICE = "dataclustering-simulator-gui"
HEALTH_PATH = "/api/health"

#: 12.2.16 — what a listing page reads to present this instance without holding a copy
#: of the description that can go stale.
DESCRIPTOR_PATH = "/exhibit.json"

#: 12.2.15 — presented by the front door on every request it forwards.  The value is
#: configuration; only the header's name is public.
FRONT_DOOR_HEADER = "x-navigator-origin"


@dataclass(frozen=True)
class Deployment:
    """Everything that differs between a laptop and a public instance.

    Read from the environment rather than from flags, because the platform is what
    supplies it and no reader ever types any of it.  Every field has a default that
    describes the local demonstration, so an unset environment is the laptop.
    """

    #: Where the socket binds.  Loopback locally; whatever the platform requires when
    #: it routes to the container itself.
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT

    #: The path prefix the front door strips before forwarding, e.g. ``/dataclustering``.
    #: Empty when this instance is the whole origin.
    #:
    #: **It is not a routing input.**  The front door strips it, so what arrives here is
    #: already the path the routes are declared at, and the application stays agnostic
    #: about where it is mounted — which is 12.2.13's rule read literally.  Handing it to
    #: the ASGI framework as a *root path* would be the opposite: the framework would then
    #: expect the prefix to still be on the request and would strip it a second time,
    #: 404ing every asset under a nested mount.  What the prefix is for is naming this
    #: instance — the identifier a listing page keys it by (12.2.16), and, through
    #: ``public_base``, the policy that keeps it apart from its siblings (12.6.5.3).
    mount_prefix: str = ""

    #: The absolute URL of this instance's mount point, e.g.
    #: ``https://theses.example.com/dataclustering/``.  Empty locally, where the instance
    #: is the whole origin and ``'self'`` already names exactly it (12.6.5.3).
    public_base: str = ""

    #: 12.2.15 — the shared secret the front door presents.  Empty disables the check,
    #: which is the local demonstration: there is no front door to be bypassed.
    front_door_secret: str = ""

    @classmethod
    def from_environment(cls, environ=None) -> "Deployment":
        """The deployment this process is running as.

        `PORT` is spelt without a prefix because that is the name every managed platform
        supplies it under; the rest are namespaced so they cannot collide with anything
        else in a container.
        """
        env = os.environ if environ is None else environ

        def text(name: str, fallback: str) -> str:
            return (env.get(name) or "").strip() or fallback

        mount_prefix = text("GUI_MOUNT_PREFIX", "").rstrip("/")
        if mount_prefix and not mount_prefix.startswith("/"):
            mount_prefix = f"/{mount_prefix}"

        return cls(
            host=text("GUI_HOST", DEFAULT_HOST),
            port=int(text("PORT", str(DEFAULT_PORT))),
            mount_prefix=mount_prefix,
            public_base=text("GUI_PUBLIC_BASE", ""),
            front_door_secret=text("GUI_FRONT_DOOR_SECRET", ""),
        )

    @property
    def exhibit_id(self) -> str:
        """The identifier the navigator keys this exhibit by (12.2.16).

        It **is** the mount prefix rather than a second name kept beside it, which is what
        makes it unique across everything sharing the domain and impossible to drift from
        the URL it names.
        """
        return self.mount_prefix.lstrip("/") or "dataclustering"
