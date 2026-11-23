# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/infrastructure/acp/folder_case.py` (ADR-0016). Declares only."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class FolderCaseInterface(Protocol):
    """Whether the volume a folder is on folds case."""

    def folds(self, path: str) -> bool:
        """True when `path`'s volume is case-insensitive (`/Work` is `/work` there); False on a
        case-sensitive one, off macOS, or when the volume cannot be asked."""
        ...
