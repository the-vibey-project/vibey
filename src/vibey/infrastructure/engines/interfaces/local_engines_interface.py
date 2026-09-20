# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts for resolving the local engines and their one endpoint.

Mirrors `vibey/infrastructure/engines/local_engines.py` (ADR-0016). Interfaces declare;
they never consume.
"""

from typing import Protocol, runtime_checkable

from vibey.application.ports import EngineAdapter
from vibey.domain.config import ClaudeloopLocalConfig
from vibey.domain.engine import EngineDescriptor, EngineId


@runtime_checkable
class LocalEndpointEnvironmentInterface(Protocol):
    """Renders the operator's one local endpoint setting into one engine's own env."""

    def overlay_for(self, engine_id: EngineId) -> dict[str, str]:
        """The variables to layer over `engine_id`'s process environment; empty when the
        engine needs none or the operator already set them."""
        ...


@runtime_checkable
class LocalEngineSettingsInterface(Protocol):
    """Which local engines are switched on for one project, and how each is configured."""

    def enabled(self, engine_id: EngineId) -> bool:
        """The environment switch when it is set at all, else `[features]`."""
        ...

    @property
    def enabled_engines(self) -> tuple[EngineId, ...]: ...

    @property
    def any_enabled(self) -> bool: ...

    @property
    def claudeloop_local(self) -> ClaudeloopLocalConfig:
        """Raises ConfigError for a table that fails validation."""
        ...

    def descriptor(self, engine_id: EngineId) -> EngineDescriptor: ...

    def descriptors(self) -> tuple[EngineDescriptor, ...]: ...

    def adapter(
        self, engine_id: EngineId, endpoint: LocalEndpointEnvironmentInterface
    ) -> EngineAdapter: ...

    def adapters(
        self, endpoint: LocalEndpointEnvironmentInterface
    ) -> dict[EngineId, EngineAdapter]: ...
