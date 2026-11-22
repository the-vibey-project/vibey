# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for finding the person's own configuration folder (ADR-0101, ADR-0102).

Implemented by `infrastructure/user_config_folder.py`. Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path


@runtime_checkable
class UserConfigFolderInterface(Protocol):
    def path(self) -> Path:
        """The person's configuration folder, always absolute; it may not exist yet."""
        ...
