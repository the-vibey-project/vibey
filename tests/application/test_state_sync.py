# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""StateSyncService (ADR-0086): one database and its `vibey-state` branch, kept the same.

Driven against in-memory ends: a store that checks every row it changes is still what the
sync read, a branch that moves only from the commit a push names, and a cipher that makes
the branch's bytes differ from the plaintext. Two stores on one branch are two machines."""

from __future__ import annotations

import hashlib

import pytest

from vibey.application.interfaces.state_sync import (
    StateCipher,
    StateRemote,
    StateStore,
    StateSyncServiceInterface,
)
from vibey.application.state_sync import ATTEMPTS, StateSyncService
from vibey.domain.state_sync import (
    ConflictRule,
    MergeOutcome,
    RemoteHead,
    RemoteMoved,
    Row,
    RowChange,
    SchemaMismatch,
    Snapshot,
    SnapshotCodec,
    SnapshotDiff,
    SnapshotDiffer,
    StateMerger,
    StateMoved,
    StateSyncRefused,
    SyncState,
    TableSpec,
)

SCHEMA = ("0001_initial",)
SPECS = (
    TableSpec("item", ("id",)),
    TableSpec("ledger", ("seq",), append_only=True),
    TableSpec("setting", ("id",), ConflictRule.MINE),
)
CODEC = SnapshotCodec(SPECS)
REMOTE = "git@example.com:org/repo.git#vibey-state"


def item(id_: int, value: str) -> Row:
    return {"id": id_, "value": value}


def snap(schema: tuple[str, ...] = SCHEMA, *, items: tuple[Row, ...] = ()) -> Snapshot:
    return CODEC.build(schema, {"item": items})


class FakeStore:
    """A database: rows by table and key, and the commit it last agreed with per remote."""

    def __init__(self, snapshot: Snapshot | None = None) -> None:
        snapshot = snapshot or snap()
        self.schema = snapshot.schema
        self.rows: dict[str, dict[str, Row]] = {t: dict(r) for t, r in snapshot.tables.items()}
        self.bases: dict[str, str | None] = {}
        self.applied = 0
        self.base_writes = 0
        #: Written by someone else just before the next apply, which then raises StateMoved.
        self.interloper: RowChange | None = None
        #: How many more applies raise StateMoved.
        self.moves = 0

    def put(self, table: str, key: str, value: Row | None) -> None:
        rows = self.rows.setdefault(table, {})
        if value is None:
            rows.pop(key, None)
        else:
            rows[key] = value

    def write(self, value: Row) -> None:
        """Someone working on this database changes an item."""
        self.put("item", CODEC.key(SPECS[0], value), value)

    async def snapshot(self) -> Snapshot:
        return Snapshot(self.schema, {t: dict(r) for t, r in self.rows.items()})

    async def apply(self, diff: SnapshotDiff) -> None:
        if self.interloper is not None:
            change, self.interloper = self.interloper, None
            self.put(change.table, change.key, change.after)
        if self.moves:
            self.moves -= 1
            raise StateMoved("the database changed under the sync")
        for change in diff.changes:
            if self.rows.get(change.table, {}).get(change.key) != change.before:
                raise StateMoved(f"{change.table} {change.key} is not what was read")
        for change in diff.changes:
            self.put(change.table, change.key, change.after)
        self.applied += 1

    async def base(self, remote: str) -> str | None:
        return self.bases.get(remote)

    async def set_base(self, remote: str, commit: str | None) -> None:
        self.base_writes += 1
        self.bases[remote] = commit

    async def is_empty(self) -> bool:
        return not any(self.rows.values())


