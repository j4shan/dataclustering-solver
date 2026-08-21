"""What a public instance must do that a laptop need not (12.2.13–12.2.16, 12.6.5.3).

Every clause here exists because this exhibit stopped being the only thing on its origin.
The tests are split from `test_gui_server.py` for the same reason: that file asks what
the interface does, and this one asks what survives being mounted under a path prefix,
behind a front door, beside siblings.
"""

from __future__ import annotations

import json
import os
import re
import threading
import urllib.error
import urllib.request
from http import HTTPStatus

import pytest

from conftest import REPO_ROOT
from simulator.gui import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    DESCRIPTOR_PATH,
    FIGURE_ROOT,
    HEALTH_PATH,
    SERVICE,
    STATIC_ROOT,
    Deployment,
)
from simulator.gui import api
from simulator.gui.server import (
    Application,
    build_server,
    content_security_policy,
)
from simulator.providers import synthetic

SECRET = "a-front-door-secret"


@pytest.fixture(scope="module")
def catalog_document():
    """The smallest catalogue a server can serve.

    Hand-built rather than generated: what this module tests is the deployment shell —
    the front door, the policy, the descriptor, the environment — and none of it reads a
    figure. `tests/test_catalog.py` is what holds the document's shape to the generator,
    so a stub here is the smallest instance of that shape and not a second definition.
    """
    return {
        "catalog_version": 1,
        "batch_id": "deployfixture",
        "corpus": {
            "dataset_id": "deployment-corpus",
            "event_count": 2_000,
            "query_count": 12,
            "feature_columns": [],
        },
        "baseline": {"strategy": "insertion_order", "capacities": [1000]},
        "strategies": [],
        "rows": [],
    }


