# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The person's own state folder: where vibey keeps per-person state that is not configuration,
never the folder vibey happens to run in (SP-LOOPS Phase 3, fix round 1: R-A).

`~/Library/Application Support/vibey` on macOS, `$XDG_STATE_HOME/vibey` elsewhere -- the same
platformdirs root the hub's default `state_dir` sits under (`<this>/hub`). A relative
`XDG_STATE_HOME` would put "the person's" folder inside whatever folder vibey runs in -- a
project's -- so it is refused for `~/.local/state/vibey`, the rule `UserConfigFolder` holds the
configuration folder to. Run inputs live in `inputs/<project id>` below it.

Declared by `interfaces/user_state_folder_interface.py`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from platformdirs import user_state_path


class UserStateFolder:
    """Declared by `UserStateFolderInterface`. `lookup` defaults to platformdirs'
    `user_state_path`, read when `path` is asked (so a test may stand in for it)."""

    def __init__(self, lookup: Callable[[str], Path] | None = None) -> None:
        self._lookup = lookup

    def path(self) -> Path:
        folder = Path((self._lookup or user_state_path)("vibey"))
        if not folder.is_absolute():
            folder = Path.home() / ".local" / "state" / "vibey"
        return folder

    def inputs(self) -> Path:
        return self.path() / "inputs"
