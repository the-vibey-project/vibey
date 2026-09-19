# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for building the gate-command runner from project config.

The *runtime* seam -- ``run`` -- is already declared as the ``GateRunner`` port
in ``application/interfaces/build.py``, because ``BuildVerifyHandler``,
``BuildIntegrateHandler`` and the automated reviewer consume it across the layer
boundary. What was not declared anywhere is the *construction* seam:
``bootstrap.build_full_worker`` builds one runner from the project's stored
config record (its ``gates`` object: the per-command timeout, the kill grace and
whether the orchestrator's Python environment is isolated), and that contract --
what config shape is read, what it may raise -- belongs in a diff (ADR-0016).
Both members are restated here so the declaration stands on its own.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey.application.interfaces import GateResult


@runtime_checkable
class ConfigurableGateRunnerInterface(Protocol):
    @classmethod
    def from_config(cls, config: Mapping[str, object]) -> "ConfigurableGateRunnerInterface": ...

    async def run(self, argv: tuple[str, ...], *, cwd: Path) -> GateResult: ...
