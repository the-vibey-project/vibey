# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What one marketplace offers: its plugins by name, and every plugin it lists that cannot be used
here, each with the reason (a remote source, a folder that is not there). A record with no
behaviour, so no seam of its own."""

from collections.abc import Mapping
from dataclasses import dataclass

from vibey_runners.common.capabilities.plugin_entry import PluginEntry


@dataclass(frozen=True, slots=True, eq=True)
class MarketplaceCatalog:
    plugins: Mapping[str, PluginEntry]
    skipped: tuple[tuple[str, str], ...]
    """(plugin name, reason) for each listed plugin that is not in `plugins`."""
