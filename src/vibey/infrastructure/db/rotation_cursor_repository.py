# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Postgres repository for rotation_cursor table.

The rotation_cursor table persists the SWRR (smooth weighted round robin) state
per project per engine. This state is updated transactionally with job leasing
to ensure crash-safety.
"""

from typing import Final
from uuid import UUID

import asyncpg

from vibey.application.dto import RotationCursor
from vibey.domain.engine import ENGINE_ID_PARSER, EngineId, UnrecognizedEngineId
from vibey.domain.interfaces.stored_value_interface import StoredValueParserInterface
from vibey.infrastructure.db.interfaces import RotationCursorRowMapperInterface


class RotationCursorRowMapper:
    """Turns one `rotation_cursor` row into a `RotationCursor`, one way for every read.

    The `engine_id` column is text, so a newer vibey keeps a cursor for an engine
    this one has never heard of the moment it first selects it. The id is read
    forward-compatibly (vibey#287): such a cursor comes back under its stored id,
    never as a `ValueError`. The selector leaves it out, so it is never rewritten
    here either -- `update_many` only writes the cursors it was handed.
    """

    def __init__(
        self,
        engines: StoredValueParserInterface[EngineId, UnrecognizedEngineId] = ENGINE_ID_PARSER,
    ) -> None:
        self._engines = engines

    def to_cursor(self, row: asyncpg.Record) -> RotationCursor:
        return RotationCursor(
            project_id=row["project_id"],
            engine_id=self._engines.parse(row["engine_id"]),
            current=row["current"],
            order=row["order"],
        )


CURSOR_ROWS: Final[RotationCursorRowMapperInterface] = RotationCursorRowMapper()
"""The one row mapper every read of `rotation_cursor` shares. Stateless."""


class PostgresRotationCursorRepository:
    def __init__(
        self, pool: asyncpg.Pool, *, rows: RotationCursorRowMapperInterface = CURSOR_ROWS
    ) -> None:
        self._pool = pool
        self._rows = rows

    @staticmethod
    def _writable(cursor: RotationCursor) -> EngineId:
        """The cursor's engine id, as long as it is one this vibey knows.

        Writers stay strict (vibey#287): this vibey reads a newer engine's cursor but
        never writes one, because it never selects that engine.
        """
        engine_id = cursor.engine_id
        if not isinstance(engine_id, EngineId):
            raise ValueError(
                f"refusing to write the rotation cursor of engine {engine_id.value!r}, "
                "which this vibey does not know"
            )
        return engine_id

    async def get(self, project_id: UUID, engine_id: EngineId) -> RotationCursor | None:
        """Get cursor for one engine, or None if not initialized."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM rotation_cursor WHERE project_id = $1 AND engine_id = $2",
                project_id,
                engine_id.value,
            )
            if row is None:
                return None
            return self._rows.to_cursor(row)

    async def list_for_project(self, project_id: UUID) -> tuple[RotationCursor, ...]:
        """Get all cursors for a project, including any a newer vibey keeps for an
        engine this one does not know."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                'SELECT * FROM rotation_cursor WHERE project_id = $1 ORDER BY "order"',
                project_id,
            )
            return tuple(self._rows.to_cursor(row) for row in rows)

    async def upsert(self, cursor: RotationCursor) -> RotationCursor:
        """Insert or update a cursor."""
        engine_id = self._writable(cursor)
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO rotation_cursor (project_id, engine_id, current, "order")
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (project_id, engine_id) DO UPDATE SET
                    current = EXCLUDED.current,
                    "order" = EXCLUDED."order"
                RETURNING *
                """,
                cursor.project_id,
                engine_id.value,
                cursor.current,
                cursor.order,
            )
            return self._rows.to_cursor(row)

    async def update_many(
        self, project_id: UUID, cursors: tuple[RotationCursor, ...]
    ) -> tuple[RotationCursor, ...]:
        """Update multiple cursors atomically (used after SWRR selection).

        This is the critical operation that must happen transactionally with
        job leasing so a crash cannot double-advance the cursor. Every cursor is
        checked before the transaction opens, so a refused one writes none.
        """
        writable = tuple((cursor, self._writable(cursor)) for cursor in cursors)
        async with self._pool.acquire() as conn, conn.transaction():
            results = []
            for cursor, engine_id in writable:
                row = await conn.fetchrow(
                    """
                        INSERT INTO rotation_cursor (project_id, engine_id, current, "order")
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (project_id, engine_id) DO UPDATE SET
                            current = EXCLUDED.current,
                            "order" = EXCLUDED."order"
                        RETURNING *
                        """,
                    cursor.project_id,
                    engine_id.value,
                    cursor.current,
                    cursor.order,
                )
                results.append(self._rows.to_cursor(row))
            return tuple(results)

    async def initialize_for_project(
        self, project_id: UUID, engines: tuple[EngineId, ...]
    ) -> tuple[RotationCursor, ...]:
        """Initialize cursors for all engines in a project.

        Sets current=0 and order based on engine position in the tuple.
        Idempotent - only inserts if not present. Returns every cursor the
        project has afterwards, including any a newer vibey keeps.
        """
        async with self._pool.acquire() as conn, conn.transaction():
            for idx, engine_id in enumerate(engines):
                await conn.execute(
                    """
                        INSERT INTO rotation_cursor (project_id, engine_id, current, "order")
                        VALUES ($1, $2, 0, $3)
                        ON CONFLICT (project_id, engine_id) DO NOTHING
                        """,
                    project_id,
                    engine_id.value,
                    idx,
                )

            # Return all cursors for the project
            rows = await conn.fetch(
                'SELECT * FROM rotation_cursor WHERE project_id = $1 ORDER BY "order"',
                project_id,
            )
            return tuple(self._rows.to_cursor(row) for row in rows)


__all__ = ["PostgresRotationCursorRepository"]
