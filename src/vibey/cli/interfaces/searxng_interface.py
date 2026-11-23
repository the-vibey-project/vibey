# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for `vibey searxng` (ADR-0102). Declares only."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SearxngCommandInterface(Protocol):
    def serve(self, unit: str | None = None) -> int:
        """What the unit runs: exec the container runtime, or the exit code of a refusal.
        `unit` is the label the unit was loaded under, when the unit says it."""
        ...

    def status(self) -> int:
        """Print what is here; 0."""
        ...

    def install(self, *, yes: bool) -> int:
        """Ask, then pull, write, load and wait; 0 once it answers as vibey's own, else 1."""
        ...

    def uninstall(self, *, purge: bool) -> int:
        """Unload and remove the unit (only as vibey wrote it) and the container; with `purge`
        the image, settings and record too. Idempotent; 1 when something failed."""
        ...

    def doctor_line(self) -> str:
        """`vibey doctor`'s `searxng` line, in its `MARK name detail` grammar. Never raises."""
        ...
