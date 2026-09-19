# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for where qwenloop's settings come from and in what order they win."""

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, runtime_checkable

from qwenloop.domain.config import QwenConfig


@runtime_checkable
class SettingsLoaderInterface(Protocol):
    """Layers a config file, then the environment, then flags; the last one set wins."""

    @property
    def path(self) -> Path:
        """The config file this loader reads (it may not exist)."""
        ...

    @property
    def api_key(self) -> str:
        """The endpoint's API key, from the environment only; empty when unset."""
        ...

    def load(self, overrides: Mapping[str, object | None] | None = None) -> QwenConfig:
        """The validated configuration. A None override means the flag was not given."""
        ...
