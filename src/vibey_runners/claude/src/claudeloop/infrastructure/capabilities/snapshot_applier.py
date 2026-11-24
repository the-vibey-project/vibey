# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads the run's capability document strictly and turns it into what one session is given
(SP-LOOPS Phase 4, Task 4; R4, R9, R11, R12).

The document is read through `vibey_runners.common`'s strict store, which refuses anything the
conductor would not have written. A refusal of any kind, or an `OSError`, is a
`CapabilitySnapshotRefused` that names the document's path and nothing it holds: the message
reaches the console, the run's outcome and the conductor's gate, and a tampered document must
not be able to put its own text there. The run never starts without the document (`claudeloop
run` exits 78).

`[loops] builtin_web = false` switches Claude Code's own web tools off (R4). On a local backend
they are always off, whatever the setting, because a local backend cannot serve them; asking
for them there is said, never silently honoured (R11).

The snapshot's MCP servers become SDK configs with an explicit transport (Task 5, R7): a local
server starts through the scrubbed launcher, which gives it only its `env_allow` names, and a
remote one is streamable HTTP. They live on the session's record only and are never written to
the run's resources, so `claudeloop snapshot` never exports them. An allowed name that is not
set in claudeloop's own environment reaches the server as nothing; that name, and never a value,
is said in claudeloop's own log. Declared by
`interfaces/capability_snapshot_applier_interface.py::CapabilitySnapshotApplierInterface`.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Final

from vibey_runners.common.capabilities.interfaces.snapshot_document_store_interface import (
    SnapshotDocumentStoreInterface,
)
from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec
from vibey_runners.common.capabilities.snapshot_document_error import SnapshotDocumentError

from claudeloop.application.ports import Logger
from claudeloop.domain.capabilities import CLAUDE_BUILTIN_WEB_TOOLS, AppliedCapabilities
from claudeloop.domain.errors import CapabilityFlagConflict, CapabilitySnapshotRefused
from claudeloop.domain.interfaces import AppliedCapabilitiesInterface, McpConfigTranslatorInterface

LOCAL_BACKEND_WEB_NOTICE: Final = (
    "[loops] builtin_web = true is not applied on a local backend: a local backend cannot "
    "serve WebSearch or WebFetch, so both stay off for this run"
)
"""What the person is told when they asked for the web tools on a local backend (R11)."""


class CapabilitySnapshotApplier:
    """Declared by `interfaces/capability_snapshot_applier_interface.py`."""

    def __init__(
        self,
        store: SnapshotDocumentStoreInterface,
        *,
        local_backend: bool,
        mcp: McpConfigTranslatorInterface,
        environ: Mapping[str, str],
        logger: Logger,
    ) -> None:
        self._store = store
        self._local_backend = local_backend
        self._mcp = mcp
        # Read for which names are set, never for a value: only names are ever logged.
        self._environ = environ
        self._logger = logger

    def load(self, path: Path) -> AppliedCapabilities:
        try:
            document = self._store.read(path)
        except (SnapshotDocumentError, OSError) as exc:
            # The cause is chained for a debugger, never put in the message: its text can carry
            # a value from the document itself.
            raise CapabilitySnapshotRefused(
                f"the capability document {path} was refused or could not be read; "
                "the run does not start without it"
            ) from exc
        web_off = not document.builtin_web or self._local_backend
        notices = (
            (LOCAL_BACKEND_WEB_NOTICE,) if document.builtin_web and self._local_backend else ()
        )
        return AppliedCapabilities(
            digest=document.digest,
            plugin_dirs=tuple(str(folder) for folder in document.plugin_dirs),
            skills=document.skills,
            mcp_servers=self._servers(document.mcp_servers),
            disallowed_tools=CLAUDE_BUILTIN_WEB_TOOLS if web_off else (),
            add_dirs=tuple(str(folder) for folder in document.folders),
            system_prompt_append="",
            notices=notices,
        )

    def _servers(self, servers: Iterable[McpServerSpec]) -> dict[str, dict[str, object]]:
        """The document's servers as SDK configs, in document order. The reader has already
        refused a duplicate name and any spec that is neither local nor remote."""
        configs: dict[str, dict[str, object]] = {}
        for server in servers:
            configs[server.name] = self._mcp.translate(server)
            absent = [name for name in server.env_allow if name not in self._environ]
            if absent:
                self._logger.warning(
                    "capabilities.mcp_env_absent", server=server.name, names=absent
                )
        return configs

    def check_flags(
        self,
        applied: AppliedCapabilitiesInterface,
        *,
        connectors: Iterable[str],
        web_search: bool,
    ) -> None:
        clashes = sorted(set(connectors) & set(applied.mcp_servers))
        if clashes:
            raise CapabilityFlagConflict(
                f"--connector {clashes[0]!r} names an MCP server this run's capability "
                "snapshot already gives it; rename the connector or leave it out"
            )
        if web_search and "WebSearch" in applied.disallowed_tools:
            raise CapabilityFlagConflict(
                "--web-search asks for the built-in web tools, which this run's capability "
                "snapshot switches off ([loops] builtin_web)"
            )
