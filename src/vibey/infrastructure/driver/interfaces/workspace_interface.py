# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/infrastructure/driver/workspace.py` (ADR-0016). Declares only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.application.dto import RepoSnapshot, TranscriptDigest


@runtime_checkable
class LocalDriverWorkspaceInterface(Protocol):
    def digest(self, path: str) -> TranscriptDigest | None: ...

    def copy_transcript(self, path: str, cwd: str, name: str) -> str: ...

    def repo(self, cwd: str) -> RepoSnapshot: ...

    def commits_since(self, cwd: str, sha: str) -> tuple[str, ...]: ...

    def write_brief(self, cwd: str, name: str, text: str) -> str: ...
