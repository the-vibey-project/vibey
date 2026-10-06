# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""PostgresStateStore: the database the state sync reads whole and changes row by row
(ADR-0086).

**Read.** Every synced table in one `REPEATABLE READ` view, each row as `to_jsonb` renders
it, in UTC and with the shortest exact float form, so the same row reads as the same JSON
on every machine and every server version vibey supports. Generated columns are left
out: they are derived, and cannot be written.

**Apply.** One transaction. Each changed row is locked and compared with what the sync
read; if any differs, a worker wrote it since, and the whole apply is rolled back with
`StateMoved`, so a sync never overwrites a write it did not see. Rows are written parents
first and deleted children first; a column that references its own table is written once
every row of that table is in. The ledger's next `seq` per project and every declared
sequence are then advanced past what was written, never back.

The sync writes tables the application role may not (ADR-0055), so it connects with its
own DSN (`VIBEY_STATE_PG_URL`). Table and column names come from the declared tables and
the catalog, never from a snapshot's text; every value travels as a bound parameter.
"""

from collections.abc import Awaitable, Callable, Sequence
from typing import Final, cast

import asyncpg

from vibey.application.interfaces.state_sync import StateStore
from vibey.domain.state_sync import (
    CANONICAL,
    TABLES,
    Row,
    RowChange,
    Snapshot,
    SnapshotCodec,
    SnapshotDiff,
    StateMoved,
    TableSpec,
)

Connect = Callable[[str], Awaitable[asyncpg.Connection]]

#: Every read and write sees times in UTC and floats in their shortest exact form.
_SESSION: Final[tuple[str, ...]] = ("SET LOCAL TIME ZONE 'UTC'", "SET LOCAL extra_float_digits = 1")

_COLUMNS: Final = """
SELECT a.attname AS name, a.attgenerated <> '' AS generated
FROM pg_catalog.pg_attribute a
WHERE a.attrelid = $1::regclass AND a.attnum > 0 AND NOT a.attisdropped
ORDER BY a.attnum
"""

#: How long the apply waits for a writer to finish before it lets the sync merge again.
LOCK_TIMEOUT_MS: Final = 10_000

_EVENT_SEQ: Final = """
INSERT INTO event_seq (project_id, next_seq)
SELECT project_id, max(seq) + 1 FROM event GROUP BY project_id
ON CONFLICT (project_id) DO UPDATE SET next_seq = GREATEST(event_seq.next_seq, EXCLUDED.next_seq)
"""


def quote(name: str) -> str:
    """A SQL identifier, quoted. Module-level: shared by the store's every statement and
    its tests, with no state of its own."""
    return '"' + name.replace('"', '""') + '"'


class PostgresStateStore(StateStore):
    """Implements `application/interfaces/state_sync.py::StateStore`."""

    def __init__(
        self,
        dsn: str,
        *,
        specs: Sequence[TableSpec] = TABLES,
        connect: Connect = asyncpg.connect,
        lock_timeout_ms: int = LOCK_TIMEOUT_MS,
    ) -> None:
        if lock_timeout_ms < 1:
            raise ValueError("the lock timeout is at least 1 ms")
        if not dsn:
            raise ValueError(
                "the state sync needs a database: set VIBEY_STATE_PG_URL or VIBEY_PG_URL"
            )
        self._dsn = dsn
        self._specs = tuple(specs)
        self._codec = SnapshotCodec(self._specs)
        self._connect = connect
        self._lock_timeout = f"SET LOCAL lock_timeout = '{int(lock_timeout_ms)}ms'"

    @staticmethod
    async def _session(conn: asyncpg.Connection) -> None:
        for statement in _SESSION:
            await conn.execute(statement)

    @staticmethod
    async def _columns(conn: asyncpg.Connection, table: str) -> tuple[list[str], list[str]]:
        """The table's writable columns and its generated ones, in table order."""
        rows = await conn.fetch(_COLUMNS, quote(table))
        writable = [str(r["name"]) for r in rows if not r["generated"]]
        generated = [str(r["name"]) for r in rows if r["generated"]]
        return writable, generated

    async def snapshot(self) -> Snapshot:
        conn = await self._connect(self._dsn)
        try:
            async with conn.transaction(isolation="repeatable_read", readonly=True):
                await self._session(conn)
                schema = [
                    str(r["version"])
                    for r in await conn.fetch(
                        "SELECT version FROM schema_migration ORDER BY version"
                    )
                ]
                tables: dict[str, list[Row]] = {}
                for spec in self._specs:
                    _, generated = await self._columns(conn, spec.name)
                    found = await conn.fetch(
                        f"SELECT (to_jsonb(t) - $1::text[])::text AS row FROM {quote(spec.name)} t",  # nosec B608 -- a declared table name, quoted
                        generated,
                    )
                    tables[spec.name] = [self._row(r["row"]) for r in found]
                return self._codec.build(schema, tables)
        finally:
            await conn.close()

    @staticmethod
    def _row(text: str) -> Row:
        return cast(Row, CANONICAL.loads(text))

    async def apply(self, diff: SnapshotDiff) -> None:
        if diff.empty:
            return
        touched = [
            (spec, [c for c in diff.changes if c.table == spec.name]) for spec in self._specs
        ]
        touched = [(spec, changes) for spec, changes in touched if changes]
        conn = await self._connect(self._dsn)
        try:
            async with conn.transaction():
                await self._session(conn)
                await conn.execute(self._lock_timeout)
                # Writers wait, briefly, while the apply runs: nothing it checked can
                # change before it writes (readers never wait).
                for spec, _ in touched:
                    await conn.execute(
                        f"LOCK TABLE {quote(spec.name)} IN SHARE ROW EXCLUSIVE MODE"  # nosec B608 -- a declared table name, quoted
                    )
                columns = {spec.name: await self._columns(conn, spec.name) for spec, _ in touched}
                for spec, changes in touched:
                    await self._guard(conn, spec, changes, columns[spec.name][1])
                for spec, changes in touched:
                    await self._upsert(conn, spec, changes, columns[spec.name][0])
                for spec, changes in reversed(touched):
                    await self._delete(conn, spec, changes)
                await self._advance(conn, {spec.name for spec, _ in touched})
        except (asyncpg.DeadlockDetectedError, asyncpg.LockNotAvailableError) as busy:
            raise StateMoved(f"the database was busy while the sync applied ({busy})") from busy
        finally:
            await conn.close()

    @staticmethod
    def _keyed(spec: TableSpec, source: str) -> str:
        """`(k1, k2) IN (SELECT k1, k2 FROM <source>)`, `source` a populate over `$1`."""
        keys = ", ".join(quote(k) for k in spec.key)
        return f"({keys}) IN (SELECT {keys} FROM {source})"  # nosec B608 -- quoted names

    @staticmethod
    def _recordset(spec: TableSpec) -> str:
        return f"jsonb_populate_recordset(NULL::{quote(spec.name)}, $1::jsonb)"

    @staticmethod
    def _record(spec: TableSpec) -> str:
        return f"jsonb_populate_record(NULL::{quote(spec.name)}, $1::jsonb)"

    async def _guard(
        self,
        conn: asyncpg.Connection,
        spec: TableSpec,
        changes: list[RowChange],
        generated: list[str],
    ) -> None:
        """Every changed row is still what the sync read, or nothing is written."""
        rows = [c.before if c.before is not None else c.after for c in changes]
        found = await conn.fetch(
            f"SELECT (to_jsonb(t) - $2::text[])::text AS row FROM {quote(spec.name)} t "  # nosec B608 -- declared names, quoted
            f"WHERE {self._keyed(spec, self._recordset(spec))}",
            CANONICAL.dumps([dict(row) for row in rows if row is not None]),
            generated,
        )
        current = {self._codec.key(spec, row): row for row in (self._row(r["row"]) for r in found)}
        for change in changes:
            if current.get(change.key) != change.before:
                raise StateMoved(
                    f"{spec.name} {change.key} changed here while the sync was merging; it "
                    "will merge again"
                )

    async def _upsert(
        self,
        conn: asyncpg.Connection,
        spec: TableSpec,
        changes: list[RowChange],
        writable: list[str],
    ) -> None:
        rows = [CANONICAL.dumps(dict(c.after)) for c in changes if c.after is not None]
        if not rows:
            return
        columns = ", ".join(quote(c) for c in writable)
        picked = ", ".join("NULL" if c in spec.deferred else quote(c) for c in writable)
        sets = ", ".join(
            f"{quote(c)} = " + ("NULL" if c in spec.deferred else f"EXCLUDED.{quote(c)}")
            for c in writable
            if c not in spec.key
        )
        conflict = f"DO UPDATE SET {sets}" if sets else "DO NOTHING"  # nosec B608 -- quoted
        await conn.executemany(
            f"INSERT INTO {quote(spec.name)} ({columns}) "  # nosec B608 -- declared names, quoted
            f"SELECT {picked} FROM {self._record(spec)} "
            f"ON CONFLICT ({', '.join(quote(k) for k in spec.key)}) {conflict}",
            [(row,) for row in rows],
        )
        for column in spec.deferred:
            await conn.executemany(
                f"UPDATE {quote(spec.name)} SET {quote(column)} = "  # nosec B608 -- declared names, quoted
                f"(SELECT {quote(column)} FROM {self._record(spec)}) "
                f"WHERE {self._keyed(spec, self._record(spec))}",
                [(row,) for row in rows],
            )

    async def _delete(
        self, conn: asyncpg.Connection, spec: TableSpec, changes: list[RowChange]
    ) -> None:
        rows = [
            CANONICAL.dumps(dict(c.before))
            for c in changes
            if c.after is None and c.before is not None
        ]
        if rows:
            await conn.executemany(
                f"DELETE FROM {quote(spec.name)} "  # nosec B608 -- declared names, quoted
                f"WHERE {self._keyed(spec, self._record(spec))}",
                [(row,) for row in rows],
            )

    async def _advance(self, conn: asyncpg.Connection, tables: set[str]) -> None:
        """The ledger's next seq, and every declared sequence, past what was written."""
        if "event" in tables:
            await conn.execute(_EVENT_SEQ)
        for spec in self._specs:
            if spec.name not in tables:
                continue
            for column, sequence in spec.sequences:
                await conn.execute(
                    f"SELECT setval($1::regclass, GREATEST(s.last_value, m.v)) "  # nosec B608 -- declared names, quoted
                    f"FROM {quote(sequence)} s, (SELECT max({quote(column)}) AS v "
                    f"FROM {quote(spec.name)}) m WHERE m.v IS NOT NULL",
                    quote(sequence),
                )

    async def base(self, remote: str) -> str | None:
        conn = await self._connect(self._dsn)
        try:
            found = await conn.fetchval(
                "SELECT base_commit FROM state_sync WHERE remote = $1", remote
            )
            return None if found is None else str(found)
        finally:
            await conn.close()

    async def set_base(self, remote: str, commit: str | None) -> None:
        conn = await self._connect(self._dsn)
        try:
            if commit is None:
                await conn.execute("DELETE FROM state_sync WHERE remote = $1", remote)
                return
            await conn.execute(
                "INSERT INTO state_sync (remote, base_commit) VALUES ($1, $2) "
                "ON CONFLICT (remote) DO UPDATE SET base_commit = EXCLUDED.base_commit, "
                "synced_at = now() WHERE state_sync.base_commit <> EXCLUDED.base_commit",
                remote,
                commit,
            )
        finally:
            await conn.close()

    async def is_empty(self) -> bool:
        conn = await self._connect(self._dsn)
        try:
            for spec in self._specs:
                if await conn.fetchval(
                    f"SELECT EXISTS (SELECT 1 FROM {quote(spec.name)})"  # nosec B608 -- a declared table name, quoted
                ):
                    return False
            return True
        finally:
            await conn.close()