class FakeRemote:
    """A branch: a list of commits, each a 40-hex sha and the sealed bytes it holds."""

    def __init__(self, name: str = REMOTE) -> None:
        self._name = name
        self.commits: list[tuple[str, bytes]] = []
        self.pushes = 0
        #: Pushed by someone else just before the next push, which then finds it moved.
        self.interloper: bytes | None = None
        #: Every push finds the branch moved.
        self.always_moves = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def tip(self) -> str | None:
        return self.commits[-1][0] if self.commits else None

    def commit(self, data: bytes) -> str:
        sha = hashlib.sha1(  # a commit id, not a security digest
            f"{len(self.commits)}:".encode() + data, usedforsecurity=False
        ).hexdigest()
        self.commits.append((sha, data))
        return sha

    async def head(self) -> RemoteHead | None:
        return RemoteHead(*self.commits[-1]) if self.commits else None

    async def at(self, commit: str) -> bytes | None:
        return dict(self.commits).get(commit)

    async def push(self, data: bytes, parent: str | None) -> str:
        self.pushes += 1
        if self.interloper is not None:
            self.commit(self.interloper)
            self.interloper = None
        if self.always_moves or parent != self.tip:
            raise RemoteMoved(f"the branch is at {self.tip}, not {parent}")
        return self.commit(data)


class XorCipher:
    """Not encryption: enough that what the branch holds is not the plaintext."""

    def __init__(self, key: int = 0x5A) -> None:
        self._key = key

    def seal(self, plaintext: bytes) -> bytes:
        return bytes(b ^ self._key for b in plaintext)

    def open(self, sealed: bytes) -> bytes:
        return bytes(b ^ self._key for b in sealed)


CIPHER = XorCipher()


def service(store: FakeStore, remote: FakeRemote, *, attempts: int = ATTEMPTS) -> StateSyncService:
    return StateSyncService(store, remote, CIPHER, codec=CODEC, attempts=attempts)


def on_branch(remote: FakeRemote, commit: str | None = None) -> Snapshot:
    """What the branch holds at `commit` (default: its head), opened."""
    data = dict(remote.commits)[commit] if commit else remote.commits[-1][1]
    return CODEC.decode(CIPHER.open(data))


def sealed(snapshot: Snapshot) -> bytes:
    return CIPHER.seal(CODEC.encode(snapshot))


async def in_sync(store: FakeStore, remote: FakeRemote) -> tuple[FakeStore, FakeRemote]:
    report = await service(store, remote).sync()
    assert report.state in (SyncState.SYNCED, SyncState.IN_SYNC)
    return store, remote


# --- the contracts --------------------------------------------------------------------------


def test_the_service_and_the_fakes_satisfy_their_interfaces() -> None:
    store, remote = FakeStore(), FakeRemote()
    assert isinstance(service(store, remote), StateSyncServiceInterface)
    assert isinstance(store, StateStore)
    assert isinstance(remote, StateRemote)
    assert isinstance(CIPHER, StateCipher)


@pytest.mark.parametrize("attempts", [0, -1])
def test_a_sync_needs_at_least_one_attempt(attempts: int) -> None:
    with pytest.raises(ValueError, match="at least one attempt"):
        service(FakeStore(), FakeRemote(), attempts=attempts)


# --- sync -----------------------------------------------------------------------------------


async def test_the_first_sync_pushes_this_database_and_records_the_commit() -> None:
    store = FakeStore(snap(items=(item(1, "a"), item(2, "b"))))
    remote = FakeRemote()

    report = await service(store, remote).sync()

    assert report.state is SyncState.SYNCED
    assert (report.pushed, report.to_push, report.pulled, report.rows) == (True, False, 0, 2)
    assert report.remote == REMOTE
    assert len(remote.commits) == 1
    assert report.commit == remote.tip
    assert report.commit is not None and len(report.commit) == 40
    assert store.bases[REMOTE] == remote.tip
    assert store.applied == 0
    # The branch holds the database, sealed: not the plaintext, but it opens to the rows.
    assert remote.commits[0][1] != CODEC.encode(await store.snapshot())
    assert on_branch(remote) == await store.snapshot()


async def test_a_second_sync_finds_nothing_to_pull_and_nothing_to_push() -> None:
    store, remote = await in_sync(FakeStore(snap(items=(item(1, "a"),))), FakeRemote())
    commits, pushes = list(remote.commits), remote.pushes

    report = await service(store, remote).sync()

    assert report.state is SyncState.IN_SYNC
    assert (report.pulled, report.pushed, report.to_push, report.rows) == (0, False, False, 1)
    assert report.commit is not None
    assert report.commit == remote.tip
    assert remote.commits == commits
    assert remote.pushes == pushes
    assert store.applied == 0
    assert report.describe() == f"{REMOTE}: in sync at {report.commit[:12]}, 1 row(s)"


