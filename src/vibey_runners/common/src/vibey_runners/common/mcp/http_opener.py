# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One blocking HTTPS exchange with a remote MCP server, on the standard library's urllib
(SP-LOOPS Phase 5, R13).

The opener is `urllib.request.build_opener` with three handlers of its own in place of the
defaults:

- `ProxyHandler({})`: no proxy is read from the environment, so neither an `*_proxy` variable
  nor the credential it may carry is ever used;
- a redirect handler that refuses every redirect, so a 3xx comes back as the reply and no second
  request is made;
- an `HTTPSHandler` on `ssl.create_default_context()`, which verifies the certificate and host.

There is no cookie processor and no auth handler, and the default `User-Agent` is removed, so a
request carries exactly the headers it is given. https is the only scheme accepted. An error
status comes back as a reply with an empty body; its body is never read. A success body is read
one buffered chunk at a time up to one byte past `limit_bytes`, and the whole exchange is held
to `timeout_seconds` (each socket operation to the same), so a server that trickles its reply
cannot hold a turn. Declared by `interfaces/http_opener_interface.py::HttpOpenerInterface`.
"""

from __future__ import annotations

import contextlib
import ssl
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from email.message import Message
from http.client import HTTPMessage
from typing import IO, Any, Final
from urllib.parse import urlsplit

from vibey_runners.common.mcp.http_reply import HttpReply

DEFAULT_LIMIT_BYTES: Final = 16_777_216
"""The largest reply body accepted, the JSON-RPC peer's own default bound on one message."""


class _RefuseRedirects(urllib.request.HTTPRedirectHandler):
    """Answers every redirect status with no new request, so the opener's default error handler
    raises it as an `HTTPError`, which `HttpOpener` returns as the reply. A urllib handler: its
    seam is urllib's own `BaseHandler` chain, not an interface of this package."""

    def http_error_301(
        self, req: urllib.request.Request, fp: IO[bytes], code: int, msg: str, headers: HTTPMessage
    ) -> None:
        return None

    def http_error_302(
        self, req: urllib.request.Request, fp: IO[bytes], code: int, msg: str, headers: HTTPMessage
    ) -> None:
        return None

    def http_error_303(
        self, req: urllib.request.Request, fp: IO[bytes], code: int, msg: str, headers: HTTPMessage
    ) -> None:
        return None

    def http_error_307(
        self, req: urllib.request.Request, fp: IO[bytes], code: int, msg: str, headers: HTTPMessage
    ) -> None:
        return None

    def http_error_308(
        self, req: urllib.request.Request, fp: IO[bytes], code: int, msg: str, headers: HTTPMessage
    ) -> None:
        return None


class HttpOpener:
    """Declared by `interfaces/http_opener_interface.py::HttpOpenerInterface`."""

    def __init__(
        self,
        timeout_seconds: float,
        *,
        limit_bytes: int = DEFAULT_LIMIT_BYTES,
        https_handler: urllib.request.HTTPSHandler | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._timeout = timeout_seconds
        self._limit = limit_bytes
        self._clock = clock
        if https_handler is None:
            https_handler = urllib.request.HTTPSHandler(context=ssl.create_default_context())
        self._opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _RefuseRedirects(), https_handler
        )
        self._opener.addheaders = []

    @property
    def handlers(self) -> tuple[urllib.request.BaseHandler, ...]:
        """The opener's whole handler chain, defaults included, for inspection. urllib keeps it
        in the director's `handlers` attribute, which typeshed does not declare."""
        return tuple(vars(self._opener)["handlers"])

    def post(self, url: str, body: bytes, headers: Mapping[str, str]) -> HttpReply:
        return self._exchange(self._request(url, "POST", headers, body), read_body=True)

    def delete(self, url: str, headers: Mapping[str, str]) -> int:
        return self._exchange(self._request(url, "DELETE", headers, None), read_body=False).status

    # -- internals ------------------------------------------------------------------------

    @staticmethod
    def _request(
        url: str, method: str, headers: Mapping[str, str], body: bytes | None
    ) -> urllib.request.Request:
        if urlsplit(url).scheme != "https":
            raise ValueError("an MCP server is reached over https only, never another scheme")
        # The scheme is https (checked above, and by `BundleSpec._https` before the URL got
        # here), so no file:, ftp: or data: handler can be reached through this request.
        return urllib.request.Request(url, data=body, headers=dict(headers), method=method)

    def _exchange(self, request: urllib.request.Request, *, read_body: bool) -> HttpReply:
        deadline = self._clock() + self._timeout
        try:
            response = self._opener.open(request, timeout=self._timeout)
        except urllib.error.HTTPError as exc:
            # An error status, a refused redirect among them: the status and headers are the
            # reply, and the body (the server's words about its error) is never read.
            with contextlib.closing(exc):
                return HttpReply(exc.code, self._headers(exc.headers), b"")
        with contextlib.closing(response):
            body = self._read(response, deadline) if read_body else b""
            return HttpReply(response.status, self._headers(response.headers), body)

    def _read(self, response: Any, deadline: float) -> bytes:
        """At most `limit_bytes + 1` bytes, one buffered read at a time, within the deadline."""
        chunks: list[bytes] = []
        size = 0
        while size <= self._limit:
            if self._clock() > deadline:
                raise TimeoutError(f"the reply took longer than {self._timeout:g}s")
            chunk = response.read1(self._limit + 1 - size)
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        return b"".join(chunks)

    @staticmethod
    def _headers(headers: Message) -> dict[str, str]:
        return {name.lower(): value for name, value in headers.items()}
