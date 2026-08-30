"""The GUI's HTTP surface (12.2).

Every test here issues a **real request against a real bound socket** on port 0.  That is
what 12.2.6 is for: the interface is JSON over HTTP precisely so the whole of Section B's
behaviour can be checked without a browser, and a test that called the handler's methods
directly would be checking something the page never does.
"""

from __future__ import annotations

import http.client
import json
import os
import re
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http import HTTPStatus
from urllib.parse import urlparse

import pytest

from simulator.bench import metrics
from simulator.core import dataset as dataset_module
from simulator.gui import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    FIGURE_ROOT,
    HEALTH_PATH,
    SERVICE,
    STATIC_ROOT,
)
from simulator.gui.server import MAX_REQUEST_BYTES, Application, build_server
from simulator.providers import synthetic
from simulator.providers.synthetic import DatasetConfig


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    """The corpus the catalogue is built from — not something the server ever sees."""
    config = DatasetConfig(
        name="server-corpus",
        n_events=2_000,
        n_transaction_days=60,
        n_query_days=12,
        half_life_days=5.0,
        seed=90,
    )
    return dataset_module.load(
        synthetic.generate(config, tmp_path_factory.mktemp("server"))
    )


@pytest.fixture(scope="module")
def catalog_document(corpus, tmp_path_factory):
    """A small catalogue, built the way the shipped one is (8.11).

    Built rather than hand-written, so what the server serves in these tests is a real
    document from the real generator — a fixture that drifted from the generator's output
    would let the server pass against a shape nothing produces.
    """
    from simulator.bench import catalog, metrics

    original = metrics.DEFAULT_DIR
    metrics.DEFAULT_DIR = tmp_path_factory.mktemp("server-metrics")
    try:
        return catalog.build(
            corpus,
            definition=(
                catalog.Entry("as-1", "AS-1", ("brand_id",)),
                catalog.Entry("as-2", "AS-2", ("brand_id", "feature_price_tier > 5")),
            ),
            capacities=(250, 1000),
        )
    finally:
        metrics.DEFAULT_DIR = original


