# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a marketplace's `.claude-plugin/marketplace.json` without leaving the marketplace
(SP-LOOPS Task 4; Review Focus 1 and 2).

A marketplace may come from the network, so its manifest is hostile until shown otherwise. Each
plugin's `source` is checked twice: lexically first -- an absolute or home-relative path, or one
with a `..` part, is refused before the file system is touched -- and then by resolving the
folder (symlinks followed) and requiring `relative_to(root.resolve())` and not inside the root's
`.git` (by file identity and by case-folded name, `GitFolderGuard`), which the lock's digest
leaves out (`CapabilityLock`). Any such failure refuses
the whole marketplace (`ManifestError`): a manifest that tries to point outside itself is not
trusted for any of its plugins. The manifest is read through the bounded reader, capped at
`MANIFEST_MAX_BYTES`, and every field is checked. A plugin that is merely unusable here (a remote
source object, a folder that is not there) is listed in `skipped` with its reason.

Declared by `interfaces/manifest_interface.py::MarketplaceManifestInterface`.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Final

from vibey_runners.common.capabilities.file_reader import BoundedFileReader
from vibey_runners.common.capabilities.file_too_large_error import FileTooLargeError
from vibey_runners.common.capabilities.git_folder_guard import GitFolderGuard
from vibey_runners.common.capabilities.interfaces.file_reader_interface import (
    FileReaderInterface,
)
from vibey_runners.common.capabilities.interfaces.git_folder_guard_interface import (
    GitFolderGuardInterface,
)
from vibey_runners.common.capabilities.interfaces.path_probe_interface import PathProbeInterface
from vibey_runners.common.capabilities.manifest_error import ManifestError
from vibey_runners.common.capabilities.marketplace_catalog import MarketplaceCatalog
from vibey_runners.common.capabilities.names import NAME_PATTERN
from vibey_runners.common.capabilities.path_probe import DIR, FILE, PathProbe
from vibey_runners.common.capabilities.plugin_entry import PluginEntry

MANIFEST_PATH: Final = PurePosixPath(".claude-plugin") / "marketplace.json"
MANIFEST_MAX_BYTES: Final = 2 * 1024 * 1024
"""The largest manifest read. vibey's own, with 157 plugins, is about 150 KiB."""
MAX_PLUGINS: Final = 1024
"""The most plugins one manifest may list."""
INSIDE_GIT: Final = "inside the marketplace's .git, which the lock does not cover"
REMOTE_SOURCE: Final = "its source is not a folder in the marketplace"
MISSING_FOLDER: Final = "its folder does not exist"


class MarketplaceManifest:
    """Declared by `interfaces/manifest_interface.py::MarketplaceManifestInterface`."""

    def __init__(
        self,
        reader: FileReaderInterface | None = None,
        guard: GitFolderGuardInterface | None = None,
        probe: PathProbeInterface | None = None,
    ) -> None:
        self._reader = reader or BoundedFileReader()
        self._guard = guard or GitFolderGuard()
        self._probe = probe or PathProbe()

    def read(self, root: Path) -> MarketplaceCatalog:
        base = self._probe.real(root)
        if not self._probed(base, f"the marketplace folder {root}", DIR):
            raise ManifestError(f"the marketplace folder {root} does not exist")
        manifest = self._probe.real(base / MANIFEST_PATH)
        if not manifest.is_relative_to(base):
            raise ManifestError(f"{root}: {MANIFEST_PATH} resolves outside the marketplace")
        if self._guard.inside(base, manifest):
            raise ManifestError(f"{root}: {MANIFEST_PATH} resolves {INSIDE_GIT}")
        if not self._probed(manifest, f"{root}: {MANIFEST_PATH}", FILE):
            raise ManifestError(f"{root} has no {MANIFEST_PATH}")
        document = self._document(manifest)
        plugins: dict[str, PluginEntry] = {}
        skipped: list[tuple[str, str]] = []
        seen: set[str] = set()
        for index, entry in enumerate(self._entries(document, manifest)):
            where = f"{manifest}: plugins[{index}]"
            name, description = self._identity(entry, where, seen)
            source = entry.get("source")
            if not isinstance(source, str):
                skipped.append((name, REMOTE_SOURCE))
                continue
            directory = self._folder(base, source, f"{where} ({name})")
            if not self._probed(directory, f"{where} ({name}): its folder", DIR):
                skipped.append((name, MISSING_FOLDER))
                continue
            plugins[name] = PluginEntry(name, directory, description)
        return MarketplaceCatalog(MappingProxyType(plugins), tuple(skipped))

    def _probed(self, path: Path, what: str, kind: str) -> bool:
        """Whether `path` is a `kind`. A path the file system will not let it look at (a folder
        that cannot be searched) is a `ManifestError`, the same on every Python, never "missing"."""
        try:
            return self._probe.kind(path) == kind
        except OSError as exc:
            raise ManifestError(f"{what} cannot be read: {exc}") from exc

    def _document(self, manifest: Path) -> object:
        try:
            text = self._reader.read_text(manifest, MANIFEST_MAX_BYTES)
        except FileTooLargeError as exc:
            raise ManifestError(str(exc)) from exc
        except UnicodeDecodeError as exc:
            raise ManifestError(f"{manifest} is not UTF-8") from exc
        except OSError as exc:
            raise ManifestError(f"{manifest} cannot be read: {exc}") from exc
        try:
            return json.loads(text)
        except ValueError as exc:
            raise ManifestError(f"{manifest} is not JSON: {exc}") from exc
        except RecursionError as exc:  # deep enough nesting exhausts json's recursion
            raise ManifestError(f"{manifest} is not JSON: nested too deeply") from exc

    @staticmethod
    def _entries(document: object, manifest: Path) -> Sequence[Mapping[str, object]]:
        if not isinstance(document, dict):
            raise ManifestError(f"{manifest}: the manifest must be a JSON object")
        plugins = document.get("plugins")
        if not isinstance(plugins, list):
            raise ManifestError(f"{manifest}: plugins must be a list")
        if len(plugins) > MAX_PLUGINS:
            raise ManifestError(f"{manifest}: plugins must hold at most {MAX_PLUGINS} entries")
        for index, entry in enumerate(plugins):
            if not isinstance(entry, dict):
                raise ManifestError(f"{manifest}: plugins[{index}] must be an object")
        return plugins

    @staticmethod
    def _identity(entry: Mapping[str, object], where: str, seen: set[str]) -> tuple[str, str]:
        name = entry.get("name")
        if not isinstance(name, str) or NAME_PATTERN.fullmatch(name) is None or name in seen:
            raise ManifestError(f"{where}.name must be a plain name, used once")
        seen.add(name)
        description = entry.get("description", "")
        if not isinstance(description, str):
            raise ManifestError(f"{where}.description must be a string")
        return name, description

    def _folder(self, base: Path, source: str, where: str) -> Path:
        if any(ord(char) < 0x20 for char in source):
            raise ManifestError(f"{where}: source contains control characters")
        relative = PurePosixPath(source)
        if relative.is_absolute() or source.startswith("~"):
            raise ManifestError(f"{where}: source {source!r} is absolute")
        if ".." in relative.parts:
            raise ManifestError(f"{where}: source {source!r} climbs out of the marketplace")
        directory = self._probe.real(base / relative)
        if not directory.is_relative_to(base):
            raise ManifestError(f"{where}: its folder resolves outside the marketplace")
        if self._guard.inside(base, directory):
            raise ManifestError(f"{where}: its folder resolves {INSIDE_GIT}")
        return directory
