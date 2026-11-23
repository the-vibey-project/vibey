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
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from fastapi import FastAPI

    from vibey.infrastructure.hub.tls import HubTls

BACKLOG: Final = 2048
"""Connections the kernel queues before the hub accepts them: uvicorn's own default."""


class UvicornServer:
    """Serves an app on one address until stopped.

    The address is bound by `bind`, before the hub writes its record, and uvicorn is handed
    that socket: it never binds one of its own. So the record never names a port another
    process holds, even for the moment between the record and the bind (SP-ACP Task 11b).

    Declared by `interfaces/server_interface.py::HubServerInterface`."""

    def bind(self, host: str, port: int) -> socket.socket:
        # As uvicorn would bind it: IPv6 for a literal with a colon, the address reusable
        # after an earlier hub's connections linger in TIME_WAIT. Never inheritable (Python's
        # default), so a child the hub starts does not keep the port.
        family = socket.AF_INET6 if ":" in host else socket.AF_INET
        sock = socket.socket(family, socket.SOCK_STREAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
            sock.listen(BACKLOG)
        except BaseException:
            sock.close()
            raise
        return sock

    async def serve(self, app: FastAPI, *, sock: socket.socket, tls: HubTls | None = None) -> None:
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
        await uvicorn.Server(config).serve(sockets=[sock])


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
