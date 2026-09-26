# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads `[failover]` from `vibey.toml` (ADR-0070; docs/reference/configuration.md).

Every key is optional and each one's default is `FailoverSettings`'s. An unknown key
or a value of the wrong type is refused by name rather than ignored, so a typo never
silently reverts a setting to its default.
"""

import tomllib
from collections.abc import Mapping
from datetime import timedelta
from pathlib import Path
from typing import Final

from vibey.domain.effort import Effort
from vibey.domain.failover import FailoverSettings

_ARGV_KEYS: Final = ("sovereign_argv", "sovereign_wind_down_argv", "probe_argv", "resume_argv")
_KNOWN: Final = frozenset(
    {"enabled", "target_engine", "target_effort", "probe_interval_seconds", *_ARGV_KEYS}
)


class FailoverSettingsLoader:
    """Declared by `interfaces/settings_loader_interface.py`."""

    def load(self, path: Path) -> FailoverSettings:
        if not path.exists():
            return FailoverSettings()
        with path.open("rb") as handle:
            section = tomllib.load(handle).get("failover", {})
        if not isinstance(section, Mapping):
            raise ValueError("[failover] must be a table")
        return self.from_mapping(section)

    def from_mapping(self, section: Mapping[str, object]) -> FailoverSettings:
        unknown = sorted(set(section) - _KNOWN)
        if unknown:
            raise ValueError(f"[failover] has unknown keys: {', '.join(unknown)}")
        kwargs: dict[str, object] = {}
        if "enabled" in section:
            kwargs["enabled"] = self._typed(section, "enabled", bool)
        if "target_engine" in section:
            kwargs["target_engine"] = self._typed(section, "target_engine", str)
        if "target_effort" in section:
            name = str(self._typed(section, "target_effort", str)).upper()
            if name not in Effort.__members__:
                raise ValueError(f"[failover] target_effort {name!r} is not an effort")
            kwargs["target_effort"] = Effort[name]
        if "probe_interval_seconds" in section:
            seconds = self._typed(section, "probe_interval_seconds", int)
            kwargs["probe_interval"] = timedelta(seconds=int(str(seconds)))
        for key in _ARGV_KEYS:
            if key in section:
                value = section[key]
                if (
                    not isinstance(value, list)
                    or not value
                    or not all(isinstance(part, str) for part in value)
                ):
                    raise ValueError(f"[failover] {key} must be a non-empty list of strings")
                kwargs[key] = tuple(value)
        return FailoverSettings(**kwargs)  # type: ignore[arg-type]

    @staticmethod
    def _typed(section: Mapping[str, object], key: str, kind: type) -> object:
        value = section[key]
        # bool is an int subclass; an integer key never accepts true/false.
        if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
            raise ValueError(f"[failover] {key} must be a {kind.__name__}")
        return value
