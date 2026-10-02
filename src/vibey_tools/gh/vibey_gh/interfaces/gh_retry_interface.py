# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for asking the forge again after it said "not now" (vibey ADR-0016)."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from typing import Protocol, runtime_checkable

from vibey_gh.config import ForgeRetryConfig


@runtime_checkable
class GhRetryInterface(Protocol):
    """Repeats a `gh` call whose failure was transient, and only that.

    A failure is transient when `[forge_retry]` says so: a 5xx status it lists, a message it
    lists (GraphQL's "Something went wrong"), or a secondary rate limit that carries
    `Retry-After`. Anything else is handed back untouched, so a caller raises exactly what
    it raised before; and when every attempt was transient, the last answer is handed back
    saying how many attempts it took. Success is never reported for an answer that was not
    seen (sub-doctrine 12.e).
    """

    @property
    def policy(self) -> ForgeRetryConfig: ...

    def wait(
        self, result: subprocess.CompletedProcess[str], attempt: int
    ) -> tuple[float, str] | None:
        """(seconds to wait, why) before asking again after `result`, the answer to
        attempt number `attempt` (from 1), or `None` when `result` is not a transient
        failure -- a success included."""
        ...

    def run(
        self, call: Callable[[], subprocess.CompletedProcess[str]], label: str
    ) -> subprocess.CompletedProcess[str]:
        """`call()`'s answer, after up to `policy.retries` further attempts while it is a
        transient failure. Each retry is announced, naming `label`."""
        ...
