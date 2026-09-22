# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Seams the documentation adapters declare. Interfaces declare; they never consume."""

from vibey.infrastructure.docs.interfaces.bookstack_interface import (
    BookStackDocsAdapterInterface,
)
from vibey.infrastructure.docs.interfaces.in_memory_interface import InMemoryDocsInterface

__all__ = [
    "BookStackDocsAdapterInterface",
    "InMemoryDocsInterface",
]
