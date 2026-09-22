# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Cache port seam (ADR-0042)."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class CachePort(Protocol):
    """Common protocol for FOSS cache backends (sovereign default: Redis)."""

    async def get(self, key: str) -> str | None:
        """Return the cached value, or None when absent or expired."""
        ...

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        """Store a value; with a TTL it must expire without a delete call."""
        ...

    async def delete(self, key: str) -> None:
        """Remove a key; deleting an absent key is not an error."""
        ...
