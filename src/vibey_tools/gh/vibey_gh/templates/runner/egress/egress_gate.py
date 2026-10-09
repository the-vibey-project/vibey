# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The runner's egress gate: the only way out of the job container (ADR-0083, 2026-10-09).

The runner container sits on a Docker network with no route out. This process sits on that
network AND the outside, and does exactly two things:

  * an HTTPS proxy (`CONNECT` only) for a declared list of hosts -- GitHub, the artifact store,
    PyPI -- on port 443, to globally routable addresses only. The name is resolved HERE and the
    address checked, so a name that points at the host, its LAN or loopback is refused whatever
    it is called.
  * a forwarder to the model server on the host that lets through four requests, and nothing
    else: the agent cannot pull, create or delete a model on the operator's machine.

Everything else -- the host's Postgres, RabbitMQ, any other loopback service, any other site --
is unreachable by construction, not by a flag the agent could ignore. Standard library only: it
runs in the stock runner image with the directory mounted read-only.
"""

from __future__ import annotations

import asyncio
import fnmatch
import ipaddress
import os
import socket
import sys
from collections.abc import Sequence
from pathlib import Path

try:
    from interfaces.egress_gate_interface import (  # type: ignore[import-not-found]
        DialerInterface,
        HostPolicyInterface,
        RequestPolicyInterface,
        ResolverInterface,
    )
except ModuleNotFoundError:  # run from outside the directory that holds `interfaces/`
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from interfaces.egress_gate_interface import (  # type: ignore[import-not-found,no-redef]
        DialerInterface,
        HostPolicyInterface,
        RequestPolicyInterface,
        ResolverInterface,
    )

MAX_HEAD = 16 * 1024
# A long prefill on a big context is silence for minutes; a hung peer is not worth a slot forever.
IDLE_SECONDS = 1800


class SystemResolver(ResolverInterface):
    async def resolve(self, host: str, port: int) -> Sequence[str]:
        loop = asyncio.get_running_loop()
        try:
            found = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except OSError:
            return []
        return [str(item[4][0]) for item in found]


class TcpDialer(DialerInterface):
    async def open(
        self, address: str, port: int
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        return await asyncio.wait_for(asyncio.open_connection(address, port), timeout=30)


class HostPolicy(HostPolicyInterface):
    """Declared host patterns (`github.com`, `*.actions.githubusercontent.com`) on declared ports."""

    def __init__(self, patterns: Sequence[str], ports: Sequence[int] = (443,)) -> None:
        self._patterns = [p.strip().lower() for p in patterns if p.strip()]
        self._ports = set(ports)

    def allows(self, host: str, port: int) -> bool:
        name = host.strip().lower().rstrip(".")
        # An address literal is never a declared host: the allowlist names services, and a
        # literal would route around the resolver's check of what a name points at.
        try:
            ipaddress.ip_address(name.strip("[]"))
            return False
        except ValueError:
            pass
        return port in self._ports and any(fnmatch.fnmatchcase(name, p) for p in self._patterns)

    def public(self, address: str) -> bool:
        try:
            return ipaddress.ip_address(address).is_global
        except ValueError:
            return False


class RequestPolicy(RequestPolicyInterface):
    """The requests the agent's engine makes of the model server, and no others."""

    ALLOWED = frozenset(
        {
            ("GET", "/api/version"),
            ("GET", "/api/tags"),
            ("GET", "/v1/models"),
            ("POST", "/v1/chat/completions"),
        }
    )

    def allows(self, method: str, target: str) -> bool:
        return (method.upper(), target.split("?", 1)[0]) in self.ALLOWED


class Pipe:
    """Copies bytes one way until either end closes or goes quiet."""

    @staticmethod
    async def run(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while True:
                chunk = await asyncio.wait_for(reader.read(65536), timeout=IDLE_SECONDS)
                if not chunk:
                    break
                writer.write(chunk)
                await writer.drain()
        except (TimeoutError, OSError, asyncio.IncompleteReadError):
            pass
        finally:
            try:
                writer.close()
            except OSError:
                pass

    @classmethod
    async def both(
        cls,
        a: tuple[asyncio.StreamReader, asyncio.StreamWriter],
        b: tuple[asyncio.StreamReader, asyncio.StreamWriter],
    ) -> None:
        await asyncio.gather(cls.run(a[0], b[1]), cls.run(b[0], a[1]))


class Head:
    """Reads one HTTP request head, bounded."""

    @staticmethod
    async def read(reader: asyncio.StreamReader) -> bytes | None:
        try:
            raw = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=30)
        except (TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError, OSError):
            return None
        return raw if len(raw) <= MAX_HEAD else None


