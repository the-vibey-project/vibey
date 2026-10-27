# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for naming what failed in a red CI job (vibey ADR-0016)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class StepFailure:
    """A step the forge reports as failed. `number` is 0 when the forge did not report one."""

    name: str
    number: int


@dataclass(frozen=True)
class FailingTest:
    """The first failing test id a job log names. `line` is None when it cannot be placed."""

    test_id: str
    line: int | None = None


@dataclass(frozen=True)
class Reproduction:
    """A declared command that reproduces a failure, or the reason there is none.

    A missing command is an answer, never a guess: `command` is None and `reason` says why.
    """

    command: str | None
    reason: str


@runtime_checkable
class FailureEvidenceInterface(Protocol):
    """Reads the evidence a red job carries: its failed step, test and reproduction."""

    def failed_steps(self, job: Mapping[str, Any]) -> tuple[StepFailure, ...]:
        """The job's failed steps, in order; empty when the forge reported no steps."""
        ...

    def first_failing_test(
        self, log: str, pattern: str, truncated: bool = False
    ) -> FailingTest | None:
        """The first line of `log` matching `pattern`, or None; no line number if truncated."""
        ...

    def first_error_line(self, log: str, truncated: bool = False) -> int | None:
        """The 1-based line of the first `##[error]` annotation, or None."""
        ...

    def reproduction(
        self,
        check: str,
        step: str | None,
        test_id: str | None,
        mapping: Sequence[tuple[str, str]],
    ) -> Reproduction:
        """The declared command for `check :: step`, else for `check`, with `{test}` filled."""
        ...
