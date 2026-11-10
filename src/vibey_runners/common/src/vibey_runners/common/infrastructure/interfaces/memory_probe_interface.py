# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for the family's physical-memory reading (ADR-0016, #383)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class MemoryProbeInterface(Protocol):
    """How much physical memory this machine has."""

    def total_bytes(self) -> int | None:
        """This machine's physical memory in bytes, or None when it will not say."""
        ...
