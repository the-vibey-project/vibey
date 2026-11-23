# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The run input store, composed when it is first needed (SP-LOOPS Phase 3c, fix round 1: review
I4).

A worker is composed once, for every phase and project. Reading `[inputs]` -- and, for a SeaweedFS
store, its credentials -- at that moment let one refused table, or two environment variables a
systemd or launchd session does not carry, stop the worker for every project, inputs or not. So
the store is composed on its first use, from a BUILD run that has inputs to give (the run inputs
service reads the ledger first and touches no store when nothing was added), and kept. A
composition that fails raises from that use, so only that run fails; the next use tries again.
Store calls run on worker threads, so the first composition is guarded by a lock.

Declared by `interfaces/lazy_input_store_interface.py::LazyInputStoreInterface`.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from uuid import UUID

from vibey.application.interfaces.input_store_interface import InputStoreInterface
from vibey.domain.run_input import InputKind, InputListing, RunInput


class LazyInputStore:
    """Declared by `interfaces/lazy_input_store_interface.py::LazyInputStoreInterface`."""

    def __init__(self, compose: Callable[[], InputStoreInterface]) -> None:
        self._compose = compose
        self._store: InputStoreInterface | None = None
        self._lock = threading.Lock()

    def _inner(self) -> InputStoreInterface:
        with self._lock:
            if self._store is None:
                self._store = self._compose()
            return self._store

    def put(self, project_id: UUID, kind: InputKind, name: str, data: bytes) -> RunInput:
        return self._inner().put(project_id, kind, name, data)

    def restore(self, project_id: UUID, data: bytes) -> str:
        return self._inner().restore(project_id, data)

    def get(self, project_id: UUID, digest: str, *, size: int) -> bytes:
        return self._inner().get(project_id, digest, size=size)

    def listed(self, project_id: UUID) -> InputListing:
        return self._inner().listed(project_id)

    def describe(self) -> str:
        return self._inner().describe()
