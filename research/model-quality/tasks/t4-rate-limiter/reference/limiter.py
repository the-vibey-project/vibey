"""A sliding-window rate limiter. Timestamps are plain numbers (seconds) supplied by the caller."""

from __future__ import annotations


class RateLimiter:
    """Independent limiter state: its own limit, window and per-key hits."""

    def __init__(self, limit: int = 3, window: float = 60.0) -> None:
        self._hits: dict[str, list[float]] = {}
        self._limit = 3
        self._window = 60.0
        self.configure(limit, window)

    def configure(self, limit: int, window: float) -> None:
        """Change the limit and window. Hits already recorded are kept."""
        if limit < 1 or window <= 0:
            raise ValueError("limit must be >= 1 and window must be > 0")
        self._limit = limit
        self._window = float(window)

    def _live(self, key: str, now: float) -> list[float]:
        kept = [t for t in self._hits.get(key, []) if now - t < self._window]
        if kept:
            self._hits[key] = kept
        else:
            self._hits.pop(key, None)
        return kept

    def allow(self, key: str, now: float) -> bool:
        """Record a hit and return True if key is still within its limit, else return False."""
        live = self._live(key, now)
        if len(live) >= self._limit:
            return False
        live.append(now)
        self._hits[key] = live
        return True

    def remaining(self, key: str, now: float) -> int:
        """How many more hits key may make right now."""
        return max(self._limit - len(self._live(key, now)), 0)

    def reset(self, key: str | None = None) -> None:
        """Forget the hits of one key, or of every key when key is None."""
        if key is None:
            self._hits.clear()
        else:
            self._hits.pop(key, None)


DEFAULT_LIMITER = RateLimiter()


def configure(limit: int, window: float) -> None:
    DEFAULT_LIMITER.configure(limit, window)


def allow(key: str, now: float) -> bool:
    return DEFAULT_LIMITER.allow(key, now)


def remaining(key: str, now: float) -> int:
    return DEFAULT_LIMITER.remaining(key, now)


def reset(key: str | None = None) -> None:
    DEFAULT_LIMITER.reset(key)
