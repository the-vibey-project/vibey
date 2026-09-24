# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The test-database reaper drops only what no live test session holds (tests/db_reaper.py).

Every database staged here uses the `vibeyreap_test_` prefix and a reaper built with that
prefix's pattern and an explicit `only` list, so neither this module nor a real reaper that
another session runs on the same server can ever touch the other's databases.
"""

from __future__ import annotations

import asyncio
import os
import re
import socket
import time
import uuid
from collections.abc import Callable, Iterator
from unittest.mock import AsyncMock, patch

import asyncpg
import pytest

from tests.db_reaper import (
    HOLD_MARK_V1,
    HOLD_MARK_V2,
    LOCK_NAMESPACE,
    Candidate,
    HoldMark,
    OtherTestSessions,
    Report,
    TestDatabaseHold,
    TestDatabaseReaper,
    UnreadableMark,
    admin_dsn,
    decide,
)

STAGED = re.compile(r"^vibeyreap_test_(?:gw\d+|main)_(?:[0-9a-f]{32}|(?P<pid>\d+)_[0-9a-f]{8})$")


def _base_dsn() -> str:
    return os.environ.get("_VIBEY_TEST_BASE_DSN") or os.environ["VIBEY_TEST_DATABASE_URL"]


def _worker_name() -> str:
    return f"vibeyreap_test_gw99_{uuid.uuid4().hex}"


class _Sessions(OtherTestSessions):
    """Another test session is, or is not, running: whatever the test says."""

    def __init__(self, running: bool) -> None:
        self._running = running

    def running(self) -> bool:
        return self._running


class _Staging:
    """Creates databases for one test and drops whatever is left of them afterwards."""

    def __init__(self) -> None:
        self.names: list[str] = []

    def create(self, name: str, *, marked: bool = False, mark: str | None = None) -> str:
        """``marked`` writes the first mark, v1, which names no process; ``mark``, this comment."""
        if mark is None and marked:
            mark = HOLD_MARK_V1

        async def go() -> None:
            conn = await asyncpg.connect(admin_dsn(_base_dsn()))
            try:
                await conn.execute(f'CREATE DATABASE "{name}"')
                if mark is not None:
                    await conn.execute(f"COMMENT ON DATABASE \"{name}\" IS '{mark}'")
            finally:
                await conn.close()

        asyncio.run(go())
        self.names.append(name)
        return name

    def exists(self, name: str) -> bool:
        async def go() -> bool:
            conn = await asyncpg.connect(admin_dsn(_base_dsn()))
            try:
                return bool(
                    await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", name)
                )
            finally:
                await conn.close()

        return asyncio.run(go())

    def reap(
        self, *, running: bool, alive: bool | Callable[[int], bool] = False, **kwargs: object
    ) -> Report:
        """Reap this test's databases. ``alive`` answers for every pid, or is the check to run."""
        reaper = TestDatabaseReaper(
            _base_dsn(),
            sessions=_Sessions(running),
            alive=alive if callable(alive) else lambda pid: alive,
            only=self.names,
            pattern=STAGED,
        )
        return asyncio.run(reaper.reap(**kwargs))  # type: ignore[arg-type]

    def drop_all(self) -> None:
        async def go() -> None:
            conn = await asyncpg.connect(admin_dsn(_base_dsn()))
            try:
                for name in self.names:
                    await conn.execute(f'DROP DATABASE IF EXISTS "{name}"')
            finally:
                await conn.close()

        asyncio.run(go())


@pytest.fixture
def staging() -> Iterator[_Staging]:
    stage = _Staging()
    yield stage
    stage.drop_all()


# --- the rule, without a database ---------------------------------------------------------


def _candidate(**overrides: object) -> Candidate:
    fields: dict[str, object] = {"name": "x", "marked": True, "connections": 0, "creator_pid": None}
    fields.update(overrides)
    return Candidate(**fields)  # type: ignore[arg-type]


