# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where `vibey state` syncs to, with what, and from which database (ADR-0086).

Every setting is an environment variable, `VIBEY_STATE_*`, with the default
`StateSyncSettings` declares (docs/reference/configuration.md#state-sync):

- `VIBEY_STATE_REPOSITORY` -- OWNER/NAME; empty: the working directory's GitHub repository.
- `VIBEY_STATE_BRANCH` -- the branch the sealed state lives on (`vibey-state`).
- `VIBEY_STATE_PATH` -- the file on that branch (`state.vibey`).
- `VIBEY_STATE_PG_URL` -- the database to sync; empty: `VIBEY_PG_URL`. The sync writes every
  synced table, so this role needs more than the application role's grants (ADR-0055):
  give it its own DSN rather than widening the one the worker holds.
- `VIBEY_STATE_KEY` -- the key itself; empty: the keychain, then `VIBEY_STATE_KEY_FILE`.
- `VIBEY_STATE_KEY_FILE` -- empty: `$XDG_CONFIG_HOME/vibey/state.key`.
- `VIBEY_STATE_CONFLICTS` -- `table=rule,...` over the declared rules
  (`vibey.domain.state_sync.TABLES`): `newest`, `mine`, `theirs` or `refuse`.
- `VIBEY_STATE_ATTEMPTS` -- how many times one sync starts again when an end moved (5).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from vibey.domain.state_sync import ConflictRules, TableSpec
from vibey.infrastructure.state.interfaces.settings_interface import (
    StateSyncSettingsInterface,
    StateSyncSettingsLoaderInterface,
)


@dataclass(frozen=True)
class StateSyncSettings(StateSyncSettingsInterface):
    """Declared by `interfaces/settings_interface.py::StateSyncSettingsInterface`."""

    repository: str = ""
    branch: str = "vibey-state"
    path: str = "state.vibey"
    pg_url: str = ""
    key: str = ""
    key_file: str = ""
    tables: tuple[TableSpec, ...] = ()
    attempts: int = 5


class StateSyncSettingsLoader(StateSyncSettingsLoaderInterface):
    """Reads `VIBEY_STATE_*`. Declared by
    `interfaces/settings_interface.py::StateSyncSettingsLoaderInterface`."""

    PREFIX: Final[str] = "VIBEY_STATE_"

    def load(self, environ: Mapping[str, str]) -> StateSyncSettings:
        defaults = StateSyncSettings()

        def text(name: str, default: str) -> str:
            return environ.get(self.PREFIX + name, "").strip() or default

        attempts_text = text("ATTEMPTS", str(defaults.attempts))
        try:
            attempts = int(attempts_text)
        except ValueError:
            raise ValueError(f"{self.PREFIX}ATTEMPTS must be a whole number") from None
        if attempts < 1:
            raise ValueError(f"{self.PREFIX}ATTEMPTS must be at least 1")
        branch = text("BRANCH", defaults.branch)
        if branch.startswith("-") or ".." in branch or " " in branch:
            raise ValueError(f"{self.PREFIX}BRANCH is not a branch name: {branch!r}")
        config_home = environ.get("XDG_CONFIG_HOME", "").strip() or str(
            Path(environ.get("HOME", "~")).expanduser() / ".config"
        )
        return StateSyncSettings(
            repository=text("REPOSITORY", defaults.repository),
            branch=branch,
            path=text("PATH", defaults.path),
            pg_url=text("PG_URL", environ.get("VIBEY_PG_URL", "").strip()),
            key=text("KEY", ""),
            key_file=text("KEY_FILE", str(Path(config_home) / "vibey" / "state.key")),
            tables=ConflictRules().apply(text("CONFLICTS", "")),
            attempts=attempts,
        )
