# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Domain-level error hierarchy. Pure — carries no I/O state."""

from __future__ import annotations


class AutoclaudeError(Exception):
    """Base class for every error raised by claudeloop's own logic."""


class InvalidPlanError(AutoclaudeError):
    """Raised when a work plan file cannot be parsed into work items."""


class InvalidSessionSelectorError(AutoclaudeError):
    """Raised when a session selector is malformed or ambiguous."""


class BudgetExceededError(AutoclaudeError):
    """Raised when a run exceeds its configured turn, dollar, or wall-clock budget."""


class AuthenticationFailedError(AutoclaudeError):
    """Raised when the agent gateway reports a terminal authentication failure.

    Never retryable — the run loop must abort rather than wait.
    """


class BackendProfileError(AutoclaudeError, ValueError):
    """Raised when a ``[profiles.<name>]`` backend profile is invalid or cannot be
    used as asked (unknown name, missing model tier, a ``claude-*`` id sent to a
    local backend, a tool the backend cannot serve).

    A ``ValueError`` as well, so every CLI path that already turns a bad value
    into a usage error (exit 2) handles it without a new except clause.
    """


class CapabilitySnapshotRefused(AutoclaudeError):
    """Raised when the run's capability document (``--capabilities PATH``) is refused or
    cannot be read. The run never starts without it: ``claudeloop run`` exits 78, and the
    conductor's ``engine_misconfigured`` gate parks the job (SP-LOOPS Phase 4, R9).

    Deliberately not a ``ValueError``: a refused snapshot is a configuration failure, not a
    usage error, and must not fall into the exit-2 path. ``reason`` names the document's path
    and nothing the document holds. Declared by
    ``interfaces/class_contracts.py::CapabilitySnapshotRefusedInterface``."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class CapabilityFlagConflict(AutoclaudeError, ValueError):
    """Raised when one of claudeloop's own flags clashes with the run's capability snapshot:
    a ``--connector`` named like a snapshot MCP server, or ``--web-search`` while the snapshot
    switches the built-in web tools off (SP-LOOPS Phase 4, R12). A refusal, never a silent
    override; a ``ValueError`` as well, so it is a usage error (exit 2)."""
