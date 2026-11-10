"""A tiny memoizing wrapper that counts its hits and misses."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class Memo:
    def __init__(self, func: Callable[..., Any]) -> None:
        self._func = func
        self._cache: dict[Any, Any] = {}
        self.hits = 0
        self.misses = 0

    def _key(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
        return (args, tuple(sorted(kwargs.items())))

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        key = self._key(args, kwargs)
        if key in self._cache:
            self.hits += 1
            return self._cache[key]
        self.misses += 1
        value = self._func(*args, **kwargs)
        self._cache[key] = value
        return value

    def clear(self) -> None:
        self._cache.clear()
        self.hits = 0
        self.misses = 0
