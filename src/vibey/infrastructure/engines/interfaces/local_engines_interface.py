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

    def model_for(self, engine_id: EngineId) -> str | None:
        """The model `engine_id` runs when it reaches the engine by a path vibey knows:
        a local runner's own model variable (`GPTOSSLOOP_MODEL`, `QWENLOOP_MODEL`), else
        the one `overlay_for` hands it (gptossloop only, only while `VIBEY_OLLAMA_URL` is
        set); None otherwise. Raises ConfigError for a malformed
        endpoint setting whenever `overlay_for` would, whatever else is set."""
        ...


@runtime_checkable
class LocalEngineSettingsInterface(Protocol):
    """Which local engines are switched on for one project, and how each is configured."""

    def switch_for(self, engine_id: EngineId) -> str | None:
        """The variable that switches `engine_id` on, or None for an engine with no switch."""
        ...

    def on_by_default(self, engine_id: EngineId) -> bool:
        """Whether `engine_id` is on when neither its variable nor `[features]` sets it."""
        ...

    def enabled(self, engine_id: EngineId) -> bool:
        """The environment switch when it is set at all, else `[features]`, else the
        engine's own default (on for gptossloop, ADR-0064)."""
        ...

    @property
    def notices(self) -> tuple[str, ...]:
        """What the operator should hear about how their switches now read."""
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
