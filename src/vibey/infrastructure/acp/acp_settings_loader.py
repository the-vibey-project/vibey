# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[acp]` read from `vibey.toml`, bounded key by key (SP-ACP, ADR-0018).

Mirrors `SupervisorSettingsLoader`: every key is optional and its default is
`AcpSettings`'s, and an unknown key or a value of the wrong type or outside its bound is
refused by name as a `ConfigError` instead of ignored, so a typo never silently reverts a
setting to its default. Declared by `interfaces/acp_settings_loader_interface.py`.
"""

import math
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from vibey.domain.acp.settings import (
    FLOAT_MINIMA,
    INSTALL_POSTGRES_CHOICES,
    INTEGER_MINIMA,
    KNOWN_MODES,
    KNOWN_SERVICES,
    RESTART_POLICIES,
    AcpSettings,
    InvalidAcpSettings,
)
from vibey.domain.config import ConfigError

_BOOLEANS: Final = ("auto_bootstrap", "auto_connect", "auto_services", "live_between_turns")
_STRINGS: Final = ("service_workdir",)
_CHOICES: Final[Mapping[str, tuple[str, ...]]] = {
    "install_postgres": INSTALL_POSTGRES_CHOICES,
    "restart": RESTART_POLICIES,
}
_SUBSETS: Final[Mapping[str, tuple[str, ...]]] = {
    "services": KNOWN_SERVICES,
    "modes": KNOWN_MODES,
}
_STRING_LISTS: Final = ("reject_words",)
_KNOWN: Final = frozenset(
    {
        *_BOOLEANS,
        *_STRINGS,
        *INTEGER_MINIMA,
        *FLOAT_MINIMA,
        *_CHOICES,
        *_SUBSETS,
        *_STRING_LISTS,
        "default_mode",
    }
)
_TABLE_SOURCE: Final = "vibey.toml"
"""The source a refusal names when the table arrives as a mapping and not from a file."""


class AcpSettingsLoader:
    """Declared by `interfaces/acp_settings_loader_interface.py`."""

    def load(self, path: Path) -> AcpSettings:
        if not path.exists():
            return AcpSettings()
        try:
            with path.open("rb") as handle:
                document = tomllib.load(handle)
        except OSError as exc:
            raise ConfigError(str(path), f"cannot be read: {exc}") from exc
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(str(path), f"is not valid TOML: {exc}") from exc
        section = document.get("acp", {})
        if not isinstance(section, Mapping):
            raise ConfigError(str(path), "[acp] must be a table")
        return self._build(section, str(path))

    def from_mapping(self, section: Mapping[str, object]) -> AcpSettings:
        return self._build(section, _TABLE_SOURCE)

    def _build(self, section: Mapping[str, object], source: str) -> AcpSettings:
        unknown = sorted(set(section) - _KNOWN)
        if len(unknown) == 1:
            raise ConfigError(source, f"[acp] {unknown[0]} is not a known key")
        if unknown:
            raise ConfigError(source, f"[acp] {', '.join(unknown)} are not known keys")
        kwargs: dict[str, object] = {}
        for key, value in section.items():
            kwargs[key] = self._value(key, value, source)
        try:
            # kwargs is keyed by names _KNOWN admits and valued by the per-key checks above;
            # mypy cannot see through the table, so the unpacking is typed loosely.
            return AcpSettings(**kwargs)  # type: ignore[arg-type]
        except InvalidAcpSettings as exc:
            raise ConfigError(source, f"[acp] {exc}") from exc

    def _value(self, key: str, value: object, source: str) -> object:
        if key in _BOOLEANS:
            return self._boolean(key, value, source)
        if key in _STRINGS or key == "default_mode":
            return self._string(key, value, source)
        if key in INTEGER_MINIMA:
            return self._integer(key, value, INTEGER_MINIMA[key], source)
        if key in FLOAT_MINIMA:
            return self._float(key, value, FLOAT_MINIMA[key], source)
        if key in _CHOICES:
            return self._choice(key, value, _CHOICES[key], source)
        if key in _SUBSETS:
            return self._subset(key, value, _SUBSETS[key], source)
        return self._reject_words(key, value, source)

    @staticmethod
    def _boolean(key: str, value: object, source: str) -> bool:
        if not isinstance(value, bool):
            raise ConfigError(source, f"[acp] {key} must be a boolean")
        return value

    @staticmethod
    def _string(key: str, value: object, source: str) -> str:
        if not isinstance(value, str):
            raise ConfigError(source, f"[acp] {key} must be a string")
        return value

    @staticmethod
    def _integer(key: str, value: object, minimum: int, source: str) -> int:
        # bool is an int subclass; an integer key never accepts true/false.
        if not isinstance(value, int) or isinstance(value, bool):
            raise ConfigError(source, f"[acp] {key} must be an integer")
        if value < minimum:
            raise ConfigError(source, f"[acp] {key} must be at least {minimum}, not {value}")
        return value

    @staticmethod
    def _float(key: str, value: object, minimum: float, source: str) -> float:
        if not isinstance(value, int | float) or isinstance(value, bool):
            raise ConfigError(source, f"[acp] {key} must be a number")
        if not math.isfinite(value):
            raise ConfigError(source, f"[acp] {key} must be a finite number, not {value}")
        if value < minimum:
            raise ConfigError(source, f"[acp] {key} must be at least {minimum}, not {value}")
        return float(value)

    @staticmethod
    def _choice(key: str, value: object, choices: tuple[str, ...], source: str) -> str:
        if not isinstance(value, str) or value not in choices:
            raise ConfigError(source, f"[acp] {key} must be one of {', '.join(choices)}")
        return value

    @staticmethod
    def _words(key: str, value: object, source: str) -> tuple[str, ...]:
        if not isinstance(value, list) or not all(isinstance(word, str) for word in value):
            raise ConfigError(source, f"[acp] {key} must be a list of strings")
        return tuple(value)

    def _reject_words(self, key: str, value: object, source: str) -> tuple[str, ...]:
        words = tuple(word.strip().lower() for word in self._words(key, value, source))
        if not all(words):
            raise ConfigError(source, f"[acp] {key} must not contain an empty word")
        return words

    def _subset(
        self, key: str, value: object, known: tuple[str, ...], source: str
    ) -> tuple[str, ...]:
        items = self._words(key, value, source)
        outside = [item for item in items if item not in known]
        if outside or len(set(items)) != len(items):
            raise ConfigError(
                source, f"[acp] {key} must list each of {', '.join(known)} at most once"
            )
        if key == "modes" and not items:
            raise ConfigError(source, f"[acp] {key} must not be empty")
        return items


ACP_SETTINGS: Final = AcpSettingsLoader()
"""The loader `vibey serve` reads `[acp] sessions_max` and `session_events_max` with."""
