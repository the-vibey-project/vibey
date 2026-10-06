# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind `vibey/infrastructure/state/state_key.py` (ADR-0016, ADR-0086).
Interfaces declare; they never consume."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class StateKeyStoreInterface(Protocol):
    """Where this machine keeps the state key."""

    def where(self) -> str:
        """Where the key in use is found, or "" when there is none."""
        ...

    def text(self) -> str:
        """The key's text form; raises when there is none."""
        ...

    def load(self) -> bytes:
        """The key; raises when there is none."""
        ...

    def create(self) -> str:
        """Make and keep a key, refusing while one exists; where it was kept."""
        ...
