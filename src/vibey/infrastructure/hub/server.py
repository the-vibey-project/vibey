# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Running the hub's app, and the names this computer answers to on the LAN.

`UvicornServer` serves an ASGI app until it is told to stop; `vibey serve` awaits it
inside the resources it opened, so the database pool lives exactly as long as the hub.

`LocalNames` lists the names a device on the LAN may put in `Host` to reach this
computer: its host name, that name under `.local` (mDNS), and the addresses the name
resolves to. With the LAN declared these join the loopback names on the allowlist; with
it undeclared they are never consulted, and only loopback names are answered.
"""

from __future__ import annotations

import errno
import socket
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from fastapi import FastAPI

    from vibey.infrastructure.hub.tls import HubTls

BACKLOG: Final = 2048
"""Connections the kernel queues before the hub accepts them: uvicorn's own default."""


class UvicornServer:
    """Serves an app on one address until stopped.

    The address is bound by `bind`, before the hub writes its record, and uvicorn is handed
    those sockets: it never binds one of its own. So the record never names a port another
    process holds, even for the moment between the record and the bind (SP-ACP Task 11b).

    Declared by `interfaces/server_interface.py::HubServerInterface`."""

    def bind(self, host: str, port: int) -> list[socket.socket]:
        # Every address the name resolves to (`localhost`: 127.0.0.1 and ::1), each IPv6 one
        # IPv6-only so the two never collide, the address reusable after an earlier hub's
        # connections linger in TIME_WAIT; with port 0, every address after the first takes
        # the first one's port, so the record names one port they all hold. Never inheritable
        # (Python's default), so a child the hub starts does not keep the port. Two failures
        # skip that one address, as asyncio's own bind does: `socket()` refused with
        # EAFNOSUPPORT (the family is not on this host) and `bind()` refused with
        # EADDRNOTAVAIL (no interface has the address): nobody can hold either. Every other
        # failure -- EADDRINUSE and EACCES above all, an address another account may hold --
        # stops the hub, as does a name with no address left; anything bound is closed first.
        answers = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM, flags=socket.AI_PASSIVE)
        addresses = list(dict.fromkeys((family, sockaddr) for family, _, _, _, sockaddr in answers))
        bound: list[socket.socket] = []
        try:
            for family, sockaddr in addresses:
                sock = self._bound(family, sockaddr, bound[0].getsockname()[1] if bound else None)
                if sock is not None:
                    bound.append(sock)
            if not bound:
                raise OSError(f"{host} resolves to no address it can bind")
        except BaseException:
            for sock in bound:
                sock.close()
            raise
        return bound

    @staticmethod
    def _bound(family: int, sockaddr: tuple[Any, ...], taken: int | None) -> socket.socket | None:
        """One address bound and listening on `taken` (else its own port); None when this host
        does not have the family or the address."""
        try:
            sock = socket.socket(family, socket.SOCK_STREAM)
        except OSError as exc:
            if exc.errno == errno.EAFNOSUPPORT:
                return None
            raise
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if family == socket.AF_INET6:
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            port = sockaddr[1] if taken is None else taken
            sock.bind((sockaddr[0], port, *sockaddr[2:]))
            sock.listen(BACKLOG)
        except BaseException as exc:
            sock.close()
            if isinstance(exc, OSError) and exc.errno == errno.EADDRNOTAVAIL:
                return None
            raise
        return sock

    async def serve(
        self, app: FastAPI, *, sockets: Sequence[socket.socket], tls: HubTls | None = None
    ) -> None:
        # Imported here, not at module level: uvicorn ships in the optional `hub` extra, and
        # `vibey serve` imports this module, so a top-level import would break every `vibey`
        # command on an install without the extra (the container image is one).
        import uvicorn

        config = uvicorn.Config(
            app,
            backlog=BACKLOG,
            log_level="warning",
            # No proxy is trusted: X-Forwarded-* from a client is never read as its address.
            proxy_headers=False,
            server_header=False,
            date_header=False,
            # The hub's own certificate on a declared LAN (`tls.py`); none on loopback.
            ssl_certfile=str(tls.cert_path) if tls is not None else None,
            ssl_keyfile=str(tls.key_path) if tls is not None else None,
        )
        await uvicorn.Server(config).serve(sockets=list(sockets))


class LocalNames:
    """The names and addresses this computer is reached by.

    Declared by `interfaces/server_interface.py::LocalNamesInterface`."""

    def names(self, bound: str) -> frozenset[str]:
        hostname = socket.gethostname().lower()
        names = {hostname, bound.lower()}
        names.add(hostname if hostname.endswith(".local") else f"{hostname}.local")
        try:
            infos = socket.getaddrinfo(hostname, None)
        except OSError:
            infos = []
        names.update(str(info[4][0]).lower() for info in infos)
        # A wildcard bind is not a name anyone can send in Host.
        return frozenset(names - {"0.0.0.0", "::"})  # nosec B104 - removed, not bound


HUB_SERVER: Final = UvicornServer()
LOCAL_NAMES: Final = LocalNames()
