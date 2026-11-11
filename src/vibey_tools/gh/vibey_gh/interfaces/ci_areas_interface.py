# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for turning a diff into changed CI areas, a tier and matrices (vibey ADR-0016).

`vibey_gh.ci_areas` supplies every class declared here. The decision is the noun the
workflow's `plan` job publishes; it is declared beside the port, as `CommitMessage` is, so
a reader of a job output or a test double needs nothing from the implementation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class AreaDecision:
    """What a change touches and whether the whole matrix must run.

    `areas` are the declared areas any changed path belongs to. `full` is True whenever there
    is ANY doubt -- an unmapped path, an always-full path, an empty diff, an event the
    declaration does not recognise -- and `reasons` names each, for a person to read.
    `owners` are the matrix-row owners (a package directory) the changed paths selected; an
    empty set means no narrowing is known and every row of the tier is selected.
    """

    areas: frozenset[str]
    full: bool
    reasons: tuple[str, ...]
    owners: frozenset[str] = frozenset()


@runtime_checkable
class CiAreasInterface(Protocol):
    """Decides, from declared maps only, which CI work a change can affect.

    A skipped required check counts as passing on GitHub, so every method fails SAFE: where it
    cannot tell, the answer is the full tier, never a skip.
    """

    def gate(self, event: str, base_ref: str) -> tuple[str, ...]:
        """Why this event runs the full tier whatever the diff says; empty when the diff decides."""
        ...

    def classify(self, paths: Sequence[str], *, event: str, base_ref: str) -> AreaDecision:
        """The areas, tier and owners of `paths` (repository-relative, `/`-separated)."""
        ...

    def unmapped(self, paths: Sequence[str]) -> list[str]:
        """The paths no area claims and the always-full list does not cover (a config defect)."""
        ...

    def full_decision(self, *reasons: str) -> AreaDecision:
        """The all-full decision: every declared area, `full`, with the reasons given."""
        ...

    def rows(self, job: str, tier: str) -> list[dict[str, Any]]:
        """Every row `job` declares at `tier` (`full` or `pr`); an unknown job or tier raises."""
        ...

    def matrix(self, job: str, decision: AreaDecision) -> Mapping[str, Any]:
        """The `strategy.matrix` for `job`: `{"include": rows}`, empty when no row must run."""
        ...

    def outputs(self, decision: AreaDecision) -> dict[str, str]:
        """The `$GITHUB_OUTPUT` pairs for `decision`, in the order they are printed."""
        ...