async def test_a_database_with_no_rows_and_no_branch_still_starts_the_branch() -> None:
    store, remote = FakeStore(), FakeRemote()
    report = await service(store, remote).sync()
    assert report.state is SyncState.SYNCED
    assert report.pushed
    assert on_branch(remote) == snap()


async def test_another_machine_pulls_what_the_first_pushed() -> None:
    _, remote = await in_sync(FakeStore(snap(items=(item(1, "a"), item(2, "b")))), FakeRemote())
    pushed = remote.tip
    other = FakeStore()

    report = await service(other, remote).sync()

    assert report.state is SyncState.SYNCED
    assert (report.pulled, report.pushed, report.to_push, report.rows) == (2, False, False, 2)
    assert report.commit == pushed
    assert remote.tip == pushed  # nothing new to push: the branch did not move
    assert await other.snapshot() == on_branch(remote)
    assert other.bases[REMOTE] == pushed
    assert other.applied == 1


async def test_both_ends_changing_different_rows_merge_at_both() -> None:
    here, remote = await in_sync(FakeStore(snap(items=(item(1, "a"), item(2, "b")))), FakeRemote())
    there, _ = await in_sync(FakeStore(), remote)

    here.write(item(1, "changed here"))
    there.write(item(2, "changed there"))
    there.write(item(3, "added there"))
    first = await service(there, remote).sync()
    second = await service(here, remote).sync()
    third = await service(there, remote).sync()

    assert (first.pushed, first.pulled) == (True, 0)
    assert (second.pushed, second.pulled) == (True, 2)
    assert (third.state, third.pulled, third.pushed) == (SyncState.SYNCED, 1, False)
    expected = snap(
        items=(item(1, "changed here"), item(2, "changed there"), item(3, "added there"))
    )
    assert await here.snapshot() == expected
    assert await there.snapshot() == expected
    assert on_branch(remote) == expected
    for store in (here, there):
        assert (await service(store, remote).status()).state is SyncState.IN_SYNC


async def test_a_conflict_changes_nothing_at_either_end() -> None:
    here, remote = await in_sync(FakeStore(snap(items=(item(1, "a"),))), FakeRemote())
    there, _ = await in_sync(FakeStore(), remote)
    there.write(item(1, "there"))
    await service(there, remote).sync()
    here.write(item(1, "here"))
    before, commits, bases = await here.snapshot(), list(remote.commits), dict(here.bases)
    base_writes = here.base_writes

    report = await service(here, remote).sync()

    assert report.state is SyncState.CONFLICT
    assert [(c.table, c.key, c.reason) for c in report.conflicts] == [
        ("item", "[1]", "changed differently at both ends")
    ]
    assert report.commit == remote.tip
    assert report.describe().startswith(f"{REMOTE}: 1 conflict(s); nothing was changed")
    assert await here.snapshot() == before
    assert remote.commits == commits
    assert here.bases == bases
    assert here.base_writes == base_writes


async def test_a_database_that_changed_under_the_sync_is_read_again() -> None:
    _, remote = await in_sync(FakeStore(snap(items=(item(1, "a"),))), FakeRemote())
    store = FakeStore()
    # Someone writes item 2 here while the sync is pulling item 1.
    store.interloper = RowChange("item", "[2]", None, item(2, "written meanwhile"))
    store.moves = 1

    report = await service(store, remote).sync()

    assert report.state is SyncState.SYNCED
    assert (report.pulled, report.pushed, report.rows) == (1, True, 2)
    expected = snap(items=(item(1, "a"), item(2, "written meanwhile")))
    assert await store.snapshot() == expected
    assert on_branch(remote) == expected
    assert store.bases[REMOTE] == remote.tip


