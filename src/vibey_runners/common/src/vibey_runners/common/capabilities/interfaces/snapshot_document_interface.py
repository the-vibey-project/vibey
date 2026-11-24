# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of a run's capability document (SP-LOOPS Phase 4, Task 2; R1)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, Self, runtime_checkable

from vibey_runners.common.capabilities.interfaces.bundle_interface import BundleSpecInterface
from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec
from vibey_runners.common.capabilities.snapshot import CapabilitySnapshot


@runtime_checkable
class SnapshotDocumentInterface(Protocol):
    """What one run is given, as the conductor hands it to a runner that never imports vibey:
    the snapshot's digest, plugin copies, qualified skill names and MCP servers, the person's
    web, instruction-file, size and capability token budget settings, and the run's input
    folders."""

    @property
    def version(self) -> int: ...

    @property
    def digest(self) -> str: ...

    @property
    def plugin_dirs(self) -> tuple[Path, ...]: ...

    @property
    def skills(self) -> tuple[str, ...]:
        """`plugin:skill` for each skill the snapshot's catalog enables, in catalog order."""
        ...

    @property
    def mcp_servers(self) -> tuple[McpServerSpec, ...]: ...

    @property
    def builtin_web(self) -> bool: ...

    @property
    def instruction_files(self) -> tuple[str, ...]: ...

    @property
    def instruction_max_bytes(self) -> int: ...

    @property
    def capability_prompt_tokens(self) -> int:
        """The most estimated tokens a loop that lists its own capabilities spends on them in its
        standing system prompt (Phase 5, R8); claudeloop ignores it."""
        ...

    @property
    def capability_answer_tokens(self) -> int:
        """The most estimated tokens any one on-demand capability answer may hold (Phase 5, R8);
        claudeloop ignores it."""
        ...

    @property
    def folders(self) -> tuple[Path, ...]:
        """The run's input folders (absolute), when it has any."""
        ...

    @classmethod
    def of(
        cls, snapshot: CapabilitySnapshot, bundle: BundleSpecInterface, folders: Sequence[Path]
    ) -> Self:
        """The document of `snapshot`, resolved from `bundle`, for a run given `folders`."""
        ...

    def to_json(self) -> str:
        """Canonical JSON: sorted keys, ASCII only, the same text for the same document. MCP
        servers are written in the `[[loops.mcp_servers]]` table shape, names only: an
        environment value is never written."""
        ...

    @classmethod
    def from_json(cls, text: str, folder: Path) -> Self:
        """The document `text` holds, read strictly, for the document that lives in `folder`.
        Raises `SnapshotDocumentError` for anything the writer would not have written: an
        unknown or missing key, a version other than 2 (checked before any missing key), a digest that is not a sha256, a plugin
        folder outside `folder` (through a symlink too) or without its
        `.claude-plugin/plugin.json`, an input folder that is not absolute, a skill not named
        `plugin:skill`, or a server or setting the `[loops]` rule refuses (a secret-named
        `env_allow` included)."""
        ...
