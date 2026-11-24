# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One BUILD run's capability snapshot: prepared before its engine starts, released when it ends,
and swept when a worker starts (SP-LOOPS Phase 4, Task 8; R1, R9, R10, R13).

**Prepare.** The bundle is the person's own `[loops]` (`user_config`), narrowed by the project's
`disable`; the worktree's `vibey.toml` is the only project input, and every other key it carries
is dropped, logged and returned as a notice, never applied and never recorded (ADR-0101). The
snapshot is resolved against the person's lock and the folders the lock names: a run reads only
locked trees and never fetches. The run's document is then written into the run's own 0700
folder, naming the run's input folders. A lock that cannot be read is a resolution error like an
unlocked marketplace: a person fixes both, so both park the job (R9). A document that cannot be
written takes the run folder with it, so a refusal leaves nothing behind.

**Release** removes that folder, and only it, through the remover's checks; one it cannot remove
is logged by name and left for the sweep. **Sweep** removes run folders older than the person's
`snapshot_max_age_days` or the engine run deadline and an hour, whichever is longer, so a session
still inside its deadline never loses its snapshot (R10). Declared by
`interfaces/loop_capabilities_interface.py::LoopCapabilitiesInterface`.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta
from pathlib import Path
from typing import Final

from vibey_runners.common.capabilities.capability_resolution_error import (
    CapabilityResolutionError,
)
from vibey_runners.common.capabilities.interfaces.resolver_interface import (
    CapabilityResolverInterface,
)
from vibey_runners.common.capabilities.interfaces.snapshot_document_store_interface import (
    SnapshotDocumentStoreInterface,
)
from vibey_runners.common.capabilities.lock_entry import LockEntry
from vibey_runners.common.capabilities.lock_error import LockError
from vibey_runners.common.capabilities.snapshot_document import SnapshotDocument

from vibey.application.dto import PreparedCapabilities, PruneReport
from vibey.application.interfaces.loop_capabilities_interface import (
    LoopMarketplacesInterface,
    LoopSnapshotRemoverInterface,
)
from vibey.application.interfaces.loops_bundle_settings_interface import (
    LoopsBundleSettingsInterface,
)
from vibey.application.interfaces.observability import Logger

DEADLINE_MARGIN: Final = timedelta(hours=1)
"""How much longer than the engine run deadline a run folder is kept by the sweep (R10)."""
LOCAL: Final = "local"
"""An MCP server's `trust` for a stdio command; every other is remote."""


class LoopCapabilitiesService:
    """Declared by `interfaces/loop_capabilities_interface.py::LoopCapabilitiesInterface`."""

    def __init__(
        self,
        *,
        settings: LoopsBundleSettingsInterface,
        marketplaces: LoopMarketplacesInterface,
        resolver: CapabilityResolverInterface,
        documents: SnapshotDocumentStoreInterface,
        pruner: LoopSnapshotRemoverInterface,
        user_config: Path,
        run_deadline: timedelta,
        logger: Logger | None = None,
    ) -> None:
        self._settings = settings
        self._marketplaces = marketplaces
        self._resolver = resolver
        self._documents = documents
        self._pruner = pruner
        self._user_config = user_config
        self._run_deadline = run_deadline
        self._logger = logger

    def prepare(
        self, *, project_config: Path | None, folders: Sequence[Path]
    ) -> PreparedCapabilities:
        trusted = self._settings.load(self._user_config, project_config)
        for notice in trusted.notices:
            self._warn("loop_capabilities_project_notice", notice=notice)
        bundle = trusted.bundle
        lock = self._locked()
        roots = self._marketplaces.roots(lock, [spec.name for spec in bundle.marketplaces])
        snapshot = self._resolver.resolve(bundle, lock, roots)
        try:
            document = self._documents.write(
                SnapshotDocument.of(snapshot, bundle, folders), snapshot.folder
            )
        except BaseException:
            self._pruner.remove(snapshot.folder, self._marketplaces.snapshots)
            raise
        local = sum(1 for server in snapshot.mcp_servers if server.trust == LOCAL)
        return PreparedCapabilities(
            document=document,
            folder=snapshot.folder,
            digest=snapshot.digest,
            plugins=len(snapshot.plugin_dirs),
            skills=len(snapshot.skills.skills),
            skills_skipped=len(snapshot.skills.skipped),
            mcp_local=local,
            mcp_remote=len(snapshot.mcp_servers) - local,
            notices=trusted.notices,
        )

    def release(self, prepared: PreparedCapabilities) -> None:
        if not self._pruner.remove(prepared.folder, self._marketplaces.snapshots):
            self._warn("loop_capabilities_snapshot_kept", folder=str(prepared.folder))

    def sweep(self) -> PruneReport:
        bundle = self._settings.load(self._user_config, None).bundle
        age = max(
            timedelta(days=bundle.snapshot_max_age_days), self._run_deadline + DEADLINE_MARGIN
        )
        return self._pruner.prune(
            self._marketplaces.snapshots, older_than_seconds=age.total_seconds()
        )

    def _locked(self) -> tuple[LockEntry, ...]:
        try:
            return self._marketplaces.locked()
        except LockError as exc:
            raise CapabilityResolutionError(f"the loops lock cannot be read: {exc}") from exc

    def _warn(self, event: str, **fields: str) -> None:
        if self._logger is not None:
            self._logger.warning(event, **fields)
