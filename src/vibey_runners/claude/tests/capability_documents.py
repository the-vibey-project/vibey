# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Writes a real capability document, the way the conductor does, for the tests that read one
back (SP-LOOPS Phase 4, Task 4)."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path

from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec
from vibey_runners.common.capabilities.snapshot_document import DOCUMENT_VERSION, SnapshotDocument
from vibey_runners.common.capabilities.snapshot_document_store import SnapshotDocumentStore

DIGEST = "sha256:" + "0f" * 32


class CapabilityDocumentWriter:
    """One run folder (0700) under `root`, its plugin copies, and the document beside them."""

    def __init__(self, root: Path) -> None:
        self.run = Path(os.path.realpath(root)) / "snapshots" / "run-1"

    def write(
        self,
        *,
        plugins: Sequence[str] = ("alpha", "beta"),
        skills: Sequence[str] = ("alpha:review", "beta:ship"),
        builtin_web: bool = False,
        folders: Sequence[Path] = (),
        mcp_servers: Sequence[McpServerSpec] = (),
        instruction_files: Sequence[str] = ("CLAUDE.md", "AGENTS.md"),
        instruction_max_bytes: int = 65536,
    ) -> Path:
        self.run.mkdir(parents=True)
        self.run.chmod(0o700)
        plugin_dirs: list[Path] = []
        for name in plugins:
            folder = self.run / "plugins" / name
            (folder / ".claude-plugin").mkdir(parents=True)
            (folder / ".claude-plugin" / "plugin.json").write_text(
                f'{{"name": "{name}"}}', encoding="utf-8"
            )
            plugin_dirs.append(folder)
        document = SnapshotDocument(
            version=DOCUMENT_VERSION,
            digest=DIGEST,
            plugin_dirs=tuple(plugin_dirs),
            skills=tuple(skills),
            mcp_servers=tuple(mcp_servers),
            builtin_web=builtin_web,
            instruction_files=tuple(instruction_files),
            instruction_max_bytes=instruction_max_bytes,
            folders=tuple(folders),
        )
        return SnapshotDocumentStore().write(document, self.run)
