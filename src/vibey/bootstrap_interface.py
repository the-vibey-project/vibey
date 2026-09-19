# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The composition-root resource contract.

``bootstrap.py`` owns concrete wiring, so lower layers must not import its
resource bundle.  This protocol is only for callers that need to pass the
assembled graph around without taking a dependency on the composition root.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from vibey.application.interfaces import (
    Clock,
    ConductorPreflightInterface,
    EngineAdapter,
)
from vibey.domain.engine import EngineId


@runtime_checkable
class AppResourcesInterface(Protocol):
    """The named services assembled once by the application bootstrap."""

    @property
    def projects(self) -> object: ...

    @property
    def jobs(self) -> object: ...

    @property
    def gates(self) -> object: ...

    @property
    def ledger(self) -> object: ...

    @property
    def design_ledger(self) -> object: ...

    @property
    def design_specs(self) -> object: ...

    @property
    def visual_inventories(self) -> object: ...

    @property
    def build_ledger(self) -> object: ...

    @property
    def review_ledger(self) -> object: ...

    @property
    def deploy_review_ledger(self) -> object: ...

    @property
    def engine_health_repo(self) -> object: ...

    @property
    def rotation_cursors(self) -> object: ...

    @property
    def engine_health_service(self) -> object: ...

    @property
    def conductor_preflight(self) -> ConductorPreflightInterface: ...

    @property
    def engine_selector(self) -> object: ...

    @property
    def rotation_handoff(self) -> object: ...

    @property
    def engine_adapters(self) -> Mapping[EngineId, EngineAdapter]: ...

    @property
    def handoffs(self) -> object: ...

    @property
    def clock(self) -> Clock: ...

    @property
    def integration_lock(self) -> object | None: ...
