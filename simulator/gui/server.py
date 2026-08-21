"""The HTTP server behind the demonstration GUI (12.2).

FastAPI on uvicorn, single worker (12.2.1.1) — the named minimal ASGI stack 10.3.1
admits, and nothing beyond it.  There is no template engine and no browser-side build
step, which is what keeps 12.2.2 checkable: a reader can confirm the page makes no
outbound request by reading the file that was served, because it is the file that was
authored.

The framework is here for the seam that faces the network.  Static serving and path
containment are `StaticFiles`', not this module's; what this module adds around them is
the three things a public instance needs and a laptop does not — a body ceiling
(12.2.12), a front-door check (12.2.15), and the response headers 12.6.5.1 requires.
Each is one ASGI middleware, so each applies to every response including a refusal.

**The catalog document is read once, at startup** (12.2.3), and held for the process's
life.  **No corpus is loaded, here or anywhere in this process.**  Every number the page
displays was computed offline by 8.11's generator, so what this server holds is a few
hundred kilobytes of already-finished answers rather than the 600 000-event corpus that
producing them needs.

**Nothing here scores anything, and nothing here could** (12.2.5).  Routes below return a
document; every number in one came from the harness through 7.2.4's primitive, in a
different process, before this one started.  10.3.1 keeps the harness out of the exhibit's
dependency set entirely, so a computation in this file is not merely a defect — it is an
import that would fail.
"""

from __future__ import annotations

import json
import signal
import socket
import threading
import webbrowser
from dataclasses import replace
from datetime import datetime, timezone
from hmac import compare_digest
from http import HTTPStatus
from typing import Callable

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import (
    DESCRIPTOR_PATH,
    FIGURE_ROOT,
    FRONT_DOOR_HEADER,
    HEALTH_PATH,
    STATIC_ROOT,
    Deployment,
)
from .. import logs

log = logs.get(__name__)

#: URL prefix the pre-rendered formulation uses for explainer assets, mapped onto the
#: repository's own `resources/` rather than a copy (`tools/render_formulation.py`).
FIGURE_PREFIX = "/figures/"

#: Served for `/`.
INDEX_FILE = "index.html"

#: Kept out of the browser cache: the page is edited and reloaded constantly during
#: development, and a deployed instance is redeployed rather than revalidated.
CACHE_CONTROL = "no-store"

#: 12.2.12 — a ceiling on what one request may send.  Four blocks of four expressions is
#: bytes, not megabytes; a declared gigabyte is a memory-exhaustion vector on a process
#: the reader cannot watch fail.
MAX_REQUEST_BYTES = 1 << 20

#: 12.2.16 — what a listing page shows for this instance.  Authored here because this
#: repository is the only place that can state its own claim without going stale.
EXHIBIT_TITLE = "The Neighbors You Pay For"
EXHIBIT_CLAIM = (
    "Assigning events to storage containers so as to minimize the volume read but not "
    "selected — stated formally, and measured on a harness any strategy can plug into."
)
EXHIBIT_TAGS = ("data layout", "data skipping", "benchmark", "Spark", "Delta Lake")


class GuiError(Exception):
    """A request that cannot be served, carrying the status it should answer with.

    `detail` is the machine-readable half.  A rejected benchmark reports every violation
    addressed by block, parameter and chain position (12.4.2.12), and a page can only put
    those beside the fields that caused them if they survive as data rather than prose.
    """

    def __init__(self, status: HTTPStatus, message: str, detail: dict | None = None):
        self.status = status
        self.detail = detail or {}
        super().__init__(message)


def with_utf8_charset(content_type: str) -> str:
    """Name the encoding on text and SVG so `nosniff` cannot leave a UTF-8 page as Latin-1.

    Type guessing returns `image/svg+xml` with no charset.  Combined with 12.6.5.1's
    `X-Content-Type-Options: nosniff`, a browser then treats the body as Windows-1252 and
    an em-dash renders as mojibake.
    """
    if "charset=" in content_type:
        return content_type
    if content_type.startswith("text/") or content_type == "image/svg+xml":
        return f"{content_type}; charset=utf-8"
    return content_type


