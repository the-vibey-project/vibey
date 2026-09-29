# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for one idempotent tracking issue per condition (vibey ADR-0016)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class TrackingIssueInterface(Protocol):
    """Opens, updates and closes the ONE issue that tracks a named condition.

    The issue is found by a marker in its body, never by its title or by search: a title
    is edited by people and a search index lags, and either would open a second issue for
    the same condition. Every method is safe to replay -- a workflow re-run, or two runs
    racing, converge on the same single issue.
    """

    def find(self, key: str) -> int | None:
        """The open issue tracking `key`, or `None` when there is none."""
        ...

    def raise_issue(
        self,
        key: str,
        title: str,
        body: str,
        *,
        event: str = "",
        event_key: str = "",
        labels: Sequence[str] = (),
    ) -> tuple[int, bool]:
        """Open the issue for `key`, or bring the open one's title and body up to date;
        (its number, whether it was created). `event` is added as a comment once per
        `event_key`, so a replayed run never repeats itself."""
        ...

    def resolve(self, key: str, comment: str) -> int | None:
        """Comment on and close the open issue for `key`; its number, or `None` when there
        was nothing open to close."""
        ...