async def test_a_diff_whose_rows_moved_is_refused_by_the_store_and_read_again() -> None:
    _, remote = await in_sync(FakeStore(snap(items=(item(1, "a"),))), FakeRemote())
    store = FakeStore()
    # Someone writes the very row being pulled, to the same value: the diff's before is stale.
    store.interloper = RowChange("item", "[1]", None, item(1, "a"))

    report = await service(store, remote).sync()

    assert report.state is SyncState.IN_SYNC
    assert await store.snapshot() == on_branch(remote)
    assert store.bases[REMOTE] == remote.tip


async def test_a_branch_that_moved_under_the_push_is_read_again_and_merged() -> None:
    here, remote = await in_sync(FakeStore(snap(items=(item(1, "a"),))), FakeRemote())
    agreed = remote.tip
    here.write(item(2, "here"))
    # Another machine pushes item 3 between this sync's read and its push.
    remote.interloper = sealed(snap(items=(item(1, "a"), item(3, "there"))))

    report = await service(here, remote).sync()

    assert report.state is SyncState.SYNCED
    assert (report.pulled, report.pushed, report.rows) == (1, True, 3)
    assert remote.pushes == 3  # the first sync's, the one that found it moved, the retry
    assert len(remote.commits) == 3
    expected = snap(items=(item(1, "a"), item(2, "here"), item(3, "there")))
    assert on_branch(remote) == expected
    assert await here.snapshot() == expected
    assert on_branch(remote, agreed) == snap(items=(item(1, "a"),))
    assert here.bases[REMOTE] == remote.tip


async def test_a_sync_gives_up_when_the_branch_moves_under_every_attempt() -> None:
    store, remote = FakeStore(snap(items=(item(1, "a"),))), FakeRemote()
    remote.always_moves = True

    with pytest.raises(StateSyncRefused, match="gave up after 3 attempts"):
        await service(store, remote, attempts=3).sync()

    assert remote.pushes == 3
    assert remote.commits == []
    assert REMOTE not in store.bases


async def test_a_sync_gives_up_when_the_database_moves_under_every_attempt() -> None:
    _, remote = await in_sync(FakeStore(snap(items=(item(1, "a"),))), FakeRemote())
    store = FakeStore()
    store.moves = 2

    with pytest.raises(StateSyncRefused, match="gave up after 2 attempts"):
        await service(store, remote, attempts=2).sync()

    assert await store.snapshot() == snap()
    assert REMOTE not in store.bases


async def test_without_push_a_sync_applies_here_and_leaves_the_branch() -> None:
    here, remote = await in_sync(FakeStore(snap(items=(item(1, "a"),))), FakeRemote())
    there, _ = await in_sync(FakeStore(), remote)
    there.write(item(2, "there"))
    await service(there, remote).sync()
    here.write(item(3, "here"))
    commits = list(remote.commits)

    report = await service(here, remote).sync(push=False)

    assert report.state is SyncState.SYNCED
    assert (report.pulled, report.pushed, report.to_push, report.rows) == (1, False, True, 3)
    assert report.commit == remote.tip
    assert remote.commits == commits
    assert await here.snapshot() == snap(items=(item(1, "a"), item(2, "there"), item(3, "here")))
    assert here.bases[REMOTE] == remote.tip
    # The recorded base keeps the next sync three-way: it pushes, and pulls nothing again.
    later = await service(here, remote).sync()
    assert (later.pulled, later.pushed) == (0, True)
    assert on_branch(remote) == await here.snapshot()


async def test_without_push_a_first_sync_writes_nothing_anywhere() -> None:
    store, remote = FakeStore(snap(items=(item(1, "a"),))), FakeRemote()

    report = await service(store, remote).sync(push=False)

    assert report.state is SyncState.SYNCED
    assert (report.pulled, report.pushed, report.to_push, report.commit) == (0, False, True, None)
    assert remote.commits == []
    assert store.base_writes == 0


