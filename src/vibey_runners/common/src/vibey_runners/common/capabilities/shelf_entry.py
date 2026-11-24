# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One thing on a run's skill shelf: a skill or a plugin command, by its qualified name
(`plugin:name`), with its one-line description and the file its text is read from (SP-LOOPS
Phase 5, R10). A record with no behaviour, so no seam of its own."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ShelfKind = Literal["skill", "command"]


@dataclass(frozen=True, slots=True)
class ShelfEntry:
    name: str
    kind: ShelfKind
    description: str
    path: Path
