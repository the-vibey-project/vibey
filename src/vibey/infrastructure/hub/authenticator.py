# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Who a request to the hub comes from.

An authenticator reads a request and names its principal, or `None` when the request
proves nothing -- and `None` is refused (401) before any route runs. `HubRequest` carries
the whole request, body included, so an authenticator that verifies a signature over the
body (a paired device's, ADR-0067) sees exactly the bytes the route will read.

`LocalTokenAuthenticator` admits the host's own token (`local_token.py`) and names the
host principal, which holds every scope. `FirstOf` asks several in turn.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from vibey_bootstrap.security import compare_secrets

from vibey.application.dto import HubPrincipal
from vibey.domain.hub_scope import HubScope
from vibey.infrastructure.hub.interfaces.authenticator_interface import (
    HubAuthenticatorInterface,
)

HOST_PRINCIPAL: Final = HubPrincipal(name="host", scopes=frozenset(HubScope))
"""The account that runs vibey, reaching the hub with its own token: every scope."""

BEARER: Final = "bearer "


@dataclass(frozen=True, slots=True)
class HubRequest:
    """One request, as an authenticator sees it. Header names are lower-case."""

    method: str
    path: str
    query: str
    headers: Mapping[str, str]
    body: bytes


class LocalTokenAuthenticator:
    """Admits `Authorization: Bearer <the host's token>`, compared in constant time.

    Declared by `interfaces/authenticator_interface.py::HubAuthenticatorInterface`."""

    def __init__(self, token: str) -> None:
        if not token:
            raise ValueError("the hub token must not be empty")
        self._token = token

    async def authenticate(self, request: HubRequest) -> HubPrincipal | None:
        header = request.headers.get("authorization", "")
        if not header.lower().startswith(BEARER):
            return None
        # vibey_bootstrap's constant-time compare (the dogfood rule), not a second one.
        if compare_secrets(header[len(BEARER) :].strip(), self._token):
            return HOST_PRINCIPAL
        return None


class FirstOf:
    """The first principal any of `authenticators` names, asked in order.

    Declared by `interfaces/authenticator_interface.py::HubAuthenticatorInterface`."""

    def __init__(self, authenticators: Sequence[HubAuthenticatorInterface]) -> None:
        self._authenticators = tuple(authenticators)

    async def authenticate(self, request: HubRequest) -> HubPrincipal | None:
        for authenticator in self._authenticators:
            principal = await authenticator.authenticate(request)
            if principal is not None:
                return principal
        return None
