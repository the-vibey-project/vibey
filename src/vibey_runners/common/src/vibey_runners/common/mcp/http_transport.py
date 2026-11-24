# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A `remote` MCP server over MCP's streamable HTTP transport (SP-LOOPS Phase 5, R5, R6, R13,
R15).

Each line the session writes is POSTed to the server's URL through the opener, off the event
loop, and the reply is fed to the stream the session reads:

- `200` `application/json`: the body, as one line;
- `200` `text/event-stream`: one line per event that carries data, its `data:` lines joined;
- `202`: nothing (the answer to a notification or a response);
- `404` while a session id is held: the end of the stream, so the session is dead (R6);
- anything else, a redirect included, or a body over `limit_bytes`: `McpUnavailable`.

A request carries exactly four headers: `Content-Type`, `Accept`, and, once the server has given
them, `Mcp-Session-Id` and `MCP-Protocol-Version`. Both are learned from the reply to
`initialize` alone, and the version only when this client speaks it (R15). No cookie, no
credential and no environment value is sent (R13); the opener follows no redirect.

Nothing a reply holds reaches a message: a refusal names the server, the host and the status,
never the URL's path or query, a header or the body. `close` deletes the session on the server
(best effort, every error ignored) and ends the stream. Declared by
`interfaces/mcp_transport_interface.py::McpTransportInterface`.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import re
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Final, cast
from urllib.parse import urlsplit

from vibey_runners.common.mcp.http_opener import DEFAULT_LIMIT_BYTES, HttpOpener
from vibey_runners.common.mcp.http_reply import HttpReply
from vibey_runners.common.mcp.interfaces.http_opener_interface import HttpOpenerInterface
from vibey_runners.common.mcp.mcp_errors import McpUnavailable
from vibey_runners.common.mcp.protocol import SUPPORTED_PROTOCOLS

_ACCEPT: Final = "application/json, text/event-stream"
_SESSION_ID: Final = re.compile(r"[\x21-\x7e]+")
"""MCP: a session id holds visible ASCII only, so it can never break a header line."""
_LINE_BREAK: Final = re.compile(rb"\r\n|\r|\n")