def test_an_open_connection_keeps_a_database_whatever_else_is_true() -> None:
    verdict = decide(_candidate(connections=2), lock_free=True, others_running=False, alive=False)
    assert not verdict.drop and "2 open connection" in verdict.reason


def test_a_held_lock_keeps_a_database() -> None:
    assert not decide(_candidate(), lock_free=False, others_running=False, alive=None).drop


def test_a_living_creator_keeps_a_serial_runs_database() -> None:
    verdict = decide(_candidate(creator_pid=42), lock_free=True, others_running=False, alive=True)
    assert not verdict.drop and "pid 42" in verdict.reason


def test_a_marked_database_whose_lock_is_free_is_dropped_even_while_others_run() -> None:
    assert decide(_candidate(), lock_free=True, others_running=True, alive=None).drop


def test_an_unmarked_database_waits_for_every_other_session_to_end() -> None:
    unmarked = _candidate(marked=False)
    assert not decide(unmarked, lock_free=True, others_running=True, alive=None).drop
    assert decide(unmarked, lock_free=True, others_running=False, alive=None).drop


# --- the mark, without a database ----------------------------------------------------------


def _seen(comment: str | None, *, host: str) -> Candidate:
    """A worker database whose comment is ``comment``, as the machine named ``host`` sees it."""
    return Candidate.from_row(
        "vibey_test_gw0_x", name_pid=None, comment=comment, connections=0, host=host
    )


def test_a_v2_mark_names_the_process_that_created_the_database_and_its_machine() -> None:
    mark = HoldMark.read("vibey-test-hold:v2 pid=4242 host=build-box.lan")
    assert mark == HoldMark(4242, "build-box.lan")
    candidate = _seen(mark.text(), host="build-box.lan")
    assert candidate.marked and candidate.creator_pid == 4242 and not candidate.unreadable


def test_a_v2_mark_from_another_machine_names_no_process_here() -> None:
    """A pid is a process only on the machine that issued it."""
    candidate = _seen("vibey-test-hold:v2 pid=4242 host=build-box.lan", host="laptop.lan")
    assert candidate.marked and candidate.creator_pid is None and not candidate.unreadable


def test_a_v1_mark_is_a_mark_that_names_no_process() -> None:
    assert HoldMark.read(HOLD_MARK_V1) is None
    candidate = _seen(HOLD_MARK_V1, host="build-box.lan")
    assert candidate.marked and candidate.creator_pid is None and not candidate.unreadable


def test_a_comment_that_is_no_mark_leaves_the_database_unmarked() -> None:
    for comment in (None, "", "a note someone wrote", "vibey-test-hold v2 pid=4242"):
        assert HoldMark.read(comment) is None
        assert not _seen(comment, host="build-box.lan").marked


@pytest.mark.parametrize(
    "comment",
    [
        "vibey-test-hold:v2",
        "vibey-test-hold:v2 pid=4242",
        "vibey-test-hold:v2 host=build-box.lan pid=4242",
        "vibey-test-hold:v2 pid=abc host=build-box.lan",
        "vibey-test-hold:v2 pid=0 host=build-box.lan",
        "vibey-test-hold:v2 pid=-4242 host=build-box.lan",
        "vibey-test-hold:v2 pid=04242 host=build-box.lan",
        "vibey-test-hold:v2 pid=4294967296 host=build-box.lan",
        "vibey-test-hold:v2 pid=42424242424 host=build-box.lan",
        "vibey-test-hold:v2 pid=4242 host=build box.lan",
        "vibey-test-hold:v2 pid=4242 host=build-box.lan\n",
        "vibey-test-hold:v2x pid=4242 host=build-box.lan",
        "vibey-test-hold:v1 pid=4242 host=build-box.lan",
        "vibey-test-hold:v3 pid=4242 host=build-box.lan",
    ],
)
def test_a_mark_that_cannot_be_read_keeps_its_database(comment: str) -> None:
    """A malformed v2 mark, or a version this reaper does not know: unknown is never dropped."""
    with pytest.raises(UnreadableMark):
        HoldMark.read(comment)
    candidate = _seen(comment, host="build-box.lan")
    assert candidate.marked and candidate.unreadable
    verdict = decide(candidate, lock_free=True, others_running=False, alive=None)
    assert not verdict.drop and verdict.reason == "kept: its mark could not be read"


