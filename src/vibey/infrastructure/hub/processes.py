# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The operating-system calls `vibey hub start | stop | status` make (#1186).

Behind one class so the commands are tested without starting or signalling a real
process. A signal is only ever sent to a process id the hub itself recorded in its
owner-only state directory, and `terminate` is SIGTERM: the hub stops cleanly and clears
its own record. Nothing here sends SIGKILL.

Declared by `interfaces/processes_interface.py` (ADR-0016).
"""

import os
import signal
import subprocess  # nosec B404 - fixed argv, shell disabled
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from vibey.infrastructure.hub.interfaces.processes_interface import HubProcessesInterface


class HubProcesses:
    """Starting, probing and stopping the hub process."""

    def alive(self, pid: int) -> bool:
        """Whether a process with this id exists. A process owned by another account is
        alive but not ours to signal, so it reads as alive."""
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def terminate(self, pid: int) -> bool:
        """Asks the process to stop (SIGTERM). False when it is already gone."""
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            return False
        return True

    def spawn(self, argv: Sequence[str], log: Path) -> int:
        """Starts `argv` detached from this terminal and session, its output appended to
        `log`, and returns its process id. Closing the program that started it, or its
        terminal, does not stop it."""
        log.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with open(log, "ab") as out:  # noqa: PTH123 - the descriptor is handed to the child
            process = subprocess.Popen(  # nosec B603 - fixed argv, shell disabled
                list(argv),
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=out,
                start_new_session=True,
                close_fds=True,
            )
        return process.pid


HUB_PROCESSES: Final[HubProcessesInterface] = HubProcesses()
"""The process calls the hub commands make. Annotated with the interface so `mypy --strict`
checks the class against its declared seam."""