async def test_a_branch_that_is_gone_after_a_sync_is_refused() -> None:
    store, remote = FakeStore(snap(items=(item(1, "a"),))), FakeRemote()
    store.bases[REMOTE] = "a" * 40

    with pytest.raises(StateSyncRefused, match=f"{REMOTE} is gone.*commit aaaaaaaaaaaa"):
        await service(store, remote).sync()
    with pytest.raises(StateSyncRefused, match="is gone"):
        await service(store, remote).status()

    assert remote.pushes == 0
    assert store.bases[REMOTE] == "a" * 40


async def test_an_unreachable_base_is_refused_until_it_is_forgotten() -> None:
    store, remote = await in_sync(FakeStore(snap(items=(item(1, "a"),))), FakeRemote())
    store.bases[REMOTE] = "f" * 40  # a commit the branch no longer reaches
    store.write(item(2, "here"))

    with pytest.raises(StateSyncRefused, match="no longer reaches ffffffffffff"):
        await service(store, remote).sync()
    assert len(remote.commits) == 1

    await service(store, remote).forget()
    assert store.bases[REMOTE] is None
    report = await service(store, remote).sync()

    assert report.state is SyncState.SYNCED
    assert report.pushed
    assert on_branch(remote) == snap(items=(item(1, "a"), item(2, "here")))


async def test_two_ends_on_different_migrations_are_refused_before_anything_is_written() -> None:
    _, remote = await in_sync(FakeStore(snap(items=(item(1, "a"),))), FakeRemote())
    store = FakeStore(snap(("0001_initial", "0002_next")))

    with pytest.raises(SchemaMismatch):
        await service(store, remote).sync()

    assert store.applied == 0
    assert store.base_writes == 0
    assert remote.pushes == 1


async def test_the_default_codec_merger_and_differ_sync_every_synced_table() -> None:
    codec = SnapshotCodec()
    project = {"id": "p1", "name": "x", "updated_at": "2026-10-06T10:00:00+00:00"}
    store = FakeStore(codec.build(SCHEMA, {"project": [project]}))
    remote = FakeRemote()

    report = await StateSyncService(store, remote, CIPHER).sync()

    assert (report.state, report.rows, report.pushed) == (SyncState.SYNCED, 1, True)
    assert codec.decode(CIPHER.open(remote.commits[-1][1])) == await store.snapshot()


async def test_a_given_merger_and_differ_are_the_ones_used() -> None:
    calls: list[str] = []

    class CountingMerger(StateMerger):
        def merge(
            self, base: Snapshot | None, mine: Snapshot, theirs: Snapshot | None
        ) -> MergeOutcome:
            calls.append("merge")
            return super().merge(base, mine, theirs)

    class CountingDiffer(SnapshotDiffer):
        def diff(self, before: Snapshot, after: Snapshot) -> SnapshotDiff:
            calls.append("diff")
            return super().diff(before, after)

    store, remote = FakeStore(snap(items=(item(1, "a"),))), FakeRemote()
    sync = StateSyncService(
        store,
        remote,
        CIPHER,
        codec=CODEC,
        merger=CountingMerger(SPECS),
        differ=CountingDiffer(SPECS),
    )
    await sync.sync()
    assert calls == ["merge", "diff"]


# --- status ---------------------------------------------------------------------------------


async def test_status_before_the_first_sync_has_everything_to_push() -> None:
    store, remote = FakeStore(snap(items=(item(1, "a"),))), FakeRemote()

    report = await service(store, remote).status()

    assert report.state is SyncState.PENDING
    assert (report.pulled, report.to_push, report.commit, report.rows) == (0, True, None, 1)
    assert report.describe() == f"{REMOTE}: 0 row change(s) to pull, changes here to push; 1 row(s)"
    assert remote.pushes == 0
    assert store.base_writes == 0


