# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What one run is given, as a JSON document the conductor writes into the run's own folder and
a runner reads back (SP-LOOPS Phase 4, Task 2; R1, R6, R13).

The runners never import `vibey`, so a run's snapshot reaches one as this document, named by
`--capabilities PATH`. It carries the snapshot's digest, the run's plugin copies, the skills the
catalog enables by qualified name (`plugin:skill`, in catalog order: a skill the index skipped is
never named, R6), the MCP servers, the person's `builtin_web`, `instruction_files` and
`instruction_max_bytes`, and the run's input folders.

**Written canonically.** Sorted keys, ASCII only, no spaces: the same document is the same text.
An MCP server is written in the `[[loops.mcp_servers]]` table shape, with `env_allow` as names
only; no environment value is ever read here, let alone written.

**Read strictly.** Every key is known and present. The servers and the three settings are parsed
back through `BundleSpec.from_mapping`, so one validator governs both files, the refusal of a
secret-named `env_allow` included. Every plugin folder must resolve (symlinks followed) to a
folder strictly inside the document's own folder that holds `.claude-plugin/plugin.json` reached
through no symlink; every input folder must be absolute; every skill must be `plugin:skill`. Any
refusal is a `SnapshotDocumentError`. Declared by
`interfaces/snapshot_document_interface.py::SnapshotDocumentInterface`.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Self

from vibey_runners.common.capabilities.bundle import BundleSpec
from vibey_runners.common.capabilities.bundle_error import BundleError
from vibey_runners.common.capabilities.interfaces.bundle_interface import BundleSpecInterface
from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec
from vibey_runners.common.capabilities.path_probe import PathProbe
from vibey_runners.common.capabilities.snapshot import CapabilitySnapshot
from vibey_runners.common.capabilities.snapshot_document_error import SnapshotDocumentError

DOCUMENT_VERSION: Final = 1
"""The only document version this code writes and reads."""
DIGEST_PATTERN: Final = re.compile(r"sha256:[0-9a-f]{64}")
"""A snapshot digest (match with `fullmatch`)."""
SKILL_PATTERN: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*:[A-Za-z0-9][A-Za-z0-9._-]*")
"""A qualified skill name, `plugin:skill` (match with `fullmatch`)."""
PLUGIN_MARKER: Final = (".claude-plugin", "plugin.json")
"""What every plugin folder in a document holds."""
_KEYS: Final = frozenset(
    {
        "version",
        "digest",
        "plugin_dirs",
        "skills",
        "mcp_servers",
        "builtin_web",
        "instruction_files",
        "instruction_max_bytes",
        "folders",
    }
)
_SETTINGS: Final = ("mcp_servers", "builtin_web", "instruction_files", "instruction_max_bytes")
"""The keys `BundleSpec.from_mapping` reads back: the one `[loops]` rule governs them here too."""
_WHERE: Final = "the capability document"
_PROBE: Final = PathProbe()
"""Resolves and asks what is at a path the same way on every Python."""


