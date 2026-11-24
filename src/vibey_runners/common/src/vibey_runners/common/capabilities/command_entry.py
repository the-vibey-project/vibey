# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One plugin command: the plugin that holds it, its name (the file stem of `commands/<name>.md`),
its description made one safe line, and its file (resolved, inside its plugin). Its text is read on
demand, through the skill tools, as instruction (SP-LOOPS Phase 5, R10 and R11). A record with no
behaviour, so no seam of its own."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CommandEntry:
    plugin: str
    name: str
    description: str
    path: Path
