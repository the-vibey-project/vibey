# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one runner `vibey acp` asks the user's service manager through (ADR-0101).

It runs `launchctl` or `systemctl --user`, with only the verbs vibey's loader uses, and nothing
else: an argv naming `sudo`, a shell, a `systemctl` without `--user`, the `system` launchd
domain, or any other verb (`launchctl asuser` or `submit`, which run a command; `bootout`,
`stop`, which vibey never issues) is refused before anything runs.
The binary is looked up on a fixed system PATH, never the editor's; the child gets stdin closed,
a minimal environment (the user's identity, locale, and the runtime directory and bus address
`systemctl --user` finds the user manager by -- never a token or a database URL), and a bound
on its time. Its output is cut to `OUTPUT_LIMIT`.

Declared by `interfaces/service_manager_runner_interface.py`.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 -- a fixed argv checked below, never a shell
from collections.abc import Callable, Mapping, Sequence
from typing import Any, Final

SYSTEM_PATH: Final = "/usr/bin:/bin:/usr/sbin:/sbin"
"""Where `launchctl` and `systemctl` are looked for: the system's own folders only."""
OUTPUT_LIMIT: Final = 65_536
"""The most of a command's output kept (`launchctl print` of one label is a few KiB)."""
LAUNCHCTL_VERBS: Final = frozenset({"print", "bootstrap", "kickstart"})
"""What vibey asks launchd: read a domain or label, load a unit, restart a label."""
SYSTEMCTL_VERBS: Final = frozenset(
    {"is-system-running", "is-active", "daemon-reload", "enable", "restart"}
)
"""What vibey asks `systemctl --user`: read the manager or a unit, load, restart."""
TIMED_OUT: Final = 124
REFUSED: Final = 126
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
        run: Callable[..., Any] = subprocess.run,
        which: Callable[[str, str], str | None] = lambda name, path: shutil.which(name, path=path),
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self._timeout = timeout_seconds
        self._run = run
        self._which = which
        self._environ = os.environ if environ is None else environ

    def __call__(self, argv: Sequence[str]) -> tuple[int, str]:
        refusal = self.refusal(argv)
        if refusal:
            return REFUSED, f"refused: {refusal}"
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
        except subprocess.TimeoutExpired:
            return TIMED_OUT, ""
        return int(done.returncode), str(done.stdout or "")[:OUTPUT_LIMIT]

    @staticmethod
    def refusal(argv: Sequence[str]) -> str:
        """Why `argv` is not a user-scoped service-manager command; "" when it is."""
        if not argv:
            return "an empty command"
        if "sudo" in argv:
            return "vibey never runs sudo here"
        if argv[0] == "systemctl":
            if len(argv) < 3 or argv[1] != "--user":
                return "systemctl without --user"
            return "" if argv[2] in SYSTEMCTL_VERBS else f"systemctl --user {argv[2]}"
        if argv[0] == "launchctl":
            if any(part == "system" or part.startswith("system/") for part in argv):
                return "the system launchd domain"
            verb = argv[1] if len(argv) > 1 else ""
            return "" if verb in LAUNCHCTL_VERBS else f"launchctl {verb}".rstrip()
        return f"{argv[0]} is not launchctl or systemctl"
