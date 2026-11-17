# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/workflow_lint.py` implements. Interfaces declare; they never consume.

A *tool spec* is data: a name, the command that runs the tool over the workflows, and how to turn
its output into a count of findings. The *lint* runs every spec, compares each count with its
recorded baseline and fails on any difference, in either direction.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol


class ToolSpecInterface(Protocol):
    """One workflow checker."""

    @property
    def name(self) -> str:
        """The key of the tool's entry in the baseline file."""
        ...

    @property
    def argv(self) -> tuple[str, ...]:
        """The command, run from the repository root."""
        ...

    @property
    def count(self) -> Callable[[str], int]:
        """Output text to a number of findings; raises `ValueError` for output it cannot read."""
        ...


class WorkflowLintInterface(Protocol):
    """Runs the tools and applies the ratchet."""

    def run(self) -> int:
        """0 when every tool's count equals its baseline; 1 otherwise."""
        ...
