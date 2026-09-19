# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Searching the ledger in Postgres: one query, one parameterised statement.

Every criterion is a `WHERE` clause and the limit is a `LIMIT`, so a search reads
the rows it returns plus one -- never the whole project ledger to filter in Python,
which is what `vibey ledger show` does and what a searchable ledger (sub-doctrine
7.a) cannot afford once the ledger is large.

**Nothing a searcher typed reaches the SQL text.** The compiler appends fixed clause
text and `$n` placeholders; every value -- the free text included -- is bound as a
parameter. Free text is matched with `ILIKE` against the payload's JSON text, with
`%`, `_` and the escape character escaped so they match literally.

What each criterion is served by (migrations/0002_event.sql and 0012):

| Criterion | Index |
|---|---|
| project, newest first | `event_project_seq` |
| `--id` | the primary key |
| `--digest` | `event_digest` |
| `--actor` (an engine) | `event_project_engine` |
| `--since` / `--until` | `event_project_produced_at` |
| `--kind` | `event_kind` |
| `--text` | none -- a scan of the project's rows. `payload::text` cannot use the
  `jsonb_path_ops` GIN index, which answers containment, not substrings. |
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final
from uuid import UUID

import asyncpg

from vibey.domain.interfaces.ledger_query_interface import (
    ActorInterface,
    LedgerQueryInterface,
)
from vibey.domain.ledger_query import ActorScope, LedgerSearchResult
from vibey.infrastructure.db.interfaces import (
    EventRowMapperInterface,
    LedgerSearchCompilerInterface,
)
from vibey.infrastructure.db.ledger_repository import EVENT_ROWS

LIKE_ESCAPE: Final = "\\"
"""The `ESCAPE` character for the free-text pattern. SQL syntax, not policy: the
compiler escapes it in the needle so every character a searcher types is literal."""


@dataclass(frozen=True, slots=True)
class SearchStatement:
    """SQL with `$n` placeholders, and the values bound to them in order."""

    sql: str
    args: tuple[object, ...]


class LedgerSearchCompiler:
    """Turns a `LedgerQuery` into one statement over the `event` table."""

    def compile(
        self, project_id: UUID, query: LedgerQueryInterface, *, fetch: int
    ) -> SearchStatement:
        args: list[object] = []

        def bind(value: object) -> str:
            # A closure rather than a method: it exists only to number the
            # placeholders of the one statement being built, in `args`.
            args.append(value)
            return f"${len(args)}"

        where = [f"project_id = {bind(project_id)}"]
        if query.event_id is not None:
            where.append(f"event_id = {bind(query.event_id)}")
        if query.digest is not None:
            where.append(f"digest = {bind(query.digest)}")
        if query.actor is not None:
            where.append(self._actor(query.actor, bind))
        if query.since is not None:
            where.append(f"produced_at >= {bind(query.since)}")
        if query.until is not None:
            where.append(f"produced_at < {bind(query.until)}")
        if query.kinds:
            kinds = sorted(kind.value for kind in query.kinds)
            where.append(f"kind = ANY({bind(kinds)}::text[])")
        if query.text is not None:
            pattern = bind(self.contains_pattern(query.text))
            where.append(f"payload::text ILIKE {pattern} ESCAPE '{LIKE_ESCAPE}'")
        # B608 below: only fixed clause text and $n placeholders are joined here,
        # every value is in `args`. Bandit cannot see that from the string shape.
        sql = (
            "SELECT * FROM event WHERE "  # nosec B608
            + " AND ".join(where)
            + f" ORDER BY seq DESC LIMIT {bind(fetch)}"
        )
        return SearchStatement(sql=sql, args=tuple(args))

    @staticmethod
    def contains_pattern(needle: str) -> str:
        """An `ILIKE` pattern matching `needle` anywhere, every character literal."""
        escaped = (
            needle.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2)
            .replace("%", LIKE_ESCAPE + "%")
            .replace("_", LIKE_ESCAPE + "_")
        )
        return f"%{escaped}%"

    @staticmethod
    def _actor(actor: ActorInterface, bind: Callable[[object], str]) -> str:
        if actor.scope is ActorScope.SELF:
            return "engine_id IS NULL"
        if actor.scope is ActorScope.ENGINE:
            return f"engine_id = {bind(actor.name)}"
        return f"provenance = {bind(actor.name)}::provenance"


LEDGER_SEARCH_SQL: Final[LedgerSearchCompilerInterface] = LedgerSearchCompiler()
"""The default compiler. Stateless, so one instance serves."""


class PostgresLedgerSearchRepository:
    """`LedgerSearch` over the Postgres ledger.

    Fetches one row past the limit: that row is how the result can say, honestly,
    that older matches were left out, without a second `count(*)` query.
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        *,
        compiler: LedgerSearchCompilerInterface = LEDGER_SEARCH_SQL,
        rows: EventRowMapperInterface = EVENT_ROWS,
    ) -> None:
        self._pool = pool
        self._compiler = compiler
        self._rows = rows

    async def search(self, project_id: UUID, query: LedgerQueryInterface) -> LedgerSearchResult:
        statement = self._compiler.compile(project_id, query, fetch=query.limit + 1)
        async with self._pool.acquire() as conn:
            newest_first = await conn.fetch(statement.sql, *statement.args)
        kept = newest_first[: query.limit]
        return LedgerSearchResult(
            events=tuple(self._rows.to_event(row) for row in reversed(kept)),
            truncated=len(newest_first) > query.limit,
        )
