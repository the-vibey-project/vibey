# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind the host's hub token and the runtime record.

Mirrors `vibey/infrastructure/hub/local_token.py` (ADR-0016). Interfaces declare; they
never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.infrastructure.hub.local_token import ServingRecord


@runtime_checkable
class LocalTokenStoreInterface(Protocol):
    """The owner-only token file, and where a running hub listens."""

    def token(self) -> str:
        """The token, created 0600 on first call; refuses a file others can read."""
        ...

    def record_serving(self, record: ServingRecord) -> None:
        """Writes where the hub listens."""
        ...

    def clear_serving(self, pid: int | None = None) -> None:
        """Removes the runtime record; with `pid`, only when the record names it."""
        ...

    def serving(self) -> ServingRecord | None:
        """The runtime record, `None` when absent; `ValueError` when malformed."""
        ...