def content_security_policy(deployment: Deployment) -> str:
    """12.6.5.1 and 12.6.5.3 — the policy this instance sends.

    Every fetch directive names **this instance's own mount point**.  Where the instance
    is the whole origin, `'self'` is exactly that, and is what a laptop sends.  Where a
    front door has put siblings on the same domain, `'self'` would silently widen from
    this instance to all of them, so the configured base URL is named instead — CSP source
    expressions match on path, which is what makes the narrower statement expressible.
    """
    own = deployment.public_base or "'self'"
    return "; ".join(
        (
            f"default-src {own}",
            f"script-src {own}",
            f"style-src {own} 'unsafe-inline'",
            f"img-src {own} data:",
            f"connect-src {own}",
            "base-uri 'none'",
            "form-action 'none'",
            "frame-ancestors 'none'",
        )
    )


class Application:
    """What the routes serve: one catalog document and the deployment it is serving as.

    Held apart from the framework because the document is read exactly once (12.2.3) while
    a request is handled many times, and because every route wants the same two things.

    **There is no dataset here and no lock around anything.**  Both were needed when a
    request could ask this process to score twenty layouts; a request can now ask it only
    for a document it already holds, so there is no work to admit one at a time and no
    corpus to hold in order to do it (12.2.4).
    """

    def __init__(self, catalog=None, deployment: Deployment | None = None):
        self.catalog = catalog
        self.deployment = deployment or Deployment()
        #: Recorded here rather than at module import because this is the moment the
        #: process becomes a server: `api` is imported lazily, per route.
        self.started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.routes: dict[tuple[str, str], Callable] = {
            ("GET", "/api/catalog"): self.catalog_document,
            ("GET", HEALTH_PATH): self.health,
            ("GET", DESCRIPTOR_PATH): self.descriptor,
        }

    # -- JSON endpoints ------------------------------------------------------------

    def health(self, _payload, scope) -> dict:
        """Who is holding this port (12.2.9), for a launcher deciding whether to bind.

        It is also what a platform asks to decide whether this instance may be routed to
        (10.3.12): the catalog is read before the socket binds, so a reply at all is
        the readiness answer.

        Those two callers are told different amounts.  A launcher is on the same machine
        and reaches an instance with no front door in front of it, so it gets everything
        it needs to decide whether to signal the process.  A platform probe bypasses the
        front door under 12.2.15's exemption, and is told only that this is up.
        """
        from . import api

        return api.health(
            None if self.catalog is None else self.catalog["corpus"]["dataset_id"],
            self.started,
            identified=scope.get(VIA_FRONT_DOOR, True),
        )

    def descriptor(self, _payload, _scope) -> dict:
        """12.2.16 — what this instance is, for a page that lists several of them.

        The identifier is the mount prefix, so it cannot drift from the URL it names, and
        it is unique across everything sharing the domain by construction.
        """
        from importlib.metadata import PackageNotFoundError, version

        try:
            release = version("dataclustering-solver")
        except PackageNotFoundError:  # pragma: no cover - an uninstalled source tree
            release = "0"
        return {
            "id": self.deployment.exhibit_id,
            "title": EXHIBIT_TITLE,
            "claim": EXHIBIT_CLAIM,
            "tags": list(EXHIBIT_TAGS),
            "version": release,
        }

    def catalog_document(self, _payload, _scope) -> dict:
        """The pre-computed catalogue Section B draws itself from (8.11.1, 12.2.3).

        Returned as it was built.  There is nothing to shape and nothing to compute: the
        generator put the document in the shape the page reads, which is what leaves this
        method a lookup and keeps 12.2.5 true by having no alternative.

        This one route replaced three — the dataset summary, the family schema, and the
        evaluation itself.  The first two existed to let the page build a form, and there
        is no form (13.9); the third is what moved offline.  Section B's whole server-side
        surface is now this GET.
        """
        if self.catalog is None:
            raise GuiError(
                HTTPStatus.SERVICE_UNAVAILABLE,
                "no catalog is loaded — build one with `python -m simulator catalog`",
            )
        return self.catalog


