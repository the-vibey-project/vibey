# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of `web/guarded_opener.py` (ADR-0016). Interfaces declare; they never consume."""

from __future__ import annotations

import http.client
import threading
import urllib.request
from collections.abc import Callable
from http.client import HTTPMessage
from typing import IO, Any, Protocol, runtime_checkable


@runtime_checkable
class SameOriginRedirectsInterface(Protocol):
    """A `urllib` redirect handler that follows a redirect only within its own origin."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        """The follow-up request, or None (the redirect is then raised as its HTTPError)."""
        ...


@runtime_checkable
class GuardedOpenerInterface(Protocol):
    """Opens one search backend's requests: same-origin redirects only, and no proxy between
    vibey and a loopback SearXNG."""

    direct: bool
    """Whether requests skip the environment's proxy (the backend is on loopback)."""

    def __call__(self, request: urllib.request.Request, timeout: float) -> Any:
        """The response, as `urllib.request.urlopen` returns it."""
        ...

    def abort(self, thread: threading.Thread) -> None:
        """Shut down the sockets the connections made in `thread` connected."""
        ...

    def connection(
        self, kind: type[http.client.HTTPConnection]
    ) -> Callable[..., http.client.HTTPConnection]:
        """A maker of `kind` connections whose `connect` records the socket it connected under
        the thread making the connection."""
        ...

    def threads(self) -> frozenset[threading.Thread]:
        """The threads, still running, whose sockets are recorded."""
        ...


@runtime_checkable
class AbortableOpenerInterface(Protocol):
    """An opener that can shut down what one thread of its own opened, so a request abandoned at
    its deadline does not keep that thread (SP-ACP Task 9c, P-9c-3)."""

    def __call__(self, request: urllib.request.Request, timeout: float) -> Any:
        """The response, as `urllib.request.urlopen` returns it."""
        ...

    def abort(self, thread: threading.Thread) -> None:
        """Shut down the sockets connected in `thread` (the object, never a reusable ident), so
        a read blocked there -- status line, headers or body -- returns at once."""
        ...


@runtime_checkable
class TrackedHandlerInterface(Protocol):
    """`urllib`'s http and https handler, opening each connection through its opener's
    `connection`, so the opener knows which thread opened it."""

    def http_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
        """Open `req` over plain http."""
        ...

    def https_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
        """Open `req` over TLS."""
        ...
