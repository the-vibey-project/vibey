# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam behind publishing: `infrastructure/publish/github.py` (ADR-0016).

Interfaces declare; they never consume.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey.domain.publish import PublishPlan, PublishResult, PublishTarget


@runtime_checkable
class PublisherInterface(Protocol):
    """Gets a finished project's work off the machine: a pull request, or a new repository."""

    async def problem(self) -> str | None:
        """Why publishing cannot be done right now (`gh` missing or not logged in), or None."""
        ...

    async def inspect(self, repo_path: Path, *, branch: str, remote: str) -> PublishTarget:
        """What the checkout looks like: whether `remote` exists, its default branch, whether
        it is empty. Raises `PublishFailed` when `branch` does not exist."""
        ...

    async def publish(self, plan: PublishPlan, *, repo_path: Path) -> PublishResult:
        """Do exactly what `plan` says, never forcing a push. Idempotent: a pull request that
        is already open for the branch is returned, not opened twice. Raises `PublishFailed`."""
        ...
