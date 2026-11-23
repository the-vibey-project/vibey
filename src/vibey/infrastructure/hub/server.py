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

import socket
from collections.abc import Sequence
from typing import TYPE_CHECKING, Final

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
        # As uvicorn's own bind did (asyncio's `create_server`): every address the name
        # resolves to -- `localhost` is 127.0.0.1 and ::1 -- each IPv6 one IPv6-only so the two
        # never collide, the address reusable after an earlier hub's connections linger in
        # TIME_WAIT. With port 0, every address after the first takes the first one's port, so
        # the record names one port they all hold. Never inheritable (Python's default), so a
        # child the hub starts does not keep the port. Any failure closes what was bound.
        answers = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM, flags=socket.AI_PASSIVE)
        addresses = list(dict.fromkeys((family, sockaddr) for family, _, _, _, sockaddr in answers))
        if not addresses:
            raise OSError(f"{host} resolves to no address")
        bound: list[socket.socket] = []
        try:
            for family, sockaddr in addresses:
                sock = socket.socket(family, socket.SOCK_STREAM)
                bound.append(sock)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                if family == socket.AF_INET6:
                    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                taken = bound[0].getsockname()[1] if len(bound) > 1 else sockaddr[1]
                sock.bind((sockaddr[0], taken, *sockaddr[2:]))
                sock.listen(BACKLOG)
        except BaseException:
            for sock in bound:
                sock.close()
            raise
        return bound

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
