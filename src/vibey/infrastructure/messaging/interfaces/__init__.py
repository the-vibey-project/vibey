# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Seams the messaging adapters declare. Interfaces declare; they never consume."""

from vibey.infrastructure.messaging.interfaces.in_memory_interface import (
    InMemoryMessagingInterface,
)
from vibey.infrastructure.messaging.interfaces.matrix_interface import (
    MatrixMessagingAdapterInterface,
)

__all__ = [
    "InMemoryMessagingInterface",
    "MatrixMessagingAdapterInterface",
]
