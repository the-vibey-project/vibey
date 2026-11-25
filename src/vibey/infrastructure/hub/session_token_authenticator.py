# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Admits an engine session's own token, and names its web-only principal (SP-LOOPS Phase 6,
Task 3).

`Authorization: Bearer <token>`, where the token is one the worker minted for an engine session
(`SessionWebPrincipals.mint`) and wrote to the run's own `web-token` file. The token is looked up
by its digest in the registry in the hub's state folder, afresh on every request, at the hub's
own wall clock: a revoked token is refused from its next request, an expired one from its expiry
instant (the session policy's `expired`, through the lookup -- this holds no copy of that rule).

What it names is `HubPrincipal(name="session:<run>", scopes={web})`. The name cannot be the
host's, the agent's or a device's (`device:`), so the hub refuses it every route but web search
and fetch (`app.py`), and the web tools charge its calls to its own cap and to the agent's bucket
(`WebToolsService`, R2). `vibey serve` asks this authenticator last, after the host, the devices
and the agent, so a session never shadows any of them.

An unreadable registry -- an entry or folder that is not this account's own (`PermissionError`)
or is malformed (`ValueError`) -- can only deny: the token is read as unknown (401) and the
registry's message, which names the entry's path and never a token, is logged at warning level.
Any other failure is not swallowed. Declared by
`interfaces/session_token_authenticator_interface.py::SessionTokenAuthenticatorInterface`.
"""

from __future__ import annotations

from collections.abc import Callable

from vibey.application.dto import HubPrincipal
from vibey.application.interfaces.observability import Logger
from vibey.application.interfaces.session_token_lookup_interface import (
    SessionTokenLookupInterface,
)
from vibey.infrastructure.hub.authenticator import BEARER, HubRequest


class SessionTokenAuthenticator:
    """Declared by
    `interfaces/session_token_authenticator_interface.py::SessionTokenAuthenticatorInterface`."""

    def __init__(
        self,
        sessions: SessionTokenLookupInterface,
        *,
        clock: Callable[[], float],
        logger: Logger | None = None,
    ) -> None:
        self._sessions = sessions
        self._clock = clock
        self._logger = logger

    async def authenticate(self, request: HubRequest) -> HubPrincipal | None:
        header = request.headers.get("authorization", "")
        if not header.lower().startswith(BEARER):
            return None
        token = header[len(BEARER) :].strip()
        if not token:
            return None
        try:
            principal = self._sessions.lookup(token, self._clock())
        except (PermissionError, ValueError) as exc:
            if self._logger is not None:
                self._logger.warning(
                    "session_registry_unreadable", error=type(exc).__name__, detail=str(exc)
                )
            return None
        if principal is None:
            return None
        return HubPrincipal(name=principal.name, scopes=principal.scopes)
