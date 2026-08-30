"""The HTTP server behind the presentation page (12.2).

FastAPI on uvicorn, single worker.  There is no template engine and no browser-side
build step, which is what keeps 12.2.2 checkable: a reader can confirm the page makes no
outbound request by reading the file that was served, because it is the file that was
authored.

**The server holds nothing and computes nothing** (12.2.5).  It hands over authored
files: the page and its assets from this package, and the figures from the repository's
own `resources/` tree.  There is no route of its own to declare — what the page fetches,
it fetches as a document — so static serving and path containment are `StaticFiles`',
and what this module adds around them is one middleware carrying the response headers
12.6.5 requires.
"""

from __future__ import annotations

import signal
import socket
import threading
import webbrowser
from http import HTTPStatus

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    FIGURE_ROOT,
    STATIC_ROOT,
)
from .. import logs

log = logs.get(__name__)

#: URL prefix the page uses for explainer assets, mapped onto the repository's own
#: `resources/` rather than a copy.
FIGURE_PREFIX = "/figures/"

#: Served for `/`.
INDEX_FILE = "index.html"

#: Kept out of the browser cache: the page is edited and reloaded constantly during
#: development.
CACHE_CONTROL = "no-store"

#: The name the browser tab and the ASGI application carry.
PROJECT_TITLE = "The Data Storage Layout Problem"

#: 12.6.5 — the policy every response carries.  The page is the whole origin, so `'self'`
#: names exactly it, and nothing it loads comes from anywhere else.
CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "connect-src 'self'",
        "base-uri 'none'",
        "form-action 'none'",
        "frame-ancestors 'none'",
    )
)


def with_utf8_charset(content_type: str) -> str:
    """Name the encoding on text and SVG so `nosniff` cannot leave a UTF-8 page as Latin-1.

    Type guessing returns `image/svg+xml` with no charset.  Combined with 12.6.5's
    `X-Content-Type-Options: nosniff`, a browser then treats the body as Windows-1252 and
    an em-dash renders as mojibake.
    """
    if "charset=" in content_type:
        return content_type
    if content_type.startswith("text/") or content_type == "image/svg+xml":
        return f"{content_type}; charset=utf-8"
    return content_type


# -- middleware -----------------------------------------------------------------------
#
# Raw ASGI rather than a response hook, because it must reach responses this module never
# produced — a file served by `StaticFiles`, or a 404 from it.


class ResponseHeaders:
    """12.6.5 — the security headers, on every response this process sends.

    The charset fix rides here for the same reason: it is the one header adjustment that
    has to reach responses this module did not construct.  One log record per request
    rides here too (10.3.7), for the same reason again — it is the only place that sees
    all of them.
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


def _canonical(name: bytes) -> bytes:
    """`content-type` sent as `Content-Type`.

    Header names are case-insensitive to a browser, and every client this project has is
    a browser or a test that reads them out of a mapping.  The mappings are the reason:
    `http.client` keys a response's headers by the case they arrived in, so a reader who
    asks for `Content-Type` finds nothing when the wire said `content-type`.
    """
    return b"-".join(part.capitalize() for part in name.split(b"-"))


# -- the application ------------------------------------------------------------------


def build_app() -> FastAPI:
    """The ASGI application, ready to be served or driven by a test client.

    **This application declares no route of its own.**  Two static mounts answer every
    request: `figures/` from the repository's `resources/` tree, and everything else from
    the authored page beside this module.  Nothing is held between requests, because
    there is nothing to hold — which is 12.2.7 read as a property of the shape rather
    than a rule someone has to keep.
    """
    app = FastAPI(title=PROJECT_TITLE, docs_url=None, redoc_url=None, openapi_url=None)

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

    # Path containment is the framework's: `StaticFiles` resolves under its own
    # root and refuses anything that leaves it, so `..`, an encoded `..`, a symlink out of
    # the tree and an absolute path all fail identically — and identically to a file that
    # simply is not there.
    app.mount(
        FIGURE_PREFIX.rstrip("/"), StaticFiles(directory=FIGURE_ROOT), name="figures"
    )
    app.mount("/", StaticFiles(directory=STATIC_ROOT, html=True), name="static")

    app.add_middleware(ResponseHeaders, policy=CONTENT_SECURITY_POLICY)
    return app


class Server:
    """A bound socket, and the ASGI server that will serve on it.

    Bound eagerly so the port is knowable before serving starts — which is what lets a
    test ask for port 0 and then address the port it was given — and so a launch that
    cannot bind fails before printing a URL nobody can open.

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
        """Serve until `shutdown`, Ctrl-C, or `SIGTERM` (12.2.8).

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


def build_server(host: str | None = None, port: int | None = None) -> Server:
    """A server ready to `serve_forever`, or to be driven directly from a test.

    Returned rather than started so the whole served surface is exercisable under pytest
    by binding port 0 and issuing real requests, with no browser involved.
    """
    return Server(
        build_app(),
        DEFAULT_HOST if host is None else host,
        DEFAULT_PORT if port is None else port,
    )


def serve(
    host: str | None = None,
    port: int | None = None,
    open_browser: bool = False,
):
    """Bind and serve until Ctrl-C or `SIGTERM`.  Called by `python -m simulator gui`.

    **`SIGTERM` closes the socket as cleanly as Ctrl-C does** (12.2.8), so the command
    exits 0 rather than 143 and a relaunch can bind.  uvicorn owns both handlers, so
    nothing here installs one.
    """
    server = build_server(host, port)
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
    # after shutting down, so the command would exit 143 where 12.2.8 asks for a clean 0.
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
