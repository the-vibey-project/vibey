# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Turns a bundle into a locked, run-scoped snapshot (SP-LOOPS Task 6; design Decisions 1, 3 and
10; Review Focus 3).

**Which marketplaces.** Only those the enabled plugins come from: a declared marketplace nothing
uses is not read, so a disabled plugin needs neither a lock nor a folder. Each is read from the
folder `roots` maps its name to -- an absolute path the conductor takes from the person's own
folders. The bundle's `source` is where `vibey loops marketplace update` fetches from; a run never
reads it as a folder, and nothing here reads a project file.

**The lock.** A person-added marketplace with no entry raises `UnlockedMarketplaceError` (a run
never fetches or locks one); an entry that pins another source or ref than `[loops]` names, or a
tree whose digest differs from the entry's, raises `LockMismatchError`. The shipped marketplace
(`DEFAULT_MARKETPLACE_NAME`, the copy in the installed wheel) locks itself the first time it is
used: its digest is written to the person's lock file beside every other entry. It locks itself
again only when the shipped copy is a new one -- `shipped_source` names the installed release, so
an upgrade is a new source, while the same source with other content is a mismatch. The name is
reserved, so a network marketplace can never take this path.

**The copy.** Checking a tree and then loading from it leaves a window (`O_NOFOLLOW` guards only a
path's last component), so a run never loads from a marketplace folder. The manifest and each
selected plugin's folder are copied into a fresh 0700 folder under `snapshots` (`SnapshotCopier`:
bytes only, no hard links, no symlinks, at most `max_snapshot_entries` entries and
`max_snapshot_bytes` bytes for the whole snapshot), and the copy's own records are compared with
the records whose digest matched the lock: a file swapped after the check is a `LockMismatchError`,
never loaded. The manifest is then read again, from the copy, and the skills are indexed from the
copy. A symlink inside a selected plugin is not copied and is named in the skipped rows, and so
is an entry whose name is not plain visible text (`SafeText.is_plain`): it is left out with
everything below it, and its row names the plain parent folder with the name escaped, so every
path a snapshot carries stays a real `Path` and is still safe to print.

**What a model or terminal sees.** A skill a disabled name names is dropped; a skill name two
plugins share goes to the first in bundle order and the later one is a skipped row. Descriptions
are made one safe line and capped at `description_limit` characters, and skipped reasons likewise
(`SafeText`).

On any failure the run's folder is removed. Declared by
`interfaces/resolver_interface.py::CapabilityResolverInterface`.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path, PurePosixPath
from typing import Final

from vibey_runners.common.capabilities.bundle import BundleSpec
from vibey_runners.common.capabilities.bundle_error import BundleError
from vibey_runners.common.capabilities.capability_resolution_error import (
    CapabilityResolutionError,
)
from vibey_runners.common.capabilities.defaults import (
    DEFAULT_MARKETPLACE_NAME,
    DEFAULT_MARKETPLACE_SOURCE,
)
from vibey_runners.common.capabilities.interfaces.bundle_interface import BundleSpecInterface
from vibey_runners.common.capabilities.interfaces.lock_interface import CapabilityLockInterface
from vibey_runners.common.capabilities.interfaces.manifest_interface import (
    MarketplaceManifestInterface,
)
from vibey_runners.common.capabilities.interfaces.safe_text_interface import SafeTextInterface
from vibey_runners.common.capabilities.interfaces.skill_index_interface import (
    SkillIndexInterface,
)
from vibey_runners.common.capabilities.interfaces.snapshot_copier_interface import (
    SnapshotCopierInterface,
)
from vibey_runners.common.capabilities.lock import CapabilityLock
from vibey_runners.common.capabilities.lock_entry import LockEntry
from vibey_runners.common.capabilities.lock_error import LockError
from vibey_runners.common.capabilities.lock_mismatch_error import LockMismatchError
from vibey_runners.common.capabilities.manifest import MANIFEST_PATH, MarketplaceManifest
from vibey_runners.common.capabilities.manifest_error import ManifestError
from vibey_runners.common.capabilities.marketplace_catalog import MarketplaceCatalog
from vibey_runners.common.capabilities.marketplace_spec import MarketplaceSpec
from vibey_runners.common.capabilities.names import NAME_PATTERN
from vibey_runners.common.capabilities.plugin_spec import PluginSpec
from vibey_runners.common.capabilities.safe_text import MIN_LIMIT, SafeText
from vibey_runners.common.capabilities.skill_catalog import SkillCatalog
from vibey_runners.common.capabilities.skill_entry import SkillEntry
from vibey_runners.common.capabilities.skill_index import SkillIndex
from vibey_runners.common.capabilities.snapshot import CapabilitySnapshot
from vibey_runners.common.capabilities.snapshot_copier import SnapshotCopier
from vibey_runners.common.capabilities.tree_record import TreeRecord
from vibey_runners.common.capabilities.unlocked_marketplace_error import (
    UnlockedMarketplaceError,
)