class HttpTransport:
    """Declared by `interfaces/mcp_transport_interface.py::McpTransportInterface`."""

    def __init__(
        self,
        name: str,
        url: str,
        *,
        timeout_seconds: float,
        limit_bytes: int = DEFAULT_LIMIT_BYTES,
        opener: HttpOpenerInterface | None = None,
    ) -> None:
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.hostname:
            raise ValueError(f"MCP server {name!r} needs an https:// URL with a host")
        self._name = name
        self._url = url
        self._host = parts.hostname
        self._timeout = timeout_seconds
        self._limit = limit_bytes
        self._opener: HttpOpenerInterface = (
            opener if opener is not None else HttpOpener(timeout_seconds, limit_bytes=limit_bytes)
        )
        self._reader: asyncio.StreamReader | None = None
        self._live = False
        self._session_id: str | None = None
        self._version: str | None = None

    async def open(self) -> tuple[asyncio.StreamReader, Callable[[str], Awaitable[None]]]:
        self._reader = asyncio.StreamReader(limit=self._limit)
        self._live = True
        self._session_id = None
        self._version = None
        return self._reader, self._write_line

    async def close(self, grace_seconds: float) -> None:
        # Nothing runs here to be given grace: that is a stdio server's.
        session_id = self._session_id
        self._end()
        if session_id is None:
            return
        headers = {"Mcp-Session-Id": session_id}
        if self._version is not None:
            headers["MCP-Protocol-Version"] = self._version
        # Best effort (R5): the server may be gone already, and nothing waits on the answer.
        with contextlib.suppress(Exception):
            await asyncio.to_thread(self._opener.delete, self._url, headers)

    def describe(self) -> str:
        return f"MCP server {self._name!r} (https {self._host})"

    # -- internals ------------------------------------------------------------------------

    async def _write_line(self, line: str) -> None:
        if not self._live:
            raise McpUnavailable(f"{self.describe()} is closed")
        # The line is the peer's own frame, a JSON object.
        sent = json.loads(line)
        initialize_id = sent.get("id") if sent.get("method") == "initialize" else None
        body = line.removesuffix("\n").encode("utf-8")
        try:
            reply = await asyncio.to_thread(self._opener.post, self._url, body, self._headers())
        except Exception as exc:
            # Only the type travels, and the cause is dropped: an opener's own message can carry
            # the URL's path and query.
            raise McpUnavailable(
                f"{self.describe()} could not complete the request: {type(exc).__name__}"
            ) from None
        if self._live:
            self._take(reply, initialize_id)
        # Otherwise the transport was closed while the request was out: the reply has nowhere
        # to go, and the session that sent it has already ended.

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": _ACCEPT}
        if self._session_id is not None:
            headers["Mcp-Session-Id"] = self._session_id
        if self._version is not None:
            headers["MCP-Protocol-Version"] = self._version
        return headers

    def _take(self, reply: HttpReply, initialize_id: object) -> None:
        status = reply.status
        if 300 <= status < 400:
            raise McpUnavailable(
                f"{self.describe()} answered HTTP {status}, a redirect, which is not followed"
            )
        if status == 404 and self._session_id is not None:
            # The server no longer knows the session: this conversation is over (R6).
            self._end()
            return
        if status == 202:
            return
        if status != 200:
            raise McpUnavailable(f"{self.describe()} answered HTTP {status}")
        if len(reply.body) > self._limit:
            raise McpUnavailable(f"{self.describe()} answered with more than {self._limit} bytes")
        headers = {name.lower(): value for name, value in reply.headers.items()}
        kind = headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if kind == "application/json":
            messages = [self._one_line(reply.body)]
        elif kind == "text/event-stream":
            messages = self._events(reply.body)
        else:
            raise McpUnavailable(
                f"{self.describe()} answered HTTP 200 with a content type that is neither "
                "application/json nor text/event-stream"
            )
        if initialize_id is not None:
            self._learn(headers, messages, initialize_id)
        reader = cast(asyncio.StreamReader, self._reader)
        for message in messages:
            reader.feed_data(message + b"\n")

    def _learn(self, headers: Mapping[str, str], messages: Sequence[bytes], msg_id: object) -> None:
        """Keep the session id and the agreed version from the reply to `initialize`."""
        session_id = headers.get("mcp-session-id")
        if session_id is not None:
            if not _SESSION_ID.fullmatch(session_id):
                raise McpUnavailable(
                    f"{self.describe()} gave a session id that is not visible ASCII"
                )
            self._session_id = session_id
        for raw in messages:
            try:
                message = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(message, dict) or message.get("id") != msg_id:
                continue
            result = message.get("result")
            version = result.get("protocolVersion") if isinstance(result, dict) else None
            if version in SUPPORTED_PROTOCOLS:
                self._version = cast(str, version)

    def _end(self) -> None:
        """End the stream the session reads, and forget the server's session."""
        self._live = False
        self._session_id = None
        if self._reader is not None:
            self._reader.feed_eof()

    @staticmethod
    def _one_line(body: bytes) -> bytes:
        """A JSON body as one line. In valid JSON a raw line break can only stand where
        whitespace may, so a space keeps the message and its meaning."""
        return _LINE_BREAK.sub(b" ", body)

    @staticmethod
    def _events(body: bytes) -> list[bytes]:
        """One message per server-sent event that carries data. An event's `data:` lines are
        joined with a space, for the reason `_one_line` gives; `event:`, `id:`, `retry:` and
        comments are ignored. A last event with no blank line after it is kept: a reply that
        has ended has nothing more to add to it."""
        events: list[bytes] = []
        data: list[bytes] = []
        for line in [*_LINE_BREAK.split(body), b""]:
            if not line:
                if data:
                    events.append(b" ".join(data))
                    data = []
            elif line.startswith(b"data:"):
                value = line[len(b"data:") :]
                data.append(value[1:] if value.startswith(b" ") else value)
        return events
