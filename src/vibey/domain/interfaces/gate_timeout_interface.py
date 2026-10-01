# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind gate timeouts.

Mirrors `vibey/domain/gate_timeout.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import timedelta


@runtime_checkable
class GateTimeoutPolicyInterface(Protocol):
    """The gate kinds a project lets resolve to their default, and each one's wait."""

    def wait_for(self, kind: str) -> timedelta | None:
        """How long a gate of this kind waits before resolving, or None when it never does."""
        ...

    def resolution(
        self, *, kind: str, default_answer: str | None, waited_seconds: float
    ) -> dict[str, str] | None:
        """The answer a gate resolves to now, or None while it must still wait for a person."""
        ...