def test_the_mark_this_process_writes_reads_back_as_itself() -> None:
    mine = HoldMark.this_process()
    assert mine == HoldMark(os.getpid(), socket.gethostname())
    assert mine.text().startswith(f"{HOLD_MARK_V2} pid={os.getpid()} host=")
    assert HoldMark.read(mine.text()) == mine


def test_a_hostname_of_any_shape_reads_back_and_never_breaks_the_mark() -> None:
    """The host is percent-encoded, so no space, quote or newline of its own reaches the text."""
    odd = HoldMark(4242, "the lab's box\n100% ~ok")
    text = odd.text()
    assert HoldMark.read(text) == odd
    assert "'" not in text and "\n" not in text and text.count(" ") == 2


def test_a_v2_creator_keeps_its_database_while_it_lives() -> None:
    """decide() gives the pid a v2 mark names the keep a serial run's name gives its pid."""
    candidate = _seen("vibey-test-hold:v2 pid=4242 host=build-box.lan", host="build-box.lan")
    kept = decide(candidate, lock_free=True, others_running=False, alive=True)
    assert not kept.drop and kept.reason == "kept: its creator, pid 4242, is alive"
    assert decide(candidate, lock_free=True, others_running=True, alive=False).drop


# --- other sessions ----------------------------------------------------------------------


# A fake process table. Row 202 copies the command line xdist gives its workers; it is
# text in a string, never executed here.
PS = """\
    1     0 /sbin/launchd
  100     1 node claude-code
  200   100 uv run pytest -q
  201   200 python -m pytest -q
  202   201 python -c import sys;exec(eval(sys.stdin.readline()))
"""


def test_a_session_never_counts_itself_its_launcher_or_its_workers() -> None:
    assert not OtherTestSessions(ps=lambda: PS, me=201).running()


def test_a_session_started_beside_this_one_under_a_shared_ancestor_is_seen() -> None:
    """The bug this guards: family grown from an ancestor hides a sibling's session."""
    sibling = PS + "  300   100 python -m pytest tests/\n"
    assert OtherTestSessions(ps=lambda: sibling, me=201).running()


# --- the reaper against the real server -----------------------------------------------------


def test_a_marked_database_no_session_holds_is_dropped(staging: _Staging) -> None:
    name = staging.create(_worker_name(), marked=True)
    report = staging.reap(running=True)
    assert report.dropped == [name]  # type: ignore[attr-defined]
    assert not staging.exists(name)


def test_a_database_a_live_session_holds_is_kept(staging: _Staging) -> None:
    name = _worker_name()
    hold = TestDatabaseHold(_base_dsn(), name)
    hold.start()
    try:
        staging.create(name, marked=True)
        report = staging.reap(running=False)
        assert report.dropped == []  # type: ignore[attr-defined]
        assert staging.exists(name)
    finally:
        hold.release()
    assert staging.reap(running=False).dropped == [name]  # type: ignore[attr-defined]


def test_an_unmarked_database_is_kept_until_no_other_session_runs(staging: _Staging) -> None:
    name = staging.create(_worker_name(), marked=False)
    assert staging.reap(running=True).dropped == []  # type: ignore[attr-defined]
    assert staging.exists(name)
    assert staging.reap(running=False).dropped == [name]  # type: ignore[attr-defined]


def test_a_database_with_an_open_connection_is_kept(staging: _Staging) -> None:
    name = staging.create(_worker_name(), marked=True)
    base, _ = _base_dsn().rsplit("/", 1)

    async def held_open() -> list[str]:
        conn = await asyncpg.connect(f"{base}/{name}")
        try:
            reaper = TestDatabaseReaper(
                _base_dsn(), sessions=_Sessions(False), only=[name], pattern=STAGED
            )
            return (await reaper.reap()).dropped
        finally:
            await conn.close()

    assert asyncio.run(held_open()) == []
    assert staging.exists(name)


