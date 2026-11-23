# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[inputs]`: how much a project's run inputs may hold, as the person sets it (SP-LOOPS Phase 3,
Task 3).

The same two-file trust split as `[loops]` (`loops_bundle_settings.py`, ADR-0101): the person's
own `vibey.toml` -- `bootstrap.acp_user_config()` -- holds the limits, and the `vibey.toml` of
the folder a command starts in may be a cloned repository's. For `[inputs]` a project narrows
nothing: limits are the person's to set, and a repository that could raise them could fill a
disk. So a project's `[inputs]` table is never applied, and one notice says so. The notice names
the two paths and none of the project's keys, so a cloned repository cannot put text of its own
on the person's terminal through it. A project file that cannot be read -- not TOML, too large, a
FIFO -- changes nothing either: it is named in a notice, never an error (fix round 1, R-H).

The limits are `RunInputsSettings` (`domain/run_input.py`); this module only decides whose file
they come from. The tables arrive through `TrustedTableReaderInterface`, so it reads no file.
Declared by `interfaces/run_inputs_settings_interface.py::RunInputsSettingsLoaderInterface`.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Final

from vibey.application.dto import TrustedRunInputsSettings
from vibey.application.interfaces.trusted_table_reader_interface import (
    TrustedTableReaderInterface,
)
from vibey.domain.config import ConfigError
from vibey.domain.run_input import RunInputsSettings

TABLE: Final = "inputs"

__all__ = ["TABLE", "RunInputsSettings", "RunInputsSettingsLoader"]


class RunInputsSettingsLoader:
    """Declared by `interfaces/run_inputs_settings_interface.py`."""

    def __init__(self, reader: TrustedTableReaderInterface) -> None:
        self._reader = reader

    def load(self, user_config: Path, project_config: Path | None) -> TrustedRunInputsSettings:
        table: Mapping[str, object] = self._reader.read_table(user_config, TABLE) or {}
        try:
            settings = RunInputsSettings.from_table(table)
        except ValueError as exc:
            raise ConfigError(str(user_config), str(exc)) from exc
        if project_config is None or self._reader.same_file(project_config, user_config):
            return TrustedRunInputsSettings(settings)
        try:
            project = self._reader.read_table(project_config, TABLE)
        except ConfigError:
            # A project's file is never heard on limits, so one that cannot be read changes
            # nothing either: no exit code, only this notice (fix round 1, R-H).
            notice = (
                f"{project_config}: cannot be read; it is not heard on [{TABLE}] anyway: how much "
                f"a project's run inputs may hold comes only from your own vibey.toml "
                f"({user_config})"
            )
            return TrustedRunInputsSettings(settings, (notice,))
        if not project:
            return TrustedRunInputsSettings(settings)
        notice = (
            f"{project_config}: [{TABLE}] is ignored; how much a project's run inputs may hold "
            f"comes only from your own vibey.toml ({user_config})"
        )
        return TrustedRunInputsSettings(settings, (notice,))
