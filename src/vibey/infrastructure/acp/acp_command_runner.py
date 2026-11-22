# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""How `vibey acp` runs `PostgresLocalService`'s package commands (SP-ACP).

The agent's stdin and stdout are the editor's protocol streams, and no one sits at a terminal
to answer a prompt. So each command:

- **runs from a fixed argv, with no shell.** The argv is `PostgresLocalService`'s own -- no text
  from the hub, the ledger or the client ever reaches a command line. `sudo` and the command
  are resolved to absolute paths once, against the PATH this process started with.
- **never prompts.** A `sudo` becomes `sudo -n`: it fails at once where it would have asked for
  a password, and vibey never feeds one. stdin is closed (`DEVNULL`), so a child that reads gets
  end of file, never protocol bytes.
- **sees a minimal environment**: a fixed PATH and the locale and home variables, never
  `VIBEY_PG_URL`, a token or an API key this process holds.
- **is captured, never printed**: stdout and stderr are read through pipes the runner keeps
  open for as long as the command lives, so a package manager never meets a closed pipe
  (SIGPIPE) mid-transaction.
- **is bounded, and stopped as a whole.** It runs in a session and process group of its own;
  past its bound the whole group gets SIGTERM, then, after a grace, SIGKILL, so the helpers it
  started (curl, dpkg, a brew Ruby) stop with it. A group this process may not signal (a `sudo`
  run as root) or that does not end within the graces is not waited for: a daemon thread keeps
  draining its output and reaps it, and the result says it may still be running
  (`STILL_RUNNING`), never that it failed.

A command that cannot start, overruns, or may still be running is a result, never an exception.

Declared by `interfaces/acp_command_runner_interface.py`.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess  # nosec B404 - fixed argv from PostgresLocalService, never shell=True
import threading
from collections.abc import Callable, Mapping
from pathlib import PurePath
from typing import Final

from vibey.infrastructure.postgres import PostgresCommandResult

SUDO_PASSWORD_REFUSALS: Final = ("a password is required", "a terminal is required")
"""What `sudo -n` says when it would have asked for a password."""
TIMED_OUT: Final = 124
"""The return code of a command that overran its bound and was stopped, as `timeout(1)`."""
STILL_RUNNING: Final = 125
"""The return code of a command that overran its bound and could not be confirmed stopped."""
SAFE_PATH: Final = (
    "/opt/homebrew/bin",
    "/usr/local/bin",
    "/usr/bin",
    "/bin",
    "/usr/sbin",
    "/sbin",
)
"""The PATH the commands see, before the folders of the executables resolved for them."""
KEPT_VARIABLES: Final = ("HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR")
"""The only variables of this process's environment the commands see."""

type Popen = Callable[..., subprocess.Popen[str]]
type KillGroup = Callable[[int, int], None]
type Which = Callable[..., str | None]


class AcpCommandRunner:
    """Declared by `interfaces/acp_command_runner_interface.py::AcpCommandRunnerInterface`."""

    def __init__(
        self,
        *,
        timeout_seconds: float,
        stop_grace_seconds: float = 10.0,
        environ: Mapping[str, str] = os.environ,
        which: Which = shutil.which,
        popen: Popen = subprocess.Popen,
        kill_group: KillGroup = os.killpg,
    ) -> None:
        self._timeout = timeout_seconds
        self._grace = stop_grace_seconds
        self._search_path = environ.get("PATH", os.defpath)
        self._which = which
        self._popen = popen
        self._kill_group = kill_group
        self._kept = {key: environ[key] for key in KEPT_VARIABLES if key in environ}
        self._resolved: dict[str, str] = {}
        self._lock = threading.Lock()

    def __call__(self, argv: tuple[str, ...]) -> PostgresCommandResult:
        argv = self._absolute(argv)
        try:
            process = self._popen(  # noqa: S603  # nosec B603 - fixed argv, no shell
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self._environment(argv),
                start_new_session=True,
            )
        except OSError as exc:
            return PostgresCommandResult(returncode=1, stderr=str(exc))
        try:
            stdout, stderr = process.communicate(timeout=self._timeout)
        except subprocess.TimeoutExpired:
            return self._stop(process, argv)
        return PostgresCommandResult(returncode=process.returncode, stdout=stdout, stderr=stderr)

    @staticmethod
    def password_refused(argv: tuple[str, ...], result: PostgresCommandResult) -> bool:
        if not argv or PurePath(argv[0]).name != "sudo" or result.returncode == 0:
            return False
        said = result.stderr.lower()
        return any(refusal in said for refusal in SUDO_PASSWORD_REFUSALS)

    @staticmethod
    def still_running(result: PostgresCommandResult) -> bool:
        return result.returncode == STILL_RUNNING

    def _stop(self, process: subprocess.Popen[str], argv: tuple[str, ...]) -> PostgresCommandResult:
        name = PurePath(argv[0]).name
        for stop in (signal.SIGTERM, signal.SIGKILL):
            try:
                self._kill_group(process.pid, stop)
            except ProcessLookupError:
                pass  # the group is gone already; reading to the end reaps the leader
            except PermissionError:
                break  # a group run as root: this process may not stop it
            try:
                stdout, stderr = process.communicate(timeout=self._grace)
            except subprocess.TimeoutExpired:
                continue
            said = f"{name} did not finish within {self._timeout:g} s and was stopped"
            return PostgresCommandResult(TIMED_OUT, stdout, f"{stderr}\n{said}".lstrip("\n"))
        # Not confirmed stopped: never wait on it here, and never close its pipes while it may
        # still write to them. A daemon thread drains them to the end and reaps it.
        threading.Thread(
            target=process.communicate, name="vibey-install-drain", daemon=True
        ).start()
        return PostgresCommandResult(
            returncode=STILL_RUNNING,
            stderr=(
                f"{name} did not finish within {self._timeout:g} s and could not be stopped; "
                "it may still be running"
            ),
        )

    def _absolute(self, argv: tuple[str, ...]) -> tuple[str, ...]:
        if argv[:1] == ("sudo",):
            rest = argv[1:] if argv[1:2] == ("-n",) else ("-n", *argv[1:])
            command = (self._resolve(rest[1]), *rest[2:]) if len(rest) > 1 else ()
            return (self._resolve("sudo"), "-n", *command)
        return (self._resolve(argv[0]), *argv[1:])

    def _resolve(self, name: str) -> str:
        if PurePath(name).is_absolute():
            return name
        with self._lock:
            if name not in self._resolved:
                self._resolved[name] = self._which(name, path=self._search_path) or name
            return self._resolved[name]

    def _environment(self, argv: tuple[str, ...]) -> dict[str, str]:
        folders = [str(PurePath(part).parent) for part in argv[:3] if PurePath(part).is_absolute()]
        path = dict.fromkeys([*SAFE_PATH, *folders])
        return {**self._kept, "PATH": os.pathsep.join(path)}
