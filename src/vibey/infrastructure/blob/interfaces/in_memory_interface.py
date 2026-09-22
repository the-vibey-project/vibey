# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The in-memory blob seam.

Mirrors `vibey/infrastructure/blob/in_memory.py` (ADR-0016). Interfaces
declare; they never consume.
"""

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.blob import BlobPort


@runtime_checkable
class InMemoryBlobInterface(BlobPort, Protocol):
    """The in-memory implementation of the Blob port."""
