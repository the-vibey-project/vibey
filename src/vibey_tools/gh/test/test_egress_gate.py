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
