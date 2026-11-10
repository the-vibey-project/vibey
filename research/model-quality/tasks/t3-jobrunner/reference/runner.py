"""Run a batch of items under a lock."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from lock import Lock


def process(batch: list[Any], lock: Lock, handler: Callable[[Any], None]) -> int:
    """Handle items in order until a None item; return how many were handled."""
    lock.acquire()
    try:
        handled = 0
        for item in batch:
            if item is None:
                return handled
            handler(item)
            handled += 1
        return handled
    finally:
        lock.release()
