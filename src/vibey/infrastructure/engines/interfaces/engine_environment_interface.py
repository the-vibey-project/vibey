# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for what an engine session may see of the worker's environment.

Mirrors `vibey/infrastructure/engines/engine_environment.py` (ADR-0016). Interfaces
declare; they never consume.
"""

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from vibey.application.interfaces import EngineAdapter
from vibey.domain.engine import EngineDescriptor
from vibey.infrastructure.process.interfaces import (
    ChildEnvironmentInterface,
    EnvironmentAllowListInterface,
    OrchestratorPythonEnvInterface,
)


@runtime_checkable
class EngineEnvironmentPolicyInterface(Protocol):
    """The engine-session allow-list: the system basics, the engine's own declared
    variables and credential, and what the project's config record adds."""

    def allow_list(self, descriptor: EngineDescriptor) -> EnvironmentAllowListInterface:
        """Exactly what a `descriptor` session may receive."""
        ...

    def environment(
        self,
        descriptor: EngineDescriptor,
        *,
        overlay: Mapping[str, str] | None = None,
        python_env: OrchestratorPythonEnvInterface | None = None,
        source: Mapping[str, str] | None = None,
    ) -> ChildEnvironmentInterface:
        """The builder every spawn of a `descriptor` session goes through."""
        ...

    def applied_to(self, adapter: EngineAdapter) -> EngineAdapter:
        """`adapter` running under this policy when it spawns loop processes; any other
        adapter unchanged."""
        ...
