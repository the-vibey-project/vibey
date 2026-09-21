# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Async SQLModel session access for vibey's PostgreSQL schema.

This adapter is deliberately separate from the existing asyncpg repositories:
the queue and append-only ledger keep driver-level SQL where their locking and
transaction contracts are explicit. New read/write adapters can use this
session factory and the Pydantic-backed models in :mod:`orm_models`.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from vibey.infrastructure.db.interfaces import PostgresOrmInterface


def _asyncpg_url(dsn: str) -> str:
    """Normalize PostgreSQL URLs for SQLAlchemy's asyncpg dialect."""
    if dsn.startswith("postgres://"):
        return "postgresql+asyncpg://" + dsn.removeprefix("postgres://")
    if dsn.startswith("postgresql://"):
        return "postgresql+asyncpg://" + dsn.removeprefix("postgresql://")
    return dsn


class PostgresOrm(PostgresOrmInterface):
    """Own an async SQLAlchemy session factory for the mapped schema.

    ``PostgresOrm`` does not run migrations or call ``SQLModel.metadata.create_all``.
    ``build_app`` remains the only composition path for the checked, forward-only
    migration runner; this object is an additional typed persistence seam.
    """

    def __init__(self, dsn: str, *, echo: bool = False) -> None:
        self._engine = create_async_engine(_asyncpg_url(dsn), echo=echo)
        self._sessions = async_sessionmaker(self._engine, expire_on_commit=False)

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._sessions() as session:
            yield session

    async def dispose(self) -> None:
        await self._engine.dispose()


__all__ = ["PostgresOrm"]
