# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Count the SQL statements a block sends through an asyncpg pool.

A pool hands connections out lazily and ``asyncpg.Pool`` is slotted, so its
``acquire`` cannot be wrapped. ``QueryCounter`` therefore holds every
connection the pool may own at once (``get_max_size()``, public API), attaches
one logger to each, and releases them; on exit it does the same to detach. A
logger survives ``release`` (asyncpg clears it only when the connection
closes), so any connection the block later acquires is already covered.

asyncpg delivers ``LoggedQuery`` records with ``loop.call_soon``, so the
counter yields to the loop once before it reads or detaches: the last
statement's record is otherwise still in flight.
"""

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import asyncpg
from asyncpg.connection import LoggedQuery

# What asyncpg runs on a connection as the pool takes it back (its reset query).
# It is driver housekeeping, not the operation under test, and it would add one
# statement to every counted block that releases a connection.
_POOL_RESET_STEPS = frozenset(
    {"SELECT pg_advisory_unlock_all()", "CLOSE ALL", "UNLISTEN *", "RESET ALL"}
)


# asyncpg introspects a type the first time a connection meets it: it switches
# JIT off, reads the type tree and switches JIT back. Whether that happens in a
# block depends on how warm the connection's cache is, never on the operation.
_INTROSPECTION_MARKERS = ("typeinfo_tree", "current_setting('jit')", "set_config('jit'")


def _is_pool_reset(query: str) -> bool:
    steps = [step.strip() for step in query.split(";") if step.strip()]
    return bool(steps) and all(step in _POOL_RESET_STEPS for step in steps)


def _is_driver_housekeeping(query: str) -> bool:
    text = " ".join(query.split())
    return _is_pool_reset(text) or any(marker in text for marker in _INTROSPECTION_MARKERS)


@dataclass
class QueryLog:
    """The statements one counted block sent, in the order asyncpg logged them."""

    statements: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.statements)

    def record(self, logged: LoggedQuery) -> None:
        if not _is_driver_housekeeping(logged.query):
            self.statements.append(logged.query)


class QueryCounter:
    @asynccontextmanager
    async def count(self, pool: asyncpg.Pool) -> AsyncIterator[QueryLog]:
        log = QueryLog()
        await self._each_connection(pool, lambda conn: conn.add_query_logger(log.record))
        # Attaching released the connections through the pool, which may log its
        # own housekeeping; the block's count starts from nothing.
        await asyncio.sleep(0)
        log.statements.clear()
        try:
            yield log
        finally:
            await asyncio.sleep(0)
            await self._each_connection(pool, lambda conn: conn.remove_query_logger(log.record))

    @staticmethod
    async def _each_connection(pool: asyncpg.Pool, action: Callable[[Any], None]) -> None:
        """Run `action` on every connection the pool can hold, all at once."""
        async with AsyncExitStack() as stack:
            held = [
                await stack.enter_async_context(pool.acquire()) for _ in range(pool.get_max_size())
            ]
            for conn in held:
                action(conn)
