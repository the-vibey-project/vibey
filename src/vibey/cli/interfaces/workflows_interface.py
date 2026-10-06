# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind `vibey -w` / `vibey --workflows`.

Mirrors `vibey/cli/workflows.py` (ADR-0016, ADR-0085). Interfaces declare; they never consume.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class WorkflowsCommandInterface(Protocol):
    """Runs a vibey command line on the repository's GitHub-hosted runners."""

    def run(self, argv: Sequence[str]) -> int:
        """Prints what the command printed there and returns its exit code: 2 for a command
        line that cannot be sent, 1 when GitHub refused or the run handed nothing back, 124
        when the wait ran out before the run finished."""
        ...
