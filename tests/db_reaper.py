# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reap the per-worker test databases that no live test session holds.

A test session creates ``vibey_test_<worker>_<run>`` (tests/conftest.py) and drops it at
teardown. A killed session never tears down, so its databases stay behind: 1,118 of them,
14 GB, were found on one machine on 2026-09-24. This module finds them and drops them.

"Held" is measured by the database server itself, never guessed from a name or an age:

- A session takes a session-level advisory lock on its database's key BEFORE it creates the
  database, marks the database with ``HOLD_MARK``, and keeps the lock on a connection of its
  own until teardown (``TestDatabaseHold``). PostgreSQL releases the lock the moment that
  connection ends, a kill included. So a marked database whose lock can be taken is held by
  no live session.
- A database without the mark was created by an older harness that took no lock, so a free
  lock proves nothing about it: a run of that harness may still be using it. It is reaped only
  when no other test session runs on this machine, since then none could be holding it.
- ``vibey_test_main_<pid>_<hex>`` names the process that created it. It is kept while that
  process is alive.
- A database with any open connection is kept, whatever else is true.
- Only names that match the per-worker pattern are ever considered. A template, or a lane's
  base database, is never touched.

Run by hand (the connection is VIBEY_TEST_DATABASE_URL's server, as the owner)::

    uv run python -m tests.db_reaper --dry-run     # say what would go, drop nothing
    uv run python -m tests.db_reaper               # drop what no live session holds

The test harness also runs it at every session's start, in the background (conftest.py), so
a leak is cleaned up by the next run on the same server without anyone remembering to (12.e).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import subprocess
import sys
import threading
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

import asyncpg

#: Written on every database the harness creates while holding its lock.
HOLD_MARK = "vibey-test-hold:v1"
#: The advisory-lock namespace for test databases: the first key of the two-key form. The
#: second is ``hashtext(<database name>)``, computed by the server both times.
LOCK_NAMESPACE = 0x76746462  # "vtdb"
#: The per-worker names conftest.py creates: xdist's 32-hex run id, or a serial run's
#: ``<pid>_<8 hex>``.
WORKER_DB = re.compile(r"^vibey_test_(?:gw\d+|main)_(?:[0-9a-f]{32}|(?P<pid>\d+)_[0-9a-f]{8})$")
#: The hold's poll, bound once, at import. A test may patch ``asyncio.sleep`` for its own
#: module -- the worker's ``--wait-for-project`` test does, through ``vibey.cli.main.asyncio``,
#: which is this very module -- and the hold, in its own thread, must never call the patched
#: one: its side effect would run here, and one that raised would end the hold and free the
#: lock that keeps the reaper away from this session's database.
_POLL = asyncio.sleep


def admin_dsn(dsn: str) -> str:
    """The same server, connected to the ``postgres`` maintenance database.

    Module-level (ADR-0016's written reason): a pure string transform that both classes
    below, and conftest.py, need.
    """
    base, _ = dsn.rsplit("/", 1)
    return f"{base}/postgres"


class TestDatabaseHold:
    """This process's hold on its test database, kept for the whole session.

    The lock lives on a connection of its own, in a thread with its own event loop, because
    the tests open and close event loops of their own all session long. ``start`` returns
    once the lock is held. Take it before the database exists, so a database never exists
    unheld while its session is alive.
    """

    __test__ = False

    def __init__(self, dsn: str, database: str) -> None:
        self._dsn = admin_dsn(dsn)
        self._database = database
        self._held = threading.Event()
        self._stop = threading.Event()
        self._error: BaseException | None = None
        self._thread = threading.Thread(target=self._run, name=f"hold:{database}", daemon=True)

    def start(self, timeout: float = 30.0) -> None:
        self._thread.start()
        if not self._held.wait(timeout):
            raise TimeoutError(f"could not take the hold on {self._database} in {timeout}s")
        if self._error is not None:
            raise self._error

    def release(self) -> None:
        self._stop.set()
        self._thread.join(timeout=10)

    def _run(self) -> None:
        asyncio.run(self._hold())

    async def _hold(self) -> None:
        try:
            conn = await asyncpg.connect(self._dsn)
        except BaseException as exc:  # noqa: BLE001 - handed to start(), which raises it
            self._error = exc
            self._held.set()
            return
        try:
            await conn.execute(
                "SELECT pg_advisory_lock($1, hashtext($2))", LOCK_NAMESPACE, self._database
            )
            self._held.set()
            while not self._stop.is_set():
                await _POLL(0.2)
        finally:
            await conn.close()


@dataclass(frozen=True, slots=True)
class Candidate:
    """One per-worker database, as the server describes it right now."""

    name: str
    marked: bool
    connections: int
    creator_pid: int | None


@dataclass(frozen=True, slots=True)
class Verdict:
    drop: bool
    reason: str


class OtherTestSessions:
    """Whether any test session other than this process's own is running on this machine.

    A pytest controller's command line names pytest; xdist's workers do not, but they die
    with their controller. This process, its ancestors (``uv run pytest``, a pre-push hook)
    and its descendants are excluded, so a session never counts itself.
    """

    def __init__(self, ps: Callable[[], str] | None = None, me: int | None = None) -> None:
        self._ps = ps or self._read_ps
        self._me = me if me is not None else os.getpid()

    @staticmethod
    def _read_ps() -> str:
        return subprocess.run(
            ["ps", "-Ao", "pid=,ppid=,command="], check=True, capture_output=True, text=True
        ).stdout

    def running(self) -> bool:
        rows: dict[int, tuple[int, str]] = {}
        for line in self._ps().splitlines():
            parts = line.split(None, 2)
            if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
                rows[int(parts[0])] = (int(parts[1]), parts[2])
        mine = self._family(rows)
        return any("pytest" in command and pid not in mine for pid, (_, command) in rows.items())

    def _family(self, rows: dict[int, tuple[int, str]]) -> set[int]:
        """This process, the chain that launched it, and the processes it launched.

        Descendants grow from this process alone, never from an ancestor: every agent's
        commands can share one ancestor (the tool that runs them), and counting that
        ancestor's other children as family would hide a concurrent test session, the one
        thing this class exists to see.
        """
        ancestors: set[int] = set()
        pid = self._me
        while pid in rows and rows[pid][0] > 1 and rows[pid][0] not in ancestors | {self._me}:
            pid = rows[pid][0]
            ancestors.add(pid)
        descendants = {self._me}
        grew = True
        while grew:
            grew = False
            for child, (parent, _) in rows.items():
                if parent in descendants and child not in descendants:
                    descendants.add(child)
                    grew = True
        return ancestors | descendants


def pid_alive(pid: int) -> bool:
    """Whether a process exists. Another user's process counts as alive.

    Module-level (ADR-0016's written reason): it is the default of the reaper's ``alive``
    injection point, which tests replace with a fake.
    """
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def decide(
    candidate: Candidate, lock_free: bool, others_running: bool, alive: bool | None
) -> Verdict:
    """Whether to drop one database. Every ``keep`` names what may still hold it.

    Module-level (ADR-0016's written reason): the whole rule as one pure function, so the
    tests can hold every branch of it without a database.
    """
    if candidate.connections:
        return Verdict(False, f"kept: {candidate.connections} open connection(s)")
    if not lock_free:
        return Verdict(False, "kept: a live session holds its lock")
    if alive:
        return Verdict(False, f"kept: its creator, pid {candidate.creator_pid}, is alive")
    if candidate.marked:
        return Verdict(True, "dropped: marked, and no session holds its lock")
    if others_running:
        return Verdict(False, "kept: unmarked, and another test session is running")
    return Verdict(True, "dropped: unmarked, and no other test session is running")


@dataclass
class Report:
    dropped: list[str] = field(default_factory=list)
    kept: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def line(self) -> str:
        kept = ", ".join(f"{count} {why}" for why, count in sorted(self.kept.items()))
        text = f"test database reaper: dropped {len(self.dropped)}"
        if kept:
            text += f"; {kept}"
        if self.errors:
            text += f"; {len(self.errors)} error(s): {self.errors[0]}"
        return text


class TestDatabaseReaper:
    """Drops the per-worker test databases that no live session holds (see the module doc)."""

    __test__ = False

    def __init__(
        self,
        dsn: str,
        *,
        sessions: OtherTestSessions | None = None,
        alive: Callable[[int], bool] = pid_alive,
        only: Iterable[str] | None = None,
        pattern: re.Pattern[str] = WORKER_DB,
    ) -> None:
        self._dsn = admin_dsn(dsn)
        self._sessions = sessions or OtherTestSessions()
        self._alive = alive
        self._only = set(only) if only is not None else None
        # Tests pass a pattern of their own, so the databases they stage are invisible to
        # the real reaper that another session may be running on the same server.
        self._pattern = pattern

    async def candidates(self, conn: asyncpg.Connection) -> list[Candidate]:
        rows = await conn.fetch(
            """
            SELECT d.datname,
                   coalesce(shobj_description(d.oid, 'pg_database'), '') = $1 AS marked,
                   (SELECT count(*) FROM pg_stat_activity a WHERE a.datname = d.datname)
                       AS connections
            FROM pg_database d
            ORDER BY d.datname
            """,
            HOLD_MARK,
        )
        found = []
        for row in rows:
            match = self._pattern.match(row["datname"])
            if match is None or (self._only is not None and row["datname"] not in self._only):
                continue
            pid = match.group("pid")
            found.append(
                Candidate(
                    row["datname"], row["marked"], row["connections"], int(pid) if pid else None
                )
            )
        return found

    async def reap(self, *, dry_run: bool = False, limit: int | None = None) -> Report:
        report = Report()
        others = self._sessions.running()
        conn = await asyncpg.connect(self._dsn)
        try:
            for candidate in await self.candidates(conn):
                if limit is not None and len(report.dropped) >= limit:
                    report.kept["over this run's limit"] = (
                        report.kept.get("over this run's limit", 0) + 1
                    )
                    continue
                await self._judge(conn, candidate, others, dry_run, report)
        finally:
            await conn.close()
        return report

    async def _judge(
        self,
        conn: asyncpg.Connection,
        candidate: Candidate,
        others: bool,
        dry_run: bool,
        report: Report,
    ) -> None:
        taken = await conn.fetchval(
            "SELECT pg_try_advisory_lock($1, hashtext($2))", LOCK_NAMESPACE, candidate.name
        )
        try:
            alive = self._alive(candidate.creator_pid) if candidate.creator_pid else None
            verdict = decide(candidate, lock_free=bool(taken), others_running=others, alive=alive)
            if not verdict.drop:
                report.kept[verdict.reason] = report.kept.get(verdict.reason, 0) + 1
                return
            if not dry_run:
                try:
                    await conn.execute(f'DROP DATABASE IF EXISTS "{candidate.name}"')
                except asyncpg.PostgresError as exc:  # a session connected since the count
                    report.errors.append(f"{candidate.name}: {exc}")
                    return
            report.dropped.append(candidate.name)
        finally:
            if taken:
                await conn.execute(
                    "SELECT pg_advisory_unlock($1, hashtext($2))", LOCK_NAMESPACE, candidate.name
                )


class BackgroundReap:
    """The harness's automatic reap: runs beside the session, never in its way."""

    __test__ = False

    def __init__(self, reaper: TestDatabaseReaper, limit: int | None) -> None:
        self._reaper = reaper
        self._limit = limit
        self.report: Report | None = None
        self._thread = threading.Thread(target=self._run, name="test-db-reaper", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def finish(self, timeout: float = 5.0) -> Report | None:
        self._thread.join(timeout)
        return self.report

    def _run(self) -> None:
        try:
            self.report = asyncio.run(self._reaper.reap(limit=self._limit))
        except Exception as exc:  # noqa: BLE001 - a reaper failure must never fail the tests
            self.report = Report(errors=[f"reaper did not run: {exc}"])


def main(argv: list[str] | None = None) -> int:
    """The command line (``python -m tests.db_reaper``). Module-level: an entry point."""
    parser = argparse.ArgumentParser(description="Drop the test databases no live session holds.")
    parser.add_argument("--dry-run", action="store_true", help="report, drop nothing")
    parser.add_argument("--limit", type=int, default=None, help="drop at most this many")
    parser.add_argument(
        "--dsn",
        default=os.environ.get(
            "VIBEY_TEST_DATABASE_URL",
            f"postgresql://{os.environ.get('USER', 'postgres')}@localhost:5432/postgres",
        ),
        help="any database on the server, as a role that may drop the test databases",
    )
    args = parser.parse_args(argv)
    report = asyncio.run(TestDatabaseReaper(args.dsn).reap(dry_run=args.dry_run, limit=args.limit))
    print(("(dry run) " if args.dry_run else "") + report.line())
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