@dataclass(frozen=True, slots=True)
class SnapshotDocument:
    """Declared by `interfaces/snapshot_document_interface.py::SnapshotDocumentInterface`."""

    version: int
    digest: str
    plugin_dirs: tuple[Path, ...]
    skills: tuple[str, ...]
    mcp_servers: tuple[McpServerSpec, ...]
    builtin_web: bool
    instruction_files: tuple[str, ...]
    instruction_max_bytes: int
    folders: tuple[Path, ...]

    @classmethod
    def of(
        cls, snapshot: CapabilitySnapshot, bundle: BundleSpecInterface, folders: Sequence[Path]
    ) -> Self:
        return cls(
            version=DOCUMENT_VERSION,
            digest=snapshot.digest,
            plugin_dirs=snapshot.plugin_dirs,
            skills=tuple(f"{entry.plugin}:{entry.name}" for entry in snapshot.skills.skills),
            mcp_servers=snapshot.mcp_servers,
            builtin_web=bundle.builtin_web,
            instruction_files=bundle.instruction_files,
            instruction_max_bytes=bundle.instruction_max_bytes,
            folders=tuple(folders),
        )

    def to_json(self) -> str:
        document = {
            "version": self.version,
            "digest": self.digest,
            "plugin_dirs": [str(path) for path in self.plugin_dirs],
            "skills": list(self.skills),
            "mcp_servers": [self._table(server) for server in self.mcp_servers],
            "builtin_web": self.builtin_web,
            "instruction_files": list(self.instruction_files),
            "instruction_max_bytes": self.instruction_max_bytes,
            "folders": [str(path) for path in self.folders],
        }
        return json.dumps(document, sort_keys=True, ensure_ascii=True, separators=(",", ":"))

    @staticmethod
    def _table(server: McpServerSpec) -> dict[str, object]:
        """`server` as a `[[loops.mcp_servers]]` table: names, never values."""
        table: dict[str, object] = {
            "name": server.name,
            "trust": server.trust,
            "env_allow": list(server.env_allow),
        }
        if server.command is not None:
            table["command"] = list(server.command)
        if server.url is not None:
            table["url"] = server.url
        return table

    # -- the strict reading -----------------------------------------------------------------------

    @classmethod
    def from_json(cls, text: str, folder: Path) -> Self:
        raw = cls._object(text)
        version = raw["version"]
        if isinstance(version, bool) or version != DOCUMENT_VERSION:
            raise SnapshotDocumentError(
                f"{_WHERE}: version {ascii(version)} is not one this runner knows "
                f"(it knows {DOCUMENT_VERSION})"
            )
        digest = raw["digest"]
        if not isinstance(digest, str) or DIGEST_PATTERN.fullmatch(digest) is None:
            raise SnapshotDocumentError(
                f"{_WHERE}: digest must be sha256: and 64 lowercase hexadecimal digits"
            )
        try:
            bundle = BundleSpec.from_mapping({"plugins": [], **{k: raw[k] for k in _SETTINGS}})
        except BundleError as exc:
            raise SnapshotDocumentError(f"{_WHERE}: {exc}") from exc
        base = _PROBE.real(folder)
        return cls(
            version=DOCUMENT_VERSION,
            digest=digest,
            plugin_dirs=tuple(
                cls._plugin_dir(entry, f"plugin_dirs[{index}]", base)
                for index, entry in enumerate(cls._list(raw, "plugin_dirs"))
            ),
            skills=tuple(
                cls._skill(entry, f"skills[{index}]")
                for index, entry in enumerate(cls._list(raw, "skills"))
            ),
            mcp_servers=bundle.mcp_servers,
            builtin_web=bundle.builtin_web,
            instruction_files=bundle.instruction_files,
            instruction_max_bytes=bundle.instruction_max_bytes,
            folders=tuple(
                cls._folder(entry, f"folders[{index}]")
                for index, entry in enumerate(cls._list(raw, "folders"))
            ),
        )

    @staticmethod
    def _object(text: str) -> Mapping[str, object]:
        """The document's top-level object, with every key known and none missing."""
        try:
            raw = json.loads(text)
        except (ValueError, RecursionError) as exc:  # RecursionError: nesting deeper than Python
            raise SnapshotDocumentError(f"{_WHERE} is not JSON: {exc}") from exc
        if not isinstance(raw, dict):
            raise SnapshotDocumentError(f"{_WHERE} must be a JSON object")
        unknown = sorted(set(raw) - _KEYS)
        if unknown:
            raise SnapshotDocumentError(f"{_WHERE}: {ascii(unknown[0])} is not a known key")
        missing = sorted(_KEYS - set(raw))
        if missing:
            raise SnapshotDocumentError(f"{_WHERE}: {missing[0]} is missing")
        return raw

    @staticmethod
    def _list(raw: Mapping[str, object], key: str) -> list[object]:
        value = raw[key]
        if not isinstance(value, list):
            raise SnapshotDocumentError(f"{_WHERE}: {key} must be a list")
        return value

    @staticmethod
    def _plugin_dir(entry: object, where: str, base: Path) -> Path:
        """`entry` resolved, when it is a plugin folder strictly inside `base` whose
        `.claude-plugin/plugin.json` is a regular file reached through no symlink."""
        if not isinstance(entry, str) or not Path(entry).is_absolute() or ".." in Path(entry).parts:
            raise SnapshotDocumentError(f"{_WHERE}: {where} must be an absolute path with no '..'")
        try:
            real = _PROBE.real(Path(entry))
            inside = real != base and real.is_relative_to(base)
            marker = real.joinpath(*PLUGIN_MARKER)
            held = inside and _PROBE.real(marker) == marker and _PROBE.is_file(marker)
        except (OSError, ValueError) as exc:  # e.g. a folder that cannot be searched, a NUL
            raise SnapshotDocumentError(f"{_WHERE}: {where} cannot be checked: {exc}") from exc
        if not inside:
            raise SnapshotDocumentError(
                f"{_WHERE}: {where} {ascii(entry)} is outside the document's folder {base}"
            )
        if not held:
            raise SnapshotDocumentError(
                f"{_WHERE}: {where} {ascii(entry)} is not a plugin folder holding "
                f"{'/'.join(PLUGIN_MARKER)}"
            )
        return real

    @staticmethod
    def _skill(entry: object, where: str) -> str:
        if not isinstance(entry, str) or SKILL_PATTERN.fullmatch(entry) is None:
            raise SnapshotDocumentError(f"{_WHERE}: {where} must be written plugin:skill")
        return entry

    @staticmethod
    def _folder(entry: object, where: str) -> Path:
        if not isinstance(entry, str) or "\x00" in entry or not Path(entry).is_absolute():
            raise SnapshotDocumentError(f"{_WHERE}: {where} must be an absolute path")
        return Path(entry)
