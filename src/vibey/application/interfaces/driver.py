# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The driver failover's seams (ADR-0070): the worktree, the driver's own append-only
ledger, the processes it starts, and the one service the hook and the probe call.

Mirrors `vibey/application/driver_failover.py` (ADR-0016). Interfaces declare; they
never consume.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from vibey.application.dto import (
    DriverOutcome,
    DriverSignal,
    ProcessResult,
    RepoSnapshot,
    TranscriptDigest,
)
from vibey.domain.failover import FailoverKind, FailoverRecord, FailoverStatus


@runtime_checkable
class DriverWorkspacePort(Protocol):
    """The worktree and Claude Code's transcript, read and written through one seam."""

    def digest(self, path: str) -> TranscriptDigest | None:
        """The file's SHA-256 and line count; None when it cannot be read."""
        ...

    def copy_transcript(self, path: str, cwd: str, name: str) -> str:
        """Copies the transcript under `<cwd>/.vibey/driver/` and returns the copy's path."""
        ...

    def repo(self, cwd: str) -> RepoSnapshot: ...

    def commits_since(self, cwd: str, sha: str) -> tuple[str, ...]: ...

    def write_brief(self, cwd: str, name: str, text: str) -> str:
        """Writes the brief under `<cwd>/.vibey/driver/` and returns its path."""
        ...


@runtime_checkable
class DriverLedgerPort(Protocol):
    """The driver's append-only record: no update, no delete."""

    def records(self) -> tuple[FailoverRecord, ...]: ...

    def append(
        self, kind: FailoverKind, *, at: datetime, payload: Mapping[str, object]
    ) -> None: ...


@runtime_checkable
class ProcessPort(Protocol):
    def spawn(self, argv: Sequence[str], *, cwd: str) -> None:
        """Starts a detached process; never waits for it (never block on a human)."""
        ...

    def run(self, argv: Sequence[str], *, cwd: str, timeout: float) -> ProcessResult:
        """Runs a process to completion; a timeout or a missing binary is a failure."""
        ...


@runtime_checkable
class DriverFailoverServiceInterface(Protocol):
    def fail_over(self, signal: DriverSignal) -> DriverOutcome: ...

    def probe(self, cwd: str) -> DriverOutcome: ...

    def status(self) -> FailoverStatus: ...
