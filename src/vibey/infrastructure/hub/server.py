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


class UvicornServer:
    """Serves an app on one address until stopped.

    Declared by `interfaces/server_interface.py::HubServerInterface`."""

    async def serve(self, app: FastAPI, *, host: str, port: int) -> None:
        # Imported here, not at module level: uvicorn ships in the optional `hub` extra, and
        # `vibey serve` imports this module, so a top-level import would break every `vibey`
        # command on an install without the extra (the container image is one).
        import uvicorn

        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="warning",
            # No proxy is trusted: X-Forwarded-* from a client is never read as its address.
            proxy_headers=False,
            server_header=False,
            date_header=False,
        )
        await uvicorn.Server(config).serve()


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
