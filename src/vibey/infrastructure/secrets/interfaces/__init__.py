# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Seams the secrets adapters declare. Interfaces declare; they never consume."""

from vibey.infrastructure.secrets.interfaces.bitwarden_interface import (
    BitwardenSecretsAdapterInterface,
)
from vibey.infrastructure.secrets.interfaces.in_memory_interface import (
    InMemorySecretsInterface,
)

__all__ = [
    "BitwardenSecretsAdapterInterface",
    "InMemorySecretsInterface",
]
