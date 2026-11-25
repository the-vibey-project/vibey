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

**Web** (SP-LOOPS Phase 6, Task 6; R3). Once BUILD has opened the run's web access, a run that
holds a grant is given one more MCP server in its document, `vibey-web` (`web_connector.py`): the
document is read back strictly and rewritten whole in one step, with the connector after the
person's own servers. A run with no grant keeps its document as written. A person's own server
already named `vibey-web` is never replaced, and a document that cannot be read or rewritten is
left as it was: both are logged and the run goes on, since a run is never stopped for want of
search.

**Release** removes that folder, and only it, through the remover's checks; one it cannot remove
is logged by name and left for the sweep. **Sweep** removes run folders older than the person's
`snapshot_max_age_days` or the engine run deadline and an hour, whichever is longer, so a session
still inside its deadline never loses its snapshot (R10). Declared by
`interfaces/loop_capabilities_interface.py::LoopCapabilitiesInterface`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import Final

from vibey_runners.common.capabilities.capability_resolution_error import (
    CapabilityResolutionError,
)
from vibey_runners.common.capabilities.interfaces.resolver_interface import (
    CapabilityResolverInterface,
)
from vibey_runners.common.capabilities.interfaces.snapshot_document_interface import (
    SnapshotDocumentInterface,
)
from vibey_runners.common.capabilities.interfaces.snapshot_document_store_interface import (
    SnapshotDocumentStoreInterface,
)
from vibey_runners.common.capabilities.lock_entry import LockEntry
from vibey_runners.common.capabilities.lock_error import LockError
from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec
from vibey_runners.common.capabilities.snapshot_document import SnapshotDocument
from vibey_runners.common.capabilities.snapshot_document_error import SnapshotDocumentError

from vibey.application.dto import PreparedCapabilities, PruneReport, RunWebAccess
from vibey.application.interfaces.loop_capabilities_interface import (
    LoopMarketplacesInterface,
    LoopSnapshotRemoverInterface,
)
from vibey.application.interfaces.loops_bundle_settings_interface import (
    LoopsBundleSettingsInterface,
)
from vibey.application.interfaces.observability import Logger
from vibey.application.interfaces.web_connector_interface import WebConnectorInterface
from vibey.application.web_connector import WEB_CONNECTOR_NAME, WebConnector

DEADLINE_MARGIN: Final = timedelta(hours=1)
SECONDS_PER_DAY: Final = 86400.0
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
        web_connector: WebConnectorInterface | None = None,
    ) -> None:
        self._settings = settings
        self._marketplaces = marketplaces
        self._resolver = resolver
        self._documents = documents
        self._pruner = pruner
        self._user_config = user_config
        self._run_deadline = run_deadline
        self._logger = logger
        self._web_connector = web_connector if web_connector is not None else WebConnector()

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

    def grant_web(self, prepared: PreparedCapabilities, web: RunWebAccess) -> PreparedCapabilities:
        if web.grant is None:
            return prepared
        try:
            document = self._documents.read(prepared.document)
            if any(server.name == WEB_CONNECTOR_NAME for server in document.mcp_servers):
                self._warn("loop_capabilities_web_connector_name_taken", server=WEB_CONNECTOR_NAME)
                return prepared
            connector = self._web_connector.spec(web.grant.token_file)
            self._documents.rewrite(self._with_server(document, connector), prepared.folder)
        except (SnapshotDocumentError, OSError) as exc:
            self._warn("loop_capabilities_web_connector_not_added", error=type(exc).__name__)
            return prepared
        return replace(prepared, mcp_local=prepared.mcp_local + 1)

    def release(self, prepared: PreparedCapabilities) -> None:
        if not self._pruner.remove(prepared.folder, self._marketplaces.snapshots):
            self._warn("loop_capabilities_snapshot_kept", folder=str(prepared.folder))

    def sweep(self) -> PruneReport:
        bundle = self._settings.load(self._user_config, None).bundle
        # Seconds as floats, not timedelta: a very large snapshot_max_age_days overflows
        # timedelta and would crash the worker at start-up. A float cutoff just moves far back.
        age_seconds = max(
            bundle.snapshot_max_age_days * SECONDS_PER_DAY,
            (self._run_deadline + DEADLINE_MARGIN).total_seconds(),
        )
        return self._pruner.prune(self._marketplaces.snapshots, older_than_seconds=age_seconds)

    @staticmethod
    def _with_server(
        document: SnapshotDocumentInterface, server: McpServerSpec
    ) -> SnapshotDocument:
        """`document` with `server` after its own servers, and nothing else changed."""
        return SnapshotDocument(
            version=document.version,
            digest=document.digest,
            plugin_dirs=document.plugin_dirs,
            skills=document.skills,
            mcp_servers=(*document.mcp_servers, server),
            builtin_web=document.builtin_web,
            instruction_files=document.instruction_files,
            instruction_max_bytes=document.instruction_max_bytes,
            capability_prompt_tokens=document.capability_prompt_tokens,
            capability_answer_tokens=document.capability_answer_tokens,
            folders=document.folders,
        )

    def _locked(self) -> tuple[LockEntry, ...]:
        try:
            return self._marketplaces.locked()
        except LockError as exc:
            raise CapabilityResolutionError(f"the loops lock cannot be read: {exc}") from exc

    def _warn(self, event: str, **fields: str) -> None:
        if self._logger is not None:
            self._logger.warning(event, **fields)
