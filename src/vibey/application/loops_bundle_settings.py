# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[loops]`: what every loop is given, as the person grants it (SP-LOOPS Task 3).

The same two-file trust split as `[acp]`, `[web]` and `[hub]` (ADR-0101; their
`load_trusted(user, project)`): the person's own `vibey.toml` -- `bootstrap.acp_user_config()`,
in their configuration folder (`user_config_path("vibey")`) -- holds the powers, and the
`vibey.toml` of the folder a run starts in may be a cloned repository's, so it may only narrow.
For `[loops]` narrowing is one key, `disable`: a project may switch off plugins, MCP servers and
skills by name, and every other key it carries (a marketplace, a plugin, a server) is dropped
and named in a notice, never applied. A project file that is absent, or that is the person's own
file, changes nothing.

The TOML is parsed by the one parser the inner layers share (`domain.config.parse_toml_string`)
and every refusal is a `ConfigError` naming the file, as for the other trusted tables. The bundle
schema itself is the family's (`vibey_runners.common.capabilities.bundle`), so the conductor and
the runners read one definition. Declared by
`interfaces/loops_bundle_settings_interface.py::LoopsBundleSettingsInterface`.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Final

from vibey_runners.common.capabilities.bundle import BundleSpec
from vibey_runners.common.capabilities.bundle_error import BundleError

from vibey.application.dto import TrustedLoopsBundle
from vibey.domain.config import ConfigError, parse_toml_string

TABLE: Final = "loops"
PROJECT_KEYS: Final = frozenset({"disable"})
"""The only `[loops]` keys a project's file is heard on."""


class LoopsBundleSettings:
    """Declared by `interfaces/loops_bundle_settings_interface.py`."""

    def load(self, user_config: Path, project_config: Path | None) -> TrustedLoopsBundle:
        mine = self._bundle(user_config)
        if (
            project_config is None
            or not project_config.exists()
            or project_config.resolve() == user_config.resolve()
        ):
            return TrustedLoopsBundle(mine)
        table = self._table(project_config)
        notices = tuple(
            f"{project_config}: [{TABLE}] {key} is ignored; a project may only disable, and "
            f"what a loop is given comes from your own vibey.toml ({user_config})"
            for key in sorted(set(table) - PROJECT_KEYS)
        )
        disable = self._disable(table.get("disable", []), project_config)
        return TrustedLoopsBundle(mine.narrowed_by(disable), notices)

    def _bundle(self, path: Path) -> BundleSpec:
        try:
            return BundleSpec.from_mapping(self._table(path))
        except BundleError as exc:
            raise ConfigError(str(path), str(exc)) from exc

    @staticmethod
    def _table(path: Path) -> Mapping[str, object]:
        if not path.exists():
            return {}
        try:
            document = parse_toml_string(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ConfigError(str(path), f"cannot be read: {exc}") from exc
        except ValueError as exc:  # a TOMLDecodeError, or bytes that are not UTF-8
            raise ConfigError(str(path), f"is not valid TOML: {exc}") from exc
        section = document.get(TABLE, {})
        if not isinstance(section, Mapping):
            raise ConfigError(str(path), f"[{TABLE}] must be a table")
        return section

    @staticmethod
    def _disable(value: object, path: Path) -> tuple[str, ...]:
        if not isinstance(value, list) or not all(isinstance(name, str) for name in value):
            raise ConfigError(str(path), f"[{TABLE}] disable must be a list of names")
        return tuple(value)
