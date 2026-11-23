# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The person's own configuration folder: where their `vibey.toml` and vibey's per-person files
live, never the folder vibey happens to run in (ADR-0101, ADR-0102).

`~/Library/Application Support/vibey` on macOS, `$XDG_CONFIG_HOME/vibey` elsewhere. A relative
`XDG_CONFIG_HOME` would put "the person's" folder inside whatever folder vibey runs in -- a
project's -- so it is refused for `~/.config/vibey`, as `SupervisorHost` refuses it for its own
paths. `bootstrap.acp_user_config` and the SearXNG vibey provisions both use this rule.

Declared by `interfaces/user_config_folder_interface.py`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from platformdirs import user_config_path


class UserConfigFolder:
    """Declared by `UserConfigFolderInterface`. `lookup` defaults to platformdirs'
    `user_config_path`, read when `path` is asked (so a test may stand in for it)."""

    def __init__(self, lookup: Callable[[str], Path] | None = None) -> None:
        self._lookup = lookup

    def path(self) -> Path:
        folder = Path((self._lookup or user_config_path)("vibey"))
        if not folder.is_absolute():
            folder = Path.home() / ".config" / "vibey"
        return folder

    def vibey_toml(self) -> Path:
        """The person's own `vibey.toml`: the one place `bootstrap.acp_user_config`, the MCP
        gateway, `vibey hub` and `vibey fetch` find it (SP-ACP Task 11a, review 1 N-6)."""
        return self.path() / "vibey.toml"
