# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The declared supervisor's host half (#1189): `[supervisor]` read from `vibey.toml`,
the platform's default places, and the service manager asked what it runs.

Reading is all this does to the service manager. Loading or unloading a unit is the
operator's own `launchctl` / `systemctl --user` command, which `vibey supervisor
install` prints (as `vibey driver timer` does, ADR-0070).
"""

import shlex
import tomllib
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Final

from vibey_gh.heartbeat_timer import HeartbeatTimer

from vibey.domain.supervisor import SupervisorSettings

LAUNCHD: Final = "launchd"
SYSTEMD: Final = "systemd"
PLATFORMS: Final = (LAUNCHD, SYSTEMD)

ServiceRunner = Callable[[Sequence[str]], tuple[int, str]]
"""Runs a service-manager command: (exit code, stdout). Never a shell."""

_STRINGS: Final = ("log_dir", "env_file", "vibey", "python", "label_prefix")
_INTEGERS: Final = ("delivery_interval_seconds", "restart_seconds")
_BOOLEANS: Final = ("delivery", "required")
_ARGV: Final = ("worker_args", "delivery_args")
_KNOWN: Final = frozenset({*_STRINGS, *_INTEGERS, *_BOOLEANS, *_ARGV})


class SupervisorSettingsLoader:
    """Declared by `interfaces/supervisor_interface.py`.

    Every key is optional and each one's default is `SupervisorSettings`'s. An unknown
    key or a value of the wrong type is refused by name rather than ignored, so a typo
    never silently reverts a setting to its default."""

    def load(self, path: Path) -> SupervisorSettings:
        if not path.exists():
            return SupervisorSettings()
        with path.open("rb") as handle:
            section = tomllib.load(handle).get("supervisor", {})
        if not isinstance(section, Mapping):
            raise ValueError("[supervisor] must be a table")
        return self.from_mapping(section)

    def from_mapping(self, section: Mapping[str, object]) -> SupervisorSettings:
        unknown = sorted(set(section) - _KNOWN)
        if unknown:
            raise ValueError(f"[supervisor] has unknown keys: {', '.join(unknown)}")
        kwargs: dict[str, object] = {}
        for key in _STRINGS:
            if key in section:
                kwargs[key] = self._typed(section, key, str)
        for key in _INTEGERS:
            if key in section:
                kwargs[key] = self._typed(section, key, int)
        for key in _BOOLEANS:
            if key in section:
                kwargs[key] = self._typed(section, key, bool)
        for key in _ARGV:
            if key in section:
                value = section[key]
                if not isinstance(value, list) or not all(isinstance(p, str) for p in value):
                    raise ValueError(f"[supervisor] {key} must be a list of strings")
                kwargs[key] = tuple(value)
        return SupervisorSettings(**kwargs)  # type: ignore[arg-type]

    @staticmethod
    def _typed(section: Mapping[str, object], key: str, kind: type) -> object:
        value = section[key]
        # bool is an int subclass; an integer key never accepts true/false.
        if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
            raise ValueError(f"[supervisor] {key} must be a {kind.__name__}")
        return value


class SupervisorHost:
    """Declared by `interfaces/supervisor_interface.py`. One platform's places, and its
    service manager's answer about one unit."""

    def __init__(
        self,
        platform: str,
        *,
        home: Path,
        environ: Mapping[str, str],
        uid: int,
        run: ServiceRunner,
        temp_roots: Callable[[], tuple[Path, ...]] = HeartbeatTimer.temp_roots,
    ) -> None:
        if platform not in PLATFORMS:
            raise ValueError(f"unknown platform {platform!r}: use launchd or systemd")
        self.platform = platform
        self._home = home
        self._environ = environ
        self._uid = uid
        self._run = run
        self._temp_roots = temp_roots

    # --- where things live ------------------------------------------------------------

    def unit_dir(self) -> Path:
        if self.platform == LAUNCHD:
            return self._home / "Library" / "LaunchAgents"
        return self._xdg("XDG_CONFIG_HOME", ".config") / "systemd" / "user"

    def unit_path(self, label: str, out: Path | None = None) -> Path:
        suffix = ".plist" if self.platform == LAUNCHD else ".service"
        return (out or self.unit_dir()) / f"{label}{suffix}"

    def default_log_dir(self) -> Path:
        if self.platform == LAUNCHD:
            return self._home / "Library" / "Logs" / "vibey"
        return self._xdg("XDG_STATE_HOME", ".local/state") / "vibey" / "logs"

    def default_env_file(self) -> Path:
        if self.platform == LAUNCHD:
            return self._home / "Library" / "Application Support" / "vibey" / "supervisor.env"
        return self._xdg("XDG_CONFIG_HOME", ".config") / "vibey" / "supervisor.env"

    def volatile_roots(self) -> tuple[str, ...]:
        """Directories a reboot or the system empties -- vibey-gh's own list, so the
        heartbeat and the supervisor refuse the same places (10.h)."""
        return tuple(str(root) for root in self._temp_roots())

    # --- the service manager ------------------------------------------------------------

    def state(self, label: str) -> str:
        """`running`, `stopped` (loaded, no process), `not loaded`, or `unknown: ...`
        when the service manager could not be asked. Never a guess (10.f)."""
        try:
            if self.platform == LAUNCHD:
                code, out = self._run(("launchctl", "print", f"gui/{self._uid}/{label}"))
                if code != 0:
                    return "not loaded"
                return "running" if "state = running" in out else "stopped"
            code, out = self._run(("systemctl", "--user", "is-active", f"{label}.service"))
        except OSError as exc:
            return f"unknown: {exc}"
        answer = out.strip()
        if answer == "active":
            return "running"
        return "not loaded" if answer in ("inactive", "unknown", "") else f"stopped ({answer})"

    def load_commands(self, labels: Sequence[str], units: Sequence[Path]) -> list[str]:
        """What the operator runs to load the units just written, and to restart one."""
        if self.platform == LAUNCHD:
            domain = f"gui/{self._uid}"
            lines = [
                f"launchctl bootout {domain}/{label} 2>/dev/null; "
                f"launchctl bootstrap {domain} {shlex.quote(str(unit))}"
                for label, unit in zip(labels, units, strict=True)
            ]
            return [*lines, f"restart one with: launchctl kickstart -k {domain}/<label>"]
        services = " ".join(f"{label}.service" for label in labels)
        return [
            "systemctl --user daemon-reload",
            f"systemctl --user enable --now {services}",
            'loginctl enable-linger "$USER"  # keep them running with nobody logged in',
        ]

    def _xdg(self, key: str, fallback: str) -> Path:
        value = self._environ.get(key, "")
        return Path(value) if value.startswith("/") else self._home / fallback
