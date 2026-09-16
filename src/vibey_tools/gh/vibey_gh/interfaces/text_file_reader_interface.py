# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for reading a small text file the machine describes itself with (ADR-0016).

Kernel interfaces such as `/proc/meminfo` and the cgroup limit files are read, not
executed, and a test must be able to hand a sampler exact file contents without
monkey-patching module attributes — sub-doctrine 9.b exists to end that habit.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TextFileReaderInterface(Protocol):
    """Reads one text file in full, or reports that it could not be read."""

    def read(self, path: str) -> str | None:
        """The file's whole text, or `None` when this machine has no such file."""
        ...
