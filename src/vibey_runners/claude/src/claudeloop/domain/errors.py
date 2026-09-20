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
