# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from typing import Final
from uuid import UUID

import asyncpg

from vibey.application.dto import EngineHealthRecord
from vibey.domain.circuit import CIRCUIT_STATE_PARSER
from vibey.domain.engine import ENGINE_ID_PARSER, EngineId, UnrecognizedEngineId
from vibey.domain.interfaces.stored_value_interface import StoredValueParserInterface
from vibey.infrastructure.db.interfaces import EngineHealthRowMapperInterface


class EngineHealthRowMapper:
    """Turns one `engine_health` row into an `EngineHealthRecord`.

    The `engine_id` column is text, so a newer vibey adds an engine without a
    migration and its health rows reach every older worker at once -- #281's
    `claudeloop-local` is the first. The id is read forward-compatibly (vibey#287):
    a known one is its `EngineId` member, anything else an `UnrecognizedEngineId`
    carrying the stored text, never a `ValueError`. The selector skips such a row;
    `vibey status` and the dashboard still show it.

    (A known id must come back as the member, not the raw str: the raw str once
    propagated into RotationCursor and crashed `update_many`'s `.value` access the
    first time EngineSelector ran against real Postgres.)
    """

    def __init__(
        self,
        engines: StoredValueParserInterface[EngineId, UnrecognizedEngineId] = ENGINE_ID_PARSER,
    ) -> None:
        self._engines = engines

    def to_record(self, row: asyncpg.Record) -> EngineHealthRecord:
        return EngineHealthRecord(
            project_id=row["project_id"],
            engine_id=self._engines.parse(row["engine_id"]),
            installed=row["installed"],
            version=row["version"],
            conformance_ok=row["conformance_ok"],
            conformance_at=row["conformance_at"],
            auth_ok_at=row["auth_ok_at"],
            circuit=CIRCUIT_STATE_PARSER.parse(row["circuit"]),
            capacity_state=row["capacity_state"],
            resets_at=row["resets_at"],
            probe_next_at=row["probe_next_at"],
            probe_attempt=row["probe_attempt"],
            consecutive_fail=row["consecutive_fail"],
            ewma_failure=row["ewma_failure"],
            cost_usd_cycle=float(row["cost_usd_cycle"]),
            selected_count=row["selected_count"],
        )


HEALTH_ROWS: Final[EngineHealthRowMapperInterface] = EngineHealthRowMapper()
"""The one row mapper every reader of `engine_health` shares. Stateless."""


class PostgresEngineHealthRepository:
    def __init__(
        self, pool: asyncpg.Pool, *, rows: EngineHealthRowMapperInterface = HEALTH_ROWS
    ) -> None:
        self._pool = pool
        self._rows = rows

    async def get(self, project_id: UUID, engine_id: str) -> EngineHealthRecord | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM engine_health WHERE project_id = $1 AND engine_id = $2",
                project_id,
                engine_id,
            )
            return self._rows.to_record(row) if row is not None else None

    async def upsert(self, record: EngineHealthRecord) -> EngineHealthRecord:
        if CIRCUIT_STATE_PARSER.known(str(record.circuit)) is None:
            raise ValueError(f"refusing to write unknown circuit {record.circuit!s}")
        engine_id = ENGINE_ID_PARSER.known(str(record.engine_id))
        if engine_id is None:
            # Writers stay strict (vibey#287): this vibey reads a newer engine's
            # health row but never writes one -- it cannot run that engine, so it
            # has nothing true to say about its health.
            raw = getattr(record.engine_id, "value", str(record.engine_id))
            raise ValueError(
                f"refusing to write health for engine {raw!r}, which this vibey does not know"
            )
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO engine_health (
                    project_id, engine_id, installed, version, conformance_ok,
                    conformance_at, auth_ok_at, circuit, capacity_state, resets_at,
                    probe_next_at, probe_attempt, consecutive_fail, ewma_failure,
                    cost_usd_cycle, selected_count
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8::circuit_state, $9, $10,
                    $11, $12, $13, $14, $15, $16
                )
                ON CONFLICT (project_id, engine_id) DO UPDATE SET
                    installed        = EXCLUDED.installed,
                    version          = EXCLUDED.version,
                    conformance_ok   = EXCLUDED.conformance_ok,
                    conformance_at   = EXCLUDED.conformance_at,
                    auth_ok_at       = EXCLUDED.auth_ok_at,
                    circuit          = EXCLUDED.circuit,
                    capacity_state   = EXCLUDED.capacity_state,
                    resets_at        = EXCLUDED.resets_at,
                    probe_next_at    = EXCLUDED.probe_next_at,
                    probe_attempt    = EXCLUDED.probe_attempt,
                    consecutive_fail = EXCLUDED.consecutive_fail,
                    ewma_failure     = EXCLUDED.ewma_failure,
                    cost_usd_cycle   = EXCLUDED.cost_usd_cycle,
                    selected_count   = EXCLUDED.selected_count
                RETURNING *
                """,
                record.project_id,
                engine_id.value,
                record.installed,
                record.version,
                record.conformance_ok,
                record.conformance_at,
                record.auth_ok_at,
                record.circuit,
                record.capacity_state,
                record.resets_at,
                record.probe_next_at,
                record.probe_attempt,
                record.consecutive_fail,
                record.ewma_failure,
                record.cost_usd_cycle,
                record.selected_count,
            )
            if row is None:
                raise LookupError(f"upsert: no row returned for engine_health {record.engine_id}")
            return self._rows.to_record(row)

    async def list_for_project(self, project_id: UUID) -> tuple[EngineHealthRecord, ...]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM engine_health WHERE project_id = $1 ORDER BY engine_id",
                project_id,
            )
            return tuple(self._rows.to_record(r) for r in rows)
