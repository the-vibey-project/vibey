# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for the ordered stages a run passes through (ADR-0016).

A run that dies at stage seven wasted stages one through six, so an operation is never
judged by its last stage alone: it is judged by the PATH to it. This seam names the
stages, in order, and cuts that path.

`Stage` is imported for typing only -- frozen data, the same standing `Machine` has in
the memory seam.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey_gh.feasibility import Stage


@runtime_checkable
class PipelineInterface(Protocol):
    """An ordered set of stages, each with its requirement vector."""

    @property
    def names(self) -> tuple[str, ...]:
        """Every stage, in the order a run passes them."""
        ...

    def path(self, operation: str, start: str | None = None) -> tuple[Stage, ...]:
        """The stages from `start` (the first stage when omitted) through `operation`,
        inclusive and in order. An unknown name, or a start after the operation, is a
        `ValueError` naming the stages that do exist."""
        ...
