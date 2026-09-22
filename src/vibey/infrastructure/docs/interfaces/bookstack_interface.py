# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The BookStack documentation seam.

Mirrors `vibey/infrastructure/docs/bookstack.py` (ADR-0016). Interfaces declare;
they never consume.
"""

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.docs import DocsPort


@runtime_checkable
class BookStackDocsAdapterInterface(DocsPort, Protocol):
    """The self-hosted BookStack implementation of the Documentation port."""
