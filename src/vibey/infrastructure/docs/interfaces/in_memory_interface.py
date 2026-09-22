# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The in-memory documentation seam.

Mirrors `vibey/infrastructure/docs/in_memory.py` (ADR-0016). Interfaces declare;
they never consume.
"""

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.docs import DocsPort


@runtime_checkable
class InMemoryDocsInterface(DocsPort, Protocol):
    """The in-memory implementation of the Documentation port."""
