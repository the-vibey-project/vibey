# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The streamable HTTP transport and its opener: no redirect, no cookie, no credential, no
environment, and a bounded reply (SP-LOOPS Phase 5, Task 4; R6, R13, R15).

No socket is opened anywhere. The transport is driven through `FakeServer`, a recording opener
that is a scripted MCP server. The real `HttpOpener` is driven through `FakeHttps`, an
`HTTPSHandler` whose `https_open` hands back a scripted response, so the whole urllib handler
chain (proxy, redirect, error processing) runs as it would against a server. Module-level test
functions rather than a class with an interface beside it (ADR-0016).
"""

from __future__ import annotations

import asyncio
import email.message
import io
import json
import ssl
import threading
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator, Mapping
from typing import Any

import pytest

from vibey_runners.common.mcp.http_opener import HttpOpener
from vibey_runners.common.mcp.http_reply import HttpReply
from vibey_runners.common.mcp.http_transport import HttpTransport
from vibey_runners.common.mcp.interfaces.http_opener_interface import HttpOpenerInterface
from vibey_runners.common.mcp.interfaces.mcp_transport_interface import McpTransportInterface
from vibey_runners.common.mcp.mcp_call_result import McpCallResult
from vibey_runners.common.mcp.mcp_errors import McpUnavailable
from vibey_runners.common.mcp.mcp_session import McpSession
from vibey_runners.common.mcp.protocol import LATEST_PROTOCOL

URL = "https://mcp.example.test/secret-path/mcp?token=query-secret"
HOST = "mcp.example.test"
BASE = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
ENV_SECRET = "env-sentinel-7f3a"
Override = Callable[[dict[str, Any], Mapping[str, str]], HttpReply | None]


def json_reply(message: Mapping[str, Any], headers: Mapping[str, str] | None = None) -> HttpReply:
    return HttpReply(
        200, {"Content-Type": "application/json", **(headers or {})}, json.dumps(message).encode()
    )


def sse_reply(text: str) -> HttpReply:
    return HttpReply(200, {"Content-Type": "text/event-stream; charset=utf-8"}, text.encode())


class FakeServer:
    """A recording opener that is a streamable HTTP MCP server. It agrees to the offered version
    (or `version`), gives `session_id` on `initialize`, lists `echo`, echoes calls and answers
    every notification and response 202. `override` may answer any request first."""

    def __init__(
        self,
        *,
        session_id: str | None = "sess-1",
        version: str | None = None,
        override: Override | None = None,
        delete_error: Exception | None = None,
    ) -> None:
        self.session_id = session_id
        self.version = version
        self.override = override
        self.delete_error = delete_error
        self.posts: list[tuple[str, bytes, dict[str, str]]] = []
        self.deletes: list[tuple[str, dict[str, str]]] = []

    def post(self, url: str, body: bytes, headers: Mapping[str, str]) -> HttpReply:
        self.posts.append((url, body, dict(headers)))
        message = json.loads(body)
        if self.override is not None:
            reply = self.override(message, headers)
            if reply is not None:
                return reply
        method = message.get("method")
        if "id" not in message or method is None:
            return HttpReply(202, {}, b"")
        if method == "initialize":
            extra = {"Mcp-Session-Id": self.session_id} if self.session_id else {}
            version = self.version or message["params"]["protocolVersion"]
            return json_reply(_result(message, {"protocolVersion": version}), extra)
        if method == "tools/list":
            tool = {"name": "echo", "description": "Echo.", "inputSchema": {"type": "object"}}
            return json_reply(_result(message, {"tools": [tool]}))
        text = json.dumps(message["params"]["arguments"], sort_keys=True)
        return json_reply(_result(message, {"content": [{"type": "text", "text": text}]}))

    def delete(self, url: str, headers: Mapping[str, str]) -> int:
        self.deletes.append((url, dict(headers)))
        if self.delete_error is not None:
            raise self.delete_error
        return 204

    def methods(self) -> list[str]:
        return [str(json.loads(body).get("method")) for _, body, _ in self.posts]


def _result(request: Mapping[str, Any], result: Mapping[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request["id"], "result": dict(result)}


def _transport(server: FakeServer, **options: Any) -> HttpTransport:
    return HttpTransport("remote", URL, timeout_seconds=5.0, opener=server, **options)


def _session(transport: HttpTransport) -> McpSession:
    return McpSession(transport, client_name="test", client_version="0", timeout_seconds=30.0)


def _request(method: str, msg_id: str = "c-1", **params: Any) -> str:
    return json.dumps({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params}) + "\n"


# -- the transport over a recording opener -------------------------------------------------


async def test_initialize_keeps_the_session_id_and_sends_it_with_the_protocol_version_after() -> (
    None
):
    server = FakeServer(version="2025-03-26")
    transport = _transport(server)
    assert isinstance(transport, McpTransportInterface)
    assert isinstance(server, HttpOpenerInterface)
    session = _session(transport)
    await session.start()
    assert await session.call("echo", {"q": 1}) == McpCallResult('{"q": 1}', False)
    assert server.methods() == ["initialize", "notifications/initialized", "tools/call"]
    first, *later = (headers for _, _, headers in server.posts)
    assert first == BASE
    agreed = {**BASE, "Mcp-Session-Id": "sess-1", "MCP-Protocol-Version": "2025-03-26"}
    assert later == [agreed, agreed]
    assert {url for url, _, _ in server.posts} == {URL}
    assert all(not body.endswith(b"\n") for _, body, _ in server.posts)
    await session.close(5.0)


async def test_without_a_session_id_only_the_protocol_version_is_added() -> None:
    server = FakeServer(session_id=None)
    session = _session(_transport(server))
    await session.start()
    await session.list_tools()
    assert [headers for _, _, headers in server.posts][1:] == [
        {**BASE, "MCP-Protocol-Version": LATEST_PROTOCOL}
    ] * 2
    await session.close(5.0)
    assert server.deletes == []


async def test_only_the_initialize_reply_is_learned_from() -> None:
    # A later reply cannot switch the session id, and an initialize reply whose version this
    # client does not speak, or whose frames are not that reply, teaches the transport nothing.
    def answer(message: dict[str, Any], headers: Mapping[str, str]) -> HttpReply | None:
        if message.get("method") == "tools/list":
            return json_reply(_result(message, {"tools": []}), {"Mcp-Session-Id": "other"})
        return None

    server = FakeServer(override=answer)
    transport = _transport(server)
    reader, write = await transport.open()
    await write(_request("initialize", "i-1", protocolVersion=LATEST_PROTOCOL))
    await reader.readline()
    await write(_request("tools/list", "c-2"))
    await reader.readline()
    await write(_request("tools/list", "c-3"))
    assert server.posts[-1][2]["Mcp-Session-Id"] == "sess-1"

    frames = "\n\n".join(
        [
            "data: not json",
            "data: [1]",
            'data: {"jsonrpc": "2.0", "id": "other", "result": {"protocolVersion": "2025-06-18"}}',
            'data: {"jsonrpc": "2.0", "id": "i-9", "error": {"code": 1, "message": "no"}}',
            'data: {"jsonrpc": "2.0", "id": "i-9", "result": {"protocolVersion": "1999-01-01"}}',
            'data: {"jsonrpc": "2.0", "id": "i-9", "result": {"protocolVersion": 7}}',
        ]
    )
    odd = FakeServer(override=lambda m, h: sse_reply(frames) if m["id"] == "i-9" else None)
    transport = _transport(odd)
    reader, write = await transport.open()
    await write(_request("initialize", "i-9", protocolVersion=LATEST_PROTOCOL))
    await write(_request("tools/list", "c-1"))
    assert odd.posts[-1][2] == BASE
    await transport.close(0.0)


async def test_an_event_stream_reply_feeds_each_event_as_one_message() -> None:
    stream = (
        ": a comment the server keeps the stream alive with\r\n"
        "event: message\r\n"
        'data: {"jsonrpc": "2.0", "id": "s-1", "method": "ping"}\r\n'
        "\r\n"
        "event: nothing-to-say\n"
        "\n"
        "id: 7\r"
        'data:{"jsonrpc": "2.0", "id": "c-1",\r'
        'data:  "result": {"content": [{"type": "text", "text": "streamed"}]}}\r'
        "\r"
    )
    server = FakeServer(override=lambda message, headers: sse_reply(stream))
    transport = _transport(server)
    reader, write = await transport.open()
    await write(_request("tools/call", "c-1", name="echo", arguments={}))
    ping = await reader.readline()
    answer = await reader.readline()
    assert json.loads(ping) == {"jsonrpc": "2.0", "id": "s-1", "method": "ping"}
    assert answer.count(b"\n") == 1
    assert json.loads(answer)["result"]["content"][0]["text"] == "streamed"
    await transport.close(0.0)
    assert await reader.read() == b""


async def test_a_session_reads_its_answer_from_an_event_stream() -> None:
    def stream(message: dict[str, Any], headers: Mapping[str, str]) -> HttpReply | None:
        if message.get("method") != "tools/call":
            return None
        body = json.dumps(_result(message, {"content": [{"type": "text", "text": "ok"}]}))
        return sse_reply(f": hello\n\nevent: message\ndata: {body}\n\n")

    session = _session(_transport(FakeServer(override=stream)))
    await session.start()
    assert await session.call("echo", {}) == McpCallResult("ok", False)
    await session.close(0.0)


async def test_a_pretty_printed_json_reply_is_fed_as_one_line() -> None:
    def pretty(message: dict[str, Any], headers: Mapping[str, str]) -> HttpReply:
        body = json.dumps(_result(message, {"ok": True}), indent=2).replace("\n", "\r\n")
        return HttpReply(200, {"content-type": "Application/JSON; charset=utf-8"}, body.encode())

    transport = _transport(FakeServer(override=pretty))
    reader, write = await transport.open()
    await write(_request("tools/list"))
    line = await reader.readline()
    assert line.count(b"\n") == 1
    assert b"\r" not in line
    assert json.loads(line)["result"] == {"ok": True}
    await transport.close(0.0)


async def test_a_202_feeds_nothing() -> None:
    def accepted(message: dict[str, Any], headers: Mapping[str, str]) -> HttpReply | None:
        if message.get("method") == "notifications/initialized":
            return HttpReply(202, {"Content-Type": "application/json"}, b'{"ignored": true}')
        return None

    transport = _transport(FakeServer(override=accepted))
    reader, write = await transport.open()
    await write('{"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}\n')
    await write(_request("tools/list", "c-2"))
    # The first line on the stream is the answer to the request: the 202 put nothing there.
    assert json.loads(await reader.readline())["id"] == "c-2"
    await transport.close(0.0)


async def test_a_404_with_a_session_ends_the_session() -> None:
    def gone(message: dict[str, Any], headers: Mapping[str, str]) -> HttpReply | None:
        return HttpReply(404, {}, b"") if message.get("method") == "tools/call" else None

    server = FakeServer(override=gone)
    transport = _transport(server)
    session = _session(transport)
    await session.start()
    with pytest.raises(McpUnavailable) as caught:
        await session.call("echo", {})
    assert (
        str(caught.value)
        == f"MCP server 'remote' (https {HOST}) closed its stream during tools/call"
    )
    assert not session.alive
    # The server said the session is gone: it is not asked to delete it.
    assert server.deletes == []


async def test_a_write_after_close_is_refused_without_a_request() -> None:
    server = FakeServer()
    transport = _transport(server)
    _, write = await transport.open()
    await transport.close(0.0)
    with pytest.raises(McpUnavailable) as caught:
        await write(_request("tools/list"))
    assert str(caught.value) == f"MCP server 'remote' (https {HOST}) is closed"
    assert server.posts == []


async def test_a_404_without_a_session_is_a_status_error() -> None:
    def gone(message: dict[str, Any], headers: Mapping[str, str]) -> HttpReply | None:
        return HttpReply(404, {}, b"") if message.get("method") == "tools/call" else None

    session = _session(_transport(FakeServer(session_id=None, override=gone)))
    await session.start()
    with pytest.raises(McpUnavailable) as caught:
        await session.call("echo", {})
    assert str(caught.value) == f"MCP server 'remote' (https {HOST}) answered HTTP 404"
    assert not session.alive


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
async def test_a_redirect_is_refused_and_names_only_the_host(status: int) -> None:
    location = "https://elsewhere.example.test/location-secret?k=location-query"
    server = FakeServer(override=lambda m, h: HttpReply(status, {"Location": location}, b""))
    session = _session(_transport(server))
    with pytest.raises(McpUnavailable) as caught:
        await session.start()
    message = str(caught.value)
    assert message == (
        f"MCP server 'remote' (https {HOST}) answered HTTP {status}, a redirect, which is not "
        "followed"
    )
    for leaked in ("secret-path", "query-secret", "location-secret", "elsewhere", "location-query"):
        assert leaked not in message
    assert len(server.posts) == 1
    assert not session.alive


@pytest.mark.parametrize("status", [200, 201, 204, 400, 401, 500])
async def test_any_other_status_or_content_type_is_refused_naming_only_the_host(
    status: int,
) -> None:
    reply = HttpReply(
        status,
        {"Content-Type": "text/html", "Set-Cookie": "c=header-secret"},
        b"<p>body-secret</p>",
    )
    transport = _transport(FakeServer(override=lambda m, h: reply))
    _, write = await transport.open()
    with pytest.raises(McpUnavailable) as caught:
        await write(_request("tools/list"))
    expected = (
        f"MCP server 'remote' (https {HOST}) answered HTTP 200 with a content type that is "
        "neither application/json nor text/event-stream"
        if status == 200
        else f"MCP server 'remote' (https {HOST}) answered HTTP {status}"
    )
    assert str(caught.value) == expected
    await transport.close(0.0)


async def test_a_reply_over_the_limit_is_refused() -> None:
    def sized(size: int) -> Override:
        def answer(message: dict[str, Any], headers: Mapping[str, str]) -> HttpReply:
            frame = json.dumps(_result(message, {"pad": ""}))
            body = frame.replace('"pad": ""', '"pad": "' + "x" * (size - len(frame)) + '"')
            assert len(body) == size
            return HttpReply(200, {"Content-Type": "application/json"}, body.encode())

        return answer

    transport = _transport(FakeServer(override=sized(200)), limit_bytes=200)
    reader, write = await transport.open()
    await write(_request("tools/list"))
    assert len(await reader.readline()) == 201

    transport = _transport(FakeServer(override=sized(201)), limit_bytes=200)
    _, write = await transport.open()
    with pytest.raises(McpUnavailable) as caught:
        await write(_request("tools/list"))
    assert (
        str(caught.value) == f"MCP server 'remote' (https {HOST}) answered with more than 200 bytes"
    )


async def test_an_opener_failure_names_only_its_type() -> None:
    def fails(message: dict[str, Any], headers: Mapping[str, str]) -> HttpReply:
        raise urllib.error.URLError(f"cannot reach {URL} with {ENV_SECRET}")

    session = _session(_transport(FakeServer(override=fails)))
    with pytest.raises(McpUnavailable) as caught:
        await session.start()
    assert str(caught.value) == (
        f"MCP server 'remote' (https {HOST}) could not complete the request: URLError"
    )
    assert not session.alive


async def test_a_session_id_that_is_not_visible_ascii_is_refused_and_not_repeated() -> None:
    session = _session(_transport(FakeServer(session_id="two words-secret")))
    with pytest.raises(McpUnavailable) as caught:
        await session.start()
    assert str(caught.value) == (
        f"MCP server 'remote' (https {HOST}) gave a session id that is not visible ASCII"
    )
    assert "secret" not in str(caught.value)


async def test_a_remote_request_carries_no_environment_cookie_or_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("ANTHROPIC_API_KEY", "VIBEY_HOST_TOKEN", "BRAVE_API_KEY", "GITHUB_TOKEN"):
        monkeypatch.setenv(name, ENV_SECRET)
    monkeypatch.setenv("HTTPS_PROXY", f"https://user:{ENV_SECRET}@proxy.example.test:8080")

    def stream(message: dict[str, Any], headers: Mapping[str, str]) -> HttpReply | None:
        if message.get("method") == "tools/call":
            return HttpReply(
                200,
                {"Content-Type": "application/json", "Set-Cookie": "jar=cookie-secret"},
                json.dumps(_result(message, {"content": []})).encode(),
            )
        return None

    server = FakeServer(override=stream)
    session = _session(_transport(server))
    await session.start()
    await session.call("echo", {"x": 1})
    await session.call("echo", {"x": 2})
    await session.close(0.0)
    allowed = {"Content-Type", "Accept", "Mcp-Session-Id", "MCP-Protocol-Version"}
    assert server.posts[0][2] == BASE
    for url, body, headers in server.posts:
        assert set(headers) <= allowed
        assert "cookie-secret" not in "".join(headers.values())
        assert ENV_SECRET not in url + body.decode() + json.dumps(headers)
    for url, headers in server.deletes:
        assert set(headers) == {"Mcp-Session-Id", "MCP-Protocol-Version"}
        assert ENV_SECRET not in url + json.dumps(headers)


async def test_close_deletes_the_session_and_ignores_a_failure() -> None:
    server = FakeServer()
    transport = _transport(server)
    session = _session(transport)
    await session.start()
    await session.close(5.0)
    assert server.deletes == [
        (URL, {"Mcp-Session-Id": "sess-1", "MCP-Protocol-Version": LATEST_PROTOCOL})
    ]
    await transport.close(5.0)
    assert len(server.deletes) == 1

    failing = FakeServer(delete_error=urllib.error.URLError("refused"))
    transport = _transport(failing)
    reader, write = await transport.open()
    await write(_request("initialize", "i-1", protocolVersion=LATEST_PROTOCOL))
    await reader.readline()
    await transport.close(0.0)
    assert len(failing.deletes) == 1
    assert reader.at_eof()

    # A session id with no agreed version is deleted with the id alone.
    unspoken = FakeServer(version="1999-01-01")
    transport = _transport(unspoken)
    reader, write = await transport.open()
    await write(_request("initialize", "i-1", protocolVersion=LATEST_PROTOCOL))
    await transport.close(0.0)
    assert unspoken.deletes == [(URL, {"Mcp-Session-Id": "sess-1"})]


async def test_close_before_open_does_nothing_and_open_starts_afresh() -> None:
    server = FakeServer()
    transport = _transport(server)
    await transport.close(0.0)
    assert server.deletes == []
    for _ in range(2):
        session = _session(transport)
        await session.start()
        await session.close(0.0)
    # The second session began with no session id or version of the first.
    initializes = [h for (_, body, h) in server.posts if b'"initialize"' in body]
    assert initializes == [BASE, BASE]
    assert len(server.deletes) == 2


async def test_a_reply_that_arrives_after_close_is_dropped() -> None:
    release = threading.Event()

    def slow(message: dict[str, Any], headers: Mapping[str, str]) -> HttpReply:
        release.wait(30)
        return json_reply(_result(message, {}))

    transport = _transport(FakeServer(override=slow))
    reader, write = await transport.open()
    pending: asyncio.Future[None] = asyncio.ensure_future(write(_request("tools/list")))
    # One turn of the loop runs the write up to its first wait: the request, out in a thread.
    await asyncio.sleep(0)
    await transport.close(0.0)
    release.set()
    await pending
    assert await reader.read() == b""


def test_a_url_that_is_not_https_with_a_host_is_refused() -> None:
    for url in ("http://mcp.example.test/", "https:///no-host", "file:///etc/passwd"):
        with pytest.raises(ValueError, match="needs an https:// URL with a host"):
            HttpTransport("remote", url, timeout_seconds=1.0, opener=FakeServer())


def test_describe_names_the_host_only() -> None:
    transport = HttpTransport("remote", URL, timeout_seconds=1.0, opener=FakeServer())
    assert transport.describe() == f"MCP server 'remote' (https {HOST})"


# -- the real opener, with a scripted HTTPS handler in place of the socket -------------------


class FakeResponse:
    """What `HTTPSHandler.https_open` returns, without a socket; reads at most `chunk` bytes."""

    def __init__(
        self, status: int, headers: Mapping[str, str], body: bytes = b"", *, chunk: int = 7
    ) -> None:
        self.code = self.status = status
        self.msg = "Reason"
        self.headers = email.message.Message()
        for name, value in headers.items():
            self.headers[name] = value
        self._body = io.BytesIO(body)
        self._chunk = chunk
        self.reads: list[int] = []
        self.closed = False

    def info(self) -> email.message.Message:
        return self.headers

    def read1(self, size: int) -> bytes:
        self.reads.append(size)
        return self._body.read(min(size, self._chunk))

    def read(self, size: int = -1) -> bytes:  # what HTTPError's file wrapper may use
        return self._body.read(size)

    def close(self) -> None:
        self.closed = True


class FakeHttps(urllib.request.HTTPSHandler):
    def __init__(self, *responses: FakeResponse) -> None:
        super().__init__()
        self.responses = list(responses)
        self.requests: list[urllib.request.Request] = []

    def https_open(self, req: urllib.request.Request) -> Any:
        self.requests.append(req)
        return self.responses.pop(0)


def _ticks(*values: float) -> Callable[[], float]:
    it: Iterator[float] = iter(values)
    return lambda: next(it)


def test_the_real_opener_follows_no_redirect() -> None:
    opener = HttpOpener(5.0)
    assert isinstance(opener, HttpOpenerInterface)
    handlers = opener.handlers
    assert not any(isinstance(h, urllib.request.HTTPCookieProcessor) for h in handlers)
    redirects = [h for h in handlers if isinstance(h, urllib.request.HTTPRedirectHandler)]
    assert len(redirects) == 1
    # `ProxyHandler({})` displaces the default one and, having no scheme to proxy, is not in
    # the chain at all: no proxy from the environment is ever used.
    assert not any(isinstance(h, urllib.request.ProxyHandler) for h in handlers)
    https = [h for h in handlers if isinstance(h, urllib.request.HTTPSHandler)]
    assert len(https) == 1
    context = https[0]._context  # type: ignore[attr-defined]
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname

    for status in (301, 302, 303, 307, 308):
        location = {"Location": "https://elsewhere.example.test/next"}
        handler = FakeHttps(FakeResponse(status, location))
        reply = HttpOpener(5.0, https_handler=handler).post(URL, b"{}", BASE)
        assert reply.status == status
        assert reply.body == b""
        assert [r.full_url for r in handler.requests] == [URL]


def test_the_real_opener_sends_exactly_the_given_headers_and_no_proxy_or_cookie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", f"https://user:{ENV_SECRET}@proxy.example.test:8080")
    monkeypatch.setenv("https_proxy", f"https://user:{ENV_SECRET}@proxy.example.test:8080")
    monkeypatch.setenv("ANTHROPIC_API_KEY", ENV_SECRET)
    handler = FakeHttps(
        FakeResponse(200, {"Content-Type": "application/json", "Set-Cookie": "a=b"}, b'{"ok": 1}'),
        FakeResponse(200, {"Content-Type": "application/json"}, b"{}"),
    )
    opener = HttpOpener(5.0, https_handler=handler)
    reply = opener.post(URL, b'{"q": 1}', {**BASE, "Mcp-Session-Id": "s"})
    assert reply == HttpReply(
        200, {"content-type": "application/json", "set-cookie": "a=b"}, b'{"ok": 1}'
    )
    opener.post(URL, b"{}", BASE)
    first, second = handler.requests
    assert first.get_method() == "POST"
    assert first.data == b'{"q": 1}'
    assert first.timeout == 5.0
    # The given headers, and only what HTTP itself needs (urllib adds `Host` and
    # `Content-length`): no User-Agent, Cookie, Authorization or Proxy-Authorization.
    assert dict(first.header_items()) == {
        "Content-type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Mcp-session-id": "s",
        "Content-length": "8",
        "Host": HOST,
    }
    # Not tunnelled through the environment's proxy, and the jar from the first reply is not
    # sent back on the second.
    assert first.host == HOST
    assert getattr(first, "_tunnel_host", None) is None
    assert not second.has_header("Cookie")
    for request in handler.requests:
        assert ENV_SECRET not in json.dumps(request.header_items())


def test_the_real_opener_reads_at_most_one_byte_past_the_limit() -> None:
    response = FakeResponse(200, {"Content-Type": "application/json"}, b"x" * 50, chunk=4)
    opener = HttpOpener(5.0, limit_bytes=10, https_handler=FakeHttps(response))
    reply = opener.post(URL, b"{}", BASE)
    assert reply.body == b"x" * 11
    assert response.reads == [11, 7, 3]
    assert response.closed

    whole = FakeResponse(200, {}, b"abc")
    assert HttpOpener(5.0, https_handler=FakeHttps(whole)).post(URL, b"", BASE).body == b"abc"


def test_the_real_opener_gives_up_on_a_reply_that_trickles_past_its_deadline() -> None:
    response = FakeResponse(200, {}, b"y" * 40, chunk=4)
    opener = HttpOpener(5.0, https_handler=FakeHttps(response), clock=_ticks(100.0, 101.0, 106.0))
    with pytest.raises(TimeoutError, match=r"longer than 5s"):
        opener.post(URL, b"{}", BASE)
    assert response.closed


def test_the_real_opener_returns_an_error_status_without_reading_its_body() -> None:
    response = FakeResponse(500, {"Content-Type": "text/plain"}, b"body-secret")
    reply = HttpOpener(5.0, https_handler=FakeHttps(response)).post(URL, b"{}", BASE)
    assert reply == HttpReply(500, {"content-type": "text/plain"}, b"")
    assert response.reads == []


def test_the_real_opener_deletes_and_returns_the_status() -> None:
    handler = FakeHttps(FakeResponse(204, {}), FakeResponse(405, {}))
    opener = HttpOpener(5.0, https_handler=handler)
    assert opener.delete(URL, {"Mcp-Session-Id": "s"}) == 204
    assert opener.delete(URL, {"Mcp-Session-Id": "s"}) == 405
    assert [r.get_method() for r in handler.requests] == ["DELETE", "DELETE"]
    assert handler.requests[0].data is None


def test_the_real_opener_refuses_a_url_that_is_not_https() -> None:
    handler = FakeHttps()
    opener = HttpOpener(5.0, https_handler=handler)
    for url in ("http://mcp.example.test/", "file:///etc/passwd", "data:,x"):
        with pytest.raises(ValueError, match="over https only"):
            opener.post(url, b"{}", BASE)
        with pytest.raises(ValueError, match="over https only"):
            opener.delete(url, {})
    assert handler.requests == []
