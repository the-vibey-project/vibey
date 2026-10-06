# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams behind `vibey state`: the database, the branch, the key, and the service that
syncs them (ADR-0086). Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey.domain.state_sync import RemoteHead, Snapshot, SnapshotDiff, SyncReport


@runtime_checkable
class StateStore(Protocol):
    """The local database, read whole and changed row by row."""

    async def snapshot(self) -> Snapshot:
        """Every synced row, read in one consistent view."""
        ...

    async def apply(self, diff: SnapshotDiff) -> None:
        """Make every change in one transaction, each only if its row is still what the diff
        says it was before; raises `StateMoved`, changing nothing, when one is not."""
        ...

    async def base(self, remote: str) -> str | None:
        """The commit of `remote` this database last agreed with, or None."""
        ...

    async def set_base(self, remote: str, commit: str | None) -> None:
        """Record the commit this database now agrees with; None forgets it."""
        ...

    async def is_empty(self) -> bool:
        """Whether no synced table holds a row."""
        ...


@runtime_checkable
class StateRemote(Protocol):
    """The branch the sealed snapshot lives on."""

    @property
    def name(self) -> str:
        """Which repository and branch, as the watermark records it."""
        ...

    async def head(self) -> RemoteHead | None:
        """The branch's head and what it holds, or None when there is no branch yet."""
        ...

    async def at(self, commit: str) -> bytes | None:
        """What the branch held at `commit`, or None when the commit cannot be reached."""
        ...

    async def push(self, data: bytes, parent: str | None) -> str:
        """Commit `data` on top of `parent` (None: start the branch) and move the branch to
        it only if the branch is still at `parent`; raises `RemoteMoved` when it is not."""
        ...


@runtime_checkable
class StateCipher(Protocol):
    """Seals a snapshot for the branch, and opens one from it."""

    def seal(self, plaintext: bytes) -> bytes: ...

    def open(self, sealed: bytes) -> bytes:
        """The plaintext; raises `SnapshotUnreadable` when this key did not seal it."""
        ...


@runtime_checkable
class StateSyncServiceInterface(Protocol):
    """Keeps a database and its branch the same."""

    async def status(self) -> SyncReport:
        """What a sync would pull and push, writing nothing at either end."""
        ...

    async def sync(self, *, push: bool = True) -> SyncReport:
        """Merge both ends and write the result to each; with `push=False`, only here."""
        ...

    async def export(self) -> bytes:
        """This database's rows, sealed, with the commit it last agreed with."""
        ...

    async def restore(self, sealed: bytes) -> SyncReport:
        """Load an export into this database, which must hold no synced row."""
        ...

    async def forget(self) -> None:
        """Forget the commit this database last agreed with: the next sync is a first one."""
        ...
