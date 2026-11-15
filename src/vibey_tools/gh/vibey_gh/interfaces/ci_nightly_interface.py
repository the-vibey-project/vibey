# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for the nightly full CI run's watermark and its tracking issue (vibey ADR-0016).

`vibey_gh.ci_nightly` supplies the class. The verdict is declared beside the port, as
`BranchHealthVerdict` is, so a test double needs nothing from the implementation.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class NightlyVerdict:
    """What one nightly run's report did: `red`, `green` or `unknown`, why, and the issue."""

    state: str
    reason: str
    issue: int | None = None


@runtime_checkable
class CiNightlyInterface(Protocol):
    """Reads the nightly's watermark and keeps ONE tracking issue open while it is red.

    The watermark is the head commit of the last GREEN scheduled run of the workflow: a
    position in the data, never a timestamp, so a run that shares an instant with another,
    or arrives late, can neither be skipped over nor counted twice. Any doubt answers no
    watermark, and no watermark runs the nightly.
    """

    def last_green(self, workflow: str, branch: str, event: str) -> str:
        """The head commit of the newest successful `event` run of `workflow` on `branch`,
        or "" when there is none the forge vouches for. Raises when the forge cannot be asked."""
        ...

    def report(
        self,
        run_id: int,
        result: str,
        *,
        ignore: Sequence[str] = (),
        labels: Sequence[str] = (),
    ) -> NightlyVerdict:
        """Open or update the branch's nightly issue when `result` is red (a comment once
        per run), close it when `result` is `success`, change nothing otherwise. The failed
        jobs are named except those in `ignore`; `labels` are applied on opening."""
        ...
