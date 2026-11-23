# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over the skills a set of plugins holds (SP-LOOPS Task 4)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey_runners.common.capabilities.skill_catalog import SkillCatalog


@runtime_checkable
class SkillIndexInterface(Protocol):
    def build(self, plugin_dirs: Sequence[Path]) -> SkillCatalog:
        """Every skill in `<plugin>/skills/*/SKILL.md` across `plugin_dirs`, in the order given
        and then by folder name, read from frontmatter only. A skills folder, skill folder or
        SKILL.md that resolves outside its plugin, an oversized or unreadable file and a
        malformed frontmatter are each in `skipped` with a reason; nothing raises."""
        ...
