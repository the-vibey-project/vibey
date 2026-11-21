# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""How `vibey acp` runs `PostgresLocalService`'s package commands (SP-ACP).

The agent's stdin and stdout are the editor's protocol streams, and no one sits at a terminal
to answer a prompt. So each command runs with stdin closed (`DEVNULL`: a child that reads gets
end of file, never protocol bytes), its stdout and stderr captured (never printed), within a
bound on its time, and from a fixed argv with no shell. A `sudo` is made non-interactive
(`sudo -n`): it fails at once where it would have asked for a password, and vibey never feeds
one. The argv itself is `PostgresLocalService`'s own -- no text from the hub, the ledger or
the client ever reaches a command line.

Declared by `interfaces/acp_command_runner_interface.py`.
"""

from __future__ import annotations

import subprocess  # nosec B404 - fixed argv from PostgresLocalService, never shell=True
from typing import Final

from vibey.infrastructure.postgres import PostgresCommandResult

SUDO_PASSWORD_REFUSALS: Final = ("a password is required", "a terminal is required")
"""What `sudo -n` says when it would have asked for a password."""
TIMED_OUT: Final = 124
"""The return code of a command that overran its bound, as `timeout(1)` reports one."""


class AcpCommandRunner:
    """Declared by `interfaces/acp_command_runner_interface.py::AcpCommandRunnerInterface`."""

    def __init__(self, *, timeout_seconds: float) -> None:
        self._timeout = timeout_seconds

    def __call__(self, argv: tuple[str, ...]) -> PostgresCommandResult:
        if argv[:1] == ("sudo",) and argv[1:2] != ("-n",):
            argv = ("sudo", "-n", *argv[1:])
        try:
            completed = subprocess.run(  # noqa: S603  # nosec B603 - fixed argv, no shell
                argv,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return PostgresCommandResult(
                returncode=TIMED_OUT, stderr=f"{argv[0]} did not finish within {self._timeout} s"
            )
        except OSError as exc:
            return PostgresCommandResult(returncode=1, stderr=str(exc))
        return PostgresCommandResult(
            returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr
        )

    @staticmethod
    def password_refused(argv: tuple[str, ...], result: PostgresCommandResult) -> bool:
        if argv[:1] != ("sudo",) or result.returncode == 0:
            return False
        said = result.stderr.lower()
        return any(refusal in said for refusal in SUDO_PASSWORD_REFUSALS)
