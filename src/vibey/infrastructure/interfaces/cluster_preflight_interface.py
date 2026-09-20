# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind ``vibey doctor --cluster`` (ADR-0016).

Two seams. ``EngineAuthCheckInterface`` is the one judgement that depends on
what the worker was told to run, so it is built from the worker's own
``--engines`` / ``--provider`` and handed to the preflight rather than read
from ``PATH``: since ADR-0037 every runner ships in the image, so an engine
binary being present says nothing about whether the worker will use it.
``ClusterPreflightInterface`` is the whole sweep that consumes it.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:  # the concrete result type lives beside its checks
    from vibey.infrastructure.cluster_preflight import ClusterCheck


@runtime_checkable
class EngineAuthCheckInterface(Protocol):
    """Judges engine credentials against the engines a worker will actually use."""

    def check(self, environ: Mapping[str, str]) -> ClusterCheck:
        """One ``engine-auth`` verdict for this environment. Never raises."""
        ...


@runtime_checkable
class ClusterPreflightInterface(Protocol):
    """Every in-cluster wiring check, in the order ``doctor --cluster`` prints them."""

    async def run(
        self,
        *,
        dsn: str,
        workspace: Path,
        migrations_dir: Path,
        environ: Mapping[str, str],
        uid: int,
    ) -> tuple[ClusterCheck, ...]:
        """Run the sweep. The migrations check runs only when the database connected."""
        ...
