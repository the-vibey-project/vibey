# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[loops]`: what every loop is given, as the person grants it (SP-LOOPS Task 3).

The same two-file trust split as `[acp]`, `[web]` and `[hub]` (ADR-0101; their
`load_trusted(user, project)`): the person's own `vibey.toml` -- `bootstrap.acp_user_config()`,
in their configuration folder (`user_config_path("vibey")`) -- holds the powers, and the
`vibey.toml` of the folder a run starts in may be a cloned repository's, so it may only narrow.
For `[loops]` narrowing is one key, `disable`, held to the same rule as the person's own list
(`BundleSpec.disable_names`: at most 256 plain names, each once). Every other key a project
carries is dropped and named in a notice, never applied. A notice quotes the project's key with
`ascii()` and cuts it at `MAX_NOTICE_KEY_CHARS`, and at most `MAX_NOTICES` keys are named, so a
cloned repository cannot write terminal control sequences or an unbounded wall of text through
it. A project file that is absent, or that is the person's own file, changes nothing.

This is the trust rule only. The tables arrive through `TrustedTableReaderInterface`, which
infrastructure implements and `bootstrap.py` wires, so this module reads no file. Every refusal
is a `ConfigError` naming the file. Declared by
`interfaces/loops_bundle_settings_interface.py::LoopsBundleSettingsInterface`.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Final

from vibey_runners.common.capabilities.bundle import BundleSpec
from vibey_runners.common.capabilities.bundle_error import BundleError

from vibey.application.dto import TrustedLoopsBundle
from vibey.application.interfaces.trusted_table_reader_interface import (
    TrustedTableReaderInterface,
)
from vibey.domain.config import ConfigError

TABLE: Final = "loops"
PROJECT_KEYS: Final = frozenset({"disable"})
"""The only `[loops]` keys a project's file is heard on."""
MAX_NOTICES: Final = 16
"""The most ignored project keys named one by one; the rest are counted in one more notice."""
MAX_NOTICE_KEY_CHARS: Final = 64
"""The longest a quoted project key may be in a notice."""


class LoopsBundleSettings:
    """Declared by `interfaces/loops_bundle_settings_interface.py`."""

    def __init__(self, reader: TrustedTableReaderInterface) -> None:
        self._reader = reader

    def load(self, user_config: Path, project_config: Path | None) -> TrustedLoopsBundle:
        mine = self._bundle(user_config)
        if project_config is None or self._reader.same_file(project_config, user_config):
            return TrustedLoopsBundle(mine)
        table = self._reader.read_table(project_config, TABLE)
        if table is None:
            return TrustedLoopsBundle(mine)
        try:
            disable = BundleSpec.disable_names(table.get("disable", []))
        except BundleError as exc:
            raise ConfigError(str(project_config), str(exc)) from exc
        ignored = sorted(set(table) - PROJECT_KEYS)
        notices = [
            f"{project_config}: [{TABLE}] {self._quoted(key)} is ignored; a project may only "
            f"disable, and what a loop is given comes from your own vibey.toml ({user_config})"
            for key in ignored[:MAX_NOTICES]
        ]
        if len(ignored) > MAX_NOTICES:
            more = len(ignored) - MAX_NOTICES
            notices.append(f"{project_config}: and {more} more [{TABLE}] keys are ignored")
        return TrustedLoopsBundle(mine.narrowed_by(disable), tuple(notices))

    def _bundle(self, path: Path) -> BundleSpec:
        table: Mapping[str, object] = self._reader.read_table(path, TABLE) or {}
        try:
            return BundleSpec.from_mapping(table)
        except BundleError as exc:
            raise ConfigError(str(path), str(exc)) from exc

    @staticmethod
    def _quoted(key: str) -> str:
        """`key` as a printable ASCII literal, cut to `MAX_NOTICE_KEY_CHARS`."""
        quoted = ascii(key)
        if len(quoted) <= MAX_NOTICE_KEY_CHARS:
            return quoted
        return quoted[: MAX_NOTICE_KEY_CHARS - 4] + "...'"
