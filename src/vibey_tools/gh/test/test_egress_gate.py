# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The runner's egress gate: the only way out of the job container (ADR-0083).

Found on 2026-10-09 by trying it: from inside the runner container the host's Postgres (5432)
and RabbitMQ (5672, 15672) accepted connections, because `--add-host host-gateway` exposes
every host port and the agent's shell had full network egress (`allow_network=False` only set
an environment variable). The gate is what makes "unreachable" true by construction.
"""

from __future__ import annotations

import asyncio
import functools
import importlib.util
import sys
from collections.abc import Sequence
from pathlib import Path


def sync(test):
    """Runs a coroutine test to completion: the tenant's CI installs no async pytest plugin."""

    @functools.wraps(test)
    def wrapper(*args, **kwargs):
        return asyncio.run(test(*args, **kwargs))

    return wrapper


GATE_DIR = Path(__file__).resolve().parents[1] / "vibey_gh" / "templates" / "runner" / "egress"


def load_gate():
    sys.path.insert(0, str(GATE_DIR))
    spec = importlib.util.spec_from_file_location(
        "egress_gate_under_test", GATE_DIR / "egress_gate.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = load_gate()

ALLOW = ["github.com", "api.github.com", "*.actions.githubusercontent.com", "pypi.org"]


def test_only_declared_hosts_on_443_are_reachable() -> None:
    policy = gate.HostPolicy(ALLOW)
    assert policy.allows("github.com", 443) and policy.allows("API.GitHub.com.", 443)
    assert policy.allows("pipelines.actions.githubusercontent.com", 443)
    assert not policy.allows("github.com", 22) and not policy.allows("github.com", 80)
    assert not policy.allows("evil.com", 443) and not policy.allows("github.com.evil.com", 443)
    assert not policy.allows("notgithub.com", 443)
    # The host's own services, by every spelling.
    for host in ("host.docker.internal", "localhost", "gateway.docker.internal"):
        assert not policy.allows(host, 443)
    for port in (5432, 5672, 15672, 11434):
        assert not policy.allows("host.docker.internal", port)


def test_an_address_literal_is_never_a_declared_host() -> None:
    policy = gate.HostPolicy(["*"])  # even an allow-everything pattern
    for literal in ("127.0.0.1", "192.168.65.254", "10.0.0.1", "140.82.112.3", "[::1]", "::1"):
        assert not policy.allows(literal, 443)


def test_only_globally_routable_addresses_are_dialled() -> None:
    policy = gate.HostPolicy(ALLOW)
    assert policy.public("140.82.112.3") and policy.public("2606:50c0:8000::154")
    for private in (
        "127.0.0.1",
        "10.1.2.3",
        "172.17.0.1",
        "192.168.65.254",
        "169.254.169.254",
        "100.64.0.1",
        "::1",
        "fe80::1",
        "fd00::1",
        "0.0.0.0",
        "not an address",
    ):
        assert not policy.public(private), private


def test_the_model_server_gets_four_requests_and_nothing_else() -> None:
    policy = gate.RequestPolicy()
    assert policy.allows("POST", "/v1/chat/completions") and policy.allows("get", "/api/version")
    assert policy.allows("GET", "/api/tags") and policy.allows("GET", "/v1/models?x=1")
    # The agent must not manage the operator's models.
    for method, target in (
        ("DELETE", "/api/delete"),
        ("POST", "/api/pull"),
        ("POST", "/api/create"),
        ("POST", "/api/push"),
        ("POST", "/api/generate"),
        ("GET", "/api/ps"),
        ("POST", "/v1/chat/completions/../../api/delete"),
        ("GET", "/v1/chat/completions"),
        ("POST", "/api/tags"),
    ):
        assert not policy.allows(method, target), (method, target)


def test_the_forwarded_head_carries_one_request_and_closes() -> None:
    head = (
        b"POST /v1/chat/completions HTTP/1.1\r\nHost: x\r\nConnection: keep-alive\r\n"
        b"Keep-Alive: 300\r\nUpgrade: websocket\r\nTE: trailers\r\nContent-Length: 2\r\n\r\n"
    )
    out = gate.ModelGate.one_request(head)
    assert out.startswith(b"POST /v1/chat/completions HTTP/1.1\r\n")
    assert out.endswith(b"Content-Length: 2\r\nConnection: close\r\n\r\n")
    for dropped in (b"keep-alive", b"Upgrade", b"TE:"):
        assert dropped.lower() not in out.lower().replace(b"connection: close", b"")


class FakeResolver:
    def __init__(self, table: dict[str, list[str]]) -> None:
        self._table = table

    async def resolve(self, host: str, port: int) -> Sequence[str]:
        return self._table.get(host, [])


class LocalDialer:
    """Connects every 'outbound' request to a local test server, and records what was asked."""

    def __init__(self, port: int) -> None:
        self.port, self.asked = port, []

    async def open(self, address: str, port: int):
        self.asked.append((address, port))
        return await asyncio.open_connection("127.0.0.1", self.port)


async def serve(handler):
    server = await asyncio.start_server(handler, "127.0.0.1", 0)
    return server, server.sockets[0].getsockname()[1]


async def exchange(port: int, payload: bytes) -> bytes:
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(payload)
    await writer.drain()
    data = await asyncio.wait_for(reader.read(65536), timeout=5)
    writer.close()
    return data


@sync
async def test_connect_reaches_a_declared_public_host_and_nothing_else() -> None:
    async def echo(reader, writer):
        writer.write(b"PONG:" + await reader.read(16))
        await writer.drain()
        writer.close()

    upstream, upstream_port = await serve(echo)
    dialer = LocalDialer(upstream_port)
    resolver = FakeResolver(
        {
            "github.com": ["140.82.112.3"],
            "pypi.org": ["151.101.0.223", "10.0.0.5"],  # one address is private
            "api.github.com": [],  # does not resolve
        }
    )
    proxy = gate.ConnectProxy(gate.HostPolicy(ALLOW), resolver, dialer)
    front, port = await serve(proxy.handle)
    try:
        ok = await exchange(
            port, b"CONNECT github.com:443 HTTP/1.1\r\nHost: github.com:443\r\n\r\n"
        )
        assert ok.startswith(b"HTTP/1.1 200")
        assert dialer.asked == [("140.82.112.3", 443)]
        asked = len(dialer.asked)
        for request, status in (
            (b"CONNECT host.docker.internal:5432 HTTP/1.1\r\n\r\n", b"403"),
            (b"CONNECT github.com:5432 HTTP/1.1\r\n\r\n", b"403"),
            (b"CONNECT 127.0.0.1:443 HTTP/1.1\r\n\r\n", b"403"),
            (b"CONNECT pypi.org:443 HTTP/1.1\r\n\r\n", b"403"),  # also points at the LAN
            (b"CONNECT api.github.com:443 HTTP/1.1\r\n\r\n", b"403"),  # does not resolve
            (b"GET http://github.com/ HTTP/1.1\r\n\r\n", b"405"),
            (b"CONNECT nonsense\r\n\r\n", b"405"),
            (b"CONNECT github.com:x HTTP/1.1\r\n\r\n", b"403"),
        ):
            answer = await exchange(port, request)
            assert status in answer.split(b"\r\n", 1)[0], (request, answer)
        assert len(dialer.asked) == asked  # not one of them was dialled
    finally:
        front.close()
        upstream.close()


@sync
async def test_a_failing_upstream_is_a_bad_gateway_and_a_huge_head_is_refused() -> None:
    class Down:
        async def open(self, address: str, port: int):
            raise ConnectionRefusedError

    proxy = gate.ConnectProxy(
        gate.HostPolicy(ALLOW), FakeResolver({"github.com": ["140.82.112.3"]}), Down()
    )
    front, port = await serve(proxy.handle)
    try:
        answer = await exchange(port, b"CONNECT github.com:443 HTTP/1.1\r\n\r\n")
        assert b"502" in answer.split(b"\r\n", 1)[0]
        answer = await exchange(
            port, b"CONNECT github.com:443 HTTP/1.1\r\n" + b"X: y\r\n" * 5000 + b"\r\n"
        )
        assert b"400" in answer.split(b"\r\n", 1)[0]
    finally:
        front.close()


@sync
async def test_the_model_gate_forwards_a_chat_and_refuses_model_management() -> None:
    seen: list[bytes] = []

    async def ollama(reader, writer):
        seen.append(await reader.readuntil(b"\r\n\r\n"))
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
        await writer.drain()
        writer.close()

    upstream, upstream_port = await serve(ollama)
    dialer = LocalDialer(upstream_port)
    model = gate.ModelGate(("host.docker.internal", 11434), dialer=dialer)
    front, port = await serve(model.handle)
    try:
        chat = (
            b"POST /v1/chat/completions HTTP/1.1\r\nHost: g\r\nConnection: keep-alive\r\n"
            b"Content-Length: 0\r\n\r\n"
        )
        answer = await exchange(port, chat)
        assert answer.startswith(b"HTTP/1.1 200") and answer.endswith(b"ok")
        assert dialer.asked == [("host.docker.internal", 11434)]
        assert b"Connection: close" in seen[0] and b"keep-alive" not in seen[0].lower()
        for request in (
            b"DELETE /api/delete HTTP/1.1\r\nHost: g\r\n\r\n",
            b"POST /api/pull HTTP/1.1\r\nHost: g\r\n\r\n",
            b"POST /api/create HTTP/1.1\r\nHost: g\r\n\r\n",
        ):
            assert b"403" in (await exchange(port, request)).split(b"\r\n", 1)[0]
        assert len(seen) == 1 and len(dialer.asked) == 1  # the host never heard of them
        assert b"403" in (await exchange(port, b"nonsense\r\n\r\n")).split(b"\r\n", 1)[0]
    finally:
        front.close()
        upstream.close()


@sync
async def test_the_model_gate_says_bad_gateway_when_the_host_model_is_down() -> None:
    class Down:
        async def open(self, address: str, port: int):
            raise ConnectionRefusedError

    front, port = await serve(gate.ModelGate(("h", 1), dialer=Down()).handle)
    try:
        answer = await exchange(port, b"GET /api/version HTTP/1.1\r\nHost: g\r\n\r\n")
        assert b"502" in answer.split(b"\r\n", 1)[0]
    finally:
        front.close()


@sync
async def test_the_system_resolver_and_dialer_are_real() -> None:
    assert await gate.SystemResolver().resolve("localhost", 80)
    assert await gate.SystemResolver().resolve("no-such-host.invalid", 443) == []

    async def hello(reader, writer):
        writer.write(b"hi")
        await writer.drain()
        writer.close()

    server, port = await serve(hello)
    try:
        reader, writer = await gate.TcpDialer().open("127.0.0.1", port)
        assert await reader.read(2) == b"hi"
        writer.close()
    finally:
        server.close()


def test_the_gate_is_configured_from_the_environment() -> None:
    seen = gate.Gate({"EGRESS_ALLOW": "a.com, b.com", "EGRESS_MODEL_UPSTREAM": "m:1"})
    assert seen._env["EGRESS_ALLOW"] == "a.com, b.com"


def test_the_shipped_default_reaches_githubs_storage_and_not_one_anyone_can_register() -> None:
    from vibey_gh.config import RunnersConfig

    policy = gate.HostPolicy(list(RunnersConfig().egress_allow))
    for n in range(20):
        assert policy.allows(f"productionresultssa{n}.blob.core.windows.net", 443)
    for host in (
        "productionresultssaz.blob.core.windows.net",
        "productionresultssa.blob.core.windows.net",
        "productionresultssa0.evil.blob.core.windows.net",
        "productionresultssa20.blob.core.windows.net.evil.com",
        "attacker.blob.core.windows.net",
        "x.github.io",
        "bucket.s3.amazonaws.com",
    ):
        assert not policy.allows(host, 443), host
    assert policy.allows("pipelines.actions.githubusercontent.com", 443)
    assert policy.allows("objects.githubusercontent.com", 443)


class Sink:
    """A writer that can fail the way a dead socket does."""

    def __init__(self, drain_error: bool = False, close_error: bool = False) -> None:
        self.drain_error, self.close_error = drain_error, close_error
        self.written: list[bytes] = []
        self.closed = False

    def write(self, data: bytes) -> None:
        self.written.append(data)

    async def drain(self) -> None:
        if self.drain_error:
            raise ConnectionResetError

    def close(self) -> None:
        self.closed = True
        if self.close_error:
            raise OSError("already gone")


class ResetReader:
    async def read(self, n: int) -> bytes:
        raise ConnectionResetError


class EmptyReader:
    async def read(self, n: int) -> bytes:
        return b""


@sync
async def test_a_peer_that_resets_mid_copy_ends_the_copy_quietly() -> None:
    sink = Sink()
    await gate.Pipe.run(ResetReader(), sink)  # no exception escapes
    assert sink.closed and sink.written == []


@sync
async def test_closing_a_writer_that_is_already_gone_is_not_an_error() -> None:
    sink = Sink(close_error=True)
    await gate.Pipe.run(EmptyReader(), sink)
    assert sink.closed


@sync
async def test_a_request_head_that_never_completes_is_no_request() -> None:
    reader = asyncio.StreamReader()
    reader.feed_data(b"GET /api/version HTTP/1.1\r\nHost: x")  # the peer hangs up mid-head
    reader.feed_eof()
    assert await gate.Head.read(reader) is None
    complete = asyncio.StreamReader()
    complete.feed_data(b"GET / HTTP/1.1\r\n\r\n")
    assert await gate.Head.read(complete) == b"GET / HTTP/1.1\r\n\r\n"


@sync
async def test_refusing_a_connection_that_is_already_dead_does_not_raise() -> None:
    sink = Sink(drain_error=True)
    await gate.ConnectProxy.refuse(sink, "403 Forbidden")
    assert sink.closed and sink.written[0].startswith(b"HTTP/1.1 403")


@sync
async def test_the_model_gate_refuses_a_head_that_never_completes() -> None:
    class Never:
        async def open(self, address: str, port: int):
            raise AssertionError("an incomplete request must not reach the host")

    front, port = await serve(gate.ModelGate(("h", 1), dialer=Never()).handle)
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(b"POST /v1/chat/completions HTTP/1.1\r\nHost: g")  # no blank line
        writer.write_eof()
        answer = await asyncio.wait_for(reader.read(65536), timeout=5)
        assert b"400" in answer.split(b"\r\n", 1)[0]
        writer.close()
    finally:
        front.close()


@sync
async def test_the_gate_serves_both_listeners_from_its_environment(capsys) -> None:
    def free_port() -> int:
        import socket

        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            return probe.getsockname()[1]

    proxy_port, model_port = free_port(), free_port()
    env = {
        "EGRESS_ALLOW": "github.com,pypi.org",
        "EGRESS_MODEL_UPSTREAM": "host.docker.internal:11434",
        "EGRESS_PROXY_PORT": str(proxy_port),
        "EGRESS_MODEL_PORT": str(model_port),
    }
    task = asyncio.ensure_future(gate.Gate(env).serve())
    try:
        for _ in range(50):
            await asyncio.sleep(0.05)
            if "egress gate up" in capsys.readouterr().out:
                break
        else:
            raise AssertionError("the gate never said it was up")
        # Both listeners are really there, and the proxy enforces the allowlist it was given.
        denied = await exchange(proxy_port, b"CONNECT example.com:443 HTTP/1.1\r\n\r\n")
        assert b"403" in denied.split(b"\r\n", 1)[0]
        refused = await exchange(model_port, b"DELETE /api/delete HTTP/1.1\r\nHost: g\r\n\r\n")
        assert b"403" in refused.split(b"\r\n", 1)[0]
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


def test_the_interface_import_falls_back_to_the_directory_beside_the_gate(monkeypatch) -> None:
    # Run from anywhere (the container runs `python3 /egress/egress_gate.py`): when the
    # `interfaces` package is not importable, the gate adds its own directory and imports it.
    monkeypatch.setattr(
        sys, "path", [p for p in sys.path if Path(p or ".").resolve() != GATE_DIR.resolve()]
    )
    for name in [n for n in sys.modules if n == "interfaces" or n.startswith("interfaces.")]:
        monkeypatch.delitem(sys.modules, name)
    spec = importlib.util.spec_from_file_location(
        "egress_gate_fallback_import", GATE_DIR / "egress_gate.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    assert str(GATE_DIR) in sys.path
    assert module.HostPolicy(["github.com"]).allows("github.com", 443)


class Recorder:
    """An access log that keeps what it is told, in order."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def allow(self, what: str) -> None:
        self.lines.append(f"ALLOW {what}")

    def deny(self, what: str, why: str) -> None:
        self.lines.append(f"DENY {what} -- {why}")


def test_the_access_log_writes_one_clean_line_per_decision(capsys) -> None:
    lines: list[str] = []
    log = gate.AccessLog(lines.append)
    log.allow("github.com:443")
    log.deny("example.com:443", "not on the allowlist")
    assert lines == [
        "egress ALLOW github.com:443",
        "egress DENY  example.com:443 -- not on the allowlist",
    ]
    # By default it speaks on standard output, which is what `docker logs` shows.
    gate.AccessLog().deny("x.com:443", "why")
    assert capsys.readouterr().out == "egress DENY  x.com:443 -- why\n"


def test_client_supplied_text_cannot_forge_a_log_line_or_drive_a_terminal() -> None:
    lines: list[str] = []
    log = gate.AccessLog(lines.append)
    log.deny("evil\r\negress ALLOW github.com:443\x1b[31m", "x")
    assert len(lines) == 1 and "\n" not in lines[0] and "\r" not in lines[0]
    assert "\x1b" not in lines[0] and "?" in lines[0]
    log.deny("a" * 500, "x")
    assert lines[1].count("a") == gate.AccessLog.LIMIT


@sync
async def test_every_decision_the_proxy_makes_is_logged_with_its_reason() -> None:
    async def hold(reader, writer):
        await reader.read(1)
        writer.close()

    upstream, upstream_port = await serve(hold)
    resolver = FakeResolver(
        {
            "github.com": ["140.82.112.3"],
            "pypi.org": ["151.101.0.223", "10.0.0.5"],
            "api.github.com": [],
        }
    )
    log = Recorder()
    proxy = gate.ConnectProxy(gate.HostPolicy(ALLOW), resolver, LocalDialer(upstream_port), log=log)
    front, port = await serve(proxy.handle)
    try:
        await exchange(port, b"CONNECT github.com:443 HTTP/1.1\r\n\r\n")
        for request in (
            b"CONNECT example.com:443 HTTP/1.1\r\n\r\n",
            b"CONNECT github.com:22 HTTP/1.1\r\n\r\n",
            b"CONNECT github.com:x HTTP/1.1\r\n\r\n",
            b"CONNECT pypi.org:443 HTTP/1.1\r\n\r\n",
            b"CONNECT api.github.com:443 HTTP/1.1\r\n\r\n",
            b"GET http://github.com/ HTTP/1.1\r\n\r\n",
            b"CONNECT\r\n\r\n",
            b"\r\n\r\n",
        ):
            await exchange(port, request)
        # A head the peer abandons half-way.
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(b"CONNECT github.com:443 HTTP/1.1\r\nHost")
        writer.write_eof()
        await asyncio.wait_for(reader.read(65536), timeout=5)
        writer.close()
    finally:
        front.close()
        upstream.close()
    assert log.lines[0] == "ALLOW github.com:443"
    assert log.lines[1:] == [
        "DENY example.com:443 -- not on the allowlist (add the host to [runners] egress_allow)",
        "DENY github.com:22 -- not on the allowlist (add the host to [runners] egress_allow)",
        "DENY github.com -- the port is not a number",
        "DENY pypi.org:443 -- resolves to an address that is not public",
        "DENY api.github.com:443 -- the name does not resolve",
        "DENY GET github.com -- only CONNECT is supported",
        "DENY CONNECT -- a CONNECT request line needs a host:port",
        "DENY (request) -- only CONNECT is supported",
        "DENY (request) -- no complete request head",
    ]


@sync
async def test_a_failing_upstream_is_logged_as_the_upstreams_fault() -> None:
    class Down:
        async def open(self, address: str, port: int):
            raise ConnectionRefusedError

    log = Recorder()
    proxy = gate.ConnectProxy(
        gate.HostPolicy(ALLOW), FakeResolver({"github.com": ["140.82.112.3"]}), Down(), log=log
    )
    front, port = await serve(proxy.handle)
    try:
        await exchange(port, b"CONNECT github.com:443 HTTP/1.1\r\n\r\n")
    finally:
        front.close()
    assert log.lines == ["DENY github.com:443 -- the upstream did not accept the connection"]


@sync
async def test_every_decision_the_model_gate_makes_is_logged_with_its_reason() -> None:
    async def ollama(reader, writer):
        await reader.readuntil(b"\r\n\r\n")
        writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
        await writer.drain()
        writer.close()

    upstream, upstream_port = await serve(ollama)

    class Down:
        async def open(self, address: str, port: int):
            raise ConnectionRefusedError

    log = Recorder()
    up = gate.ModelGate(("h", 1), dialer=LocalDialer(upstream_port), log=log)
    down = gate.ModelGate(("h", 1), dialer=Down(), log=log)
    front, port = await serve(up.handle)
    front_down, port_down = await serve(down.handle)
    try:
        await exchange(port, b"GET /api/version HTTP/1.1\r\nHost: g\r\n\r\n")
        await exchange(port, b"DELETE /api/delete HTTP/1.1\r\nHost: g\r\n\r\n")
        await exchange(port, b"nonsense\r\n\r\n")
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        writer.write(b"POST /v1/chat/completions HTTP/1.1\r\nHost")
        writer.write_eof()
        await asyncio.wait_for(reader.read(65536), timeout=5)
        writer.close()
        await exchange(port_down, b"GET /api/version HTTP/1.1\r\nHost: g\r\n\r\n")
    finally:
        front.close()
        front_down.close()
        upstream.close()
    assert log.lines == [
        "ALLOW GET /api/version",
        "DENY DELETE /api/delete -- not one of the model requests allowed",
        "DENY nonsense -- not one of the model requests allowed",
        "DENY (model request) -- no complete request head",
        "DENY GET /api/version -- the host's model server did not answer",
    ]


def test_a_log_line_says_where_a_request_was_going_and_nothing_it_carried() -> None:
    host, path = gate.Destination.host, gate.Destination.path
    assert host("github.com:443") == "github.com:443"
    assert host("user:hunter2@evil.com:443") == "evil.com:443"
    assert host("http://deploy:ghp_SECRET@internal.example/p?token=abc#frag") == "internal.example"
    assert host("https://h.example:8443/a/b") == "h.example:8443"
    assert host("a@b@c.example") == "c.example"  # the last @ ends the credentials
    assert path("/v1/models?api_key=SECRET#x") == "/v1/models"
    assert path("/api/tags") == "/api/tags"
    request = gate.Destination.request
    assert request([]) == "(request)"
    assert request(["CONNECT"]) == "CONNECT"
    assert request(["GET", "/api/version?x=1"]) == "GET /api/version"
    assert request(["GET", "http://u:p@h.example/x?t=1"]) == "GET h.example"
    assert request(["X" * 100, "h.example"]) == "X" * gate.Destination.METHOD_LIMIT + " h.example"


@sync
async def test_no_secret_in_a_request_target_reaches_the_log() -> None:
    # Found by a security review: the log wrote client-supplied targets whole, so URL
    # credentials and query-string tokens were written to `docker logs`.
    log = Recorder()
    proxy = gate.ConnectProxy(gate.HostPolicy(["github.com"]), FakeResolver({}), log=log)
    model = gate.ModelGate(("h", 1), dialer=LocalDialer(1), log=log)
    front, port = await serve(proxy.handle)
    front_model, model_port = await serve(model.handle)
    try:
        for request in (
            b"CONNECT user:hunter2@evil.com:443 HTTP/1.1\r\n\r\n",
            b"CONNECT user:hunter2@evil.com:secretport HTTP/1.1\r\n\r\n",
            b"CONNECT justaword HTTP/1.1\r\n\r\n",
            b"GET http://deploy:ghp_SECRET@internal.example/p?token=abc123 HTTP/1.1\r\n\r\n",
        ):
            await exchange(port, request)
        for request in (
            b"DELETE /api/delete?api_key=sk-LIVE-KEY HTTP/1.1\r\nHost: g\r\n\r\n",
            b"GET http://x:tok@h.example/api/version?k=v HTTP/1.1\r\nHost: g\r\n\r\n",
        ):
            await exchange(model_port, request)
    finally:
        front.close()
        front_model.close()
    joined = "\n".join(log.lines)
    for secret in ("hunter2", "ghp_SECRET", "abc123", "sk-LIVE-KEY", "secretport", "tok@", "k=v"):
        assert secret not in joined, secret
    assert log.lines == [
        "DENY evil.com:443 -- not on the allowlist (add the host to [runners] egress_allow)",
        "DENY evil.com -- the port is not a number",
        "DENY (no host) -- the port is not a number",
        "DENY GET internal.example -- only CONNECT is supported",
        "DENY DELETE /api/delete -- not one of the model requests allowed",
        "DENY GET h.example -- not one of the model requests allowed",
    ]


def test_a_flood_of_connections_cannot_make_an_endless_log() -> None:
    now = [0.0]
    lines: list[str] = []
    log = gate.AccessLog(lines.append, clock=lambda: now[0])
    rate = gate.AccessLog.RATE
    for n in range(rate + 250):
        log.deny(f"h{n}.evil.example:443", "not on the allowlist")
    assert len(lines) == rate  # the rest were counted, not written
    # An allow flood has its own budget: it cannot hide a refusal, nor the other way round.
    for n in range(rate + 5):
        log.allow(f"ok{n}.github.com:443")
    log.deny("later.evil.example:443", "still counted")
    assert len(lines) == 2 * rate
    # The next window says what was not written, then writes normally again.
    now[0] += gate.AccessLog.WINDOW
    log.deny("again.evil.example:443", "not on the allowlist")
    assert lines[-2:] == [
        "egress LIMIT 251 DENY lines were not written in the last 60s (at most 600 a window)",
        "egress DENY  again.evil.example:443 -- not on the allowlist",
    ]
    log.allow("ok.github.com:443")
    assert lines[-2] == (
        "egress LIMIT 5 ALLOW lines were not written in the last 60s (at most 600 a window)"
    )
    # A quiet window prints no summary of nothing.
    now[0] += gate.AccessLog.WINDOW
    before = len(lines)
    log.deny("quiet.evil.example:443", "x")
    assert len(lines) == before + 1
