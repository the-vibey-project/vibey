# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The in-memory file storage seam.

Mirrors `vibey/infrastructure/files/in_memory.py` (ADR-0016). Interfaces declare;
they never consume.
"""

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.files import FilesPort


@runtime_checkable
class InMemoryFilesInterface(FilesPort, Protocol):
    """The in-memory implementation of the Files port."""