@pytest.fixture(scope="module")
def deployed(catalog_document):
    """An instance running as a public one: mounted, behind a front door, beside others."""
    deployment = Deployment(
        host="127.0.0.1",
        port=0,
        mount_prefix="/dataclustering",
        public_base="https://exhibits.example.com/dataclustering/",
        front_door_secret=SECRET,
    )
    server = build_server(catalog=catalog_document, deployment=deployment)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def fetch(url: str, secret: str | None = SECRET):
    """One request, carrying the front door's secret unless a test withholds it."""
    request = urllib.request.Request(
        url, headers={} if secret is None else {"X-Navigator-Origin": secret}
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as failure:
        return failure.status, failure.read(), dict(failure.headers)


# -- 12.2.13  addressing --------------------------------------------------------------

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
    — a comment reading "from /api/catalog" describes a route rather than fetching one, and
    a check that flagged it would be checking English.
    """
    return [
        found.group(1) or found.group(2) for found in ROOT_ABSOLUTE.finditer(text)
    ]

#: Every document this process serves that a person authored or a generator wrote.
SERVED = sorted(
    [*STATIC_ROOT.rglob("*.html"), *STATIC_ROOT.rglob("*.js"), *STATIC_ROOT.rglob("*.css")]
    + [*FIGURE_ROOT.rglob("*.html"), *FIGURE_ROOT.rglob("*.svg")]
)


def test_the_inventory_of_served_documents_is_not_empty():
    """A scan that found nothing would pass the next test for the wrong reason."""
    assert len(SERVED) > 5


@pytest.mark.parametrize("document", SERVED, ids=lambda p: p.name)
def test_no_served_document_addresses_the_site_root(document):
    """12.2.13 — nothing this page emits may reach above its own mount point.

    Under `/dataclustering/`, a leading slash leaves this exhibit entirely and lands in the
    landing page's namespace: the figures 404 and the benchmark posts somewhere that is
    not this exhibit.  The rule is checked here rather than remembered, because the next
    person to write a URL into a page will not have read this docstring.
    """
    offending = root_absolute(document.read_text(encoding="utf-8"))
    assert offending == [], f"{document.name} addresses the site root: {offending}"


def test_a_relative_fetch_resolves_under_the_mount_point(deployed):
    """12.2.13 — the addressing the page uses is addressing this server answers.

    `api/catalog` beside a document at `/dataclustering/` is `/dataclustering/api/catalog`
    at the browser, and the prefix the front door strips brings it back to `/api/catalog`
    here.  What this asserts is the other end of that: the path the front door forwards is
    the path the routes are declared at.
    """
    status, body, _ = fetch(f"{deployed}/api/catalog")
    assert status == HTTPStatus.OK
    assert json.loads(body)["corpus"]["event_count"] == 2_000


# -- 12.6.5.3  the policy under a shared origin ---------------------------------------


def test_the_policy_names_this_instances_own_mount_point():
    """12.6.5.3 — `'self'` stops isolating once the origin holds siblings."""
    deployed = Deployment(public_base="https://exhibits.example.com/dataclustering/")
    policy = content_security_policy(deployed)
    for directive in ("default-src", "script-src", "img-src", "connect-src"):
        assert f"{directive} https://exhibits.example.com/dataclustering/" in policy
    assert "'self'" not in policy


def test_an_instance_that_is_the_whole_origin_still_says_self():
    """12.6.5.3 — `'self'` *is* the mount point when nothing else shares the origin.

    A laptop has no front door and no siblings, so naming an absolute URL there would be
    a narrower statement about nothing, and one that breaks the moment the port changes.
    """
    policy = content_security_policy(Deployment())
    assert "default-src 'self'" in policy


def test_the_policy_travels_on_the_deployed_responses(deployed):
    """12.6.5.1 — enforced by the browser, which means it has to be on the response."""
    _, _, headers = fetch(f"{deployed}/")
    assert "exhibits.example.com/dataclustering/" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"


# -- 12.2.15  the front door is the only way in ---------------------------------------


def test_a_request_that_did_not_come_through_the_front_door_is_refused(deployed):
    """12.2.15 — the platform hostname must answer nothing useful.

    Reaching the container directly would bypass the path prefix, the trailing-slash
    redirect and the rate limit, so the shared secret is what makes the front door the
    only route that works.
    """
    for path in ("/", "/api/catalog", DESCRIPTOR_PATH):
        status, body, _ = fetch(f"{deployed}{path}", secret=None)
        assert status == HTTPStatus.NOT_FOUND
        assert json.loads(body) == {"error": "no such resource"}


def test_the_wrong_secret_is_refused_exactly_as_no_secret_is(deployed):
    """12.2.15 — a different answer for a wrong secret tells a prober there is one."""
    status, body, _ = fetch(f"{deployed}/api/catalog", secret="not-the-secret")
    assert status == HTTPStatus.NOT_FOUND
    assert json.loads(body) == {"error": "no such resource"}


def test_the_readiness_probe_reaches_a_deployed_instance_without_the_secret(deployed):
    """12.2.15 — the one exemption, without which no deployed instance is ever ready.

    A platform probes readiness from an internal address and has no way to present the
    secret.  Refusing it would take the service down rather than defend it: the instance
    serves perfectly and is restarted forever for failing a check it cannot pass.
    """
    status, body, _ = fetch(f"{deployed}{HEALTH_PATH}", secret=None)
    assert status == HTTPStatus.OK
    assert json.loads(body)["service"] == SERVICE


def test_the_exempt_answer_withholds_what_identifies_the_instance(deployed):
    """12.2.15 — the exemption is safe only because the exempt answer is reduced.

    The probe asks whether this is up.  The process id, the dataset and the start time
    answer a question it did not ask, and an unauthenticated caller on the platform
    hostname is exactly who must not be told them.  The signature stays: it names the
    software, never this instance.
    """
    exempt = json.loads(fetch(f"{deployed}{HEALTH_PATH}", secret=None)[1])
    assert exempt == {"service": SERVICE}

    through = json.loads(fetch(f"{deployed}{HEALTH_PATH}")[1])
    assert through["pid"] and through["dataset_id"] and through["started"]


def test_the_exemption_is_readiness_alone(deployed):
    """12.2.15 — one endpoint, not a hole the rest of the surface fits through."""
    for path in (DESCRIPTOR_PATH, "/api/catalog"):
        assert fetch(f"{deployed}{path}", secret=None)[0] == HTTPStatus.NOT_FOUND


def test_a_launcher_is_told_everything_it_needs_to_recognise_an_instance(catalog_document):
    """12.2.9 — the reduction never reaches the local launcher.

    A laptop has no front door, so no request is ever the exempt one, and 12.2.8's probe
    still gets the pid it needs to address a shutdown.
    """
    server = build_server(host=DEFAULT_HOST, port=0, catalog=catalog_document)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}{HEALTH_PATH}"
        answered = json.loads(fetch(url, secret=None)[1])
        assert answered["service"] == SERVICE
        assert answered["pid"] == os.getpid()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_a_laptop_has_no_front_door_to_come_through(catalog_document):
    """12.2.15 — the check is off where there is nothing to bypass."""
    server = build_server(host=DEFAULT_HOST, port=0, catalog=catalog_document)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/api/catalog"
        status, _, _ = fetch(url, secret=None)
        assert status == HTTPStatus.OK
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


# -- 12.2.16  self-description --------------------------------------------------------


def test_the_descriptor_says_what_this_instance_is(deployed):
    """12.2.16 — a listing page renders from this rather than from a copy of it."""
    status, body, _ = fetch(f"{deployed}{DESCRIPTOR_PATH}")
    assert status == HTTPStatus.OK
    described = json.loads(body)
    assert set(described) == {"id", "title", "claim", "tags", "version"}
    assert described["title"]
    assert described["claim"]
    assert described["tags"]


def test_the_identifier_is_the_mount_prefix_rather_than_a_second_name(deployed):
    """12.2.16 — one string, so it cannot drift from the URL it names."""
    _, body, _ = fetch(f"{deployed}{DESCRIPTOR_PATH}")
    assert json.loads(body)["id"] == "dataclustering"
    assert Deployment(mount_prefix="/something-else").exhibit_id == "something-else"


# -- 12.2.4  a request that costs nothing to serve ------------------------------------
#
# What stood here: four tests over an admission semaphore and a wall-clock ceiling, both
# of which existed because a request could ask this process to score twenty layouts.
# 12.2.14 and the ceiling in 12.2.4 were deleted along with that request. What replaces
# them is the far simpler claim below — that there is no longer any per-request work to
# bound — which is the whole reason the redesign lowers what a deployed instance costs.


def test_serving_a_request_needs_no_admission_bound(catalog_document):
    """12.2.4 — a request returns a held document, so it has no cost to meter.

    Asserted structurally: the application holds no lock and no ceiling, because there is
    no work for either to guard. A semaphore reappearing here would mean something in the
    request path had started doing work again.
    """
    application = Application(catalog=catalog_document)
    held = set(vars(application))
    assert "evaluating" not in held
    assert not any("second" in name or "ceiling" in name for name in held)


def test_the_deployment_declares_no_evaluation_ceiling():
    """12.2.4 — nothing to time out, so nothing configures a timeout."""
    assert not hasattr(Deployment(), "evaluate_seconds")


def test_the_process_can_reach_no_scoring_code_at_all():
    """12.2.5, 10.3.1 — the prohibition is structural, not a matter of discipline.

    The serving package must not import the harness even transitively, because the
    exhibit install does not carry it: an import added here would fail on the deployed
    image rather than merely violating a rule.
    """
    import subprocess
    import sys

    probe = (
        "import sys, simulator.gui.server, simulator.gui.api;"
        "heavy=[m for m in ('numpy','pyarrow','matplotlib') if m in sys.modules];"
        "print(','.join(heavy))"
    )
    finished = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=True
    )
    assert finished.stdout.strip() == "", "the GUI package pulled in the harness"


# -- 10.3.12  the image itself -------------------------------------------------------
#
# The Dockerfile is a deliverable (10.3.12) and nothing else in the suite reads it, so the
# claims 10.3.12.1 makes about it are asserted here. They are the claims that matter for
# what a 24/7 instance costs, and all three are invisible from inside a running process.

DOCKERFILE = (REPO_ROOT / "Dockerfile").read_text()
DOCKERIGNORE = (REPO_ROOT / ".dockerignore").read_text()


def test_the_image_installs_no_harness():
    """10.3.1, 12.2.5 — the serving process carries no library that could score.

    A `[harness]` here would put 174 MB of numeric wheels into an image whose process is
    forbidden to use them, and would quietly make 12.2.5 a matter of discipline again.
    """
    installs = [line for line in DOCKERFILE.splitlines() if "pip install" in line]
    assert installs, "the image must install the package"
    for line in installs:
        assert "harness" not in line, line
        for library in ("numpy", "pyarrow", "matplotlib"):
            assert library not in line, line


def test_the_image_carries_no_corpus():
    """10.3.12.1 — the corpus is a versioned external asset and never enters the image."""
    copied = [line for line in DOCKERFILE.splitlines() if line.startswith("COPY")]
    assert copied
    for line in copied:
        assert "data/generated" not in line, line
    assert "simulator generate" not in DOCKERFILE


def test_the_catalog_is_a_build_input_the_image_copies():
    """10.3.12.1 — an absent catalogue fails the build rather than serving blanks."""
    assert any(
        "strategy-catalog.json" in line and line.startswith("COPY")
        for line in DOCKERFILE.splitlines()
    )


def test_the_build_context_does_not_exclude_the_catalog():
    """10.3.12.1 — `data/` is excluded, and this is the one thing under it that is not.

    The catalogue is generated rather than committed, so the build context is its only
    route into the image: an un-negated `data/` would exclude it and fail the COPY above.
    """
    assert "data/" in DOCKERIGNORE
    assert "!data/catalog/strategy-catalog.json" in DOCKERIGNORE


# -- the environment is the only difference -------------------------------------------


def test_an_unset_environment_is_the_laptop():
    """10.3.12 — one image, and the defaults describe the local demonstration."""
    laptop = Deployment.from_environment({})
    assert laptop == Deployment()
    assert laptop.host == DEFAULT_HOST
    assert laptop.port == DEFAULT_PORT
    assert laptop.front_door_secret == ""


def test_the_platform_supplies_the_deployment_rather_than_a_second_code_path():
    """10.3.12 — bind address, port and mount prefix all arrive in the environment."""
    container = Deployment.from_environment(
        {
            "GUI_HOST": "0.0.0.0",
            "PORT": "10000",
            "GUI_MOUNT_PREFIX": "dataclustering/",
            "GUI_PUBLIC_BASE": "https://exhibits.example.com/dataclustering/",
            "GUI_FRONT_DOOR_SECRET": SECRET,
        }
    )
    assert container.host == "0.0.0.0"
    assert container.port == 10_000
    # Normalised on the way in, so a route configured with or without the slashes lands
    # on the same prefix and the same identifier.
    assert container.mount_prefix == "/dataclustering"
    assert container.exhibit_id == "dataclustering"
