# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Starting a `vibey worker` that keeps running after the command that started it exits.

`vibey retry --start-worker` used to be a shell script: `nohup vibey worker ... >> log &`. The
process is its own session leader (so closing the terminal does not signal it), reads nothing from
the terminal, and writes to a log the operator can tail. The command line is `vibey worker ...`,
which is exactly what `vibey recover --stop-workers` looks for, so the next restart stops it.
"""

import os
import shutil
import subprocess  # nosec B404 - fixed argv, never shell=True
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Final
from uuid import UUID

_LOG_ID_CHARS: Final[int] = 8


def default_executable() -> str:
    """The `vibey` this command is running as: the one on PATH, else the one that was started."""
    return shutil.which("vibey") or sys.argv[0]


def default_log(project_id: UUID, *, environ: dict[str, str] | None = None) -> Path:
    """`$XDG_STATE_HOME/vibey/worker-<project>.log`, else under `~/.local/state`."""
    env = os.environ if environ is None else environ
    state = env.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(state) / "vibey" / f"worker-{str(project_id)[:_LOG_ID_CHARS]}.log"


class WorkerLauncher:
    """Starts `vibey ARGS...` detached, its output appended to a log."""

    def __init__(
        self,
        *,
        executable: str,
        popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
    ) -> None:
        self._executable = executable
        self._popen = popen

    def start(self, args: Sequence[str], *, log: Path) -> int:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("ab") as handle:
            process = self._popen(
                [self._executable, *args],
                stdin=subprocess.DEVNULL,
                stdout=handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                close_fds=True,
            )
        return process.pid
