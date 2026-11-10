"""A non-reentrant lock that refuses to be taken twice."""

from __future__ import annotations


class Lock:
    def __init__(self) -> None:
        self.held = False
        self.acquisitions = 0

    def acquire(self) -> None:
        if self.held:
            raise RuntimeError("lock already held")
        self.held = True
        self.acquisitions += 1

    def release(self) -> None:
        self.held = False