DESCRIPTION_MAX_CHARS: Final = 1024
"""The longest skill description a snapshot carries (design Decision 10: descriptions are loaded
up front into every loop's context)."""
REASON_MAX_CHARS: Final = 1024
"""The longest skipped reason a snapshot carries."""
SNAPSHOT_MAX_ENTRIES: Final = 10_000
"""The most folders and files one run's snapshot may hold, across its marketplaces."""
SNAPSHOT_MAX_BYTES: Final = 64 * 1024 * 1024
"""The most bytes one run's snapshot may hold; vibey's whole shipped marketplace is about 15 MiB."""
LINK_NOT_COPIED: Final = "a symlink, which a snapshot never copies"
UNPLAIN_NAME: Final = (
    "holds {}, whose name is not plain visible text (a control, bidi or invisible character); "
    "a snapshot never copies it"
)
"""The reason for an entry left out for its name: the row names its parent folder, and the name
appears only escaped (`ascii()`), so nothing a row carries can drive a terminal."""
COPY_CHANGED: Final = "a file changed while it was copied into the run's snapshot"
_RUN_PREFIX: Final = "run-"
_SYMLINK: Final = "L"


@dataclass(slots=True)
class _Budget:
    """What is left of the snapshot's caps as each marketplace is copied."""

    entries: int
    bytes: int


