# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The in-memory config-store seam.

Mirrors `vibey/infrastructure/config_store/in_memory.py` (ADR-0016). Interfaces
declare; they never consume.
"""

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.config_store import ConfigStorePort


@runtime_checkable
class InMemoryConfigStoreInterface(ConfigStorePort, Protocol):
    """The in-memory implementation of the ConfigStore port."""
