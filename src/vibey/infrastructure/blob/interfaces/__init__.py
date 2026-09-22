# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Seams the blob adapters declare. Interfaces declare; they never consume."""

from vibey.infrastructure.blob.interfaces.garage_interface import GarageBlobAdapterInterface
from vibey.infrastructure.blob.interfaces.in_memory_interface import InMemoryBlobInterface

__all__ = [
    "GarageBlobAdapterInterface",
    "InMemoryBlobInterface",
]
