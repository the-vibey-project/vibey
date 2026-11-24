# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over finding the session principal a presented token names (SP-LOOPS Phase 6,
Task 3).

Mirrors `vibey/application/session_token_lookup.py` (ADR-0016). What the hub's authenticator
consumes: it never mints, so it holds no token source, no token files and no run deadline.
Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey.domain.session_principal import SessionPrincipal


@runtime_checkable
class SessionTokenLookupInterface(Protocol):
    """Finds the engine session's principal a presented token names."""

    def lookup(self, token: str, now: float) -> SessionPrincipal | None:
        """The principal `token` names, or `None` when it is unknown, revoked, expired at `now`
        (expiry is exclusive) or could not have been minted at all. Raises what the registry
        raises for an entry or folder that is not this account's own (`PermissionError`) or is
        malformed (`ValueError`); its messages name the entry's path, never a token."""
        ...
