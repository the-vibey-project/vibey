# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for the read-only repository-settings drift check (vibey ADR-0016)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from vibey_gh.config import GhConfig


@runtime_checkable
class ProfileDriftInterface(Protocol):
    """Compares the live repository settings with `[repository_profile]`.

    Read-only by construction: it never PATCHes anything. A setting changed by hand is
    reported, not repaired, because the workflow that repairs it overwrites it on the next
    release without saying so. A setting the forge would not show this token is reported as
    not surveyed, never counted as matching.
    """

    def compare(
        self, cfg: GhConfig, live: Mapping[str, Any]
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """`(drift, not_surveyed)` for the declaration against `live`, as `fetch` returns it."""
        ...

    def fetch(self, repository: str) -> dict[str, Any]:
        """The live settings keyed like the declaration; `_unread` names any it could not read."""
        ...

    def survey(self, cfg: GhConfig) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """`(drift, not_surveyed)`: fetch and compare, or say why nothing could be judged."""
        ...
