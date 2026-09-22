# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Seams the secrets adapters declare. Interfaces declare; they never consume."""

from vibey.infrastructure.secrets.interfaces.in_memory_interface import (
    InMemorySecretsInterface,
)
from vibey.infrastructure.secrets.interfaces.openbao_interface import (
    OpenBaoSecretsAdapterInterface,
)

__all__ = [
    "InMemorySecretsInterface",
    "OpenBaoSecretsAdapterInterface",
]
