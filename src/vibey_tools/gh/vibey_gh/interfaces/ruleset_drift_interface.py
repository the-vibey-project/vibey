# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for the read-only ruleset drift check (vibey ADR-0016)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

from vibey_gh.config import GhConfig


@runtime_checkable
class RulesetDriftInterface(Protocol):
    """Compares every live repository ruleset with what `.vibey-gh.toml` renders.

    Read-only by construction: it never creates, updates or deletes a ruleset. Drift is
    everything the declaration does not account for -- a declared ruleset that is missing
    or differs, a rule nobody declared inside one, and any repository ruleset that is not
    declared at all, with its bypass actors named.
    """

    def compare(self, cfg: GhConfig, live: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
        """Every drift between the declaration and `live`, the fully fetched rulesets.
        Empty means they agree."""
        ...

    def fetch(self) -> list[dict[str, Any]]:
        """Every repository-level ruleset, each fetched in full by its id."""
        ...
