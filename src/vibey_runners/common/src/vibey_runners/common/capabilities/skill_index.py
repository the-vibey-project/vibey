# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Indexes the skills a set of plugins holds, from `skills/*/SKILL.md` frontmatter (SP-LOOPS
Task 4; Review Focus 2 and 5).

Each plugin folder is the bound: it was itself contained in its marketplace by
`MarketplaceManifest`, so a skills folder, a skill folder or a SKILL.md that resolves (through a
symlink) outside its plugin's folder is outside the locked marketplace content as far as this
plugin is concerned, and is skipped as `OUTSIDE` without being read. A path through a `.git`
folder below the plugin -- by case-folded name at any depth, or by file identity with the plugin
folder's own `.git` (`GitFolderGuard`) -- is skipped as `INSIDE_GIT`: the lock leaves the
marketplace root's `.git` out of its digest, so nothing in one may be loaded. Only the frontmatter's
`name` and `description` are kept (design Decision 10: bodies are fetched on demand). A file over
`SKILL_MAX_BYTES`, one that is not UTF-8 or cannot be opened, and a malformed frontmatter are each
skipped with a named reason; so is any entry, skill folder or `skills/` folder the file system
will not let it look at (a symlink loop, a folder that cannot be searched). The index never raises
for what a plugin contains.

Declared by `interfaces/skill_index_interface.py::SkillIndexInterface`.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from vibey_runners.common.capabilities.file_reader import BoundedFileReader
from vibey_runners.common.capabilities.file_too_large_error import FileTooLargeError
from vibey_runners.common.capabilities.frontmatter import SkillFrontmatter
from vibey_runners.common.capabilities.frontmatter_error import FrontmatterError
from vibey_runners.common.capabilities.git_folder_guard import GitFolderGuard
from vibey_runners.common.capabilities.interfaces.file_reader_interface import (
    FileReaderInterface,
)
from vibey_runners.common.capabilities.interfaces.frontmatter_interface import (
    SkillFrontmatterInterface,
)
from vibey_runners.common.capabilities.interfaces.git_folder_guard_interface import (
    GitFolderGuardInterface,
)
from vibey_runners.common.capabilities.names import NAME_PATTERN
from vibey_runners.common.capabilities.skill_catalog import SkillCatalog
from vibey_runners.common.capabilities.skill_entry import SkillEntry

SKILL_FILE: Final = "SKILL.md"
SKILL_MAX_BYTES: Final = 64 * 1024
"""The largest SKILL.md indexed (the plan's 64 KiB). vibey's largest is well under it."""
MAX_SKILLS_PER_PLUGIN: Final = 256
"""The most skill folders of one plugin looked at; the rest are one skipped row."""
OUTSIDE: Final = "outside the marketplace"
INSIDE_GIT: Final = "inside a .git folder"
"""The lock leaves the marketplace root's `.git` out of its digest, and the index cannot tell a
plugin's own folder from the root, so no path through a `.git` below a plugin is read at all."""


class SkillIndex:
    """Declared by `interfaces/skill_index_interface.py::SkillIndexInterface`."""

    def __init__(
        self,
        reader: FileReaderInterface | None = None,
        frontmatter: SkillFrontmatterInterface | None = None,
        guard: GitFolderGuardInterface | None = None,
    ) -> None:
        self._reader = reader or BoundedFileReader()
        self._guard = guard or GitFolderGuard()
        self._frontmatter = frontmatter or SkillFrontmatter()

    def build(self, plugin_dirs: Sequence[Path]) -> SkillCatalog:
        skills: list[SkillEntry] = []
        skipped: list[tuple[Path, str]] = []
        for plugin_dir in plugin_dirs:
            try:
                self._plugin(plugin_dir, skills, skipped)
            except (OSError, RuntimeError) as exc:  # RuntimeError: a symlink loop on 3.12
                skipped.append((plugin_dir, f"cannot be read: {exc}"))
        return SkillCatalog(tuple(skills), tuple(skipped))

    def _plugin(
        self, plugin_dir: Path, skills: list[SkillEntry], skipped: list[tuple[Path, str]]
    ) -> None:
        base = plugin_dir.resolve()
        if not base.is_dir():
            skipped.append((plugin_dir, "the plugin folder does not exist"))
            return
        folder = plugin_dir / "skills"
        resolved = folder.resolve()
        reason = self._unsafe(resolved, base)
        if reason:
            skipped.append((folder, reason))
            return
        if not resolved.is_dir():
            return
        names: set[str] = set()
        # One scan, classified from the directory entry (no stat for a plain file or folder;
        # a symlink is followed). Only skill folders count toward the limit, so stray files
        # cannot crowd skills out; folders past it are one skipped row, never stat'ed again.
        folders: list[Path] = []
        with os.scandir(resolved) as scan:
            for listed in scan:
                try:
                    if listed.is_dir():  # a symlink to itself raises ELOOP here
                        folders.append(Path(listed.path))
                except OSError as exc:
                    skipped.append((Path(listed.path), f"cannot be read: {exc}"))
        folders.sort()
        if len(folders) > MAX_SKILLS_PER_PLUGIN:
            over = len(folders) - MAX_SKILLS_PER_PLUGIN
            skipped.append(
                (
                    resolved,
                    f"{over} more skill folders past the {MAX_SKILLS_PER_PLUGIN}-folder limit "
                    "of one plugin",
                )
            )
        candidates = folders[:MAX_SKILLS_PER_PLUGIN]
        for skill_dir in candidates:
            try:
                entry, reason, where = self._skill(plugin_dir.name, base, skill_dir)
            except (OSError, RuntimeError) as exc:  # e.g. a skill folder that cannot be searched
                entry, reason, where = None, f"cannot be read: {exc}", skill_dir
            if entry is not None and entry.name in names:
                reason = f"names the skill {entry.name} twice in {plugin_dir.name}"
                entry = None
            if entry is None:
                skipped.append((where, reason))
                continue
            names.add(entry.name)
            skills.append(entry)

    def _unsafe(self, resolved: Path, base: Path) -> str:
        """Why `resolved` may not be read for the plugin at `base`, or "" when it may."""
        if not resolved.is_relative_to(base):
            return OUTSIDE
        if self._guard.inside(base, resolved, any_depth=True):
            return INSIDE_GIT
        return ""

    def _skill(
        self, plugin: str, base: Path, skill_dir: Path
    ) -> tuple[SkillEntry | None, str, Path]:
        """The entry, or None with the reason and the path the reason is about."""
        reason = self._unsafe(skill_dir.resolve(), base)
        if reason:
            return None, reason, skill_dir
        path = (skill_dir / SKILL_FILE).resolve()
        reason = self._unsafe(path, base)
        if reason:
            return None, reason, skill_dir / SKILL_FILE
        if not path.is_file():
            return None, f"has no {SKILL_FILE}", skill_dir
        try:
            text = self._reader.read_text(path, SKILL_MAX_BYTES)
            meta = self._frontmatter.parse(text)
        except FileTooLargeError:
            return None, f"is larger than {SKILL_MAX_BYTES} bytes", path
        except UnicodeDecodeError:
            return None, "is not UTF-8", path
        except FrontmatterError as exc:
            return None, str(exc), path
        except OSError as exc:
            return None, f"cannot be read: {exc}", path
        name = meta.get("name", "").strip()
        description = meta.get("description", "").strip()
        if not name:
            return None, "frontmatter has no name", path
        if NAME_PATTERN.fullmatch(name) is None:
            return None, f"frontmatter name {name!r} is not a plain name", path
        if not description:
            return None, "frontmatter has no description", path
        return SkillEntry(plugin, name, description, path), "", path