# -- middleware -----------------------------------------------------------------------
#
# Raw ASGI rather than request/response hooks, because two of the three must act *before*
# the body is read, and the third must reach responses the routes never produced — a 404
# from the static mount, or a refusal from one of the other two.


class ResponseHeaders:
    """12.6.5.1 — the security headers, on every response this process sends.

    Outermost, so a refusal decided by the middleware below still carries them, and so a
    file served by `StaticFiles` does too.  The charset fix rides here for the same
    reason: it is the one header adjustment that has to reach responses this module did
    not construct.  One log record per request rides here too (10.3.7), for the same
    reason again — it is the only place that sees all of them.
    """

    def __init__(self, app, policy: str):
        self.app = app
        self.policy = policy

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":  # pragma: no cover - nothing else is served
            return await self.app(scope, receive, send)

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = [
                    (key, value)
                    for key, value in message["headers"]
                    if key.lower() != b"content-type"
                ]
                declared = next(
                    (
                        value.decode()
                        for key, value in message["headers"]
                        if key.lower() == b"content-type"
                    ),
                    None,
                )
                if declared is not None:
                    headers.append(
                        (b"content-type", with_utf8_charset(declared).encode())
                    )
                headers += [
                    (b"cache-control", CACHE_CONTROL.encode()),
                    (b"content-security-policy", self.policy.encode()),
                    (b"x-content-type-options", b"nosniff"),
                ]
                message = {
                    **message,
                    "headers": [(_canonical(key), value) for key, value in headers],
                }
                log.info(
                    "%s %s → %s", scope["method"], scope["path"], message["status"]
                )
            await send(message)

        await self.app(scope, receive, send_with_headers)


#: Whether this request arrived through the front door.  Absent means yes — either it
#: presented the secret, or no front door is configured and the question does not arise.
#: Only 12.2.15's one exemption ever sets it False, and only the health handler reads it.
VIA_FRONT_DOOR = "gui.via_front_door"


class FrontDoorOnly:
    """12.2.15 — a publicly bound instance answers only what its front door forwarded.

    A managed platform gives every service a public hostname of its own, so the bind
    address cannot be what excludes direct access.  The front door presents a shared
    secret instead, and anything arriving without it is refused before it reaches a route.

    Disabled when no secret is configured, which is the local demonstration: there is no
    front door there, so there is nothing to bypass.  The refusal is a 404 rather than a
    403, because saying "wrong secret" tells a prober there is a secret.

    **Readiness is the single exemption.**  The platform's own probe reaches this process
    on an internal address and has no way to be given the secret, so refusing it would
    leave every deployed instance permanently unready — the protection would take the
    service down rather than defend it.  The request is admitted and *marked*, and the
    handler answers it in the reduced form 12.2.15 requires.
    """

    def __init__(self, app, secret: str = ""):
        self.app = app
        self.secret = secret

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and self.secret:
            presented = _header(scope, FRONT_DOOR_HEADER)
            # Constant time: a byte-by-byte comparison on a shared secret is a timing
            # oracle for it.
            if not compare_digest(presented.encode(), self.secret.encode()):
                if scope.get("path") != HEALTH_PATH:
                    log.warning(
                        "refused a request that did not come through the front door"
                    )
                    return await _refuse(
                        send, HTTPStatus.NOT_FOUND, {"error": "no such resource"}
                    )
                scope[VIA_FRONT_DOOR] = False
        await self.app(scope, receive, send)


