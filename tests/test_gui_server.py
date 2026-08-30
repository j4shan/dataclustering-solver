"""The page's HTTP surface (12.2).

Every test here issues a **real request against a real bound socket** on port 0, so what
is checked is what a browser would actually receive: the file, its headers, and the
status — not a helper's return value.
"""

from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.request
from http import HTTPStatus

import pytest

from simulator.gui import DEFAULT_HOST, FIGURE_ROOT, STATIC_ROOT
from simulator.gui.server import build_app, build_server


@pytest.fixture(scope="module")
def server_url():
    """A live server on an ephemeral port, torn down with the module."""
    server = build_server(host="127.0.0.1", port=0)
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
    """12.2.1 — one user, no trust boundary, and nothing reachable off the machine."""
    assert DEFAULT_HOST == "127.0.0.1"
    server = build_server(port=0)
    try:
        assert server.server_address[0] == "127.0.0.1"
    finally:
        server.server_close()


# -- guardrails ---------------------------------------------------------------------


def test_every_response_carries_the_security_headers(server_url):
    """12.6.5 — 12.2.2 enforced by the browser, not only asserted in a test."""
    for path in ("/", "/figures/html/section-gini-illustration.html", "/no-such-file.html"):
        _, _, headers = fetch(f"{server_url}{path}")
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert "default-src 'self'" in headers["Content-Security-Policy"]


def test_the_policy_admits_no_inline_script(server_url):
    """12.6.5 — the load-bearing directive stays strict; both scripts are files."""
    _, _, headers = fetch(f"{server_url}/")
    directives = dict(
        part.strip().split(" ", 1)
        for part in headers["Content-Security-Policy"].split(";")
        if " " in part.strip()
    )
    assert "'unsafe-inline'" not in directives["script-src"]
    assert "'unsafe-eval'" not in directives["script-src"]
    assert directives["connect-src"] == "'self'"


def test_nothing_this_server_answers_takes_reader_supplied_text(server_url):
    """12.6.5 — the page sends no request carrying reader input.

    There is nothing left to bound: the application declares no route of its own, so what
    it answers is a file or a 404, and there is no reader-supplied string for a handler
    to accept, echo, or refuse.
    """
    declared = [route for route in build_app().routes if hasattr(route, "methods")]
    assert declared == []


# -- static assets ------------------------------------------------------------------


def test_it_serves_the_pre_rendered_formulation(server_url):
    status, body, headers = fetch(f"{server_url}/formulation.html")
    assert status == HTTPStatus.OK
    assert headers["Content-Type"] == "text/html; charset=utf-8"
    assert b"<math" in body  # 12.3 — native MathML, no client-side library


def test_html_and_svg_declare_utf8_so_nosniff_does_not_mojibake(server_url):
    """12.6.5 — nosniff without a charset leaves a UTF-8 em-dash as Windows-1252.

    A fragment is fetched as its own document before it is mounted into index.html
    (which already declares utf-8), so the response has to name the encoding itself.
    The em-dash is the character that showed as ``â€``.
    """
    _, body, headers = fetch(f"{server_url}/figures/html/section-problem-illustration.html")
    assert headers["Content-Type"] == "text/html; charset=utf-8"
    assert "—".encode() in body
    assert "â€".encode() not in body


def test_it_serves_the_section_a_illustration(server_url):
    status, body, _ = fetch(f"{server_url}/figures/html/section-problem-illustration.html")
    assert status == HTTPStatus.OK
    assert b"section_a_medical_cabinet.png" in body
    assert b"section_a_smart_organizer.png" in body


def test_it_serves_the_section_d_illustration(server_url):
    status, body, _ = fetch(f"{server_url}/figures/html/section-gini-illustration.html")
    assert status == HTTPStatus.OK
    assert b"D.lorenz-wealth" in body
    assert b"D.selective-tree" in body
    assert b"D.tree-split-cycle" in body
    assert b"section_gini_tree_split_cycle.png" in body
    assert b"Exploring a Data Tree with Gini" in body


def test_it_serves_the_section_e_illustration(server_url):
    status, body, _ = fetch(f"{server_url}/figures/html/section-budget-illustration.html")
    assert status == HTTPStatus.OK
    assert b"E.storage-limits" in body
    assert b"E.knapsack-ladder" in body
    assert b"E.greedy-guardrails" in body
    assert b"section_e_greedy_guardrails.png" in body
    assert b"Visualization placeholder" not in body


def test_figures_are_served_from_the_repository_rather_than_a_copy(server_url):
    """One set of figures, two readers — the Markdown host and this page."""
    figure = FIGURE_ROOT / "img" / "section_a_medical_cabinet.png"
    assert figure.exists(), "fixture assumes the committed figures are present"

    status, body, headers = fetch(f"{server_url}/figures/img/section_a_medical_cabinet.png")
    assert status == HTTPStatus.OK
    assert headers["Content-Type"].startswith("image/png")
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
    for name in ("formulation.html", "figures/html/section-problem-illustration.html"):
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


# -- Problem Statement is reachable end to end (12.3) ---------------------------------------


def test_the_formulation_is_served_at_the_light_variant_only(server_url):
    """12.3 — a reader whose system is dark is never served a dark figure."""
    _, body, _ = fetch(f"{server_url}/formulation.html")
    text = body.decode()
    assert "demo_index_table.png" in text
    assert "demo_container_activation.png" in text
    assert ".dark.svg" not in text
    assert "<picture" not in text  # collapsed at pre-render, not switched in the browser


def test_the_formulation_carries_its_own_table_of_contents(server_url):
    """12.3 — generated from the document's own headings, not authored beside them."""
    _, body, _ = fetch(f"{server_url}/formulation.html")
    text = body.decode()
    entries = re.findall(r'<li class="toc-h[23]"><a href="#([\w-]+)"', text)
    assert entries
    for anchor in entries:
        assert f'id="{anchor}"' in text


def test_serving_persists_nothing_at_all(server_url, tmp_path, monkeypatch):
    """12.2.7 — nothing a reader does reaches storage, because nothing a reader does
    reaches anything but a file already on disk.

    Watched from the working directory, which is where a stray write would land. Under
    the old design a click ran twenty evaluations and the assertion was that none of their
    rows was written; now no request computes anything, and the same assertion holds for a
    stronger reason.
    """
    monkeypatch.chdir(tmp_path)
    before = sorted(path.name for path in tmp_path.rglob("*"))

    for _ in range(3):
        status, _, _ = fetch(f"{server_url}/")
        assert status == HTTPStatus.OK

    assert sorted(path.name for path in tmp_path.rglob("*")) == before


def test_the_server_keeps_nothing_on_a_readers_behalf(server_url):
    """12.2.7 — no session, no cache, no memory of what was asked before.

    The failure this guards against is a *convenience* someone adds later: a response
    cache, a last-result field, a per-reader dict. None is possible while the answer to
    every request is a file read off disk, so this asks the one question that would
    expose one — whether a second identical request is answered from anywhere else.
    """
    first_status, first_body, _ = fetch(f"{server_url}/")
    second_status, second_body, headers = fetch(f"{server_url}/")

    assert first_status == second_status == HTTPStatus.OK
    assert first_body == second_body
    assert headers["Cache-Control"] == "no-store"
    assert "Set-Cookie" not in headers
