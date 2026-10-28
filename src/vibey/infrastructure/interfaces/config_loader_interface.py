# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for choosing the configuration a process starts from."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.config import VibeyConfig


@runtime_checkable
class StartupConfigResolverInterface(Protocol):
    """Picks the configuration a process starts from: its vibey.toml, else its environment."""

    @property
    def skipped_file(self) -> bool:
        """True when the last `resolve` found a `vibey.toml` it could not use."""
        ...

    def resolve(self, cwd: Path) -> VibeyConfig | None:
        """The configuration for a process started in `cwd`, or None when none can be read."""
        ...
