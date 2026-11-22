# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[web]`: the hub's web tools' budgets, hosts and bounds, read from the person's own `vibey.toml`
and narrowed by a project's (ADR-0102, ADR-0018).

The person grants: their own file (`bootstrap.acp_user_config()`, in their configuration folder)
sets every key. The `vibey.toml` of the folder the hub was started in may belong to a cloned
repository, so it is not the person's word: it may only tighten (`domain/web_tools.py`'s
`WebToolTrust`). Only `[web]` is read; every value is checked, and a file or key that cannot be
read is refused naming the file and the key, never ignored.

Declared by `interfaces/web_settings_loader_interface.py`.
"""

import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from vibey.domain.config import ConfigError
from vibey.domain.interfaces.web_tools_interface import WebToolTrustInterface
from vibey.domain.web_tools import WEB_TOOL_TRUST, WebToolSettings

_INTEGERS: Final = (
    "searches_per_hour",
    "fetches_per_hour",
    "max_bytes",
    "max_chars",
    "max_redirects",
)
_HOST_LISTS: Final = ("allow_hosts", "deny_hosts")
KEYS: Final = frozenset({*_INTEGERS, *_HOST_LISTS, "timeout_seconds", "content_types"})
"""Every `[web]` key; `tests/meta/test_web_settings_documented.py` holds the reference to it."""


class WebToolSettingsLoader:
    """Declared by `interfaces/web_settings_loader_interface.py::WebToolSettingsLoaderInterface`."""

    def __init__(self, trust: WebToolTrustInterface = WEB_TOOL_TRUST) -> None:
        self._trust = trust

    def load(self, path: Path) -> WebToolSettings:
        return self._build(self._table(path), str(path))

    def load_trusted(self, user: Path, project: Path) -> WebToolSettings:
        mine = self.load(user)
        if not project.exists() or project.resolve() == user.resolve():
            return mine
        table = self._table(project)
        return self._trust.merge(mine, self._build(table, str(project)), frozenset(table))

    @staticmethod
    def _table(path: Path) -> Mapping[str, object]:
        if not path.exists():
            return {}
        try:
            with path.open("rb") as handle:
                document = tomllib.load(handle)
        except OSError as exc:
            raise ConfigError(str(path), f"cannot be read: {exc}") from exc
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(str(path), f"is not valid TOML: {exc}") from exc
        section = document.get("web", {})
        if not isinstance(section, Mapping):
            raise ConfigError(str(path), "[web] must be a table")
        return section

    @staticmethod
    def _build(section: Mapping[str, object], source: str) -> WebToolSettings:
        unknown = sorted(set(section) - KEYS)
        if len(unknown) == 1:
            raise ConfigError(source, f"[web] {unknown[0]} is not a known key")
        if unknown:
            raise ConfigError(source, f"[web] {', '.join(unknown)} are not known keys")
        values: dict[str, object] = {}
        for key, value in section.items():
            if key in _HOST_LISTS or key == "content_types":
                if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                    what = "host names" if key in _HOST_LISTS else "type/subtype strings"
                    raise ConfigError(source, f"[web] {key} must be a list of {what}")
                values[key] = tuple(value)
            else:
                values[key] = value
        try:
            # Every value's type and range is checked by the settings themselves.
            return WebToolSettings(**values)  # type: ignore[arg-type]
        except (ValueError, TypeError) as exc:
            raise ConfigError(source, str(exc)) from exc


WEB_SETTINGS: Final = WebToolSettingsLoader()
"""The loader the hub and `vibey doctor` read `[web]` with."""
