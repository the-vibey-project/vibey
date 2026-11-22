# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind reading `[web]`.

Mirrors `vibey/infrastructure/web/web_settings_loader.py` (ADR-0016). Interfaces declare; they
never consume.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.web_tools import WebToolSettings


@runtime_checkable
class WebToolSettingsLoaderInterface(Protocol):
    """Reads `[web]` and only `[web]`, every value checked."""

    def load(self, path: Path) -> WebToolSettings:
        """The settings `path` declares; the defaults when it or its table is missing."""
        ...

    def load_trusted(self, user: Path, project: Path) -> WebToolSettings:
        """The person's settings (`user`), narrowed by the project's file, never widened."""
        ...
