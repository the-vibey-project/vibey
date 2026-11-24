# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind an engine session's own web-only hub principal.

Mirrors `vibey/domain/session_principal.py` (ADR-0016, SP-LOOPS Phase 6). Interfaces declare;
they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from uuid import UUID

    from vibey.domain.hub_scope import HubAction, HubScope


@runtime_checkable
class SessionPrincipalInterface(Protocol):
    """One engine session's hub principal: its name, its run, when it expires, and the one
    scope it holds."""

    @property
    def name(self) -> str:
        """`session:<id>`; never a device's or the agent's name."""
        ...

    @property
    def run_id(self) -> UUID:
        """The engine run whose session holds this principal."""
        ...

    @property
    def expires_at(self) -> float:
        """The finite instant, in the caller's clock, at which it stops being honoured."""
        ...

    @property
    def scopes(self) -> frozenset[HubScope]:
        """Always exactly `{HubScope.WEB}`."""
        ...


@runtime_checkable
class SessionPrincipalPolicyInterface(Protocol):
    """Decides what a session principal may do, and when. Pure; `now` is passed in."""

    def permits(self, principal: SessionPrincipalInterface, action: HubAction, now: float) -> bool:
        """True only for an action the principal's scopes cover, and only before `expires_at`
        (expiry is exclusive)."""
        ...

    def expired(self, principal: SessionPrincipalInterface, now: float) -> bool:
        """True from `expires_at` on: the complement of the time half of `permits`."""
        ...
