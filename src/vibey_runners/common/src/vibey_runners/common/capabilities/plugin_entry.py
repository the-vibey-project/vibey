# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One plugin a marketplace lists: its name, its folder (resolved, inside the marketplace) and
its description. A record with no behaviour, so no seam of its own."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PluginEntry:
    name: str
    directory: Path
    description: str
