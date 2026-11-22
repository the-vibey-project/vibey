# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind the hub's web tools: what may be fetched, and what a project may say.

Mirrors `vibey/domain/web_tools.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.web_tools import WebOutcome, WebTarget, WebTool, WebToolSettings


@runtime_checkable
class WebToolPolicyInterface(Protocol):
    """Decides, with no I/O, what the hub's search and fetch may reach and record."""

    def target(self, url: str, settings: WebToolSettings) -> WebTarget:
        """`url` read apart as one the hub may fetch, or `WebToolRefused` saying why not."""
        ...

    def follow(self, current: WebTarget, location: str, settings: WebToolSettings) -> WebTarget:
        """A redirect's `location`, read against `current` and checked as a new target; never a
        step from https down to http."""
        ...

    def address_problem(self, address: str) -> str | None:
        """None when `address` is a public one a fetch may connect to, else why not."""
        ...

    def host_problem(self, host: str, settings: WebToolSettings) -> str | None:
        """None when the person's `[web]` host lists let `host` be fetched, else why not."""
        ...

    def budget_wait(self, used: Sequence[float], *, now: float, per_hour: int) -> float | None:
        """None when one more use fits in the rolling hour, else the seconds until it does."""
        ...

    def audit(
        self,
        tool: WebTool,
        *,
        principal: str,
        outcome: WebOutcome,
        backend: str,
        hosts: Sequence[str] | None = None,
        reason: str | None = None,
    ) -> dict[str, object]:
        """The ledger payload for one use: who, which tool, the outcome and the backend, and for
        a fetch the hosts it reached. Never the query, never a URL."""
        ...


@runtime_checkable
class WebToolTrustInterface(Protocol):
    """The person's `[web]` grants; a project's only narrows it."""

    def merge(
        self, user: WebToolSettings, project: WebToolSettings, project_keys: frozenset[str]
    ) -> WebToolSettings:
        """`user`, narrowed by each key the project named (`project_keys`), never widened."""
        ...
