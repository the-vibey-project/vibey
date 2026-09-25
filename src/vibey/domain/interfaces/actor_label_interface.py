# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind naming who made a person-made record.

Mirrors `vibey/domain/actor_label.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ActorLabelPolicyInterface(Protocol):
    """Checks a label a caller named itself by, or falls back to the account."""

    def resolve(self, label: str | None, *, account: str) -> str:
        """`label`, stripped, when given and recordable; else `account`. Raises the
        policy's error for an empty, over-long or control-bearing label."""
        ...
