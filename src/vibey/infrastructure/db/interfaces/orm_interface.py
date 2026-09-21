# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for the SQLModel/SQLAlchemy session factory."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


@runtime_checkable
class PostgresOrmInterface(Protocol):
    """Provides typed async sessions without owning schema migration."""

    @property
    def engine(self) -> AsyncEngine:
        """The SQLAlchemy engine used by this session factory."""
        ...

    def session(self) -> AbstractAsyncContextManager[AsyncSession]:
        """Open one session; callers own transaction boundaries and commits."""
        ...

    async def dispose(self) -> None:
        """Release the engine's connections."""
        ...