class ConnectProxy:
    """`CONNECT host:443` for declared hosts that resolve to public addresses; 403 otherwise."""

    def __init__(
        self,
        policy: HostPolicyInterface,
        resolver: ResolverInterface | None = None,
        dialer: DialerInterface | None = None,
    ) -> None:
        self._policy = policy
        self._resolver = resolver or SystemResolver()
        self._dialer = dialer or TcpDialer()

    @staticmethod
    async def refuse(writer: asyncio.StreamWriter, status: str) -> None:
        try:
            writer.write(
                f"HTTP/1.1 {status}\r\nConnection: close\r\nContent-Length: 0\r\n\r\n".encode()
            )
            await writer.drain()
        except OSError:
            pass
        writer.close()

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        head = await Head.read(reader)
        if head is None:
            return await self.refuse(writer, "400 Bad Request")
        parts = head.split(b"\r\n", 1)[0].decode("latin-1").split()
        if len(parts) != 3 or parts[0].upper() != "CONNECT":
            return await self.refuse(writer, "405 Method Not Allowed")
        host, _, port_text = parts[1].rpartition(":")
        if not port_text.isdigit() or not self._policy.allows(host, int(port_text)):
            return await self.refuse(writer, "403 Forbidden")
        port = int(port_text)
        everything = await self._resolver.resolve(host, port)
        addresses = [a for a in everything if self._policy.public(a)]
        # EVERY address must be public: a name that also points at the host is refused whole.
        if not addresses or len(addresses) != len(everything):
            return await self.refuse(writer, "403 Forbidden")
        try:
            upstream = await self._dialer.open(addresses[0], port)
        except (TimeoutError, OSError):
            return await self.refuse(writer, "502 Bad Gateway")
        writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        await writer.drain()
        await Pipe.both((reader, writer), upstream)


class ModelGate:
    """Forwards the allowed requests to the model server on the host, one request a connection."""

    def __init__(
        self,
        upstream: tuple[str, int],
        policy: RequestPolicyInterface | None = None,
        dialer: DialerInterface | None = None,
    ) -> None:
        self._upstream = upstream
        self._policy = policy or RequestPolicy()
        self._dialer = dialer or TcpDialer()

    @staticmethod
    def one_request(head: bytes) -> bytes:
        """The head with `Connection: close` and without the headers that would keep the
        connection open or hand the upstream a second request, so the gate has judged the only
        request the connection will ever carry."""
        lines = head.split(b"\r\n")
        keep = [
            line
            for line in lines[1:-2]
            if line.split(b":", 1)[0].strip().lower()
            not in {b"connection", b"proxy-connection", b"keep-alive", b"upgrade", b"te"}
        ]
        return b"\r\n".join([lines[0], *keep, b"Connection: close", b"", b""])

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        head = await Head.read(reader)
        if head is None:
            return await ConnectProxy.refuse(writer, "400 Bad Request")
        line = head.split(b"\r\n", 1)[0].decode("latin-1").split()
        if len(line) != 3 or not self._policy.allows(line[0], line[1]):
            return await ConnectProxy.refuse(writer, "403 Forbidden")
        try:
            upstream = await self._dialer.open(*self._upstream)
        except (TimeoutError, OSError):
            return await ConnectProxy.refuse(writer, "502 Bad Gateway")
        upstream[1].write(self.one_request(head))
        await upstream[1].drain()
        await Pipe.both((reader, writer), upstream)


class Gate:
    """Both listeners, from the environment the supervisor sets."""

    def __init__(self, env: dict[str, str]) -> None:
        self._env = env

    async def serve(self) -> None:
        patterns = self._env.get("EGRESS_ALLOW", "").split(",")
        host, _, port = self._env.get(
            "EGRESS_MODEL_UPSTREAM", "host.docker.internal:11434"
        ).rpartition(":")
        proxy = ConnectProxy(HostPolicy(patterns))
        model = ModelGate((host, int(port)))
        servers = [
            await asyncio.start_server(
                proxy.handle, "0.0.0.0", int(self._env.get("EGRESS_PROXY_PORT", "3128"))
            ),
            await asyncio.start_server(
                model.handle, "0.0.0.0", int(self._env.get("EGRESS_MODEL_PORT", "11434"))
            ),
        ]
        print(f"egress gate up: allow={patterns} model={host}:{port}", flush=True)
        await asyncio.gather(*(s.serve_forever() for s in servers))


if __name__ == "__main__":
    asyncio.run(Gate(dict(os.environ)).serve())
