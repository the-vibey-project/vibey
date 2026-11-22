# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one runner `vibey acp` asks the user's service manager through (ADR-0101).

It runs exactly the commands vibey's loader issues, matched argv for argv, and nothing else:

- `launchctl print gui/<uid>` and `launchctl print gui/<uid>/<label>`
- `launchctl bootstrap gui/<uid> <absolute .plist>`
- `launchctl kickstart -k gui/<uid>/<label>` and `launchctl bootout gui/<uid>/<label>`
- `systemctl --user is-system-running`, `systemctl --user daemon-reload`
- `systemctl --user is-active|restart|stop <label>.service`
- `systemctl --user enable|disable --now <label>.service`

`<uid>` is this user's own, and `<label>` is held to the closed alphabet `LABEL` (no leading
`-`, no `/`, no space), so no other flag (`--system`, `--global`, `-H`, `-M`, `--root`), no other
domain (`system`, `user/`, `pid/`, another uid's `gui/`), no other verb (`asuser`, `submit`), no
`sudo` and no shell can be spelled through it. A refusal raises `PermissionError` before anything
runs. The binary is looked up on a fixed system PATH, never the editor's; the child gets stdin
closed, a minimal environment (the user's identity, locale, and the runtime directory and bus
address `systemctl --user` finds the user manager by -- never a token or a database URL), and a
bound on its time, past which it is a `TimeoutError` -- an unknown answer, never "not loaded".
Its output is cut to `OUTPUT_LIMIT`.

Declared by `interfaces/service_manager_runner_interface.py`.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 -- a fixed argv checked below, never a shell
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Final

from vibey.domain.supervisor import LABEL

SYSTEM_PATH: Final = "/usr/bin:/bin:/usr/sbin:/sbin"
"""Where `launchctl` and `systemctl` are looked for: the system's own folders only."""
OUTPUT_LIMIT: Final = 65_536
"""The most of a command's output kept (`launchctl print` of one label is a few KiB)."""
_CONTROL: Final = frozenset(chr(code) for code in (*range(0x20), 0x7F))
_KEPT: Final = (
    "HOME",
    "USER",
    "LOGNAME",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TMPDIR",
    "XDG_RUNTIME_DIR",
    "DBUS_SESSION_BUS_ADDRESS",
)


class ServiceManagerRunner:
    """Declared by `ServiceManagerRunnerInterface`. `run`, `which` and `environ` are seams."""

    def __init__(
        self,
        *,
        timeout_seconds: float,
        uid: int,
        run: Callable[..., Any] = subprocess.run,
        which: Callable[[str, str], str | None] = lambda name, path: shutil.which(name, path=path),
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self._timeout = timeout_seconds
        self._uid = uid
        self._run = run
        self._which = which
        self._environ = os.environ if environ is None else environ

    def __call__(self, argv: Sequence[str]) -> tuple[int, str]:
        refusal = self.refusal(argv, self._uid)
        if refusal:
            raise PermissionError(f"refused: {refusal}")
        binary = self._which(argv[0], SYSTEM_PATH)
        if binary is None:
            raise FileNotFoundError(2, f"{argv[0]} is not on {SYSTEM_PATH}")
        environment = {key: self._environ[key] for key in _KEPT if key in self._environ}
        environment["PATH"] = SYSTEM_PATH
        try:
            done = self._run(  # nosec B603 -- fixed, checked argv; an absolute binary; no shell
                [binary, *argv[1:]],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                errors="replace",
                env=environment,
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(
                f"{argv[0]} {argv[1]} gave no answer within {self._timeout:g} s"
            ) from exc
        return int(done.returncode), str(done.stdout or "")[:OUTPUT_LIMIT]

    @classmethod
    def refusal(cls, argv: Sequence[str], uid: int) -> str:
        """Why `argv` is not one of the commands vibey issues in user `uid`'s own domain; ""
        when it is one, argv for argv."""
        shape = tuple(argv)
        if not shape:
            return "an empty command"
        if shape[0] == "launchctl":
            return (
                ""
                if cls._launchctl(shape, f"gui/{uid}")
                else "not a launchctl command vibey issues"
            )
        if shape[0] == "systemctl":
            return "" if cls._systemctl(shape) else "not a systemctl --user command vibey issues"
        return f"{shape[0]} is not launchctl or systemctl"

    @classmethod
    def _launchctl(cls, shape: tuple[str, ...], gui: str) -> bool:
        match shape:
            case ("launchctl", "print", target):
                return target == gui or cls._labelled(target, gui)
            case ("launchctl", "bootstrap", domain, plist):
                return domain == gui and cls._plist(plist)
            case ("launchctl", "kickstart", "-k", target) | ("launchctl", "bootout", target):
                return cls._labelled(target, gui)
        return False

    @classmethod
    def _systemctl(cls, shape: tuple[str, ...]) -> bool:
        match shape:
            case ("systemctl", "--user", "is-system-running" | "daemon-reload"):
                return True
            case ("systemctl", "--user", "is-active" | "restart" | "stop", unit):
                return cls._unit(unit)
            case ("systemctl", "--user", "enable" | "disable", "--now", unit):
                return cls._unit(unit)
        return False

    @staticmethod
    def _labelled(target: str, gui: str) -> bool:
        return target.startswith(gui + "/") and LABEL.fullmatch(target[len(gui) + 1 :]) is not None

    @staticmethod
    def _unit(unit: str) -> bool:
        return (
            unit.endswith(".service") and LABEL.fullmatch(unit.removesuffix(".service")) is not None
        )

    @staticmethod
    def _plist(path: str) -> bool:
        return os.path.isabs(path) and path.endswith(".plist") and not _CONTROL.intersection(path)
