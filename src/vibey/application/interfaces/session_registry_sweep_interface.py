# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams over sessions that ended without being revoked (SP-LOOPS Phase 6, Task 7; R4).

A worker that crashed or was killed never revokes its sessions: their registry entries stay until
their expiry, refused by the hub from then on, and are the start-up sweep's to remove.
`SessionPrincipalListingInterface` is what the sweep and the hub's web budget consume, and the
registry implements (`infrastructure/hub/session_registry.py`); `SessionRegistrySweepInterface` is
what a worker runs once as it starts (`session_registry_sweep.py`). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey.application.dto import SessionRegistryListing, SessionSweepReport


@runtime_checkable
class SessionPrincipalListingInterface(Protocol):
    """Every session principal the registry holds, and removal by digest."""

    def entries(self) -> SessionRegistryListing:
        """Every entry, read afresh, in name order. An entry that cannot be read -- malformed,
        not this account's own and owner-only, a symlink, not a file -- is named in
        `unreadable` and never listed; a name that is not `<digest>.json` (a staged write) is
        not an entry. A registry never made lists nothing. Raises `PermissionError` when the
        registry's folder itself is not this account's own and owner-only, or is a symlink: then
        nothing in it can be trusted."""
        ...

    def forget(self, digest: str) -> bool:
        """Removes the entry under `digest` and says whether there was one. Never follows a
        symlink."""
        ...


@runtime_checkable
class SessionRegistrySweepInterface(Protocol):
    """Removes the registry's expired entries."""

    def sweep(self) -> SessionSweepReport:
        """Removes every entry whose principal has expired by the wall clock's now (expiry is
        exclusive: at the expiry instant it has), and only those: a live entry is never removed,
        and an unreadable one is named and kept. Idempotent: a second sweep removes nothing the
        first did not. Raises `ValueError` for a clock that is not finite, and whatever the
        registry raises when it cannot be listed, having removed nothing."""
        ...
