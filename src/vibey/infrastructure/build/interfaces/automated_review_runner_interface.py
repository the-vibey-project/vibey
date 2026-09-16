# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for building REVIEW's automated checks from project config.

The *runtime* seam -- run_automated_reviews -- is already declared as the
``AutomatedReviewRunner`` port in ``application/interfaces/review.py``, because
``ReviewDemoHandler`` consumes it across the layer boundary. What was not
declared anywhere is the *construction* seam: ``bootstrap.build_full_worker``
builds the runner from the project's stored config record, and that contract
(what config shape is read, what it may raise) belongs in a diff (ADR-0016).
Both members are restated here so the declaration stands on its own.
"""

from collections.abc import Mapping
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.build_verify_handler import GateRunner
from vibey.application.interfaces import AutomatedFinding, ProjectStore


@runtime_checkable
class ConfigurableAutomatedReviewRunnerInterface(Protocol):
    @classmethod
    def from_config(
        cls,
        config: Mapping[str, object],
        *,
        projects: ProjectStore | object,
        gates: GateRunner,
    ) -> "ConfigurableAutomatedReviewRunnerInterface": ...

    async def run_automated_reviews(
        self, project_id: UUID, cycle: int
    ) -> tuple[AutomatedFinding, ...]: ...