class BodyCeiling:
    """12.2.12 — a body above the ceiling is refused with 413, before it is read.

    The bound applies to the declared length *and* to the bytes actually taken, because
    trusting `Content-Length` to be honest is the other half of the same mistake.  A
    refusal decided before the body was read leaves the client still writing, so the
    connection is closed rather than left half-read on a reusable socket.
    """

    def __init__(self, app, ceiling: int = MAX_REQUEST_BYTES):
        self.app = app
        self.ceiling = ceiling

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":  # pragma: no cover
            return await self.app(scope, receive, send)

        declared = _header(scope, "content-length")
        if declared:
            try:
                length = int(declared)
            except ValueError:
                return await _refuse(
                    send, HTTPStatus.BAD_REQUEST, {"error": "malformed Content-Length"}
                )
            if length > self.ceiling:
                return await _refuse(
                    send,
                    HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                    {"error": f"request body over {self.ceiling} bytes"},
                    close=True,
                )

        taken = 0

        async def receive_bounded():
            """Never read past the ceiling, whatever the request declared."""
            nonlocal taken
            message = await receive()
            if message["type"] == "http.request":
                taken += len(message.get("body", b""))
                if taken > self.ceiling:
                    log.warning("a request body ran past the ceiling it declared")
                    return {"type": "http.disconnect"}
            return message

        await self.app(scope, receive_bounded, send)


def _canonical(name: bytes) -> bytes:
    """`content-type` sent as `Content-Type`.

    Header names are case-insensitive to a browser, and every client this project has is
    a browser or a test that reads them out of a mapping.  The mappings are the reason:
    `http.client` keys a response's headers by the case they arrived in, so a reader who
    asks for `Content-Type` finds nothing when the wire said `content-type`.
    """
    return b"-".join(part.capitalize() for part in name.split(b"-"))


def _header(scope, name: str) -> str:
    return next(
        (
            value.decode()
            for key, value in scope["headers"]
            if key.decode().lower() == name
        ),
        "",
    )


async def _refuse(send, status: HTTPStatus, payload: dict, close: bool = False) -> None:
    """A JSON refusal from inside the middleware, where no route ran to produce one."""
    body = json.dumps(payload).encode()
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode()),
    ]
    if close:
        headers.append((b"connection", b"close"))
    await send({"type": "http.response.start", "status": int(status), "headers": headers})
    await send({"type": "http.response.body", "body": body})


# -- the application ------------------------------------------------------------------