@pytest.fixture(scope="module")
def server_url(catalog_document):
    """A live server on an ephemeral port, torn down with the module."""
    server = build_server(host="127.0.0.1", port=0, catalog=catalog_document)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def fetch(url: str, payload=None):
    """One request, returning `(status, body)` whether it succeeded or not."""
    request = urllib.request.Request(
        url,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={} if payload is None else {"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as failure:
        return failure.status, failure.read(), dict(failure.headers)


def fetch_json(url: str, payload=None):
    status, body, _ = fetch(url, payload)
    return status, json.loads(body)


# -- how it binds -------------------------------------------------------------------


def test_it_binds_loopback_by_default():
    """13.1 — one user, no trust boundary, and nothing reachable off the machine."""
    assert DEFAULT_HOST == "127.0.0.1"
    server = build_server(port=0)
    try:
        assert server.server_address[0] == "127.0.0.1"
    finally:
        server.server_close()


def test_the_catalog_is_read_before_the_first_request(server_url, catalog_document):
    """12.2.3 — the server holds a parsed document, it does not read one per request."""
    status, body = fetch_json(f"{server_url}/api/catalog")
    assert status == HTTPStatus.OK
    assert body["corpus"]["dataset_id"] == catalog_document["corpus"]["dataset_id"]
    assert body["corpus"]["event_count"] == catalog_document["corpus"]["event_count"]


# -- JSON endpoints -----------------------------------------------------------------


def test_the_catalog_endpoint_carries_what_a_figure_must_be_read_against(server_url):
    """12.4.3.3 — a number is never detached from the corpus that produced it."""
    _, body = fetch_json(f"{server_url}/api/catalog")
    assert set(body["corpus"]) >= {
        "dataset_id",
        "event_count",
        "query_count",
        "selection_log_rows",
        "feature_columns",
    }


def test_the_catalog_is_served_exactly_as_it_was_built(server_url, catalog_document):
    """12.2.5 — the server shapes nothing, because 8.11.1 already shaped it."""
    _, body = fetch_json(f"{server_url}/api/catalog")
    assert body == catalog_document


def test_the_feature_columns_come_through_for_the_panel_to_list(server_url):
    """12.4.2.3 — listed from the document, so the process needs no corpus (12.2.3)."""
    _, body = fetch_json(f"{server_url}/api/catalog")
    columns = body["corpus"]["feature_columns"]
    assert columns and all("family" in column for column in columns)


def test_the_catalog_carries_the_rows_and_the_structure_the_page_draws(server_url):
    """8.11.1 — one document answers every question Section B can ask."""
    _, body = fetch_json(f"{server_url}/api/catalog")
    assert body["rows"], "P2 and P3 are drawn from these"
    assert body["strategies"], "the panel and P1 are drawn from these"
    for entry in body["strategies"]:
        assert {"id", "label", "expressions", "stages", "leaf_count", "capacities"} <= set(entry)


def test_section_b_needs_exactly_one_request(server_url):
    """12.2.6 — the whole of Section B's server-side surface is this GET.

    The three endpoints the builder needed — a dataset summary, a family schema, and the
    evaluation itself — are gone, and nothing replaced them but this.
    """
    for retired in ("/api/dataset", "/api/family", "/api/strategies", "/api/evaluate"):
        status, _ = fetch_json(f"{server_url}{retired}")
        assert status == HTTPStatus.NOT_FOUND, retired


def test_the_health_endpoint_identifies_the_process_holding_the_port(
    server_url, catalog_document
):
    """12.2.9 — a launcher recognises this server by what the server says it is."""
    status, body = fetch_json(f"{server_url}{HEALTH_PATH}")
    assert status == HTTPStatus.OK
    assert body["service"] == SERVICE
    assert body["pid"] == os.getpid()
    # The corpus the *catalogue* was built against — this process never loaded one.
    assert body["dataset_id"] == catalog_document["corpus"]["dataset_id"]


def test_health_carries_a_start_time_a_reader_can_be_shown(server_url):
    """12.2.9 — 'up 12m' beside a running instance comes from this field."""
    _, body = fetch_json(f"{server_url}{HEALTH_PATH}")
    began = datetime.fromisoformat(body["started"])
    assert began.tzinfo is not None
    assert began <= datetime.now(timezone.utc)


def test_a_malformed_body_is_a_bad_request_not_a_traceback(server_url):
    target = f"{server_url}/api/dataset"
    request = urllib.request.Request(target, data=b"{not json", method="POST")
    try:
        with urllib.request.urlopen(request) as response:
            status = response.status
    except urllib.error.HTTPError as failure:
        status = failure.status
    assert status in (HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND)


# -- guardrails ---------------------------------------------------------------------


def test_a_body_over_the_ceiling_is_refused(server_url):
    """12.2.12 — an oversized request is a refusal, not an allocation.

    Refusing *before* reading leaves the client mid-upload, so it may meet a closed socket
    instead of the 413 — which is what early rejection costs and what every server that
    does it produces. Either outcome is the refusal; what must never happen is a 200.
    """
    oversized = b"x" * (MAX_REQUEST_BYTES + 1)
    request = urllib.request.Request(
        f"{server_url}/api/anything",
        data=oversized,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            status = response.status
    except urllib.error.HTTPError as refused:
        status = refused.status
    except urllib.error.URLError:
        status = HTTPStatus.REQUEST_ENTITY_TOO_LARGE  # closed on us, mid-write
    assert status == HTTPStatus.REQUEST_ENTITY_TOO_LARGE


def test_a_dishonest_content_length_is_not_trusted(server_url):
    """12.2.12 — the declared length is refused before anything is read on its word."""
    connection = http.client.HTTPConnection(urlparse(server_url).netloc, timeout=5)
    connection.putrequest("POST", "/api/anything")
    connection.putheader("Content-Type", "application/json")
    connection.putheader("Content-Length", str(1 << 40))  # a declared terabyte
    connection.endheaders()
    try:
        assert connection.getresponse().status == HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    finally:
        connection.close()


def test_every_response_carries_the_security_headers(server_url):
    """12.6.5.1 — 12.2.2 enforced by the browser, not only asserted in a test."""
    for path in ("/", "/api/family", "/no-such-file.html"):
        _, _, headers = fetch(f"{server_url}{path}")
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert "default-src 'self'" in headers["Content-Security-Policy"]


def test_the_policy_admits_no_inline_script(server_url):
    """12.6.5.1 — the load-bearing directive stays strict; both scripts are files."""
    _, _, headers = fetch(f"{server_url}/")
    directives = dict(
        part.strip().split(" ", 1)
        for part in headers["Content-Security-Policy"].split(";")
        if " " in part.strip()
    )
    assert "'unsafe-inline'" not in directives["script-src"]
    assert "'unsafe-eval'" not in directives["script-src"]
    assert directives["connect-src"] == "'self'"


def test_no_route_accepts_reader_supplied_text_at_all(server_url):
    """12.4.2.5, 12.6.5.2 — Section B sends no request carrying reader input.

    The bound that used to sit on a block name is not merely unenforced now, there is
    nothing left to bound: every route is a GET taking no parameters, so the seam has no
    reader-supplied string to accept, echo, or refuse.
    """
    from simulator.gui.server import Application

    application = Application(catalog={})
    assert all(method == "GET" for method, _ in application.routes)


# -- static assets ------------------------------------------------------------------


def test_it_serves_the_pre_rendered_formulation(server_url):
    status, body, headers = fetch(f"{server_url}/formulation.html")
    assert status == HTTPStatus.OK
    assert headers["Content-Type"] == "text/html; charset=utf-8"
    assert b"<math" in body  # 12.3.2 — native MathML, no client-side library


def test_html_and_svg_declare_utf8_so_nosniff_does_not_mojibake(server_url):
    """12.6.5.1 — nosniff without a charset leaves a UTF-8 em-dash as Windows-1252.

    The canvases and the selection matrix are opened as their own documents, not
    mounted into index.html (which already declares utf-8). The title of the
    closet canvas is the case: its em-dash is the character that showed as ``â€``.
    """
    _, body, headers = fetch(f"{server_url}/figures/graphics/closet-canvas.html")
    assert headers["Content-Type"] == "text/html; charset=utf-8"
    assert "—".encode() in body
    assert "â€".encode() not in body

    _, _, svg_headers = fetch(f"{server_url}/figures/img/selection-matrix.light.svg")
    assert svg_headers["Content-Type"] == "image/svg+xml; charset=utf-8"


def test_it_serves_the_section_a_illustration(server_url):
    status, body, _ = fetch(f"{server_url}/figures/graphics/section-a-illustration.html")
    assert status == HTTPStatus.OK
    assert b"section_a_medical_cabinet.png" in body
    assert b"section_a_smart_organizer.png" in body


def test_it_serves_the_section_c_illustration(server_url):
    status, body, _ = fetch(f"{server_url}/figures/graphics/section-c-illustration.html")
    assert status == HTTPStatus.OK
    assert b"engine-pruning" in body
    assert b"c-container-activation" in body


def test_it_serves_the_section_d_illustration(server_url):
    status, body, _ = fetch(f"{server_url}/figures/graphics/section-d-illustration.html")
    assert status == HTTPStatus.OK
    assert b"D.lorenz-wealth" in body
    assert b"D.search-trajectory" in body


def test_figures_are_served_from_the_repository_rather_than_a_copy(server_url):
    """One set of figures, two readers — the Markdown host and this page."""
    figure = FIGURE_ROOT / "img" / "container-zoom.light.svg"
    assert figure.exists(), "fixture assumes the generated figures are present"

    status, body, headers = fetch(f"{server_url}/figures/img/container-zoom.light.svg")
    assert status == HTTPStatus.OK
    assert headers["Content-Type"] == "image/svg+xml; charset=utf-8"
    assert body == figure.read_bytes()


def test_a_missing_asset_is_a_clean_404(server_url):
    status, body = fetch_json(f"{server_url}/no-such-file.html")
    assert status == HTTPStatus.NOT_FOUND
    assert "no such asset" in body["error"]


@pytest.mark.parametrize(
    "path",
    [
        "/../pyproject.toml",
        "/../../etc/passwd",
        "/%2e%2e/pyproject.toml",
        "/figures/../../pyproject.toml",
        "/figures/../../../etc/passwd",
        "//etc/passwd",
    ],
)
def test_no_path_escapes_its_document_root(server_url, path):
    """The one thing a loopback server still has to get right.

    Checked on the *resolved* path, so `..`, an encoded `..`, and an absolute path all
    fail identically — and the refusal says nothing about what exists outside the root.
    """
    status, _, _ = fetch(f"{server_url}{path}")
    assert status == HTTPStatus.NOT_FOUND


def test_a_directory_is_not_served_as_a_file(server_url):
    status, _, _ = fetch(f"{server_url}/figures/img")
    assert status == HTTPStatus.NOT_FOUND


def test_an_unknown_post_route_is_a_404(server_url):
    status, body = fetch_json(f"{server_url}/api/nope", payload={})
    assert status == HTTPStatus.NOT_FOUND
    assert "no route for POST" in body["error"]


# -- what it must not do ------------------------------------------------------------


#: What actually causes a browser to fetch something.  An `<a href>` does not: a citation
#: in the formulation's bibliography is a link a reader may choose to follow, not a
#: resource the page loads, and 12.2.2 is about what the page fetches on its own.
FETCHING_ATTRIBUTE = re.compile(
    r"""(?:\bsrc\s*=|<link\b[^>]*?\bhref\s*=|@import\s+|\burl\()\s*['"]?([^'")\s>]+)""",
    re.IGNORECASE,
)


def test_the_served_page_fetches_nothing_from_the_network(server_url):
    """12.2.2 — checkable by reading the file, which is the point of 10.3.5.

    Every asset the server hands out must be self-contained: no CDN script, no remote
    stylesheet, no web font.  A hyperlink in the bibliography is not one of those, and
    a check that flagged it would be checking the wrong requirement.
    """
    for name in ("formulation.html", "figures/graphics/section-a-illustration.html"):
        _, body, _ = fetch(f"{server_url}/{name}")
        fetched = FETCHING_ATTRIBUTE.findall(body.decode())
        remote = [url for url in fetched if url.startswith(("http://", "https://", "//"))]
        assert remote == [], f"{name} would fetch {remote}"


def test_every_asset_the_page_fetches_is_actually_served(server_url):
    """A local reference that 404s is the same failure as a remote one, one step later."""
    _, body, _ = fetch(f"{server_url}/formulation.html")
    referenced = set(FETCHING_ATTRIBUTE.findall(body.decode()))
    assert referenced, "fixture assumes the formulation embeds at least one figure"

    for reference in referenced:
        status, _, _ = fetch(f"{server_url}/{reference.lstrip('/')}")
        assert status == HTTPStatus.OK, f"{reference} is referenced but not served"


def test_the_server_module_computes_nothing_of_its_own():
    """12.2.5 — it routes and shapes responses; the harness computes.

    Checked by what the module can *reach*, not by what its text contains. The bar is
    higher than it was: the server used to be allowed to *delegate* a computation to the
    harness, and now it may not reach the harness at all — 10.3.1 keeps those libraries
    out of the exhibit install, so an import here would fail on the deployed image rather
    than merely breaking a rule.
    """
    import ast

    source = (STATIC_ROOT.parent / "server.py").read_text()
    imported = {
        alias.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        f"{node.module}.{alias.name}"
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
        for alias in node.names
    }
    assert not any("numpy" in name for name in imported)
    assert not any(
        name.endswith((".evaluate", ".run_one", ".summarize_containers"))
        for name in imported
    )


# -- GET /api/catalog (12.4.2, 12.4.3) ----------------------------------------------
#
# What this section used to hold: twenty-odd tests over a POST that took reader-composed
# blocks, validated them, and scored twenty layouts.  All of it moved to
# `tests/test_catalog.py`, where the generator that does that work now lives, and what is
# left here is the far smaller question of whether the server hands the document over
# unchanged.  The shrinkage is the point of the redesign showing up in the test suite.


def test_the_catalogue_carries_the_baseline_and_does_not_list_it_as_an_entry(server_url):
    """12.4.6.5 — the reference the candidates are read against, not a fifth candidate."""
    _, body = fetch_json(f"{server_url}/api/catalog")
    assert body["baseline"]["strategy"] == "insertion_order"
    assert "insertion_order" not in {entry["id"] for entry in body["strategies"]}
    assert any(row["Block"] is None for row in body["rows"])


def test_every_set_is_scored_and_named(server_url):
    """12.4.3.2 — a single number presented without its set name is a defect."""
    _, body = fetch_json(f"{server_url}/api/catalog")
    assert {"training", "validation"} <= {row["Set_Name"] for row in body["rows"]}


def test_the_process_view_gets_the_chain_and_its_splits(server_url):
    """8.11.2 — the panel lists the counts, and 12.4.4.4 keeps capacity out of them."""
    _, body = fetch_json(f"{server_url}/api/catalog")
    for entry in body["strategies"]:
        for stage in entry["stages"]:
            assert set(stage) == {"expression", "splits"}
            assert isinstance(stage["splits"], int)


def test_the_page_can_reach_every_row_a_figure_is_drawn_from(server_url):
    """12.6.4 — every displayed number is traceable to a row the page was handed."""
    _, body = fetch_json(f"{server_url}/api/catalog")
    for row in body["rows"]:
        assert {"Strategy_Name", "Set_Name", "Batch_ID", "Run_ID", "Block"} <= set(row)


def test_the_server_refuses_rather_than_serving_an_empty_section():
    """12.4.2.5 — an instance with no catalogue says so instead of rendering blanks."""
    server = build_server(host="127.0.0.1", port=0, catalog=None)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, body = fetch_json(
            f"http://127.0.0.1:{server.server_address[1]}/api/catalog"
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert status == HTTPStatus.SERVICE_UNAVAILABLE
    assert "catalog" in body["error"]


# -- Section A is reachable end to end (12.3) ---------------------------------------


def test_the_formulation_is_served_at_the_light_variant_only(server_url):
    """12.3.8 — a reader whose system is dark is never served a dark figure."""
    _, body, _ = fetch(f"{server_url}/formulation.html")
    text = body.decode()
    assert "demo_index_table.png" in text
    assert "demo_container_activation.png" in text
    assert ".dark.svg" not in text
    assert "<picture" not in text  # collapsed at pre-render, not switched in the browser


def test_the_formulation_carries_its_own_table_of_contents(server_url):
    """12.3.3 — generated from the document's own headings, not authored beside them."""
    _, body, _ = fetch(f"{server_url}/formulation.html")
    text = body.decode()
    entries = re.findall(r'<li class="toc-h[23]"><a href="#([\w-]+)"', text)
    assert entries
    for anchor in entries:
        assert f'id="{anchor}"' in text


def test_serving_persists_nothing_at_all(server_url, tmp_path, monkeypatch):
    """12.2.7.1, 12.4.3.5 — nothing a reader does reaches storage, because nothing a
    reader does reaches the harness.

    The metric table is where product data would land, so it is where this watches. Under
    the old design a click ran twenty evaluations and the assertion was that none of their
    rows was written; now no request scores anything, and the same assertion holds for a
    stronger reason.
    """
    monkeypatch.setattr(metrics, "DEFAULT_DIR", tmp_path)
    before = sorted(path.name for path in tmp_path.rglob("*"))

    for _ in range(3):
        status, _ = fetch_json(f"{server_url}/api/catalog")
        assert status == HTTPStatus.OK

    assert sorted(path.name for path in tmp_path.rglob("*")) == before
    assert not list(tmp_path.rglob("run_*.csv"))


def test_the_served_rows_are_the_rows_a_sweep_writes(server_url, corpus):
    """8.10 — same primitive, same row schema; only the destination differs.

    Pinned against what `run_one` actually produces rather than a hand-listed subset, so
    a KPI added to the primitive does not quietly stop reaching the page.
    """
    from simulator.bench.runner import add_baseline_lift, run_one

    _, body = fetch_json(f"{server_url}/api/catalog")
    candidate = next(r for r in body["rows"] if r["Strategy_Name"] == "group_by_chain")

    swept = add_baseline_lift(run_one(corpus, "insertion_order", 250, batch_id="w"))[0]
    # `Block` names the catalogue entry and is the one field a sweep does not produce.
    assert set(candidate) - {"Block"} == set(swept)
    assert candidate["Batch_ID"] == body["batch_id"]
    assert candidate["Run_ID"] != candidate["Batch_ID"]
    assert "brand_id" in candidate["Params"]


def test_the_server_keeps_nothing_on_a_readers_behalf(catalog_document):
    """12.2.7 — no session, no cache, no memory of what was asked before.

    Checked structurally rather than by observing behaviour, because the failure this
    guards against is a *convenience* someone adds later: a response cache, a last-result
    field, a per-reader dict. Any of those would show up as an attribute the application
    grew between requests, and on the public deployment 12.2.7 anticipates it would be
    reachable by the next reader along.
    """
    application = Application(catalog=catalog_document)
    before = set(vars(application))

    application.catalog_document(None, {})
    application.health(None, {})
    application.descriptor(None, {})

    assert set(vars(application)) == before
    # Four things are held across requests and none is anyone's in particular: the
    # catalogue read at startup (12.2.3), the moment this process became a server
    # (12.2.9), the deployment it is serving as (10.3.12), and the route table. All are
    # fixed before the first connection and identical for every reader.
    #
    # The admission semaphore that used to sit here is gone with the work it admitted:
    # 12.2.14 was deleted because a request that returns a held document has no cost to
    # bound (12.2.4).
    assert before == {"catalog", "deployment", "routes", "started"}
