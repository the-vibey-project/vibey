# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Indexes the commands a set of plugins holds, from `commands/*.md` (SP-LOOPS Phase 5, R10).

A plugin command is a markdown file directly in its plugin's `commands/` folder; folders below it
are not looked in. It is held to the skill index's rules (`SkillIndex`), with the same seams and
the same named reasons: a `commands/` folder or a command file that resolves (through a symlink)
outside its plugin is `OUTSIDE` and is never read; one through a `.git` folder below the plugin is
`INSIDE_GIT`; a file over `SKILL_MAX_BYTES`, one that is not UTF-8 and one that cannot be read
are each skipped with their reason, and so is anything the file system will not let it look at.
At most `MAX_SKILLS_PER_PLUGIN` command files of one plugin are looked at; the rest are one
skipped row. The index never raises for what a plugin contains.

The command's name is its file stem and must be a plain name (`NAME_PATTERN`). Its description is
the frontmatter's `description` when the file opens with one, or else the first non-blank line of
what follows the frontmatter (the whole file when it has none), made one safe line of at most
`DESCRIPTION_MAX_CHARS` characters (`SafeText`). A malformed frontmatter and a file with no
description at all are skipped with the reason. The text is read in full only later, on demand,
as instruction (R11). Declared by
`interfaces/plugin_command_index_interface.py::PluginCommandIndexInterface`.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from vibey_runners.common.capabilities.command_entry import CommandEntry
from vibey_runners.common.capabilities.file_reader import BoundedFileReader
from vibey_runners.common.capabilities.file_too_large_error import FileTooLargeError
from vibey_runners.common.capabilities.frontmatter import FENCE, SkillFrontmatter
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
from vibey_runners.common.capabilities.interfaces.path_probe_interface import PathProbeInterface
from vibey_runners.common.capabilities.names import NAME_PATTERN
from vibey_runners.common.capabilities.path_probe import PathProbe
from vibey_runners.common.capabilities.resolver import DESCRIPTION_MAX_CHARS
from vibey_runners.common.capabilities.safe_text import SafeText
from vibey_runners.common.capabilities.skill_index import (
    INSIDE_GIT,
    MAX_SKILLS_PER_PLUGIN,
    OUTSIDE,
    SKILL_MAX_BYTES,
)

COMMANDS_FOLDER: Final = "commands"
COMMAND_SUFFIX: Final = ".md"


class PluginCommandIndex:
    """Declared by `interfaces/plugin_command_index_interface.py::PluginCommandIndexInterface`."""

    def __init__(
        self,
        reader: FileReaderInterface | None = None,
        frontmatter: SkillFrontmatterInterface | None = None,
        guard: GitFolderGuardInterface | None = None,
        probe: PathProbeInterface | None = None,
    ) -> None:
        self._reader = reader or BoundedFileReader()
        self._frontmatter = frontmatter or SkillFrontmatter()
        self._guard = guard or GitFolderGuard()
        # The same answer on every Python, as in `SkillIndex`: a folder that cannot be searched
        # raises, and is named as a skipped row, never read as missing.
        self._probe = probe or PathProbe()
        self._text = SafeText()

    def build(
        self, plugin_dirs: Sequence[Path]
    ) -> tuple[tuple[CommandEntry, ...], tuple[tuple[Path, str], ...]]:
        commands: list[CommandEntry] = []
        skipped: list[tuple[Path, str]] = []
        for plugin_dir in plugin_dirs:
            try:
                self._plugin(plugin_dir, commands, skipped)
            except OSError as exc:  # a folder the file system will not let it look at
                skipped.append((plugin_dir, f"cannot be read: {exc}"))
        return tuple(commands), tuple(skipped)

    def _plugin(
        self, plugin_dir: Path, commands: list[CommandEntry], skipped: list[tuple[Path, str]]
    ) -> None:
        base = self._probe.real(plugin_dir)
        if not self._probe.is_dir(base):
            skipped.append((plugin_dir, "the plugin folder does not exist"))
            return
        folder = plugin_dir / COMMANDS_FOLDER
        resolved = self._probe.real(folder)
        reason = self._unsafe(resolved, base)
        if reason:
            skipped.append((folder, reason))
            return
        if not self._probe.is_dir(resolved):
            return
        # One scan, classified from the directory entry (a symlink is followed); only command
        # files count toward the limit, and files past it are one skipped row.
        files: list[Path] = []
        with os.scandir(resolved) as scan:
            for listed in scan:
                if not listed.name.endswith(COMMAND_SUFFIX):
                    continue
                try:
                    if listed.is_file():  # a symlink to itself raises ELOOP here
                        files.append(Path(listed.path))
                except OSError as exc:
                    skipped.append((Path(listed.path), f"cannot be read: {exc}"))
        files.sort()
        if len(files) > MAX_SKILLS_PER_PLUGIN:
            over = len(files) - MAX_SKILLS_PER_PLUGIN
            skipped.append(
                (
                    resolved,
                    f"{over} more command files past the {MAX_SKILLS_PER_PLUGIN}-file limit "
                    "of one plugin",
                )
            )
        for listed_file in files[:MAX_SKILLS_PER_PLUGIN]:
            try:
                entry, reason, where = self._command(plugin_dir.name, base, listed_file)
            except OSError as exc:  # e.g. a commands folder that cannot be searched
                entry, reason, where = None, f"cannot be read: {exc}", listed_file
            if entry is None:
                skipped.append((where, reason))
            else:
                commands.append(entry)

    def _unsafe(self, resolved: Path, base: Path) -> str:
        """Why `resolved` may not be read for the plugin at `base`, or "" when it may."""
        if not resolved.is_relative_to(base):
            return OUTSIDE
        if self._guard.inside(base, resolved, any_depth=True):
            return INSIDE_GIT
        return ""

    def _command(
        self, plugin: str, base: Path, listed: Path
    ) -> tuple[CommandEntry | None, str, Path]:
        """The entry, or None with the reason and the path the reason is about."""
        path = self._probe.real(listed)
        reason = self._unsafe(path, base)
        if reason:
            return None, reason, listed
        name = listed.name.removesuffix(COMMAND_SUFFIX)
        if NAME_PATTERN.fullmatch(name) is None:
            return None, f"the command name {name!r} is not a plain name", path
        if not self._probe.is_file(path):
            return None, "is not a regular file", path
        try:
            text = self._reader.read_text(path, SKILL_MAX_BYTES)
            description = self._description(text)
        except FileTooLargeError:
            return None, f"is larger than {SKILL_MAX_BYTES} bytes", path
        except UnicodeDecodeError:
            return None, "is not UTF-8", path
        except FrontmatterError as exc:
            return None, str(exc), path
        except OSError as exc:
            return None, f"cannot be read: {exc}", path
        if not description:
            return None, "has no description", path
        return CommandEntry(plugin, name, description, path), "", path

    def _description(self, text: str) -> str:
        """The frontmatter's description, or the first non-blank line after it, as one safe
        line; "" when there is neither. Raises `FrontmatterError` for a malformed one."""
        lines = text.lstrip("﻿").replace("\r\n", "\n").split("\n")
        description = ""
        if lines[0].rstrip() == FENCE:
            description = self._frontmatter.parse(text).get("description", "")
            # The parse succeeded, so the closing fence is there.
            end = next(i for i in range(1, len(lines)) if lines[i].rstrip() == FENCE)
            lines = lines[end + 1 :]
        if not description.strip():
            description = next((line for line in lines if line.strip()), "")
        return self._text.clean(description, DESCRIPTION_MAX_CHARS)
