# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Hearing the ledger grow: `LISTEN vibey_ledger_appended`, fanned out per project.

Migration 0019 has every ledger append `NOTIFY vibey_ledger_appended` with the project and
the new seq, delivered when the appending transaction commits. One connection listens for
the whole hub; each live feed subscribes to one project and is woken when that project's
ledger grows.

A wake-up carries no event and no promise. The feed reads every event after the last seq
it delivered (sub-doctrine 10.g), so a wake-up that is dropped -- a subscriber already has
one pending, the listener was reconnecting -- delays an event, never loses one. That is why
each subscriber's queue holds a single pending wake-up and further ones are discarded.
"""

import asyncio
import json
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from typing import Any, Final
from uuid import UUID

import asyncpg

CHANNEL: Final = "vibey_ledger_appended"


class LedgerAnnouncements:
    """One LISTEN connection, and a wake-up queue per subscribed feed.

    Declared by `interfaces/live_interface.py::LedgerAnnouncementsInterface`."""

    def __init__(self, connect: Callable[[], Awaitable[Any]]) -> None:
        self._connect = connect
        self._conn: Any = None
        self._subscribers: dict[UUID, set[asyncio.Queue[int]]] = {}

    async def start(self) -> None:
        self._conn = await self._connect()
        await self._conn.add_listener(CHANNEL, self._heard)

    async def stop(self) -> None:
        if self._conn is None:
            return
        conn, self._conn = self._conn, None
        await conn.remove_listener(CHANNEL, self._heard)
        await conn.close()

    @contextmanager
    def subscribe(self, project_id: UUID) -> Iterator[asyncio.Queue[int]]:
        """A queue woken with the new seq whenever `project_id`'s ledger grows."""
        queue: asyncio.Queue[int] = asyncio.Queue(maxsize=1)
        self._subscribers.setdefault(project_id, set()).add(queue)
        try:
            yield queue
        finally:
            listeners = self._subscribers[project_id]
            listeners.discard(queue)
            if not listeners:
                del self._subscribers[project_id]

    def _heard(self, _conn: asyncpg.Connection, _pid: int, _channel: str, payload: str) -> None:
        try:
            announced = json.loads(payload)
            project_id, seq = UUID(str(announced["project_id"])), int(announced["seq"])
        except (ValueError, KeyError, TypeError):
            # Not an announcement this hub wrote; nothing a feed can resume from.
            return
        for queue in self._subscribers.get(project_id, ()):
            if not queue.full():
                queue.put_nowait(seq)
