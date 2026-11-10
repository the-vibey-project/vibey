"""A sliding-window rate limiter. Timestamps are plain numbers (seconds) supplied by the caller."""

from __future__ import annotations

_limit = 3
_window = 60.0
_hits: dict[str, list[float]] = {}


def configure(limit: int, window: float) -> None:
    """Change the limit and window. Hits already recorded are kept."""
    global _limit, _window
    if limit < 1 or window <= 0:
        raise ValueError("limit must be >= 1 and window must be > 0")
    _limit = limit
    _window = float(window)


def _live(key: str, now: float) -> list[float]:
    """Drop expired hits for key and return the live ones. A hit is live while now - hit < window."""
    kept = [t for t in _hits.get(key, []) if now - t < _window]
    if kept:
        _hits[key] = kept
    else:
        _hits.pop(key, None)
    return kept


def allow(key: str, now: float) -> bool:
    """Record a hit and return True if key is still within its limit, else return False."""
    live = _live(key, now)
    if len(live) >= _limit:
        return False
    live.append(now)
    _hits[key] = live
    return True


def remaining(key: str, now: float) -> int:
    """How many more hits key may make right now."""
    return max(_limit - len(_live(key, now)), 0)


def reset(key: str | None = None) -> None:
    """Forget the hits of one key, or of every key when key is None."""
    if key is None:
        _hits.clear()
    else:
        _hits.pop(key, None)
