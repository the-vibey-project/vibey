# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for finding the person's own state folder (SP-LOOPS Phase 3, fix round 1: R-A).

Implemented by `infrastructure/user_state_folder.py`. Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path


@runtime_checkable
class UserStateFolderInterface(Protocol):
    def path(self) -> Path:
        """The person's state folder, always absolute; it may not exist yet."""
        ...

    def inputs(self) -> Path:
        """Where every project's run inputs are stored, one folder per project id: in the
        person's state, never inside a checkout a cloned repository controls."""
        ...