def build_app(catalog=None, deployment: Deployment | None = None) -> FastAPI:
    """The ASGI application, ready to be served or driven by a test client.

    Route order is load-bearing.  The JSON endpoints are declared first, so they win; the
    POST catch-all follows, so an unknown POST is a 404 naming the route rather than a
    405 from the static mount; the two static mounts come last and answer every GET the
    endpoints did not.

    **Every route this serves is a GET.**  The catch-all is what makes that a statement
    rather than an omission: the application declares no POST at all, so every POST that
    arrives is refused by name.  It used to be the fallback behind one real POST; it is
    now the whole of this application's answer to the verb.
    """
    deployment = deployment or Deployment()
    application = Application(catalog, deployment)

    # No `root_path`.  The front door strips the mount prefix, so the path that arrives
    # is already the path these routes are declared at — and a framework told to expect
    # the prefix would strip it a second time, which 404s every asset under a nested
    # mount.  Nothing here generates a URL, so nothing needs the prefix to do it with.
    app = FastAPI(title=EXHIBIT_TITLE, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.application = application

    @app.exception_handler(GuiError)
    async def _refused(_request: Request, refused: GuiError) -> JSONResponse:
        return JSONResponse(
            {"error": str(refused), **refused.detail}, status_code=int(refused.status)
        )

    @app.exception_handler(StarletteHTTPException)
    async def _missing(request: Request, failure: StarletteHTTPException) -> JSONResponse:
        """A missing asset says nothing about what exists outside the document root."""
        if failure.status_code == HTTPStatus.NOT_FOUND:
            return JSONResponse(
                {"error": f"no such asset: {request.url.path}"},
                status_code=HTTPStatus.NOT_FOUND,
            )
        return JSONResponse({"error": failure.detail}, status_code=failure.status_code)

    @app.exception_handler(Exception)
    async def _failed(request: Request, failure: Exception) -> JSONResponse:  # pragma: no cover
        # A traceback belongs in the terminal the reader started the server from, not in
        # the browser.
        log.exception(
            "unhandled %s on %s %s",
            failure.__class__.__name__,
            request.method,
            request.url.path,
        )
        return JSONResponse(
            {"error": failure.__class__.__name__},
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    def _bind(method: str, path: str, handler: Callable) -> None:
        async def endpoint(request: Request):
            payload = await _payload(request)
            # Every handler takes the body and the request's scope, in that order.  The
            # scope carries what was decided about the request before it reached a route
            # — currently only 12.2.15's exemption flag — and a uniform signature keeps
            # that out of the dispatch table as a special case.
            #
            # Synchronous by design (12.2.4), and run in a worker thread so the event
            # loop stays free to answer a health check while a sweep is in flight.
            return JSONResponse(
                await run_in_threadpool(handler, payload, request.scope)
            )

        app.add_api_route(path, endpoint, methods=[method], include_in_schema=False)

    for (method, path), handler in application.routes.items():
        _bind(method, path, handler)

    @app.post("/{unmatched:path}", include_in_schema=False)
    async def _no_post_route(unmatched: str):
        raise GuiError(HTTPStatus.NOT_FOUND, f"no route for POST /{unmatched}")

    # Path containment is the framework's (12.2.1.1): `StaticFiles` resolves under its own
    # root and refuses anything that leaves it, so `..`, an encoded `..`, a symlink out of
    # the tree and an absolute path all fail identically — and identically to a file that
    # simply is not there.
    app.mount(
        FIGURE_PREFIX.rstrip("/"), StaticFiles(directory=FIGURE_ROOT), name="figures"
    )
    app.mount("/", StaticFiles(directory=STATIC_ROOT, html=True), name="static")

    # Added innermost first: `add_middleware` prepends, so the last added is outermost.
    app.add_middleware(BodyCeiling)
    app.add_middleware(FrontDoorOnly, secret=deployment.front_door_secret)
    app.add_middleware(ResponseHeaders, policy=content_security_policy(deployment))
    return app


async def _payload(request: Request) -> dict:
    """The request body as JSON.  An empty body is an empty mapping, not an error."""
    if request.method == "GET":
        return {}
    raw = await request.body()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as malformed:
        raise GuiError(HTTPStatus.BAD_REQUEST, f"malformed JSON: {malformed}") from None


class Server:
    """A bound socket, and the ASGI server that will serve on it.

    Bound eagerly so the port is knowable before serving starts — which is what lets a
    test ask for port 0 and then address the port it was given (12.2.6) — and so a launch
    that cannot bind fails before printing a URL nobody can open.

    Four members are the whole lifecycle a caller needs: where it bound, run, stop, close.
    """

    def __init__(self, app, host: str, port: int):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((host, port))
        self.socket.listen(128)
        self.server_address = self.socket.getsockname()
        #: Set when the serving loop has actually returned, so `shutdown` can block until
        #: it has.  Without that, a caller that stops the server and immediately closes
        #: the socket pulls the descriptor out from under a loop still polling it.
        self._stopped = threading.Event()
        self._uvicorn = uvicorn.Server(
            uvicorn.Config(
                app,
                # This project's own logging is already a tee to stdout and a run file
                # (10.3.7); a second configuration would print each line twice.
                log_config=None,
                access_log=False,
            )
        )

    def serve_forever(self) -> None:
        """Serve until `shutdown`, Ctrl-C, or `SIGTERM` (12.2.10).

        uvicorn installs both signal handlers itself, and skips them entirely off the
        main thread, where they are illegal — which is what lets a test run this on a
        thread and stop it with `shutdown`.
        """
        try:
            self._uvicorn.run(sockets=[self.socket])
        finally:
            self._stopped.set()

    def shutdown(self, timeout: float = 5.0) -> None:
        """Stop the serving loop and wait for it to return.

        Safe from another thread, and only from another thread: the loop cannot be waited
        on from inside itself.  It blocks rather than signalling, because every caller
        closes the socket next and doing that while the loop still holds it is what turns
        an orderly stop into an invalid-descriptor traceback.
        """
        self._uvicorn.should_exit = True
        self._stopped.wait(timeout)

    def server_close(self) -> None:
        self.socket.close()


def build_server(
    host: str | None = None,
    port: int | None = None,
    catalog=None,
    deployment: Deployment | None = None,
) -> Server:
    """A server ready to `serve_forever`, or to be driven directly from a test.

    Returned rather than started so 12.2.6 is reachable: the whole interface is
    exercisable under pytest by binding port 0 and issuing real requests, with no browser
    involved.
    """
    deployment = _bound(deployment or Deployment(), host, port)
    return Server(build_app(catalog, deployment), deployment.host, deployment.port)


def _bound(deployment: Deployment, host: str | None, port: int | None) -> Deployment:
    """The same deployment, bound elsewhere — what a flag or a test overrides."""
    return replace(
        deployment,
        host=deployment.host if host is None else host,
        port=deployment.port if port is None else port,
    )


def serve(
    host: str | None = None,
    port: int | None = None,
    catalog=None,
    open_browser: bool = False,
    deployment: Deployment | None = None,
):
    """Bind and serve until Ctrl-C or `SIGTERM`.  Called by `python -m simulator gui`.

    `catalog` is an already-parsed catalog document, not a path: resolving which one to
    serve — and refusing when there is none — is the CLI's job, and doing it there keeps
    the "read once, before the first connection" promise visible at the call site
    (12.2.3).

    **`SIGTERM` closes the socket as cleanly as Ctrl-C does** (12.2.10), which is what a
    restart depends on: `launcher.stop` signals this process and then waits for the port
    to come free.  uvicorn owns both handlers, so nothing here installs one.
    """
    if catalog is not None:
        corpus = catalog["corpus"]
        print(
            f"catalog  {len(catalog['strategies'])} strategies over"
            f" {corpus['dataset_id']}  {corpus['event_count']:,} events"
        )

    server = build_server(host, port, catalog, deployment)
    bound_host, bound_port = server.server_address
    url = f"http://{bound_host}:{bound_port}/"
    log.info("bound host=%s port=%s", bound_host, bound_port)
    print(f"serving {url}  (ctrl-c to stop)")

    stopping = threading.Event()

    def _terminate(*_):
        log.info("SIGTERM received, shutting down")
        stopping.set()

    # The serving loop runs on its own thread and the main thread waits on the signal.
    # Two reasons, and the second is the load-bearing one.  `shutdown` is only safe from
    # *off* the loop.  And an ASGI server that captures `SIGTERM` itself re-raises it
    # after shutting down, so the command would exit 143 — 12.2.10 asks for a clean 0,
    # because `launcher.restart` reads the exit status as well as the freed port.
    signal.signal(signal.SIGTERM, _terminate)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    # After the bind, so the page the browser asks for is already answerable.
    if open_browser:
        webbrowser.open(url)

    try:
        while not stopping.wait(0.5):
            if not thread.is_alive():  # pragma: no cover - the loop failed on its own
                break
    except KeyboardInterrupt:
        pass
    finally:
        log.info("closing listener")
        print("\nstopped")
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()  # idempotent: uvicorn closes what it was handed
    return 0
