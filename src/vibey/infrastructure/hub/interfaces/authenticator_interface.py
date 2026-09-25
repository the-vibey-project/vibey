# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind naming who a hub request comes from.

Mirrors `vibey/infrastructure/hub/authenticator.py` (ADR-0016). Interfaces declare; they
never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.application.dto import HubPrincipal
    from vibey.infrastructure.hub.authenticator import HubRequest


@runtime_checkable
class HubAuthenticatorInterface(Protocol):
    """Names a request's principal, or `None` when the request proves nothing."""

    async def authenticate(self, request: HubRequest) -> HubPrincipal | None:
        """The principal `request` proves, or `None` (refused with 401)."""
        ...
