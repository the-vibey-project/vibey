# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for reading a stored closed vocabulary forward-compatibly.

Mirrors `vibey/domain/stored_value.py` (ADR-0016). Interfaces declare; they never
consume. The seam is generic over the member type and the unrecognized type, so one
declaration serves `EngineId`, `Phase`, `Provenance`, `JobState` and `CircuitState`
alike (vibey#287).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class UnrecognizedValueInterface(Protocol):
    """A stored value this vibey has no member for."""

    @property
    def value(self) -> str:
        """The value exactly as stored."""
        ...


@runtime_checkable
class StoredValueParserInterface[M, U](Protocol):
    """Reads the stored text of one closed vocabulary."""

    def parse(self, raw: str) -> M | U:
        """The member, or the unrecognized text preserved. Never raises."""
        ...

    def known(self, raw: str) -> M | None:
        """The member, or None for a value this vibey does not know."""
        ...
