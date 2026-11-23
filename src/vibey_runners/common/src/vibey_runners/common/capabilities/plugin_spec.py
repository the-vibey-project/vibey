# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One plugin, written `name@marketplace` in `[loops] plugins`. A record with no behaviour, so no
seam of its own."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PluginSpec:
    name: str
    marketplace: str