class CapabilityResolver:
    """Declared by `interfaces/resolver_interface.py::CapabilityResolverInterface`."""

    def __init__(
        self,
        lock_path: Path,
        snapshots: Path,
        *,
        shipped_source: str = DEFAULT_MARKETPLACE_SOURCE,
        locker: CapabilityLockInterface | None = None,
        manifest: MarketplaceManifestInterface | None = None,
        skills: SkillIndexInterface | None = None,
        copier: SnapshotCopierInterface | None = None,
        text: SafeTextInterface | None = None,
        description_limit: int = DESCRIPTION_MAX_CHARS,
        max_snapshot_entries: int = SNAPSHOT_MAX_ENTRIES,
        max_snapshot_bytes: int = SNAPSHOT_MAX_BYTES,
    ) -> None:
        self._lock_path = self._absolute(lock_path, "the lock file")
        self._snapshots = self._absolute(snapshots, "the snapshot folder")
        for option, value, least in (
            ("description_limit", description_limit, MIN_LIMIT),
            ("max_snapshot_entries", max_snapshot_entries, 1),
            ("max_snapshot_bytes", max_snapshot_bytes, 1),
        ):
            if value < least:
                raise ValueError(f"{option} must be at least {least}, not {value}")
        try:
            self._shipped_source = BundleSpec.option_safe_text(shipped_source, "shipped_source")
        except BundleError as exc:
            raise CapabilityResolutionError(str(exc)) from exc
        self._locker = locker or CapabilityLock()
        self._manifest = manifest or MarketplaceManifest()
        self._skills = skills or SkillIndex()
        self._copier = copier or SnapshotCopier()
        self._text = text or SafeText()
        self._description_limit = description_limit
        self._max_entries = max_snapshot_entries
        self._max_bytes = max_snapshot_bytes

    def resolve(
        self, bundle: BundleSpecInterface, lock: Sequence[LockEntry], roots: Mapping[str, Path]
    ) -> CapabilitySnapshot:
        declared = self._declared(bundle.marketplaces)
        entries = self._entries(lock)
        plugins = [plugin for plugin in bundle.plugins if plugin.name not in bundle.disabled]
        by_marketplace: dict[str, list[PluginSpec]] = {}
        for plugin in plugins:
            by_marketplace.setdefault(plugin.marketplace, []).append(plugin)
        used: dict[str, LockEntry] = {}
        located: dict[tuple[str, str], Path] = {}
        links: list[tuple[Path, str]] = []
        budget = _Budget(self._max_entries, self._max_bytes)
        run: Path | None = None
        try:
            for name, wanted in by_marketplace.items():
                spec = self._spec(name, declared)
                root = self._root(name, roots)
                records, used[name] = self._verified(name, spec, root, entries.get(name))
                if run is None:
                    run = self._run_folder()
                folders, skipped = self._copy(name, root, records, wanted, run / name, budget)
                located.update(((name, plugin), folder) for plugin, folder in folders.items())
                links.extend(skipped)
            plugin_dirs = tuple(located[(p.marketplace, p.name)] for p in plugins)
            skills = self._catalog(self._skills.build(plugin_dirs), bundle.disabled, links)
        except BaseException:
            if run is not None:
                shutil.rmtree(run, ignore_errors=True)  # an unverified copy is never left behind
            raise
        servers = tuple(s for s in bundle.mcp_servers if s.name not in bundle.disabled)
        return CapabilitySnapshot(plugin_dirs, skills, servers, self._digest(bundle, used))

    # -- the inputs ------------------------------------------------------------------------------

    @staticmethod
    def _absolute(path: Path, what: str) -> Path:
        if not path.is_absolute():
            raise CapabilityResolutionError(
                f"{what} must be an absolute path, not {path} (a relative path would be read from "
                "the current folder, which may be a project's)"
            )
        return path

    @staticmethod
    def _declared(marketplaces: Iterable[MarketplaceSpec]) -> dict[str, MarketplaceSpec]:
        declared: dict[str, MarketplaceSpec] = {}
        for spec in marketplaces:
            if spec.name == DEFAULT_MARKETPLACE_NAME:
                raise CapabilityResolutionError(
                    f"the marketplace name {spec.name} is reserved for the marketplace that ships "
                    "with vibey; a declared marketplace may not take it"
                )
            declared[spec.name] = spec
        return declared

    @staticmethod
    def _entries(lock: Sequence[LockEntry]) -> dict[str, LockEntry]:
        entries: dict[str, LockEntry] = {}
        for entry in lock:
            if entry.marketplace in entries:
                raise CapabilityResolutionError(
                    f"the lock names the marketplace {entry.marketplace} twice"
                )
            entries[entry.marketplace] = entry
        return entries

    @staticmethod
    def _spec(name: str, declared: Mapping[str, MarketplaceSpec]) -> MarketplaceSpec | None:
        """The declared marketplace `name`, or None for the shipped one."""
        if NAME_PATTERN.fullmatch(name) is None:
            raise CapabilityResolutionError(f"the marketplace {name!r} is not a plain name")
        if name == DEFAULT_MARKETPLACE_NAME:
            return None
        if name not in declared:
            raise CapabilityResolutionError(
                f"a plugin names the marketplace {name}, which the bundle does not declare"
            )
        return declared[name]

    def _root(self, name: str, roots: Mapping[str, Path]) -> Path:
        root = roots.get(name)
        if root is None:
            raise CapabilityResolutionError(f"no folder is given for the marketplace {name}")
        return self._absolute(root, f"the folder of the marketplace {name}")

    # -- the lock ---------------------------------------------------------------------------------

    def _verified(
        self, name: str, spec: MarketplaceSpec | None, root: Path, entry: LockEntry | None
    ) -> tuple[tuple[TreeRecord, ...], LockEntry]:
        """The tree's records, which hash to `entry`'s digest, and the entry they match."""
        if spec is None and (entry is None or entry.source != self._shipped_source):
            records = self._records(name, root)
            entry = LockEntry(
                name, self._shipped_source, None, self._locker.digest_records(records)
            )
            self._lock_itself(entry)
            return records, entry
        if entry is None:
            raise UnlockedMarketplaceError(name)
        if spec is not None and (entry.source, entry.ref) != (spec.source, spec.ref):
            raise LockMismatchError(
                name,
                f"the lock pins {self._pin(entry.source, entry.ref)}, but [loops] names "
                f"{self._pin(spec.source, spec.ref)}",
            )
        records = self._records(name, root)
        if self._locker.digest_records(records) != entry.digest:
            raise LockMismatchError(name)
        return records, entry

    @staticmethod
    def _pin(source: str, ref: str | None) -> str:
        return source if ref is None else f"{source} at {ref}"

    def _records(self, name: str, root: Path) -> tuple[TreeRecord, ...]:
        try:
            return self._locker.tree_records(root)
        except (LockError, OSError) as exc:
            raise CapabilityResolutionError(
                f"the marketplace {name} cannot be read: {exc}"
            ) from exc

    def _lock_itself(self, entry: LockEntry) -> None:
        """Adds or replaces the shipped marketplace's entry in the person's lock file, keeping
        every other entry as the file holds it now."""
        try:
            current = self._locker.read(self._lock_path)
            kept = [other for other in current if other.marketplace != entry.marketplace]
            self._locker.write(self._lock_path, [*kept, entry])
        except (LockError, OSError) as exc:
            raise CapabilityResolutionError(
                f"the marketplace {entry.marketplace} cannot lock itself: {exc}"
            ) from exc

    # -- the copy ---------------------------------------------------------------------------------

    def _run_folder(self) -> Path:
        self._snapshots.mkdir(mode=0o700, parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix=_RUN_PREFIX, dir=self._snapshots))  # 0700

    def _copy(
        self,
        name: str,
        root: Path,
        records: Sequence[TreeRecord],
        wanted: Sequence[PluginSpec],
        target: Path,
        budget: _Budget,
    ) -> tuple[dict[str, Path], list[tuple[Path, str]]]:
        """Copies the manifest and the `wanted` plugins' folders to `target`, checks the copy
        against `records`, and returns each plugin's folder in the copy and the symlinks left
        out."""
        base = root.resolve()
        original = self._read_manifest(name, root)
        items = [MANIFEST_PATH]
        for plugin in wanted:
            entry = original.plugins.get(plugin.name)
            if entry is None:
                raise CapabilityResolutionError(
                    f"the marketplace {name} has no plugin {plugin.name}: "
                    f"{self._why_not(original, plugin.name)}"
                )
            items.append(PurePosixPath(entry.directory.relative_to(base).as_posix()))
        plan, left_out = self._plan(records, items)
        budget.bytes -= self._copier.copy(
            root, plan, target, max_entries=budget.entries, max_bytes=budget.bytes
        )
        budget.entries -= len(plan)
        copied = {record.path: record for record in self._records(name, target)}
        if copied != {record.path: record for record in plan}:
            raise LockMismatchError(name, COPY_CHANGED)
        snapshot = self._read_manifest(name, target)
        folders: dict[str, Path] = {}
        for plugin in wanted:
            entry = snapshot.plugins.get(plugin.name)
            if entry is None:  # e.g. its folder is reached through a symlink, which is not copied
                raise CapabilityResolutionError(
                    f"the plugin {plugin.name} is not in the snapshot of {name}: "
                    f"{self._why_not(snapshot, plugin.name)}"
                )
            folders[plugin.name] = entry.directory
        here = target.resolve()
        return folders, [
            (here / where, self._text.clean(reason, REASON_MAX_CHARS)) for where, reason in left_out
        ]

    def _read_manifest(self, name: str, root: Path) -> MarketplaceCatalog:
        try:
            return self._manifest.read(root)
        except ManifestError as exc:
            raise CapabilityResolutionError(f"the marketplace {name}: {exc}") from exc

    @staticmethod
    def _why_not(catalog: MarketplaceCatalog, plugin: str) -> str:
        return dict(catalog.skipped).get(plugin, "its manifest does not list it")

    def _plan(
        self, records: Sequence[TreeRecord], items: Sequence[PurePosixPath]
    ) -> tuple[list[TreeRecord], list[tuple[PurePosixPath, str]]]:
        """The folders and files to copy (each item, everything under it, and the folders
        above it), and what is left out, each as the place in the copy a row names and why: a
        symlink under an item, and an entry whose name is not plain text (with everything below
        it), named by its plain parent folder so that no path a row carries can hold a control,
        bidi or invisible character."""
        plan: list[TreeRecord] = []
        left_out: list[tuple[PurePosixPath, str]] = []
        for record in records:
            path = PurePosixPath(record.path)
            inside = any(path == item or item in path.parents for item in items)
            if not inside and not any(path in item.parents for item in items):
                continue
            unplain = [i for i, part in enumerate(path.parts) if not self._text.is_plain(part)]
            if unplain:
                if unplain[0] == len(path.parts) - 1:  # the top unplain entry, named once
                    left_out.append((path.parent, UNPLAIN_NAME.format(ascii(path.name))))
            elif record.kind == _SYMLINK:
                if inside:  # a symlink above an item leaves that item out of the copy anyway
                    left_out.append((path, LINK_NOT_COPIED))
            else:
                plan.append(record)
        return plan, left_out

    # -- what the run sees ------------------------------------------------------------------------

    def _catalog(
        self, catalog: SkillCatalog, disabled: frozenset[str], links: Sequence[tuple[Path, str]]
    ) -> SkillCatalog:
        providers: dict[str, str] = {}
        kept: list[SkillEntry] = []
        skipped = [
            (path, self._text.clean(reason, REASON_MAX_CHARS)) for path, reason in catalog.skipped
        ]
        skipped.extend(links)
        for entry in catalog.skills:
            if entry.name in disabled:
                continue
            if entry.name in providers:
                skipped.append(
                    (
                        entry.path,
                        f"names the skill {entry.name}, which the plugin "
                        f"{providers[entry.name]} already provides",
                    )
                )
                continue
            providers[entry.name] = entry.plugin
            description = self._text.clean(entry.description, self._description_limit)
            kept.append(replace(entry, description=description))
        return SkillCatalog(tuple(kept), tuple(skipped))

    @staticmethod
    def _digest(bundle: BundleSpecInterface, used: Mapping[str, LockEntry]) -> str:
        document = {
            "bundle": {
                "marketplaces": [asdict(spec) for spec in bundle.marketplaces],
                "plugins": [asdict(spec) for spec in bundle.plugins],
                "mcp_servers": [asdict(spec) for spec in bundle.mcp_servers],
                "skills": list(bundle.skills),
                "disabled": sorted(bundle.disabled),
            },
            "lock": [asdict(used[name]) for name in sorted(used)],
        }
        return CapabilityLock.checksum(document)
