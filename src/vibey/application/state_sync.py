# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""StateSyncService: one database and its `vibey-state` branch, kept the same (ADR-0086).

One sync is one cycle:

1. read the branch's head, and the commit this database last agreed with (its base);
2. read this database whole, and merge it with the head against the base;
3. on any conflict, stop: nothing is written at either end, and every conflict is named;
4. apply the merge here, in one transaction that checks each row is still what was read;
5. record the head as the base: this database now holds everything the head held;
6. push the merge if it differs from the head, moving the branch only if it is still at
   the head, and record the pushed commit as the base.

A database that changed under step 4, or a branch that moved under step 6, starts the
cycle again; the base recorded in step 5 keeps the second merge three-way, so what was
just pulled is never mistaken for a change made here. Each step writes only what differs,
so a cycle with nothing new writes nothing, and a cycle that died anywhere is completed by
the next one (10.g: the watermark moves only once what it marks is durable).
"""

from __future__ import annotations

from dataclasses import dataclass

from vibey.application.interfaces.state_sync import (
    StateCipher,
    StateRemote,
    StateStore,
    StateSyncServiceInterface,
)
from vibey.domain.interfaces.state_sync_interface import (
    SnapshotCodecInterface,
    SnapshotDifferInterface,
    StateMergerInterface,
)
from vibey.domain.state_sync import (
    Exported,
    MergeOutcome,
    RemoteHead,
    RemoteMoved,
    SchemaMismatch,
    Snapshot,
    SnapshotCodec,
    SnapshotDiff,
    SnapshotDiffer,
    StateMerger,
    StateMoved,
    StateSyncRefused,
    SyncReport,
    SyncState,
)

#: How many times a cycle starts again before saying both ends kept moving.
ATTEMPTS = 5


@dataclass(frozen=True)
class SyncPlan:
    """One read of both ends, and what merging them comes to."""

    head: RemoteHead | None
    theirs: Snapshot | None
    outcome: MergeOutcome
    local: SnapshotDiff
    push: bool


class StateSyncService(StateSyncServiceInterface):
    """Implements `interfaces/state_sync.py::StateSyncServiceInterface`."""

    def __init__(
        self,
        store: StateStore,
        remote: StateRemote,
        cipher: StateCipher,
        *,
        codec: SnapshotCodecInterface | None = None,
        merger: StateMergerInterface | None = None,
        differ: SnapshotDifferInterface | None = None,
        attempts: int = ATTEMPTS,
    ) -> None:
        if attempts < 1:
            raise ValueError("a sync needs at least one attempt")
        self._store = store
        self._remote = remote
        self._cipher = cipher
        self._codec = codec or SnapshotCodec()
        self._merger = merger or StateMerger(self._codec.specs)
        self._differ = differ or SnapshotDiffer(self._codec.specs)
        self._attempts = attempts

    def _open(self, sealed: bytes) -> Snapshot:
        return self._codec.decode(self._cipher.open(sealed))

    async def _base(self, head: RemoteHead | None, theirs: Snapshot | None) -> Snapshot | None:
        commit = await self._store.base(self._remote.name)
        if commit is None:
            return None
        if head is None:
            raise StateSyncRefused(
                f"{self._remote.name} is gone, but this database last synced with its commit "
                f"{commit[:12]}: restore the branch, or run `vibey state forget` to start it "
                "again from this database"
            )
        if commit == head.commit:
            return theirs
        sealed = await self._remote.at(commit)
        if sealed is None:
            raise StateSyncRefused(
                f"{self._remote.name} no longer reaches {commit[:12]}, the commit this database "
                "last synced with, so a three-way merge has no base: run `vibey state forget` "
                "to merge the two ends as a first sync"
            )
        return self._open(sealed)

    async def plan(self) -> SyncPlan:
        """Read both ends and merge them, writing nothing."""
        head = await self._remote.head()
        theirs = self._open(head.data) if head is not None else None
        base = await self._base(head, theirs)
        mine = await self._store.snapshot()
        outcome = self._merger.merge(base, mine, theirs)
        local = self._differ.diff(mine, outcome.merged)
        push = theirs is None or self._codec.encode(outcome.merged) != self._codec.encode(theirs)
        return SyncPlan(head, theirs, outcome, local, push)

    def _report(
        self, state: SyncState, plan: SyncPlan, commit: str | None, *, pushed: bool = False
    ) -> SyncReport:
        return SyncReport(
            state=state,
            remote=self._remote.name,
            pulled=plan.local.count(),
            pushed=pushed,
            to_push=plan.push and not pushed,
            commit=commit,
            rows=plan.outcome.merged.row_count,
            conflicts=plan.outcome.conflicts,
        )

    async def status(self) -> SyncReport:
        plan = await self.plan()
        commit = plan.head.commit if plan.head else None
        if plan.outcome.conflicts:
            return self._report(SyncState.CONFLICT, plan, commit)
        if plan.local.empty and not plan.push:
            return self._report(SyncState.IN_SYNC, plan, commit)
        return self._report(SyncState.PENDING, plan, commit)

    async def sync(self, *, push: bool = True) -> SyncReport:
        for _ in range(self._attempts):
            plan = await self.plan()
            head = plan.head.commit if plan.head else None
            if plan.outcome.conflicts:
                return self._report(SyncState.CONFLICT, plan, head)
            if not plan.local.empty:
                try:
                    await self._store.apply(plan.local)
                except StateMoved:
                    continue
            if head is not None:
                await self._store.set_base(self._remote.name, head)
            if not plan.push or not push:
                quiet = plan.local.empty and not plan.push
                return self._report(SyncState.IN_SYNC if quiet else SyncState.SYNCED, plan, head)
            sealed = self._cipher.seal(self._codec.encode(plan.outcome.merged))
            try:
                commit = await self._remote.push(sealed, head)
            except RemoteMoved:
                continue
            await self._store.set_base(self._remote.name, commit)
            return self._report(SyncState.SYNCED, plan, commit, pushed=True)
        raise StateSyncRefused(
            f"gave up after {self._attempts} attempts: {self._remote.name} or this database "
            "changed under every one; nothing is half-written, so the next sync starts clean"
        )

    async def export(self) -> bytes:
        mine = await self._store.snapshot()
        base = await self._store.base(self._remote.name)
        return self._cipher.seal(self._codec.encode_export(Exported(mine, self._remote.name, base)))

    async def restore(self, sealed: bytes) -> SyncReport:
        exported = self._codec.decode_export(self._cipher.open(sealed))
        if not await self._store.is_empty():
            raise StateSyncRefused("an export is restored only into a database with no rows")
        here = await self._store.snapshot()
        if exported.snapshot.schema != here.schema:
            raise SchemaMismatch(
                "the export and this database have applied different migrations: "
                "migrate this one to the export's, then restore"
            )
        changes = self._differ.diff(here, exported.snapshot)
        if not changes.empty:
            await self._store.apply(changes)
        await self._store.set_base(exported.remote, exported.base)
        return SyncReport(
            state=SyncState.SYNCED,
            remote=exported.remote,
            pulled=changes.count(),
            commit=exported.base,
            rows=exported.snapshot.row_count,
        )

    async def forget(self) -> None:
        await self._store.set_base(self._remote.name, None)
