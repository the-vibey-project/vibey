# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""In-memory Cache implementation of the Cache port (ADR-0042)."""

from __future__ import annotations

import time

from vibey.application.interfaces.cache import CachePort


class InMemoryCache(CachePort):
    """Faked cache for testing and unconfigured local runs."""

    def __init__(self) -> None:
        self._values: dict[str, str] = {}
        self._expires_at: dict[str, float] = {}

    async def get(self, key: str) -> str | None:
        if key in self._expires_at and time.monotonic() >= self._expires_at[key]:
            del self._values[key]
            del self._expires_at[key]
            return None
        return self._values.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        self._values[key] = value
        if ttl_seconds is None:
            self._expires_at.pop(key, None)
        else:
            self._expires_at[key] = time.monotonic() + ttl_seconds

    async def delete(self, key: str) -> None:
        self._values.pop(key, None)
        self._expires_at.pop(key, None)
