# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams over an engine session's web-only hub principal (SP-LOOPS Phase 6, Task 2; R1, R4).

`SessionWebPrincipalsInterface` is what the worker consumes to mint and revoke a session's
principal, and what the hub consumes to find the principal a presented token names. The three
below it are what that service consumes and infrastructure implements: the token source, the
token file in a run's own folder, and the registry the worker and the hub share. Interfaces
declare; they never consume.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import SessionGrant
from vibey.domain.session_principal import SessionPrincipal


@runtime_checkable
class SessionWebPrincipalsInterface(Protocol):
    """Mints, finds and revokes the web-only principal each engine session holds."""

    def mint(self, run_id: UUID, folder: Path, now: float) -> SessionGrant:
        """Makes a fresh token, writes it to `<folder>/web-token` (0600, in the run's own 0700
        folder) and registers its digest -- never the token -- as `session:<run_id>`, holding
        only `web`, until the run deadline plus `DEADLINE_MARGIN` after `now` (R4). Raises
        `SessionGrantRefused` when `now` is not finite, the source's token is unusable, or the
        folder already holds a token or is not owner-only; an `OSError` when the registry cannot
        be written takes the token file with it. Never names the token in an error or a log."""
        ...

    def revoke(self, grant: SessionGrant) -> None:
        """Forgets the grant's digest, so the hub refuses its token from the next request, then
        removes its token file. Idempotent. A token file that cannot be removed is logged by
        path and left for the sweep; a registry that cannot forget raises its `OSError` after
        the file has still been removed."""
        ...

    def lookup(self, token: str, now: float) -> SessionPrincipal | None:
        """The principal `token` names, or `None` when it is unknown, revoked or expired at
        `now` (expiry is exclusive). For the hub's authenticator. Raises what the registry
        raises for an entry that is not this account's own or cannot be read."""
        ...


@runtime_checkable
class SessionTokenSourceInterface(Protocol):
    """Where a session's token comes from: random in production, fixed in tests."""

    def token(self) -> str:
        """A fresh, unguessable token: printable ASCII with no whitespace."""
        ...


@runtime_checkable
class SessionTokenFilesInterface(Protocol):
    """The token file in a run's own folder (R1)."""

    def write(self, folder: Path, token: str) -> Path:
        """Writes `token` to `<folder>/web-token`, 0600, created exclusively and never through
        a symlink, and returns its path. Raises `SessionGrantRefused` when the file already
        exists, or `folder` is missing, a symlink, not a folder, not this account's or open to
        other accounts; an `OSError` while writing removes the file first."""
        ...

    def read(self, path: Path) -> str:
        """The token at `path`. Raises `FileNotFoundError` when it is not there, and
        `SessionGrantRefused` when it is a symlink, not a regular file, not this account's,
        open to other accounts, or empty."""
        ...

    def remove(self, path: Path) -> bool:
        """Removes the token file and says whether it is gone (already gone counts). A symlink
        or anything not a regular file at `path` is never followed or removed: `False`, as is a
        file that cannot be removed."""
        ...


@runtime_checkable
class SessionPrincipalRegistryInterface(Protocol):
    """The session principals the worker minted, by their token's SHA-256 digest, where the
    hub -- another process on the same host -- finds them. It holds digests, never tokens."""

    def record(self, digest: str, principal: SessionPrincipal) -> None:
        """Registers `principal` under `digest` (64 lower-case hex characters, or
        `ValueError`)."""
        ...

    def find(self, digest: str) -> SessionPrincipal | None:
        """The principal registered under `digest`, or `None` when there is none (a name that
        is not a digest is none). Raises `PermissionError` for an entry or folder that is not
        this account's own, owner-only and real, and `ValueError` for a malformed entry."""
        ...

    def forget(self, digest: str) -> bool:
        """Removes the entry under `digest` and says whether there was one. Never follows a
        symlink."""
        ...
