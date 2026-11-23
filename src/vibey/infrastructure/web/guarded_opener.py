# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""How a search backend opens its requests.

`urllib`'s default opener follows any redirect to any host and carries every header but the
content ones along, so a SearXNG answering `302 Location: https://elsewhere/` would send the
query there, and a redirect from Brave would send the `X-Subscription-Token` key with it. This
opener follows a redirect only to the same scheme, host and port; any other is refused, which
the backend reports as the `3xx` it was.

A SearXNG on a loopback address is reached directly, never through `HTTP_PROXY` or
`ALL_PROXY`: a proxy would see every query, and the local SearXNG is local so that nothing
does. A backend elsewhere (an operator's remote SearXNG, Brave) uses the environment's proxy
settings as any other request would.

Each connection is made through the opener's `connection`, which records it under the thread
making it, so `abort(thread)` can shut down the sockets of a request abandoned at its deadline
(`BoundedRequest`): the reader blocked in that thread wakes and ends, rather than living as long
as a listener that trickles its answer likes (SP-ACP Task 9c, P-9c-3). What a finished thread
made is forgotten the next time a connection is made.

Declared by `interfaces/guarded_opener_interface.py` (ADR-0016).
"""

from __future__ import annotations

import contextlib
import http.client
import ipaddress
import socket
import threading
import urllib.parse
import urllib.request
from collections.abc import Callable
from http.client import HTTPMessage
from typing import IO, Any


class SameOriginRedirects(urllib.request.HTTPRedirectHandler):
    """Follows a redirect only within the origin it started from.

    Declared by `interfaces/guarded_opener_interface.py::SameOriginRedirectsInterface`."""

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        here = urllib.parse.urlsplit(req.full_url)
        there = urllib.parse.urlsplit(urllib.parse.urljoin(req.full_url, newurl))
        if (here.scheme, here.netloc) != (there.scheme, there.netloc):
            # None makes urllib raise the redirect as the HTTPError it was.
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class TrackedHandler(urllib.request.HTTPHandler, urllib.request.HTTPSHandler):
    """Opens http and https through `GuardedOpener.connection`, in place of `urllib`'s own two
    handlers (a subclass of both, so `build_opener` adds neither default).

    Declared by `interfaces/guarded_opener_interface.py::TrackedHandlerInterface`."""

    def __init__(self, opener: GuardedOpener) -> None:
        super().__init__()
        self._opener = opener

    def http_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
        return self.do_open(self._opener.connection(http.client.HTTPConnection), req)

    def https_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
        made = self._opener.connection(http.client.HTTPSConnection)
        return self.do_open(made, req, context=getattr(self, "_context", None))


class GuardedOpener:
    """Declared by `interfaces/guarded_opener_interface.py::GuardedOpenerInterface`."""

    def __init__(self, base_url: str) -> None:
        self.direct = self.is_loopback(base_url)
        self._lock = threading.Lock()
        self._made: dict[int, list[http.client.HTTPConnection]] = {}
        handlers: list[urllib.request.BaseHandler] = [SameOriginRedirects(), TrackedHandler(self)]
        if self.direct:
            handlers.append(urllib.request.ProxyHandler({}))
        self._director = urllib.request.build_opener(*handlers)

    def __call__(self, request: urllib.request.Request, timeout: float) -> Any:
        return self._director.open(request, timeout=timeout)

    def connection(
        self, kind: type[http.client.HTTPConnection]
    ) -> Callable[..., http.client.HTTPConnection]:
        def made(host: str, **kwargs: Any) -> http.client.HTTPConnection:
            connection = kind(host, **kwargs)
            running = {thread.ident for thread in threading.enumerate()}
            with self._lock:
                for gone in [ident for ident in self._made if ident not in running]:
                    del self._made[gone]
                self._made.setdefault(threading.get_ident(), []).append(connection)
            return connection

        return made

    def abort(self, thread_id: int) -> None:
        with self._lock:
            made = self._made.pop(thread_id, [])
        for connection in made:
            sock = connection.sock
            if sock is None:
                continue  # not connected yet: its connect is bounded by its own timeout
            # Shut down, never closed from here: the thread reading it still owns the
            # descriptor, and closes it as it unwinds. The base class's method, so a TLS
            # socket's own state is never touched from this thread.
            with contextlib.suppress(OSError):
                socket.socket.shutdown(sock, socket.SHUT_RDWR)

    def threads(self) -> frozenset[int]:
        with self._lock:
            return frozenset(self._made)

    @staticmethod
    def is_loopback(url: str) -> bool:
        """Whether `url` names this machine: `localhost` or a name under it (RFC 6761), with or
        without the root's trailing dot, or an address in 127.0.0.0/8 or ::1."""
        host = (urllib.parse.urlsplit(url).hostname or "").lower().rstrip(".")
        if host == "localhost" or host.endswith(".localhost"):
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False
