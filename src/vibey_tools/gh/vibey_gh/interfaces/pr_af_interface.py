# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam between a workflow and Agent-Field `pr-af`'s control plane.

`vibey_gh.pr_af` supplies the client and the command; this declares only what a caller
holds. A verdict with `passed is None` is not a pass and not a failure: it is pr-af saying
nothing, which the gate answers with the fallback reviewer rather than a guess.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class PrAfVerdictInterface(Protocol):
    """What one pr-af execution decided, in the terms the gate reads."""

    @property
    def passed(self) -> bool | None:
        """True with no blocking finding, False with one, None for no verdict at all."""
        ...

    @property
    def findings(self) -> int:
        """The blocking findings the review's own merge gate counted."""
        ...

    @property
    def event(self) -> str:
        """The GitHub review event pr-af chose: `APPROVE`, `COMMENT` or `REQUEST_CHANGES`."""
        ...

    @property
    def reason(self) -> str:
        """Why there is no verdict, or the sentence that accompanies one; never empty."""
        ...

    @property
    def cost_usd(self) -> float:
        """What the review spent, when the result reported it."""
        ...

    @property
    def duration_seconds(self) -> float:
        """How long the review ran, when the result reported it."""
        ...

    @property
    def budget_exhausted(self) -> bool:
        """Whether the review stopped at its cap instead of finishing."""
        ...


@runtime_checkable
class PrAfClientInterface(Protocol):
    """Dispatch one exact-head review and wait for its result."""

    def review(
        self,
        pr_url: str,
        *,
        depth: str,
        dry_run: bool,
        max_cost_usd: float,
        max_duration_seconds: int,
    ) -> PrAfVerdictInterface:
        """Run pr-af against `pr_url`, returning its verdict or the reason there is none."""
        ...
