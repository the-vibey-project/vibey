# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind `vibey retry`.

Mirrors `vibey/cli/retry.py` (ADR-0016). Interfaces declare; they never consume. The types the
seam is declared over are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path
    from uuid import UUID


@runtime_checkable
class RetryCommandInterface(Protocol):
    """Gets a stalled project moving again: workers stopped, exhausted gates granted, a worker
    started."""

    async def run(
        self,
        project_id: UUID,
        *,
        max_attempts: int,
        keep_workers: bool,
        start_worker: bool,
        worker_args: Sequence[str],
        log: Path | None,
        grace_seconds: float,
        dry_run: bool,
    ) -> None:
        """Raises typer.Exit(1) for an unknown project or a worker that would not stop."""
        ...
