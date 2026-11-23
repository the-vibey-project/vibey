# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every skill a set of plugins holds, and every one that was skipped with the reason. A record
with no behaviour, so no seam of its own."""

from dataclasses import dataclass
from pathlib import Path

from vibey_runners.common.capabilities.skill_entry import SkillEntry


@dataclass(frozen=True, slots=True)
class SkillCatalog:
    skills: tuple[SkillEntry, ...]
    skipped: tuple[tuple[Path, str], ...]
    """(path, reason) for each skill folder or file that is not in `skills`."""