async def test_status_reports_in_sync_pending_and_conflict_without_writing() -> None:
    here, remote = await in_sync(FakeStore(snap(items=(item(1, "a"),))), FakeRemote())
    there, _ = await in_sync(FakeStore(), remote)

    def writes() -> tuple[int, int, int, int]:
        return (remote.pushes, here.applied, here.base_writes, len(remote.commits))

    seen = writes()
    assert (await service(here, remote).status()).state is SyncState.IN_SYNC
    assert writes() == seen

    there.write(item(2, "there"))
    await service(there, remote).sync()
    seen = writes()
    pending = await service(here, remote).status()
    assert (pending.state, pending.pulled, pending.to_push) == (SyncState.PENDING, 1, False)
    assert pending.commit == remote.tip

    here.write(item(3, "here"))
    both = await service(here, remote).status()
    assert (both.state, both.pulled, both.to_push) == (SyncState.PENDING, 1, True)

    here.write(item(2, "here too"))
    conflict = await service(here, remote).status()
    assert conflict.state is SyncState.CONFLICT
    assert [c.key for c in conflict.conflicts] == ["[2]"]

    assert writes() == seen
    assert await here.snapshot() == snap(items=(item(1, "a"), item(2, "here too"), item(3, "here")))


# --- export, restore, forget ----------------------------------------------------------------


async def test_an_export_restores_into_an_empty_database_with_its_base() -> None:
    here, remote = await in_sync(FakeStore(snap(items=(item(1, "a"), item(2, "b")))), FakeRemote())
    exported = await service(here, remote).export()
    assert CODEC.encode(await here.snapshot()) not in exported  # sealed

    elsewhere = FakeStore()
    report = await service(elsewhere, FakeRemote()).restore(exported)

    assert report.state is SyncState.SYNCED
    assert (report.remote, report.pulled, report.rows) == (REMOTE, 2, 2)
    assert report.commit == remote.tip
    assert await elsewhere.snapshot() == await here.snapshot()
    assert elsewhere.bases == {REMOTE: remote.tip}
    # Restored with its base, the copy is already in sync with the branch.
    assert (await service(elsewhere, remote).status()).state is SyncState.IN_SYNC


async def test_an_export_of_a_database_never_synced_restores_with_no_base() -> None:
    here = FakeStore(snap(items=(item(1, "a"),)))
    exported = await service(here, FakeRemote()).export()

    elsewhere = FakeStore()
    report = await service(elsewhere, FakeRemote()).restore(exported)

    assert report.commit is None
    assert elsewhere.bases == {REMOTE: None}
    assert await elsewhere.snapshot() == await here.snapshot()


async def test_an_empty_export_restores_without_applying_anything() -> None:
    exported = await service(FakeStore(), FakeRemote()).export()
    elsewhere = FakeStore()

    report = await service(elsewhere, FakeRemote()).restore(exported)

    assert (report.pulled, report.rows) == (0, 0)
    assert elsewhere.applied == 0
    assert elsewhere.bases == {REMOTE: None}


async def test_restore_refuses_a_database_that_holds_rows() -> None:
    exported = await service(FakeStore(snap(items=(item(1, "a"),))), FakeRemote()).export()
    occupied = FakeStore(snap(items=(item(9, "mine"),)))

    with pytest.raises(StateSyncRefused, match="only into a database with no rows"):
        await service(occupied, FakeRemote()).restore(exported)

    assert await occupied.snapshot() == snap(items=(item(9, "mine"),))
    assert occupied.base_writes == 0


async def test_restore_refuses_an_export_on_other_migrations() -> None:
    exported = await service(FakeStore(snap(items=(item(1, "a"),))), FakeRemote()).export()
    newer = FakeStore(snap(("0001_initial", "0002_next")))

    with pytest.raises(SchemaMismatch, match="migrate this one to the export's"):
        await service(newer, FakeRemote()).restore(exported)

    assert newer.applied == 0
    assert newer.base_writes == 0


async def test_forget_clears_the_base_so_the_next_sync_is_a_first_one() -> None:
    store, remote = await in_sync(FakeStore(snap(items=(item(1, "a"),))), FakeRemote())
    assert store.bases[REMOTE] is not None

    await service(store, remote).forget()

    assert store.bases[REMOTE] is None
    # Both ends hold the same rows, so a first sync between them is a quiet one.
    report = await service(store, remote).sync()
    assert report.state is SyncState.IN_SYNC
    assert store.bases[REMOTE] == remote.tip
