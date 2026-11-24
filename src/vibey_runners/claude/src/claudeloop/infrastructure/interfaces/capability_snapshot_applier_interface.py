# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract of `infrastructure/capabilities/snapshot_applier.py`: reading the run's
capability document and checking claudeloop's own flags against it (SP-LOOPS Phase 4, Task 4;
R9, R11, R12)."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Protocol, runtime_checkable

from claudeloop.domain.interfaces import AppliedCapabilitiesInterface


@runtime_checkable
class CapabilitySnapshotApplierInterface(Protocol):
    def load(self, path: Path) -> AppliedCapabilitiesInterface:
        """What the document at `path` gives the session, its MCP servers as SDK configs with
        an explicit transport (a local one through the scrubbed launcher). An allowed variable
        name that claudeloop's environment does not set is logged by name, never by value.
        Raises `CapabilitySnapshotRefused`, naming only `path`, when the document is refused or
        cannot be read."""
        ...

    def check_flags(
        self,
        applied: AppliedCapabilitiesInterface,
        *,
        connectors: Iterable[str],
        web_search: bool,
    ) -> None:
        """Raises `CapabilityFlagConflict` when a `--connector` is named like a snapshot MCP
        server, or `--web-search` is asked for while the snapshot switches the web tools off."""
        ...