def test_a_serial_runs_database_is_kept_while_its_creator_lives(staging: _Staging) -> None:
    name = staging.create(f"vibeyreap_test_main_{os.getpid()}_{os.urandom(4).hex()}", marked=True)
    assert staging.reap(running=False, alive=True).dropped == []  # type: ignore[attr-defined]
    assert staging.reap(running=False, alive=False).dropped == [name]  # type: ignore[attr-defined]


def test_a_dry_run_names_what_would_go_and_drops_nothing(staging: _Staging) -> None:
    name = staging.create(_worker_name(), marked=True)
    assert staging.reap(running=False, dry_run=True).dropped == [name]  # type: ignore[attr-defined]
    assert staging.exists(name)


def test_the_limit_caps_one_runs_drops(staging: _Staging) -> None:
    for _ in range(3):
        staging.create(_worker_name(), marked=True)
    report = staging.reap(running=False, limit=2)
    assert len(report.dropped) == 2  # type: ignore[attr-defined]
    assert report.kept == {"over this run's limit": 1}  # type: ignore[attr-defined]


def test_a_name_outside_the_pattern_is_never_a_candidate(staging: _Staging) -> None:
    name = staging.create(f"vibeyreap_test_template_{uuid.uuid4().hex[:8]}", marked=True)
    assert staging.reap(running=False).dropped == []  # type: ignore[attr-defined]
    assert staging.exists(name)


# --- the harness -------------------------------------------------------------------------


def test_this_sessions_own_database_is_marked_and_held() -> None:
    """conftest.py took the hold before creating this worker's database, and marked it with
    this process, on this machine, as its creator."""
    database = os.environ["VIBEY_TEST_DATABASE_URL"].rsplit("/", 1)[1]

    async def look() -> tuple[str, bool]:
        conn = await asyncpg.connect(admin_dsn(_base_dsn()))
        try:
            mark = await conn.fetchval(
                "SELECT shobj_description(oid, 'pg_database') FROM pg_database WHERE datname = $1",
                database,
            )
            free = await conn.fetchval(
                "SELECT pg_try_advisory_lock($1, hashtext($2))", LOCK_NAMESPACE, database
            )
            if free:
                await conn.execute(
                    "SELECT pg_advisory_unlock($1, hashtext($2))", LOCK_NAMESPACE, database
                )
            return mark, bool(free)
        finally:
            await conn.close()

    mark, free = asyncio.run(look())
    assert HoldMark.read(mark) == HoldMark(os.getpid(), socket.gethostname())
    assert not free, "a live session's database must be held"


def test_a_test_that_patches_asyncio_sleep_never_reaches_the_hold() -> None:
    """The worker's `--wait-for-project` test patches `asyncio.sleep` through
    `vibey.cli.main.asyncio`, which is the module itself, to create a project. The hold's
    poll called it too: the project was created twice, and a side effect that raised ended
    the hold and freed the lock that keeps the reaper away from the session's database."""
    name = _worker_name()
    hold = TestDatabaseHold(_base_dsn(), name)
    hold.start()

    async def still_held() -> bool:
        conn = await asyncpg.connect(admin_dsn(_base_dsn()))
        try:
            free = await conn.fetchval(
                "SELECT pg_try_advisory_lock($1, hashtext($2))", LOCK_NAMESPACE, name
            )
            if free:
                await conn.execute(
                    "SELECT pg_advisory_unlock($1, hashtext($2))", LOCK_NAMESPACE, name
                )
            return not free
        finally:
            await conn.close()

    try:
        with patch("asyncio.sleep", new=AsyncMock(side_effect=RuntimeError("patched"))):
            time.sleep(0.7)  # three of the hold's polls, on the real clock
        assert asyncio.run(still_held()), "a patched asyncio.sleep ended the hold"
    finally:
        hold.release()
