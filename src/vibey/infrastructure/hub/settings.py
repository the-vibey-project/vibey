# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[hub]` in vibey.toml: whether the hub may leave the loopback interface, and how.

Every key is optional and the defaults are the closed ones (ADR-0067, 12.c):

```toml
[hub]
lan = false           # true declares that the hub may listen on a LAN address
port = 8765           # the port `vibey serve` listens on
names = []            # extra Host names a request may use, e.g. "studio.local"
state_dir = ""        # where the hub keeps its token and runtime file; "" = the default
lane_roots = []       # where to look for lanes; [] = the directory `vibey serve` runs in
```

A missing file or table declares nothing, so the hub stays on loopback. A table that is
there and malformed raises `ConfigError`: a declaration that cannot be read is not the
same fact as no declaration (10.f), and an unknown key is refused rather than ignored, so
a misspelt `lan` never silently means "not declared".
"""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

from platformdirs import user_state_dir

from vibey.domain.config import ConfigError, parse_toml_string

DEFAULT_PORT: Final = 8765
"""The port `vibey serve` listens on when `[hub] port` is not set."""

KEYS: Final = frozenset({"lan", "port", "names", "state_dir", "lane_roots"})
"""Every key `[hub]` may carry."""


@dataclass(frozen=True, slots=True)
class HubSettings:
    """`[hub]`, read and checked."""

    lan: bool = False
    port: int = DEFAULT_PORT
    names: frozenset[str] = field(default_factory=frozenset)
    state_dir: Path = field(default_factory=lambda: Path(user_state_dir("vibey")) / "hub")
    lane_roots: tuple[Path, ...] = ()


class HubSettingsLoader:
    """Reads `[hub]` from a vibey.toml, and only `[hub]`.

    Declared by `interfaces/settings_interface.py::HubSettingsLoaderInterface`."""

    def load(self, path: Path) -> HubSettings:
        try:
            text = path.read_text()
        except FileNotFoundError:
            return HubSettings()
        except (OSError, UnicodeDecodeError) as exc:
            raise ConfigError(str(path), f"cannot be read: {exc}") from exc
        try:
            data = parse_toml_string(text)
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(str(path), f"is not valid TOML: {exc}") from exc
        table = data.get("hub", {})
        if not isinstance(table, dict):
            raise ConfigError("hub", "must be a table")
        return self.from_table(table)

    def from_table(self, table: dict[str, Any]) -> HubSettings:
        unknown = sorted(set(table) - KEYS)
        if unknown:
            raise ConfigError("hub", f"unknown key(s) {', '.join(unknown)}")
        lan = table.get("lan", False)
        if not isinstance(lan, bool):
            raise ConfigError("hub.lan", "must be true or false")
        port = table.get("port", DEFAULT_PORT)
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise ConfigError("hub.port", "must be a port number from 1 to 65535")
        names = table.get("names", [])
        if not isinstance(names, list) or not all(
            isinstance(name, str) and name.strip() for name in names
        ):
            raise ConfigError("hub.names", "must be a list of host names")
        state_dir = table.get("state_dir", "")
        if not isinstance(state_dir, str):
            raise ConfigError("hub.state_dir", "must be a path")
        lane_roots = table.get("lane_roots", [])
        if not isinstance(lane_roots, list) or not all(
            isinstance(root, str) and root.strip() for root in lane_roots
        ):
            raise ConfigError("hub.lane_roots", "must be a list of directories")
        defaults = HubSettings()
        return HubSettings(
            lan=lan,
            port=port,
            names=frozenset(name.strip().lower() for name in names),
            state_dir=Path(state_dir).expanduser() if state_dir else defaults.state_dir,
            lane_roots=tuple(Path(root).expanduser() for root in lane_roots),
        )


HUB_SETTINGS: Final = HubSettingsLoader()
"""The loader `vibey serve` and `vibey doctor` read `[hub]` through."""
