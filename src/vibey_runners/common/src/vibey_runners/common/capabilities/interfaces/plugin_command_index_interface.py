# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over the commands a set of plugins holds (SP-LOOPS Phase 5, R10)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey_runners.common.capabilities.command_entry import CommandEntry


@runtime_checkable
class PluginCommandIndexInterface(Protocol):
    def build(
        self, plugin_dirs: Sequence[Path]
    ) -> tuple[tuple[CommandEntry, ...], tuple[tuple[Path, str], ...]]:
        """Every command in `<plugin>/commands/*.md` (not below it) across `plugin_dirs`, in
        the order given and then by file name, each with a one-line description: the
        frontmatter's, or else the first non-blank line. Then (path, reason) for each file or
        folder that was skipped -- outside its plugin, inside a .git folder, too large, not
        UTF-8, unreadable, not plainly named, or without a description; nothing raises."""
        ...
