# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Seams the file adapters declare. Interfaces declare; they never consume."""

from vibey.infrastructure.files.interfaces.in_memory_interface import InMemoryFilesInterface
from vibey.infrastructure.files.interfaces.nextcloud_interface import (
    NextcloudFilesAdapterInterface,
)

__all__ = [
    "InMemoryFilesInterface",
    "NextcloudFilesAdapterInterface",
]
