# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind building the hub's HTTP app.

Mirrors `vibey/infrastructure/hub/app.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from fastapi import FastAPI

    from vibey.application.hub.interfaces.hub_service_interface import HubServiceInterface
    from vibey.infrastructure.hub.interfaces.authenticator_interface import (
        HubAuthenticatorInterface,
    )
    from vibey.infrastructure.hub.interfaces.live_interface import (
        LedgerAnnouncementsInterface,
    )


@runtime_checkable
class HubAppFactoryInterface(Protocol):
    """Builds the hardened, versioned hub app over a service."""

    def build(
        self,
        service: HubServiceInterface,
        *,
        authenticator: HubAuthenticatorInterface,
        allowed_hosts: frozenset[str],
        ready: Callable[[], Awaitable[bool]],
        live: LedgerAnnouncementsInterface,
    ) -> FastAPI:
        """The app: Host allowlist, security headers, no CORS, principal before route."""
        ...
